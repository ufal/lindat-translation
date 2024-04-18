import requests

class BatchRequest:
    def __init__(self, batch_max_bytes, callback, compute_size=lambda x: len(x.encode())):
        self.batch = []
        self.batch_current_bytes = 0
        self.batch_max_bytes = batch_max_bytes
        self.callback = callback
        self.compute_size = compute_size

        self.results = []

    def _send_batch(self):
        self.results += self.callback(self.batch)
        self.batch = []
        self.batch_current_bytes = 0

    def __call__(self, line):
        size = self.compute_size(line)
        if self.batch_current_bytes + size > self.batch_max_bytes:
            self._send_batch()
        self.batch.append(line)
        self.batch_current_bytes += size

    def flush(self):
        if self.batch:
            self._send_batch()

def _send_batch(batch, src_lang, trg_lang):
    source_tokens, target_tokens = zip(*batch)
    alignments = align_tokens_request(source_tokens, target_tokens, src_lang, trg_lang)
    return alignments["alignment"]

def align_tokens_request(source_tokens, target_tokens, src_lang, trg_lang):
    url = f'https://lindat.cz/services/text-aligner/align/{src_lang}-{trg_lang}'
    headers = {
        'Content-Type': 'application/json',
    }
    data = {
        'src_tokens': source_tokens,
        'trg_tokens': target_tokens,
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        return response.json()
    else:
        raise ValueError(f"Error: {response.status_code} {response.text}")

def align_tokens(source_lines, target_lines, src_lang, trg_lang, batch_max_bytes=10000):
    # return align_tokens_request(source_lines, target_lines, src_lang, trg_lang)["alignment"]
    callback = lambda l: _send_batch(l, src_lang, trg_lang)
    compute_size = lambda x: len(" ".join(x[0]).encode()) + len(" ".join(x[1]).encode())
    batchreq = BatchRequest(batch_max_bytes, callback, compute_size)

    for src, trg in zip(source_lines, target_lines):
        batchreq((src, trg))
    batchreq.flush()

    return batchreq.results