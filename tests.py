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

import unittest
import shortmessage

class ShortMessageTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def _get_split_messages(self, msg):
        short_message = shortmessage.ShortMessage(msg)
        split_messages = short_message.split(140)
        return split_messages 

    def test_shorter_than_max_length_message(self):
        msg = "This message is less than 140 chars." 
        split_messages = self._get_split_messages(msg)
        self.assertEqual(len(split_messages), 1)
        self.assertEqual(split_messages[0], msg)

    def test_equal_to_max_length_message(self):
        msg = "This message is going to try very, very, very, very, very hard to be 140 characters.  Very, very, very, very, very, very hard.  Very hard .."
        split_messages = self._get_split_messages(msg)
        self.assertEqual(len(split_messages), 1)
        self.assertEqual(split_messages[0], msg)

    def test_long_message_split_not_on_word_boundary(self):
        msg = "This message is going to try very, very, very, very, very hard to be 140 characters.  Very, very, very, very, very, very hard.  Very hard. Very."
        split_messages = self._get_split_messages(msg)
        self.assertEqual(len(split_messages), 2)
        self.assertEqual(split_messages[0], "This message is going to try very, very, very, very, very hard to be 140 characters. Very, very, very, very, very, very hard. Very hard. ")
        self.assertEqual(split_messages[1], "Very.")

    def test_long_message_split_on_word_boundary(self):
        msg = "This message is going to be greater than 140 characters split on a word boundary. It is hard to make strings of specific character length. I can do it though."
        split_messages = self._get_split_messages(msg)
        self.assertEqual(len(split_messages), 2)
        self.assertEqual(split_messages[0], "This message is going to be greater than 140 characters split on a word boundary. It is hard to make strings of specific character length. I")
        self.assertEqual(split_messages[1], "can do it though.")

    def test_long_message_3_splits(self):
        msg = "This is a string that will be split 3 ways. This is a string that will be split 3 ways. This is a string that will be split 3 ways. This is a string that will be split 3 ways. This is a string that will be split 3 ways. This is a string that will be split 3 ways. This is a string that will be split 3 ways. This is a string that will be split 3 ways. This is a string that will be split 3 ways."
        split_messages = self._get_split_messages(msg)
        self.assertEqual(len(split_messages), 3)
        self.assertEqual(split_messages[0], "This is a string that will be split 3 ways. This is a string that will be split 3 ways. This is a string that will be split 3 ways. This is ")
        self.assertEqual(split_messages[1], "a string that will be split 3 ways. This is a string that will be split 3 ways. This is a string that will be split 3 ways. This is a string")
        self.assertEqual(split_messages[2], "that will be split 3 ways. This is a string that will be split 3 ways. This is a string that will be split 3 ways.")
    
    def test_zero_length_message(self):
        msg = ""
        split_messages = self._get_split_messages(msg)
        self.assertEqual(len(split_messages), 1)
        self.assertEqual(split_messages[0], "")


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(ShortMessageTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)

