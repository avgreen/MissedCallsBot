# -*- coding: utf-8 -*-
import cherrypy
import config
import subprocess
import logging
import IncomingCalls
#import users

try:
    import telebot
    from telebot import types
except:
    print('You need to install pytelegrambotapi (pip install pytelegrambotapi) first!')
    exit()

bot = telebot.TeleBot(config.token)
logger = logging.getLogger("bot.misscall")

def getCallHistory(phoneNumber):
    UNICODE_EMOJ_REPEAT_BUTTON = '\U0001F501'
    cmd = '/usr/local/bin/1tg.php 1 %s  %s "%s Повторный дозвон"' % (phoneNumber, phoneNumber, UNICODE_EMOJ_REPEAT_BUTTON) 
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return ''.join(map(lambda line: line.decode("utf-8"), p.stdout.readlines()))

# Звонок с ожиданием окончания
class CallWithAwait(object):
    try:
        from asterisk.ami import AMIClient, SimpleAction, EventListener
    except:
        print('You need to install asterisk-ami (pip install asterisk-ami) first!')
        exit()
    from time import sleep, time
    try:
        import pymysql
        from pymysql.cursors import DictCursor
    except:
        print('You need to install PyMySQL (pip install PyMySQL) first!')
        exit()
    import os, sys, re
    from contextlib import closing

    def __init__(self, Extension, phoneNumber, CallerID = 'python', Context = 'from-internal'):
        self.sys.stderr = self.os.devnull
        self.complited = False
        self.phoneNumber = phoneNumber
        self.Extension = Extension
        self.callStatus = False
        self.client = self.AMIClient(**config.AMIClientAddress)
        self.client.login(**config.AMIClientUser)
        self.logger = logging.getLogger("bot.asterisk")
        self.startTime = self.time()
        self.action = self.SimpleAction(
            'Originate',
            Channel='SIP/'+str(Extension),
            Exten=phoneNumber,
            Priority=1,
            Context=Context,
            CallerID=CallerID,
        )
        self.logger.info("Start originate from %s to %s" % (self.Extension, self.phoneNumber))
        if self.client.send_action(self.action).response.status == 'Success':
            self.logger.info("Start call from %s to %s" % (self.Extension, self.phoneNumber))
            self.client.add_event_listener(self.event_Hangup, white_list=['Hangup'], Channel=self.re.compile('^SIP/%s.*'%Extension))
            while not self.complited:
                self.sleep(0.1)
                if (self.time() - self.startTime) > 600: # О чем можно трепаться больше 10 минут - не знаю! :) 
                    self.logger.info("Timeout waiting hangup from %s to %s" % (self.Extension, self.phoneNumber))
                    self.complited = True
                    break
        else:
            self.logger.info("Cancel originate from %s to %s" % (self.Extension, self.phoneNumber))
        self.client.logoff()

    def event_Hangup(self, event, **kwargs):
        self.logger.debug(vars(event))
        if event['ConnectedLineNum'][-10:] == self.phoneNumber[-10:]:
            self.logger.info("Hangup call from %s to %s" % (self.Extension, self.phoneNumber))
            self.sleep(2.0) # подождем пока звонок запишется в базу статистики. Если 2 сек маловато - можно поставить больше. Нам принципе не к спеху - когда сообщение в телеграмме вернутся/удалится
            with self.closing(self.pymysql.connect(**{**config.CdrDB, 'charset': 'utf8mb4', 'cursorclass': self.DictCursor})) as connection:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT billsec, disposition FROM cdr WHERE UniqueId = "%s"' % (event['Uniqueid']))
                    for row in cursor:
                        if row['disposition'] == 'ANSWERED'  and row['billsec'] > 10:
                            self.callStatus = True
            self.complited = True

class WebhookServer(object):
    @cherrypy.expose
    def index(self):
        if 'content-length' in cherrypy.request.headers and \
                        'content-type' in cherrypy.request.headers and \
                        cherrypy.request.headers['content-type'] == 'application/json':
            length = int(cherrypy.request.headers['content-length'])
            json_string = cherrypy.request.body.read(length).decode("utf-8")
            update = telebot.types.Update.de_json(json_string)
            # Эта функция обеспечивает проверку входящего сообщения
            bot.process_new_updates([update])
            return ''
        else:
            raise cherrypy.HTTPError(403)

@bot.message_handler(commands=['id'])
def cmd_ID(message):
    logger.debug(vars(message))
    bot.reply_to(message, "You ID = %s \nChat ID = %s" % (message.from_user.id, message.chat.id))

# Хэндлер на все текстовые сообщения
@bot.message_handler(func=lambda message: True, content_types=['text'])
def echo_message(message):
#    bot.reply_to(message, message.text)
    logger.debug(vars(message))
    keyboard = types.InlineKeyboardMarkup()
    url_button = types.InlineKeyboardButton(text="Перейти на Google", url="https://google.com")
    keyboard.add(url_button)
    bot.send_message(message.chat.id, "Привет! Нажми на кнопку и перейди в поисковик.", reply_markup=keyboard)    

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    # Если сообщение из чата с ботом
    if call.message:
        Extension = config.Users.getExtension(call.from_user.id)
        if Extension:
            callbackData=list(filter(lambda button: button['text'] == 'Перезвонить', call.message.json['reply_markup']['inline_keyboard'][0]))[0]['callback_data']
            iCalls = IncomingCalls.IncomingCalls()
            if call.data == "DeleteYes":
                iCalls.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
                logger.info("Delete message from %s by %s"%(callbackData[6::], Extension))
            elif call.data == "DeleteNo" or call.data == "Delete":
                keyboard = types.InlineKeyboardMarkup()
                callback_button = types.InlineKeyboardButton(text="Перезвонить", callback_data=callbackData)
                if call.data == "Delete":
                    deleteYes_button = types.InlineKeyboardButton(text="Таки удалить!", callback_data="DeleteYes")
                    deleteNo_button = types.InlineKeyboardButton(text="Нет!", callback_data="DeleteNo")
                    keyboard.add(callback_button, deleteYes_button, deleteNo_button)
                else:
                    delete_button = types.InlineKeyboardButton(text="Удалить", callback_data="Delete")
                    keyboard.add(callback_button, delete_button)
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=call.message.text, parse_mode='HTML', reply_markup = keyboard)
            elif call.data[:6:] == "CallTo":
                phoneNumber = call.data[6::]
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=call.message.text, reply_markup='{"inline_keyboard": [[{"text": "В процессе ... (%s)", "callback_data": "-CallTo"}]]}'%(Extension))
                callAwait = CallWithAwait(Extension, phoneNumber)
                if callAwait.callStatus:
                    iCalls.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
                    callAwait.logger.info('Success call to %s from EXT %s. Deleting from history' % (phoneNumber, Extension))
                else: 
                    keyboard = types.InlineKeyboardMarkup()
                    callback_button = types.InlineKeyboardButton(text="Перезвонить", callback_data=call.data)
                    if callAwait.complited: # Если нет - значит звонок отбили еще на этапе Originate ну или Extension того кто нажал перезвон был в данный момент недоступен 
                        delete_button = types.InlineKeyboardButton(text="Удалить", callback_data="Delete")
                        keyboard.add(callback_button, delete_button)
                    else:
                        keyboard.add(callback_button)
                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=getCallHistory(phoneNumber) if callAwait.complited else call.message.text, parse_mode='HTML', reply_markup = keyboard)
                #logger.debug(call.message.json['reply_markup'])
            else:
                 logger.debug("call.data=%s"%call.data)
        else:
            logger.info("Not found Ext for ID="+str(call.from_user.id))
    # Если сообщение из инлайн-режима
    elif call.inline_message_id:
        if call.data == "test":
            bot.edit_message_text(inline_message_id=call.inline_message_id, text="test inline")


