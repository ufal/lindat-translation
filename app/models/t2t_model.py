from math import ceil
from pprint import pformat

import numpy as np
from flask import current_app, session
from tensor2tensor.serving import serving_utils
from tensor2tensor.utils import registry

import app.models as models
from app.text_utils import split_text_into_sentences


class T2TModel(models.Model):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.problem = registry.problem(cfg['problem'])
        self.problem.get_hparams(models.hparams)

    def send_sentences_to_backend(self, sentences, src, tgt):
        if self.prefix_with:
            prefix = self.prefix_with.format(source=src, target=tgt)
            sentences = [prefix + sent for sent in sentences]

        return self._do_send_request(sentences)

    def _do_send_request(self, text_arr, with_scores=False):
        """
        Divide the arr into batches and send the batches to the backend to be processed
        :param text_arr: individual elements of arr will be grouped into batches
        :return:
        """
        outputs_with_scores = []
        request_fn = serving_utils.make_grpc_request_fn(servable_name=self.model, timeout_secs=500,
                                                        server=self.server)

        for batch in np.array_split(text_arr,
                                    ceil(len(text_arr) / self.batch_size)):
            try:
                models.log.debug(f"===== sending batch\n{pformat(batch)}\n")
                outputs_with_scores += serving_utils.predict(batch.tolist(), self.problem, request_fn)
            except:
                # When tensorflow serving restarts web clients seem to "remember" the channel where
                # the connection have failed. clearing up the session, seems to solve that
                session.clear()
                raise

        if not with_scores:
            return list(map(lambda sent_score: sent_score[0], outputs_with_scores))
        else:
            # change (sent, score) tuples to list; tuples are immutable; reconstruct_formatting needs mutable
            # np.float32 ... `Object of type float32 is not JSON serializable` .item() turns it into python scalar 
            return list(map(lambda tup: {'output_text': tup[0], 'output_score': tup[1].item()}, outputs_with_scores))

    def split_to_sent_array(self, text, lang):
        charlimit = self.sent_chars_limit
        sent_array = []
        for sent in split_text_into_sentences(text=text, language=lang):
            while len(sent) > charlimit:
                try:
                    # When sent starts with a space, then sent[0:0] was an empty string,
                    # and it caused an infinite loop. This fixes it.
                    beg = 0
                    while sent[beg] == ' ':
                        beg += 1
                    last_space_idx = sent.rindex(" ", beg, charlimit)
                    sent_array.append(sent[0:last_space_idx])
                    sent = sent[last_space_idx:]
                except ValueError:
                    # raised if no space found by rindex
                    sent_array.append(sent[0:charlimit])
                    sent = sent[charlimit:]
            sent_array.append(sent)
        # print(len(sent_array), [len(x) for x in sent_array])
        return sent_array


class T2TDocModel(T2TModel):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.MAX_CHARS = 1800
        self.USE_CHARS = 1000
        self.PRE_CHARS = 400
        self.PRE_TOO_SHORT = self.PRE_CHARS/2
        self.CUT_PRE = True

    @staticmethod
    def has_next_sent(index, array):
        return index < len(array) - 1

    @staticmethod
    def has_prev_sent(index):
        return index > 0

    @staticmethod
    def it_fits_into_the_limit(current, next_len, limit):
        return current + next_len < limit

    def extract_blocks_of_text(self, text, src):
        models.log.debug("T2TDocLevel::extract_blocks_of_text")
        sentences, formatting = self.extract_sentences(text, src)  # honors the sent max len setting
        clever_context = self._create_clever_context(sentences)
        return {"clever_context": clever_context, "sentences": sentences}, formatting

    def send_blocks_to_backend(self, clever_context_with_sentences, src, tgt):
        models.log.debug("T2TDocLevel::send_blocks_to_backend")
        sequences = clever_context_with_sentences["clever_context"]
        sentences = clever_context_with_sentences["sentences"]
        outputs = self._do_send_request([x["sequence"] for x in sequences])
        outputs = self._postproc_context(outputs, [x["pattern"] for x in sequences], sentences)
        return outputs

    def _create_clever_context(self, sentences):
        """
        group sentences into seqeunces of sentences
        sequence has optional precontext, postcontext and a block of sentenctes that are being translated
        :param sentences:
        :return:
        """

        block_start = 0
        block_end = -1
        current_block_len = 0
        pre_context_len = 0
        pre_context_start = block_start

        # helpers to make the while loops more readable #
        def has_next_sent(index=None):
            if index is None:
                return T2TDocModel.has_next_sent(block_end, sentences)
            else:
                return T2TDocModel.has_next_sent(index, sentences)

        def has_prev_sent():
            return T2TDocModel.has_prev_sent(pre_context_start)

        def it_fits_use_chars_limit():
            return T2TDocModel.it_fits_into_the_limit(current_block_len, len(sentences[block_end + 1]), self.USE_CHARS)

        def it_fits_pre_chars_limit():
            return T2TDocModel.it_fits_into_the_limit(pre_context_len, len(sentences[pre_context_start - 1]), self.PRE_CHARS)

        def pre_context_is_too_short():
            return pre_context_len < self.PRE_TOO_SHORT

        # /helpers #

        sequences = []
        while has_next_sent():
            block_end += 1
            current_block_len = len(sentences[block_start])
            current_block = [sentences[block_start]]
            sequence_pattern = [True]
            while has_next_sent() and it_fits_use_chars_limit():
                block_end += 1
                current_block_len += len(sentences[block_end])
                current_block.append(sentences[block_end])
                sequence_pattern.append(True)

            pre_context_len = 0
            pre_context_start = block_start

            while has_prev_sent() and it_fits_pre_chars_limit():
                pre_context_start -= 1
                pre_context_len += len(sentences[pre_context_start])
                current_block.insert(0, sentences[pre_context_start])
                sequence_pattern.insert(0, False)

            if self.CUT_PRE and has_prev_sent() and pre_context_is_too_short():
                pre_context_start -= 1
                too_long_pre_sent = sentences[pre_context_start]
                cut_sent = too_long_pre_sent[-(self.PRE_CHARS - pre_context_len):]
                models.log.debug(f"====CUT_PRE===={pre_context_len}:{too_long_pre_sent}->{cut_sent}")
                after_first_space = cut_sent.index(" ") + 1
                cut_sent = cut_sent[after_first_space:]
                if cut_sent:
                    pre_context_len += len(cut_sent)
                    current_block.insert(0, cut_sent)
                    sequence_pattern.insert(0, False)

            post_context_len = 0
            post_context_end = block_end
            POST_CHARS = self.MAX_CHARS - current_block_len - pre_context_len

            def it_fits_post_chars_limit():
                return T2TDocModel.it_fits_into_the_limit(post_context_len, len(sentences[post_context_end + 1]), POST_CHARS)

            while has_next_sent(post_context_end) and it_fits_post_chars_limit():
                post_context_end += 1
                post_context_len += len(sentences[post_context_end])
                current_block.append(sentences[post_context_end])
                sequence_pattern.append(False)

            sequences.append({
                "sequence": ' ¬ '.join(current_block),
                "pattern": sequence_pattern
            })
            block_start = block_end + 1

        return sequences

    def _postproc_context(self, translated_blocks, patterns, original_untranslated_sentences):
        assert len(translated_blocks) == len(patterns)
        i = 0
        outputs = []
        for block in translated_blocks:
            models.log.debug(f"===== postprocessing block\n{block}\n")
            sents = block.split(' ¬ ')
            pattern = patterns[i]
            i += 1
            expected = len(pattern)
            found = len(sents)
            if found != expected:
                models.log.warn(f"expected={expected} ({pattern}), but got {found}:\n{block}\n")
                current_sent_i = len(outputs)
                translate_again = original_untranslated_sentences[current_sent_i:current_sent_i+sum(pattern)]
                models.log.warn(f"===TRANSLATING_AGAIN==={current_sent_i}:{sum(pattern)}={translate_again}")
                outputs += self._do_send_request(translate_again)
            else:
                for b, sent in zip(pattern, sents):
                    if b:
                        outputs.append(sent)
        return outputs


class T2TModelWithScores(T2TModel):
    def send_sentences_to_backend(self, sentences, src, tgt):
        return self._do_send_request(sentences, with_scores=True)

    def reconstruct_formatting(self, outputs, newlines_after):
        """
        reimplemeneted for outputs_with_scores
        :param outputs:
        :param newlines_after:
        :return:
        """
        for i in newlines_after:
            if i >= 0:
                outputs[i]['output_text'] += '\n'
        return outputs
