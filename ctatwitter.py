#!/usr/bin/python

import twitter
import sqlite3
import getopt, sys
from poplib import *
import os
from email.Parser import Parser
from string import *
import ConfigParser
import logging
import shortmessage

class BusTrackerMessageParserException(Exception):
    """Base class for exceptions raised by BusTrackerMessageParser"""
    pass

class CommandNotUnderstoodException(BusTrackerMessageParserException):
    """Exception raised when there is some problem with the command syntax"""
    pass           

# NOTE: This is the command syntax:
# 
# help|h: Outputs help message
#
# <bus_line_number> <direction> stops|s (<stop_name>): List stops and stop IDs as they appear in their route
# Example: "2 n s" lists all northbound # bus stops
# Example: "2 n s Stony Island" lists all northbound #2 bus stops that have Stony Island in the n
#
# <bus_line_number> <stop_id>|<stop_name> <direction>: List next busses
# Example: "2 n 10487" gets the next northbound busses for stop with stop ID 10487
# Example: "2 n Stony Island" gets the next northbound busses for all stops with Stony Island in the name
class BusTrackerMessageParser(object):
    """Class to encapsulate parsing messages and returning a response."""

    def __init__(self, logger):
        self._logger = logger

    def get_response(self, msg):
        # Split the message into tokens
        msg_tokens = msg.split()

        if len(msg_tokens) < 1:
            raise CommandNotUnderstoodException('Your request is empty!')
        
        if (msg_tokens[0] == 'help' or msg_tokens[0] == 'h'):
            response = "List stops and their ids: <route #> <direction> s\n" + 
                       "Get next busses: <route #> <direction> <stop id>\n" +
                       "See http://tinyurl.com/ctatwit for more."

        elif (msg_tokens[0].isdigit()):
            route = msg_tokens[0]
            direction = None
            stop_name = None
            stop_id = None
            # BOOKMARK
            
            # First token is a number, interpret it as a bus line
            if len(msg_tokens) == 3 and (msg_tokens[1] == 'stops' or msg_tokens[1] == 's'):
                # List stops

                if msg_tokens[2]:
                    # There's more info, list only the stops matching the remaining tokens 
                    # TODO: Figure out algorithm for intelligently matching strings to stops
                    pass
            elif len(msg_tokens) == 3:
                # Entered the name or id of a stop, try to get next busses.
                if (msg_tokens[1].isdigit()):
                    # Numeric value, interpret this as a stop ID
                    pass
                else:
                    # Textual value, try to search for a stop that matches
                    pass

                # Search for the upcoming busses
            else:
                # fail
                pass

        # For now, just send an auto-Threply
        response = "This doesn't do much yet.  See tinyurl.com/ctatwit for updates."
        return response


class TwitterBot(object):
    '''A class for a bot processs that will poll a POP server for Twitter e-mails and respond to them''' 

    def __init__(self, config, logger):
        self._config = config
        self._messages = []
        self._logger = logger
        self._twitter_username = config.get('twitter', 'username')
        self._api = twitter.Api(username=self._twitter_username, \
                                password=config.get('twitter', 'password'))


    def get_messages(self):
        if self._config.get('general', 'mail_protocol') == 'pop': 
            server = POP3(self._config.get('pop', 'hostname'))

            # Authenticate to the POP server
            server.getwelcome()
            server.user(self._config.get('pop', 'username'))
            server.pass_(self._config.get('pop', 'password'))

            messages_info = server.list()[1]


            # Get the messages
            for message_info in messages_info: 
              message_num = int(split(message_info, " ")[0])
              message_size = int(split(message_info, " ")[1])
              if (message_size < 20000):
                message = server.retr(message_num)[1]
                message = join(message, "\n")
                self._messages.append(message)
              #server.dele(message_num) # Remove message from server.

            server.quit()
        else:
            # Default to IMAP
            import imaplib
            server = imaplib.IMAP4(self._config.get('imap', 'hostname'))
            server.login(self._config.get('imap', 'username'),
                         self._config.get('imap', 'password'))
            server.select('INBOX')             
            type, data = server.search(None, 'NOT', 'DELETED')
            for num in data[0].split():
              typ, data = server.fetch(num, '(RFC822)')
              #self._logger.debug('Message %s\n%s\n' % (num, data[0][1]))
              self._messages.append(data[0][1])
              server.copy(num, self._config.get('imap', 'backup_mailbox'))
              server.store(num, 'FLAGS', '(\Deleted)')

            # QUESTION: Should we expunge deleted messages?
            # server.expunge()
            server.close()
            server.logout()

    def parse_messages(self):
        parser = Parser()
        for message_str in self._messages:
          message = parser.parsestr(message_str)
          self.parse_message(message)

    def parse_message(self, message):
        pass

    def __del__(self):
        pass

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
    
    def _db_log_error_message(self, message, type, error):
        cursor = self._conn.cursor() 
        # TODO: Implement this database structure
        cursor.execute("INSERT INTO direct_message_errors(directmessageid, error_message) values (?, ?, ?)", \
                       [ \
                       message['X-Twitterdirectmessageid'], \
                       error
                       ])
        self._conn.commit()
        cursor.close()

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
        self._logger.debug("Begin parsing message with id %s" % (message['Message-ID']))

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

                    # Assume direct message is the first line of the e-mail body.
                    # From my tests it appears to be
                    direct_message = message_body.splitlines()[0]
                    # logger.debug(direct_message)

                    message_parser = BusTrackerMessageParser(self._logger) 
                    try:
                        response  = message_parser.get_response(direct_message)
                    except CommandNotUnderstoodException as e: 
                        response = "I couldn't understand your request!  Try messaging me with 'help' or see http://tinyurl.com/ctatwit"
                        self._db_log_error_message(message, e)
                        
                    response_message = shortmessage.ShortMessage(response)
                    for response_direct_message in response_message.split():
                      self._api.PostDirectMessage(message['X-Twittersenderscreenname'], response_direct_message)

                # Everything we wanted to do worked, so log the message so we don't repeat
                # these actions in the future
                self._db_log_message(message, direct_message) # log it in the database

            else: 
                self._logger.debug("Message has been seen before or isn't to us.")
        
        else:
            self._logger.debug("Message is not from Twitter") 
        
        self._logger.debug("End parsing message with id %s" % (message['Message-ID']))
        self._logger.debug(" ")
        
def main():        
    # Set up logging
    logger = logging.getLogger('ctatwitter')
    handler = logging.StreamHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    # Parse command line options
    config_file = 'ctatwitter.conf'
    command = None
    try:
        opts, args = getopt.getopt(sys.argv[1:], "f:c:", ["file=", "command="])
    except getopt.GetoptError, err:
        print str(err)
        sys.exit(2)

    for o, a in opts:
        if o in ("-f", "--file"):
            config_file = a
        if o in ("-c", "--command"):
            command = a
        else:
            assert False, "unhandled option"

    # Load the configuration
    config = ConfigParser.ConfigParser()
    config.read(config_file)

    if not command:
        # No command passed on the command line.  Attempt to check messages in e-mail.
        bot = CtaTwitterBot(config, logger)
        bot.get_messages()
        bot.parse_messages()
    else:
        message_parser = BusTrackerMessageParser() 
        response  = message_parser.get_response(direct_message) 
        response_message = shortmessage.ShortMessage(response)
        for response_direct_message in response_message.split():
            print response_direct_message
        

if __name__ ==  "__main__":
    main()
