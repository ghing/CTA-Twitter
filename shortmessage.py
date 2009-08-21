class ShortMessage(object):
    """A class to represent short messages such as a tweet or SMS message"""

    def __init__(self, msg):
        self._msg = msg

    def split(self, max_length, sep=None):
        """Split the message at word boundaries into strings of max_length length.  Returns a list of strings of max_length or less. Note that this method replaces runs of whitespace with a single space."""
        messages = []

        # TODO: Implement this method
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
