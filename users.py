# -*- coding: utf-8 -*-
import config
import logging

class Users(object):

    def __init__(self):
        self.dictExtensions = dict()
        self.dictChatID = {}
        # Читаем соответствие телеграмовских ID и внутренних номеров .... пока в файле пусть будет!
        try:
            with open('/usr/local/bin/1pbx_users.txt', 'r') as file:
                users = file.readlines()
        except:
            print('Error open file /usr/local/bin/1pbx_users.txt')
            sys.exit(1)

        for user in users:
            if user[:1:] != "#":
                user_data = user.rstrip().split(';')
                self.dictExtensions[int(user_data[1])] = user_data[0]
                self.dictChatID[user_data[0]] = user_data[1]

    def getExtension(self, chat_id):
        return self.dictExtensions.get(chat_id)

    def getChatID(self, extension):
        return self.dictChatID.get(extension)

