import unittest

class ShortMessageTestCase(unittest.TestCase):
    def setUp(self):
        pass

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(ShortMessageTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)

