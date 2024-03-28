import unittest
import requests
from pprint import pp

class ModelsEndpointTester(unittest.TestCase):
    ADDRESS = 'http://127.0.0.1:5000/api/v2/models'

    def test_list_models(self):
        r = requests.get(self.ADDRESS)
        self.assertEqual(r.status_code, 200)
        # test valid json
        self.assertTrue(r.json())
        # test that model list is in the json
        self.assertTrue("_links" in r.json())
    
    def test_translate(self):
        # Test successful translation request, direct input
        r = requests.post(self.ADDRESS+"/en-cs", data={
            "input_text": "this is a sample text"
        })
        # we need to set the encoding, 
        # the server does not define charset and it defaults to ISO-8859-1 for text/plain
        r.encoding = 'utf-8'
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, 'toto je ukázkový text\n')

        # Test successful translation request, file upload
        r = requests.post(self.ADDRESS+"/en-cs", headers={
            "accept": "application/json",
        }, files={
            'input_text': ('hello.txt', 'this is a sample text', 'text/plain')
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()[0], 'toto je ukázkový text\n')


    def test_empty(self):
        # Test empty request (input_text not set)
        r = requests.post(self.ADDRESS+"/en-cs")
        self.assertEqual(r.status_code, 400)
        self.assertIn("No text found", r.text)

        r = requests.post(self.ADDRESS+"/en-cs", data={
            "input_text": ""
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, '')
        # with open("test_data/empty.txt", "w+") as f:
        #     f.write("hello world")
        r = requests.post(self.ADDRESS+"/en-cs", files={
            'input_text': ('empty.txt', '', 'text/plain', {'Expires': '0'})
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, '')


    def test_srctgt(self):
        # correct usage of src/tgt on /model endpoint
        r = requests.post(self.ADDRESS+"/en-cs", data={
            "src": "en",
            "tgt": "cs",
            "input_text": "this is a sample text"
        })
        r.encoding = 'utf-8'
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, 'toto je ukázkový text\n')

        # incorrect usages
        for src, tgt in [("en", "uk"), ("uk", "cs"), ("cs", "en"), ("", 123)]:
            r = requests.post(self.ADDRESS+"/en-cs", data={
                "src": src,
                "tgt": tgt,
                "input_text": "this is a sample text"
            })
            r.encoding = 'utf-8'
            self.assertEqual(r.status_code, 404)
            self.assertIn('This model does not support ', r.text)

    def test_document(self):
        # Test successful translation request, file upload
        r = requests.post(self.ADDRESS+"/en-cs", headers={
            "accept": "application/json",
        }, files={
            'input_text': ('hello.html', '<p>This is <i>a <b>sample</b> text</i></p>', 'text/html')
        })
        pp(r.json())
        self.assertEqual(r.status_code, 200)
        # self.assertEqual(r.json()[0], 'toto je ukázkový text\n')


if __name__ == "__main__":
    unittest.main()
