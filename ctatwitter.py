#!/usr/bin/python

from poplib import *
import os
from email.Parser import Parser
from string import *
import sqlite3 
import ConfigParser
import logging
import twitter

class ShortMessage(object):
    """A class to represent short messages such as a tweet or SMS message"""

    def __init__(self, msg):
        self._msg = msg

    def split(self, max_length):
        """Split the message at word boundaries into strings of max_length length.  Returns a list of strings of max_length or less. Note that this method replaces runs of whitespace with a single space."""
        messages = []

        # TODO: Implement this method
        if len(self._msg) <= max_length:
            # Message is within the length limit.  Just return it.
            messages.append(self._msg)
        else:
            msg_words = self._msg.split()
            while len(msg_words) > 0:
               message = ""
               max_len_reached = False
               while not max_len_reached:
                   if len(message) + len(msg_words[0]) <= max_length:
                       # Our message isn't full length yet
                       message += msg_words.pop(0)

                       if len(msg_words) > 0 and len(message) + 1 <= max_length:
                           message += ' ' 
                   else:
                       max_len_reached = True

               messages.append(message)

        return messages



# NOTE: This is the command syntax:
# 
# help: Outputs help message
#
# <bus_line_number> stops|s (<stop_name>): List stops and stop IDs
# Example: "2 stops Stony Island" lists all #2 bus stops that have Stony Island in the name
#
# <bus_line_number> <stop_id>|<stop_name>: List next busses
# Example: "2 10487" gets the next busses for stop with stop ID 10487
# Example: "2 Stony Island" gets the next busses for all stops with Stony Island in the name
class BusTrackerMessageParser(object):
    """Class to encapsulate parsing messages and returning a response."""

    def get_response(self, msg):
        # Split the message into tokens
        msg_tokens = msg.split()
        
        if (msg_tokens[0] == 'help' or msg_tokens[0] == 'h'):
            # TODO: Implement help message
            pass
        elif (msg_tokens[0].isdigit()):
            # First token is a number, interpret it as a bus line
            if (msg.tokens[1] == 'stops' or msg.tokens[1] == 's'):
                # List stops

                if msg.tokens[2]:
                    # There's more info, list only the stops matching the remaining tokens 
                    # TODO: Figure out algorithm for intelligently matching strings to stops
                    pass
            else:
                # Entered the name or id of a stop, try to get next busses.
                if (msg.tokens[1].isdigit()):
                    # Numeric value, interpret this as a stop ID
                    pass
                else:
                    # Textual value, try to search for a stop that matches
                    pass

                # Search for the upcoming busses

        # For now, just send an auto-Threply
        response = "This doesn't do much yet.  Please check back soon."
        return response


class TwitterBot(object):
    '''A class for a bot processs that will poll a POP server for Twitter e-mails and respond to them''' 

    def __init__(self, config, logger):
        self._server = POP3(config.get('pop', 'hostname'))
        self._messages = []
        self._logger = logger
        self._twitter_username = config.get('twitter', 'username')
        self._api = twitter.Api(username=self._twitter_username, \
                                password=config.get('twitter', 'password'))

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

    def __init__(self, config, logger):
        TwitterBot.__init__(self, config, logger)
        if config.get('database', 'engine') == 'sqlite':
	    self._conn = sqlite3.connect(config.get('database', 'file'))

    def _seen_message(self, message):
        cursor = self._conn.cursor() 
        cursor.execute("SELECT messageid FROM emails WHERE messageid = ?", [message['Message-ID']])
        if (cursor.fetchone() != None):
            # We have seen this message before 
            cursor.close()
            return True
        else:
            cursor.close()
            return False

    def _db_log_message(self, message, direct_message):        
        cursor = self._conn.cursor() 
        cursor.execute("INSERT INTO emails(messageid, createdat, recipientid, recipientscreenname, recipientname, campaignid, emailtype, senderid, sendername, senderscreenname, directmessageid) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", \
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
                       message['X-Twitterdirectmessageid'], \
                       ] \
        ) 
        if message['X-Twitteremailtype'] == 'direct_message':
            cursor.execute("INSERT INTO direct_messages(directmessageid, message) values (?, ?)", \
                           [message['X-Twitterdirectmessageid'], direct_message])
        self._conn.commit()
        cursor.close()

    def parse_message(self, message):
        logger.debug("Begin parsing message with id %s" % (message['Message-ID']))

        if message['X-Twittercreatedat']:
            email_type = message['X-Twitteremailtype']
            sender_screen_name = message['X-Twittersenderscreenname']
            recipient_screen_name = message['X-Twitterrecipientscreenname']
            direct_message = None

            if message.is_multipart():
                for message_part in message.get_payload():
                    if message_part.get_content_type() == 'text/plain':
                        message_body = message_part.get_payload() 
            else:
                message_body = message.get_payload()

            if (recipient_screen_name == self._twitter_username and \
                not self._seen_message(message)):
                # This is a new twitter message to us
                self._logger.debug("Message is a %s message from %s" % \
                                   (email_type, \
                                    sender_screen_name))


                if email_type == 'is_following':
                    # Message is a notification that someone is following us.

                    # NOTE: Just for future reference here are the e-mail headers for a 
                    # is_following message e-mail 
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

                    # Follow them too.
                    friends = self._api.GetFriends()
                    is_friend = False
                    for friend in friends:
                        if sender_screen_name == friend.screen_name:
                            is_friend = True

                    if not is_friend:
                       # We're not friends with this person yet.  Befriend them.
                       self._api.CreateFriendship(message['X-Twittersenderscreenname'])
                       self._api.PostDirectMessage(message['X-Twittersenderscreenname'], \
                           "Thanks for using the CTA Bus Tracker Twitter interface.  Msg. 'help' for a list of commands or see tinyurl.com/ctabt")
                elif email_type == 'direct_message':
                    # Message is a direct message.
                    
                    # NOTE: Here are the headers for a direct message e-mail.
                    #X-Twittercreatedat: Tue Aug 11 18:01:47 +0000 2009
                    #X-Twitterrecipientid: 61280330
                    #X-Twitterrecipientscreenname: ctabt
                    #X-Twitteremailtype: direct_message
                    #X-Twitterdirectmessageid: 292129578
                    #Bounces-To: Twitter <twitter-dm-twitter=terrorware.com@postmaster.twitter.com>
                    #X-Twittersenderid: 11360602
                    #Errors-To: Twitter <twitter-dm-twitter=terrorware.com@postmaster.twitter.com>
                    #X-Twittersendername: geoffhing
                    #X-Twittersenderscreenname: geoffhing
                    #X-Twitterrecipientname: CTA Bus Tracker

                    # TODO: See if we can parse the message directly from the e-mail.
                    # Assume direct message is the first line of the e-mail body.
                    # From my tests it appears to be
                    direct_message = message_body.splitlines()[0]
                    # logger.debug(direct_message)

                    # TODO: Implement direct message handling
                    message_parser = BusTrackerMessageParser() 
                    response  = message_parser.get_response(direct_message) 
                    self._api.PostDirectMessage(message['X-Twittersenderscreenname'], response)

                # Everything we wanted to do worked, so log the message so we don't repeat
                # these actions in the future
                self._db_log_message(message, direct_message) # log it in the database

            else: 
                self._logger.debug("Message has been seen before or isn't to us.")
        
        else:
            self._logger.debug("Message is not from Twitter") 
        
        logger.debug("End parsing message with id %s" % (message['Message-ID']))

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
