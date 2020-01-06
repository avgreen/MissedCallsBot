# -*- coding: utf-8 -*-
import cherrypy
import config
import logging
import json
from asterisk.ami import AMIClient, SimpleAction, EventListener
import hashlib

def checkSignature(checkDict, secret):
    if 'signature' in checkDict and 'key' in checkDict:
        srcSignature = checkDict.pop('signature')
        key = checkDict.pop('key')
        dictStr = secret+json.dumps(checkDict, sort_keys=True, separators=(',', ':'))
        if srcSignature == hashlib.md5(dictStr.encode('utf-8')).hexdigest():
            return True
#        print("%s => %s"%(dictStr,hashlib.md5(dictStr.encode('utf-8')).hexdigest()))
#        print(srcSignature)
    return False

def Originate(Extension, phoneNumber, CallerID = 'python', Context = 'from-internal'):
    client = AMIClient(**config.AMIClientAddress)
    client.login(**config.AMIClientUser)
    logger = logging.getLogger("bot.ClinicaWeb")
    action = SimpleAction(
        'Originate',
        Channel='SIP/'+str(Extension),
        Exten=phoneNumber,
        Priority=1,
        Context=Context,
        CallerID=CallerID,
    )
    logger.info("Start originate from %s to %s" % (Extension, phoneNumber))
#    if client.send_action(action).response.status == 'Success':
#        logger.info("Start call from %s to %s" % (Extension, phoneNumber))

class ClinicaWebAPI(object):
    @cherrypy.expose
    def index(self):
        return "Hello world!"
    @cherrypy.expose
    def ext_to_phone_json(self, *args, **kwargs):
#        if cherrypy.request.headers.get('Remote-Addr') ==  '77.222.152.144':
#        print((cherrypy.request.headers))
        if 'content-length' in cherrypy.request.headers and \
                'content-type' in cherrypy.request.headers and \
                cherrypy.request.headers['content-type'].split("; ")[0] == 'application/json':
            rawbody = cherrypy.request.body.read(int(cherrypy.request.headers['Content-Length']))
            body = json.loads(rawbody)
            #print(body)
            if checkSignature(body, 'KNAynOFovXVUthG8N8j2'):
                phoneNumber = ('+38' if len(body['phone_number']) == 10 else '') + body['phone_number']
                Originate(body['ext_number'], phoneNumber)
                return "Updated %r." % (body,)
            else:
                raise cherrypy.HTTPError(401)
        else:
            raise cherrypy.HTTPError(403)

        r = cherrypy.response
        r.headers['Content-Type'] = 'text/plain'
        content = "Positional arguments\n\n"
        for k in args:
            content += k + "\n"
        content += "\nKeyword arguments\n\n"
        for k in kwargs:
            content += k + ": " + kwargs[k] + "\n"
        return content

