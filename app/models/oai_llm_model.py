import sentencepiece as spm
from flask import current_app
from websocket import create_connection

import app.models as models
from app.text_utils import split_text_into_sentences
from openai import OpenAI
import sys
import iso639
import logging

class OaiLLMModel(models.Model):

    def __init__(self, cfg):
        super().__init__(cfg)
        self.provider=cfg['provider']
        default_prompt = "Translate the following text from {src} to {tgt}, including correctly transferring the markup from the source sentence into the translation. Do not add any explanations, make sure to only output the translated text, including markup like HTML tags, transferred from the source and nothing else. Do not exaplain any abrreviations or terms, only print out the translation, or, for untranslatable content, print out the source. Source text: {sentence} "
        default_prompt_terms= "Translate the following text from {src} to {tgt}, including correctly transferring the markup from the source sentence into the translation. Do not add any explanations, make sure to only output one single line with the translated sentence and nothing else.  Use the following terminology database to translate specific terms: Source term -> Target term \n {terms} \n Source sentence: {sentence} "
        self.token=cfg.get('token', None)
        self.prompt=cfg.get('prompt', default_prompt)
        self.prompt_terms=cfg.get('prompt_terms', default_prompt_terms)
        self.allow_custom_prompt=cfg.get('allow_custom_prompt', True)
    @property
    def batch_size(self):
        """
        This method needs a valid app context, current_app is not available at init time.
        """
        if hasattr(self, '_batch_size'):
            return self._batch_size
        else:
            return 1

    def send_sentences_to_backend(self, sentences, src=None, tgt=None, custom_prompt=None, terms=None):
        self.client = OpenAI(
            base_url=f"{self.server}/v1",
            api_key=self.token,
        )
        print("Connecting to '{}'".format(self.server), flush=True, file=sys.stderr)
        print("Sentences: ", sentences, flush=True, file=sys.stderr)
        res=[]

        if self.provider=="openai":
            model=self.model
        else:
            model=f"{self.provider}/{self.model}"
        for i,sentence in enumerate(sentences):
            sent_terms=None
            if terms:
                try:
                    sent_terms= ""
                    for x in terms[i]:
                        sent_terms+=f"{x[0]} -> {x[1]}\n"
                except Exception as e:
                    logging.warning("Error while trying to format terms: {}".format(e))

            #prompt = f"Translate the following text from {iso639.to_name(src)} to {iso639.to_name(tgt)}, including correctly transferring the markup from the source sentence into the translation. Do not add any explanations, make sure to only output one single line with the translated sentence and nothing else. Source sentence: " + sentence
            if custom_prompt and self.allow_custom_prompt:

                prompt = custom_prompt.format(src=iso639.to_name(src), tgt=iso639.to_name(tgt), sentence=sentence, terms=sent_terms)
            else:
                if sent_terms:
                    prompt = self.prompt_terms.format(src=iso639.to_name(src), tgt=iso639.to_name(tgt), sentence=sentence, terms=sent_terms)
                else:
                    prompt = self.prompt.format(src=iso639.to_name(src), tgt=iso639.to_name(tgt), sentence=sentence)
            print("Prompt: ", prompt, flush=True, file=sys.stderr)

            completion = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt},
            ], temperature=0.01
        )
            #TODO: maybe we should handle this replace better?
            res.append(completion.choices[0].message.content.replace('\n', ' '))

        print("Result: ", '\n'.join(res), flush=True, file=sys.stderr)
        return res

    def split_to_sent_array(self, text, lang):
        sent_array = text.split("\n")
        return sent_array
