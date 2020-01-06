# -*- coding: utf-8 -*-
import config
import logging
import telebot
from telebot import types

class IncomingCalls(object):
    try:
        import pymysql
        from pymysql.cursors import DictCursor
    except:
        print('You need to install PyMySQL (pip install PyMySQL) first!')
        exit()
    from contextlib import closing
    from time import strftime as ftime, time
    import unicodeEmoji as emo
    disposMark = {
        'BU': emo.MULTIPLICATION,
        'AN': emo.CHECKMARK,
        'NO': emo.MINUS,
    }
    import sqlite3
 

    def __init__(self):
        self.bot = telebot.TeleBot(config.token)
        self.conn = self.sqlite3.connect(config.CallsDB)
        self.conn.row_factory = self.sqlite3.Row
        self.cursor = self.conn.cursor()
        self.cursor.execute("CREATE TABLE if not exists calls (timeStamp real, chatID integer, extPhone text, msgID integer)")

    def getCallHistory(self, phoneNumber):
        strHistory = f"{self.emo.NEW_BUTTON}<b>Новый контакт</b>\n"
        with self.closing(self.pymysql.connect(**{**config.CdrDB, 'charset': 'utf8mb4', 'cursorclass': self.DictCursor})) as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"""SELECT
                     CASE WHEN RIGHT(src,10) = RIGHT("{phoneNumber}",10)  THEN "IN" ELSE "OUT" END as direct,
                     DATE_FORMAT(calldate, "%d/%m/%Y-%H:%i") as calldate,
                     TIME_FORMAT(SEC_TO_TIME(billsec),"%i:%s") as calltime,
                     LEFT(disposition,2) as disposition,
                     CASE WHEN RIGHT(src,10) = RIGHT("{phoneNumber}",10)  THEN concat('<b>',dst,'</b>') ELSE concat('<b>',src,'</b>') END as abon,
                     DATE_FORMAT(calldate, "%y/%m/%d=%H:%i:%s") as cd
                     FROM asteriskcdrdb.cdr as cdr
                     LEFT JOIN asterisk.users as users on CASE WHEN length(cdr.src) < 4 THEN cdr.src ELSE cdr.dst END  = users.extension
                     WHERE (RIGHT(src,10) = RIGHT("{phoneNumber}",10) and length(cdr.dst) = 3 OR RIGHT(dst,10) = RIGHT("{phoneNumber}",10) and length(cdr.src) = 3)
                       AND (disposition='ANSWERED' AND billsec > 4 OR RIGHT(dst,10) = RIGHT("{phoneNumber}",10))
                       AND NOT cdr.lastapp = "Queue"
                     order by cdr.calldate desc
                     limit 15""")
                if cursor.rowcount > 0:
                    strHistory = f"{self.emo.OPEN_BOOK}история звонков ({self.emo.BLACK_SMALL_SQUARE}вх. {self.emo.WHITE_SMALL_SQUARE}исх.)\n"
                    for row in cursor:
                        direct = self.emo.BLACK_SMALL_SQUARE if row['direct'] == 'IN' else self.emo.WHITE_SMALL_SQUARE
                        strHistory += f"{direct} {row['calldate']} {row['calltime']} {self.disposMark[row['disposition']]} {row['abon']}\n"
        return strHistory

    def delete_message(self, chat_id, message_id = 0,  extPhone = ''):
        if message_id == 0:
            self.cursor.execute("SELECT * from calls WHERE chatID = ? and extPhone = ?", (chat_id, extPhone))
            for row in self.cursor.fetchall():
                self.delete_message(chat_id, message_id = row['msgID'])
        else:
            self.cursor.execute("DELETE FROM calls WHERE chatID = ? and msgID = ?", (chat_id, message_id))
            self.bot.delete_message(chat_id=chat_id, message_id=message_id)
            self.conn.commit()
            print("delete messge id = %s" % (message_id))

    def send_message(self, intPhone, extPhone, extName, head_message = ''):
        vars = {
            'headMessage': head_message,
            'extPhone': extPhone, 
            'extName': extName if extName else extPhone, 
            'dateTime': self.ftime("%H:%M--%d/%m/%Y"),
            'callHistory': self.getCallHistory(extPhone),
        }
        keyboard = types.InlineKeyboardMarkup()
        if len(head_message) > 0:
            callback_button = types.InlineKeyboardButton(text="Перезвонить", callback_data='CallTo'+extPhone)
            keyboard.add(callback_button)
        message = self.bot.send_message(chat_id=config.Users.getChatID(intPhone), text=config.messageTemplate.format(**vars), parse_mode='HTML', reply_markup = keyboard)
        self.delete_message(message.chat.id, extPhone = extPhone)
        self.cursor.execute("INSERT INTO calls VALUES (?,?,?,?)", (self.time(), message.chat.id, extPhone, message.message_id))
        self.conn.commit()
        
