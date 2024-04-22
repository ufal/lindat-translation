import unittest
import requests
import os
from pprint import pp
from math import ceil

class LanguagesEndpointTester(unittest.TestCase):
    ADDRESS = 'http://127.0.0.1:5000/api/v2/languages/'
    en_cs = {
        "src": "en",
        "tgt": "cs",
    }
    cs_en = {
        "src": "cs",
        "tgt": "en",
    }
    def setUp(self):
        os.makedirs("test_data", exist_ok=True)

    def test_list_languages(self):
        r = requests.get(self.ADDRESS)
        self.assertEqual(r.status_code, 200)
        # test valid json
        self.assertTrue(r.json())
        # test that language list is in the json
        self.assertTrue("_links" in r.json())
    
    def test_translate(self):
        # Test successful translation request, direct input
        r = requests.post(self.ADDRESS, data={
            "src": "en",
            "tgt": "cs",
            "input_text": "this is a sample text"
        })
        # we need to set the encoding, 
        # the server does not define charset and it defaults to ISO-8859-1 for text/plain
        r.encoding = 'utf-8'
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, 'toto je ukázkový text\n')

        # Test successful translation request, file upload
        r = requests.post(self.ADDRESS, headers={
            "accept": "application/json",
        }, data=self.en_cs, files={
            'input_text': ('hello.txt', 'this is a sample text', 'text/plain')
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()[0], 'toto je ukázkový text\n')


    def test_empty(self):
        # Test empty request (input_text not set)
        r = requests.post(self.ADDRESS, data=self.en_cs)
        self.assertEqual(r.status_code, 400)
        self.assertIn("No text found", r.text)

        r = requests.post(self.ADDRESS, data={
            "src": "en",
            "tgt": "cs",
            "input_text": ""
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, '')
        r = requests.post(self.ADDRESS, data=self.en_cs, files={
            'input_text': ('empty.txt', '', 'text/plain')
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, '')
        r = requests.post(self.ADDRESS, data=self.en_cs, files={
            'input_text': ('empty.txt', None, 'text/plain')
        })
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.text, '{"message": "No text found in the input_text form/field or in request files"}\n')

    def test_wrong_extension(self):
        # wrong extension
        r = requests.post(self.ADDRESS, data=self.en_cs, files={
            'input_text': ('empty.zip', b"asdfasdaf", 'application/zip')
        })
        self.assertEqual(r.status_code, 415)
        self.assertEqual(r.text, '{"message": "Unsupported file type for translation"}\n')


    def test_srctgt(self):
        # the default language pair is en-cs
        # missing tgt
        r = requests.post(self.ADDRESS, data={
            "src": "en",
            "input_text": "this is a sample text"
        })
        self.assertEqual(r.status_code, 200)
        # missing src
        r = requests.post(self.ADDRESS, data={
            "tgt": "cs",
            "input_text": "this is a sample text"
        })
        self.assertEqual(r.status_code, 200)
        # missing both
        r = requests.post(self.ADDRESS, data={
            "input_text": "this is a sample text"
        })
        self.assertEqual(r.status_code, 200)

    def test_document_html(self):
        # Test successful translation request, file upload
        r = requests.post(self.ADDRESS, data=self.en_cs, files={
            'input_text': ('hello.html', '<p>This is <i>a <b>sample</b> text</i></p><p><p><p></p></p></p>', 'text/html')
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text.replace(" ", ""), '<p>Totoje<i><b>ukázkový</b>text</i></p><p><p><p></p></p></p>')

    def test_document_xml(self):
        # Test successful translation request, file upload
        r = requests.post(self.ADDRESS, data=self.en_cs, files={
            'input_text': ('hello.xml', '<p>This is <i>a <b>sample</b> text</i></p>', 'text/xml')
        })
        self.assertEqual(r.status_code, 200)
        expected = '<?xml version="1.0" encoding="UTF-8"?>\n'
        expected += '<p>Toto je <i>a <b>ukázka</b> text</i></p>'
        self.assertEqual(r.text, expected)

    def _upload_binary_file(self, filename, langpair):
        src, tgt = langpair.split("-")
        path_in = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data", filename)
        with open(path_in, "rb") as f:
            r = requests.post(self.ADDRESS, data={
                "src": src,
                "tgt": tgt,
            }, files={
                'input_text': f
            })
            outname = r.headers["X-Billing-Filename"]
        with open(outname, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024): 
                if chunk:
                    f.write(chunk)
        return r

    def test_document_docx(self):
        # Test successful translation request, file upload
        r = self._upload_binary_file("test.docx", "cs-en")
        # pp(r)
        # pp(r.headers)
        self.assertEqual(r.status_code, 200)

    def test_document_odt(self):
        r = self._upload_binary_file("kentucky_russian.odt", "ru-en")
        self.assertEqual(r.status_code, 200)

    def test_too_long_text(self):
        # too long text
        r = requests.post(self.ADDRESS, data={
            "input_text": "This is a "*(1024*10) # 100kB
        })
        self.assertEqual(r.status_code, 413)
        self.assertEqual(r.text, '{"message": "The data value transmitted exceeds the capacity limit."}\n')

        r = requests.post(self.ADDRESS, files={
            'input_text': ('hello.txt', "This is a "*(1024*10), 'text/plain') # 100kB
        })
        self.assertEqual(r.status_code, 413)
        self.assertEqual(r.text, '{"message": "The data value transmitted exceeds the capacity limit."}\n')

    def test_too_long_doc(self):
        # disable test for now, file upload is temporarily unlimited
        return

        text = "<p><p><p><p>How are you?</p></p></p></p>"
        repeats = ceil(102400/len(text)) + 1
        print(repeats, len(text), len(text)*repeats)
        final = text*repeats
        print("message length:", len(final))
        print("without tags: ", len(final.replace("<p>", "").replace("</p>", "")))
        r = requests.post(self.ADDRESS, files={
            'input_text': ('hello.html', final, 'text/html')
        })
        pp(r.status_code)
        pp(r.text)
        self.assertEqual(r.status_code, 413)
        self.assertEqual(r.text, '{"message": "The data value transmitted exceeds the capacity limit."}\n')

    def test_do_not_add_whitespace(self):
        r = requests.post(self.ADDRESS, data=self.en_cs, files={
            'input_text': ('hello.html', '<p><b>Sample</b>. <i>text</i>.<br />Hello!</p>', 'text/html')
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, '<p><b>Ukázka</b>. <i>textu</i>.<br />Ahoj!</p>')

    def test_preserve_whitespace(self):
        r = requests.post(self.ADDRESS, data=self.en_cs, files={
            'input_text': ('hello.html', '<pre>This\t\t\tis   <i>a <b>sample</b> text</i></pre><pre>A\t  \t<b>\t \t </b> <i>\t \t</i> </pre>', 'text/html')
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, '<pre>Toto\t\t\tje   <i> <b>ukázkový</b> text</i></pre><pre>A\t  \t<b>\t \t </b> <i>\t \t</i> </pre>')

    def test_whitespace_after_removed_comma(self):
        r = requests.post(self.ADDRESS, data=self.cs_en, files={
            'input_text': ('kofr1.html', 'V 8. stol. př. n. l. vznikly v Řecku eposy <i>Ilias a Odysseia</i>, jejichž autorství je tradičně připisováno Homérovi (1200–700 př. n. l.).', 'text/html')
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, 'In the 8th century BC, the Greek epics <i>Iliad and Odysseus</i> were created, the authorship of which is traditionally attributed to Homer (1200–700 BC).\n')


if __name__ == "__main__":
    unittest.main()
