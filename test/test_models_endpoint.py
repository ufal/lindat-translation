import unittest
import requests
import os
from pprint import pp

class ModelsEndpointTester(unittest.TestCase):
    ADDRESS = 'http://127.0.0.1:5000/api/v2/models'

    def setUp(self):
        os.makedirs("test_data", exist_ok=True)

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

    def test_document_html(self):
        # Test successful translation request, file upload
        r = requests.post(self.ADDRESS+"/en-cs", files={
            'input_text': ('hello.html', '<p>This is <i>a <b>sample</b> text</i></p>', 'text/html')
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text.replace(" ", ""), '<p>Totoje<i><b>ukázkový</b>text</i></p>')

    def test_document_xml(self):
        # Test successful translation request, file upload
        r = requests.post(self.ADDRESS+"/en-cs", files={
            'input_text': ('hello.xml', '<p>This is <i>a <b>sample</b> text</i></p>', 'text/xml')
        })
        self.assertEqual(r.status_code, 200)
        expected = '<?xml version="1.0" encoding="UTF-8"?>\n'
        expected += '<p>Tohle je <i>a <b>vzorek</b> text</i></p>'
        self.assertEqual(r.text, expected)

    def _upload_binary_file(self, filename, outname, langpair):
        with open(filename, "rb") as f:
            r = requests.post(self.ADDRESS+"/"+langpair, files={
                'input_text': f
            })
        with open(outname, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024): 
                if chunk:
                    f.write(chunk)
        return r

    def test_document_docx(self):
        # Test successful translation request, file upload
        r = self._upload_binary_file("./test_data/test.docx", "./test_data/test_response.docx", "cs-en")
        self.assertEqual(r.status_code, 200)

    def test_document_odt(self):
        r = self._upload_binary_file("./test_data/kentucky_russian.odt", "./test_data/kentucky_eng_translation.odt", "ru-en")
        self.assertEqual(r.status_code, 200)


if __name__ == "__main__":
    unittest.main()
