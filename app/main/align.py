import requests

def align_tokens(source_tokens, target_tokens, src_lang, trg_lang):
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
