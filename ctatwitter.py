#!/usr/bin/python

# Copyright 2009 Geoffrey Hing
#
# This file is part of the CTA Twitter package.
#
# CTA Twitter is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# CTA Twitter is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AfferoGeneral Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with CTA Twitter.  If not, see <http://www.gnu.org/licenses/>.

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
import transitapi
import re
import traceback

class BusTrackerMessageParserException(Exception):
    """Base class for exceptions raised by BusTrackerMessageParser"""
    pass

class CommandNotUnderstoodException(BusTrackerMessageParserException):
    """Exception raised when there is some problem with the command syntax"""
    pass           

class MultipleMatchingStopsError(BusTrackerMessageParserException):
    """Exception raised when a command that requires a stop search returns multiple matching stops"""
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
    """Class to encapsulate parsing messages and returning "a response."""

    # Insert this into the response to force the message to be broken at that
    # point by ShortMessage.split().  The default is to split messages at
    # whitespace, but in some cases, for readability, we might want to force
    # a split elsewhere (for example, keeping stop names and IDs together)
    MESSAGE_TOKEN_SEP = "-;;-" 

    def __init__(self):
        self._name_history = []

    def shorten_name(self, name):
        short_name = ""
        min_name_len = 3
 
        name_parts = name.split()
        new_name_parts = []
        for name_part in name_parts:
           new_name_part = None

           # Strip street names
           name_part = name_part.replace('Street', '')
           name_part = name_part.replace('Drive', '')
           name_part = name_part.replace('Avenue', '')

           # Abbreviate directions
           name_part = name_part.replace('East', 'E')
           name_part = name_part.replace('West', 'W')
           name_part = name_part.replace('North', 'N')
           name_part = name_part.replace('South', 'S')
         
           if len(name_part) >= min_name_len:
               #print "'%s'" % (name_part)

               if name_part not in self._name_history:
                   #print "adding '%s'" % (name_part)
                   self._name_history.append(name_part)
               else:
                   vowel_re = re.compile(r'[AEIOUaeiou]')
                   new_name_part = vowel_re.sub('', name_part)  
                   if new_name_part[0] != name_part[0]:
                       # Got rid of the first letter in the name
                       # b/c it was a vowel.  We want it back.
                       new_name_part = name_part[0] + new_name_part
                   
                   #print "converted '%s' to '%s'" % (name_part, new_name_part)

           if new_name_part:
               new_name_parts.append(new_name_part)      
           else:
               if not name_part.isspace() and not name_part == '':
                   new_name_parts.append(name_part)

        return ' '.join(new_name_parts) 
                

    def flush_name_history(self):
        del self._name_history
        self._name_history = []

    def filter_stops(self, stops, filter):
        """Filter out a list of stops based on a string.  The purpose of this is to abstract stop searches (that is, finding a stop id from a stop name, using different partial matching algorithms"""
        filtered_stops = []

        for stop in stops:
            if stop.name.find('&') != -1 and filter.find('&') != -1:
                # Stop contains ampersand and filter contains ampersan. Search
                # for partial strings on either side of the ampersand.
                # For example if the stop name is "60th Street & Blackstone"
                # we want to match with a filter of "60 & Black"
                stop_name_parts = stop.name.lower().split('&')
                filter_parts = filter.lower().split('&')

                if len(stop_name_parts) == 2 and len(filter_parts) == 2:
                    if stop_name_parts[0].find(filter_parts[0].strip()) != -1 and \
                       stop_name_parts[1].find(filter_parts[1].strip()) != -1:
                        filtered_stops.append(stop)
            else:
                if stop.name.lower().find(filter.lower()) != -1:
                    filtered_stops.append(stop)
             
        return filtered_stops

    def get_response(self, msg):
        logger = logging.getLogger('ctatwitter')

        # Split the message into tokens
        msg_tokens = msg.split()

        if len(msg_tokens) < 1:
            raise CommandNotUnderstoodException('Your request is empty!')
        
        if (msg_tokens[0] == 'help' or msg_tokens[0] == 'h'):
            response = "List stops and their ids: <route #> <direction> (<search>)\n" + \
                       "Get next busses: <route #> <direction> <stop id>|<search>\n" + \
                       "Examples:\n" + \
                       "77 e s - Get stop names and IDs for Eastbound #77 busses.\n" + \
                       "77 e shef - Get upcoming busses for Sheffield stop.\n" + \
                       "See http://tinyurl.com/ctatwit for more."

        elif (msg_tokens[0].isdigit()):
            # First token is a number, interpret it as a bus route 
            route = msg_tokens[0]

            direction = None
            stop_id = None

            if len(msg_tokens) < 3:
                raise CommandNotUnderstoodException("Command is incomplete.")

            direction = msg_tokens[1].lower()[0]
            if direction not in ('n', 's', 'e', 'w'):
                raise CommandNotUnderstoodException("Missing direction.")

            if direction == "n":
               direction_arg = "North Bound"
            elif direction == "s":
               direction_arg = "South Bound"
            elif direction =="e":
               direction_arg = "East Bound"
            elif direction =="w":
               direction_arg = "West Bound"


            if msg_tokens[2] == 'stops' or msg_tokens[2] == 's':
                # List stops

                response = "Stops (ID:Name): "

                filter = None
                if len(msg_tokens) > 3:
                    filter = " ".join(msg_tokens[3:])

                try:
                    bt = transitapi.Bustracker()
                    stops = bt.getRouteDirectionStops(route, direction_arg)
                    if (filter):
                        stops = self.filter_stops(stops, filter)
                    for stop in stops:
                        response += "%s:%s;" % (stop.id, stop.name) + self.MESSAGE_TOKEN_SEP
                except transitapi.BustrackerApiConnectionError, e:
                    logger.error("Couldn't connect to the API: %s" % e)
                    response = "I'm having trouble getting bus information from the CTA's system.  Please try again later."
                except transitapi.BustrackerApiXmlError, e:
                    logger.error("%s" % e)
                    response = "Oops.  That didn't go as planned.  I'm looking into it."
                    
            elif len(msg_tokens) >= 3:
                # Search for next busses

                try:
                  stop_id = None
                  bt = transitapi.Bustracker()

                  if msg_tokens[2].isdigit():
                      # Entered the id of a stop
                      stop_id = msg_tokens[2];
                  else:
                      # Interpret the rest of the command message as the name of a
                      # stop
                      filter = " ".join(msg_tokens[2:])
                      stops = bt.getRouteDirectionStops(route, direction_arg)
                      stops = self.filter_stops(stops, filter)
                      if len(stops) == 1:
                          stop_id = stops[0].id
                      else:
                          # TODO: Handle multiple matching stops
                          raise MultipleMatchingStopsError

                  predicted_busses = bt.getStopPredictions(stop_id, route)
                  if len(predicted_busses) == 0:
                      response = "No busses are predicted for this stop."
                  elif len(predicted_busses) == 1:
                      response = "Upcoming bus in %s" % predicted_busses[0].predicted_time
                  else:
                    response = "Upcoming busses in "
                    for i in range(0, len(predicted_busses)):
                        response += predicted_busses[i].predicted_time
                        if i != len(predicted_busses) - 1:
                            response += ", "

                except transitapi.BustrackerApiConnectionError, e:
                    logger.error("Couldn't connect to the API: %s" % e)
                    response = "I'm having trouble getting bus information from the CTA's system.  Please try again later."
                except transitapi.BustrackerApiXmlError, e:
                    logger.error("%s" % e)
                    response = "Oops.  That didn't go as planned.  I'm looking into it."
                except MultipleMatchingStopsError, e:
                    response = "Found multiple matching stops.  Try arrowing your search or messaging '%s %s stops' for a list" % (route, direction)

            else:
                # General fail
                raise CommandNotUnderstoodException("Invalid command.")

        else:
            raise CommandNotUnderstoodException("First part of the command must be 'h(elp)' or a route #")

        return response

class TwitterBot(object):
    '''A class for a bot processs that will poll a POP server for Twitter e-mails and respond to them''' 

    def __init__(self, config):
        self._config = config
        self._messages = []
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
    def __init__(self, config):
        TwitterBot.__init__(self, config)
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
        logger = logging.getLogger('ctatwitter')
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
                logger.debug("Message is a %s message from %s" % \
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

                    message_parser = BusTrackerMessageParser() 
                    try:
                        response  = message_parser.get_response(direct_message)
                    except CommandNotUnderstoodException, err: 
                        response = "I couldn't understand your request!  Try messaging me with 'help' or see http://tinyurl.com/ctatwit"
                        self._db_log_error_message(message, err)

                    if response.find(BusTrackerMessageParser.MESSAGE_TOKEN_SEP) != -1:
                        sep = BusTrackerMessageParser.MESSAGE_TOKEN_SEP
                        if len(response) <= 140:
                            response = response.replace(BusTrackerMessageParser.MESSAGE_TOKEN_SEP, '')
                    else:
                        sep = None

                    response_message = shortmessage.ShortMessage(response)
                    for response_direct_message in response_message.split(140, sep):
                      self._api.PostDirectMessage(message['X-Twittersenderscreenname'], response_direct_message)

                # Everything we wanted to do worked, so log the message so we don't repeat
                # these actions in the future
                self._db_log_message(message, direct_message) # log it in the database

            else: 
                logger.debug("Message has been seen before or isn't to us.")
        
        else:
            logger.debug("Message is not from Twitter") 
        
        logger.debug("End parsing message with id %s" % (message['Message-ID']))
        logger.debug(" ")
        
def main():        
    # Set up console logging
    logger = logging.getLogger('ctatwitter')
    logger.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler()
    logger.addHandler(stream_handler)

    # Parse command line options
    config_file = 'ctatwitter.conf'
    command = None
    log_file = 'ctatwitter.log'
    try:
        opts, args = getopt.getopt(sys.argv[1:], "f:c:", ["file=", "command="])
    except getopt.GetoptError, err:
        print str(err)
        sys.exit(2)

    for o, a in opts:
        if o in ("-f", "--file"):
            config_file = a
        elif o in ("-c", "--command"):
            command = a
        elif o in ("-l", "--log-file"):
            log_file = a
        else:
            assert False, "unhandled option"

    # Load the configuration
    config = ConfigParser.ConfigParser()
    config.read(config_file)

    # Set up logging to a file 
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.ERROR)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    try:
        if not command:
            # No command passed on the command line.  Attempt to check messages in e-mail.
            bot = CtaTwitterBot(config)
            bot.get_messages()
            bot.parse_messages()
        else:
            message_parser = BusTrackerMessageParser() 
            response  = message_parser.get_response(command) 
            if response.find(BusTrackerMessageParser.MESSAGE_TOKEN_SEP) != -1:
                sep = BusTrackerMessageParser.MESSAGE_TOKEN_SEP
                if len(response) <= 140:
                    response = response.replace(BusTrackerMessageParser.MESSAGE_TOKEN_SEP, '')
            else:
                sep = None
            response_message = shortmessage.ShortMessage(response)
            for response_direct_message in response_message.split(140, sep):
                print response_direct_message
    except:
        # HACK ALERT! Catch all exceptions and log them until
        # this service gets to run long enough to get a feel
        # for what kind of exceptions are to be expected.
        exception_type, exception_value, exception_traceback = sys.exc_info()
       
        msg = "\n" + ' '.join(traceback.format_exception(exception_type, exception_value, \
                   exception_traceback))
        logger.error(msg)

if __name__ ==  "__main__":
    main()

