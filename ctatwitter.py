#!/usr/bin/python

from poplib import *
import os
from email.Parser import Parser
from string import *
import sqlite3 
import ConfigParser
import logging


class TwitterBot(object):
    '''A class for a bot processs that will poll a POP server for Twitter e-mails and respond to them''' 

    def __init__(self, config, logger):
        self._server = POP3(config.get('pop', 'hostname'))
        self._messages = []
        self._logger = logger
        self._twitter_screenname = config.get('twitter', 'screenname')

        # Authenticate to the POP server
        self._server.getwelcome()
        self._server.user(config.get('pop', 'username'))
        self._server.pass_(config.get('pop', 'password'))

    def get_messages(self):
        messages_info = self._server.list()[1]

        # Get the messages
        for message_info in messages_info: 
          message_num = int(split(message_info, " ")[0])
          message_size = int(split(message_info, " ")[1])
          if (message_size < 20000):
            message = self._server.retr(message_num)[1]
            message = join(message, "\n")
            self._messages.append(message)
          #server.dele(message_num) # Remove message from server.

    def parse_messages(self):
        parser = Parser()
        for message_str in self._messages:
          message = parser.parsestr(message_str)
          self.parse_message(message)

    def parse_message(self, message):
        pass

    def __del__(self):
        self._server.quit()

class CtaTwitterBot(TwitterBot):
    # NOTE: Just for future reference I'm going to put the headers for a twitter
    # generated e-mail here.
    #X-Twittercreatedat: Wed Jul 29 19:58:32 +0000 2009
    #X-Twitterrecipientid: 61280330
    #X-Twitterrecipientscreenname: ctabt
    #X-Campaignid: twitter20080331162631
    #X-Twitteremailtype: is_following
    #Bounces-To: Twitter <twitter-follow-twitter=terrorware.com@postmaster.twitter.com>
    #X-Twittersenderid: 11360602
    #Errors-To: Twitter <twitter-follow-twitter=terrorware.com@postmaster.twitter.com>
    #X-Twittersendername: geoffhing
    #X-Twittersenderscreenname: geoffhing
    #X-Twitterrecipientname: CTA Bus Tracker 

    def __init__(self, config, logger):
        TwitterBot.__init__(self, config, logger)
        if config.get('database', 'engine') == 'sqlite':
	    self._conn = sqlite3.connect(config.get('database', 'file'))

    def _seen_message(self, message):
        cursor = self._conn.cursor() 
        cursor.execute("SELECT messageid FROM ctatwitter WHERE messageid = ?", [message['Message-ID']])
        if (cursor.fetchone() != None):
            # We have seen this message before 
            cursor.close()
            return True
        else:
            cursor.close()
            return False

    def _log_message(self, message):        
        cursor = self._conn.cursor() 
        cursor.execute("INSERT INTO ctatwitter(messageid, createdat, recipientid, recipientscreenname, recipientname, campaignid, emailtype, senderid, sendername, senderscreenname) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", \
                       [ \
                       message['Message-ID'], \
                       message['X-Twittercreatedat'], \
                       message['X-Twitterrecipientid'], \
                       message['X-Twitterrecipientscreenname'], \
                       message['X-Twitterrecipientname'], \
                       message['X-Campaignid'], \
                       message['X-Twitteremailtype'], \
                       message['X-Twittersenderid'], \
                       message['X-Twittersendername'], \
                       message['X-Twittersenderscreenname'], \
                       ] \
        ) 
        self._conn.commit()
        cursor.close()

    def parse_message(self, message):
        if (message['X-Twittercreatedat'] and \
            message['X-Twitterrecipientscreenname'] == self._twitter_screenname and \
            not self._seen_message(message)):
            # This is a new twitter message to us, log it in the database
            self._log_message(message)


# Set up logging
logger = logging.getLogger('ctatwitter')
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

# Load the configuration
config = ConfigParser.ConfigParser()
# TODO: Make the config filename a command line argument 
config.read('ctatwitter.conf')

bot = CtaTwitterBot(config, logger)
bot.get_messages()
bot.parse_messages()
