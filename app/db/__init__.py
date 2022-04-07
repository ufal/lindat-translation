import os
import sqlite3
from flask import g

dirname = os.path.dirname(__file__)

DATABASE = os.path.join(dirname, 'database.db')


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


def init_db():
    db = sqlite3.connect(DATABASE)
    with open(os.path.join(dirname, 'schema.sql'), mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


def log_translation(src_lang, tgt_lang, src, tgt, author, frontend, ip_address):
    db = get_db()
    db.cursor().execute("INSERT INTO translations (src_lang, tgt_lang, src, tgt, author, frontend, ip_address) VALUES (?,?,?,?,?,?,?)",
            (src_lang, tgt_lang, src, tgt, author, frontend, ip_address))
    db.commit()


def log_access(src_lang, tgt_lang, author, frontend, input_nfc_len, duration_us):
    db = get_db()
    db.cursor().execute("INSERT INTO access (src_lang, tgt_lang, input_nfc_len, author, frontend, duration_us) VALUES (?,?,?,?,?,?)",
            (src_lang, tgt_lang, input_nfc_len, author, frontend, duration_us))
    db.commit()
