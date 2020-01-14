#!/usr/bin/python36
# -*- coding: utf-8 -*-
import cherrypy
import config
import sys, os, shutil
import logging
import argparse
from ClinicaWeb import ClinicaWebAPI as cwAPI
from MissedCallsBot import WebhookServer as webHook
import IncomingCalls
import users

try:
    import telebot
except:
    print('You need to install pytelegrambotapi (pip install pytelegrambotapi) first!')
    exit()

def sendMessage(args):
    if args.intPhone and args.extPhone:
        iCalls = IncomingCalls.IncomingCalls()
        intPhone = args.intPhone[4::] if args.intPhone[:3:] == 'SIP' else args.intPhone
        iCalls.send_message(intPhone, args.extPhone, args.extName, args.message if args.message else '')
    
def deleteMessage(args):
    if args.intPhone and args.extPhone:
        iCalls = IncomingCalls.IncomingCalls()
        intPhone = args.intPhone[4::] if args.intPhone[:3:] == 'SIP' else args.intPhone
        iCalls.delete_message(intPhone = intPhone, extPhone = args.extPhone)

def parse_args():
    """Настройка argparse"""
    parser = argparse.ArgumentParser(description='Missed calls Telegram bot')
    subparsers = parser.add_subparsers()

    parser_append = subparsers.add_parser('sendMessage', help='Send message to chat')
    parser_append.add_argument("-i", "--intPhone", help="internal phone number", required=True)
    parser_append.add_argument("-e", "--extPhone", help="external phone number")
    parser_append.add_argument("-n", "--extName", help="external phone name")
    parser_append.add_argument("-m", "--message", help="head of message")
    parser_append.set_defaults(func=sendMessage)

    parser_append = subparsers.add_parser('deleteMessage', help='Delete message from chat')
    parser_append.add_argument("-i", "--intPhone", help="internal phone number", required=True)
    parser_append.add_argument("-e", "--extPhone", help="external phone number")
    parser_append.set_defaults(func=deleteMessage)

    return parser.parse_args()

def main():
    config.Users = users.Users()
    logger = logging.getLogger("bot")
    logger.setLevel(logging.INFO)
    # create the logging file handler
    fh = logging.FileHandler(config.logfile)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    # add handler to logger object
    logger.addHandler(fh)
    shutil.chown(config.logfile, user=config.user, group=config.group)
    # create databases and set permission for it 
    if not os.path.exists(os.path.dirname(config.CallsDB)):
        os.makedirs(os.path.dirname(config.CallsDB))
        shutil.chown(os.path.dirname(config.CallsDB), user=config.user, group=config.group)
    if not os.path.exists(config.CallsDB):
        os.mknod(config.CallsDB)
        shutil.chown(config.CallsDB, user=config.user, group=config.group)
    if not os.path.exists(config.UsersDB):
        os.mknod(config.UsersDB)
        shutil.chown(config.UsersDB, user=config.user, group=config.group)

    if len(sys.argv) > 1:
        args = parse_args()
        try:
            args.func(args)
        except Exception as e:
            print(e.message)
        return
    else:
        bot = telebot.TeleBot(config.token)
        # Снимаем вебхук перед повторной установкой (избавляет от некоторых проблем)
        bot.remove_webhook()

        # Если нету корневого сертификата, т.е. у нас самоподписанный сертификат, то в качестве корневого загружаем его
        # При наличии корневого он прописывается в самом WEB сервере чуть ниже
        bot.set_webhook(url=config.WEBHOOK_URL_BASE + config.WEBHOOK_URL_PATH, certificate=open(config.WEBHOOK_SSL_CERT, 'r') if not config.WEBHOOK_SSL_CA  else '')
        # Указываем настройки сервера CherryPy
        cherrypy.config.update({
            'server.socket_host': config.WEBHOOK_LISTEN,
            'server.socket_port': config.WEBHOOK_PORT,
            'server.ssl_module': 'builtin',
            'server.ssl_certificate': config.WEBHOOK_SSL_CERT,
            'server.ssl_private_key': config.WEBHOOK_SSL_PRIV,
            'server.ssl_certificate_chain': config.WEBHOOK_SSL_CA,
        })
        
        logger.info("Program started")    
        # Первое CherryPy приложение будет доступно по URL: "/".
        cherrypy.tree.mount(webHook(), config.WEBHOOK_URL_PATH, {'/': {}})
        # Второе CherryPy приложение будет доступно по URL: "/calls".
        cherrypy.tree.mount(cwAPI(), '/calls', None)
        # Передача управления в CherryPy.
        cherrypy.quickstart()

        logger.info("Done!")
        bot.remove_webhook()

if __name__ == "__main__":
    main()

