import unittest

from swagger_tester import swagger_test


class TestTester(unittest.TestCase):

    def test_server(self):
        # TODO should swagger.json be available at root?
        swagger_test(app_url='http://localhost:5000/api/v2')
