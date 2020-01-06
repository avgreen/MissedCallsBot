#!/usr/bin/python36
# -*- coding: utf-8 -*-
import cherrypy
import config
import sys
#import subprocess
import logging
import argparse
from ClinicaWeb import ClinicaWebAPI as cwAPI
from MissedCallsBot import WebhookServer as webHook
import IncomingCalls
import users

try:
    import telebot
#    from telebot import types
except:
    print('You need to install pytelegrambotapi (pip install pytelegrambotapi) first!')
    exit()


def main():
    config.Users = users.Users()
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(add_help=True)
        parser.add_argument("-i", "--intPhone", help="internal phone number")
        parser.add_argument("-e", "--extPhone", help="external phone number")
        parser.add_argument("-n", "--extName", help="external phone name")
        parser.add_argument("-m", "--message", help="head of message")
        args = parser.parse_args()
        if args.intPhone and args.extPhone:
            iCalls = IncomingCalls.IncomingCalls()
            iCalls.send_message(args.intPhone, args.extPhone, args.extName, args.message if args.message else '')
        #print(args)
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

        logger = logging.getLogger("bot")
        logger.setLevel(logging.INFO)
        # create the logging file handler
        fh = logging.FileHandler(config.logfile)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        # add handler to logger object
        logger.addHandler(fh)
        
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

