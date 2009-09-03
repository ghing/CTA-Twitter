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

class ShortMessage(object):
    """A class to represent short messages such as a tweet or SMS message"""

    def __init__(self, msg):
        self._msg = msg

    def split(self, max_length, sep=None):
        """Split the message at word boundaries into strings of max_length length.  Returns a list of strings of max_length or less. Note that this method replaces runs of whitespace with a single space."""
        messages = []

        if len(self._msg) <= max_length:
            # Message is within the length limit.  Just return it.
            messages.append(self._msg)
        else:
            msg_words = self._msg.split(sep)
            while len(msg_words) > 0:
               message = ""
               max_len_reached = False
               while not max_len_reached:
                   if len(msg_words) > 0 and len(message) + len(msg_words[0]) <= max_length:
                       # Our message isn't full length yet
                       message += msg_words.pop(0)

                       if len(msg_words) > 0 and len(message) + 1 <= max_length:
                           message += ' ' 
                   else:
                       max_len_reached = True

               messages.append(message)

        return messages
