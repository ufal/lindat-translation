CREATE TABLE IF NOT EXISTS translations(src_lang TEXT, tgt_lang TEXT, src TEXT, tgt TEXT, author TEXT, frontend TEXT,
 inserted DATETIME default current_timestamp);
ALTER TABLE translations ADD ip_address TEXT default 'unknown';
CREATE TABLE IF NOT EXISTS access(src_lang TEXT, tgt_lang TEXT, input_nfc_len INTEGER, author TEXT, frontend
    TEXT, duration_us INTEGER, inserted DATETIME default current_timestamp);
ALTER TABLE translations ADD input_type TEXT default 'keyboard';
ALTER TABLE access ADD input_type TEXT default 'keyboard';
ALTER TABLE translations ADD COLUMN app_version TEXT default 'unknown';
ALTER TABLE translations ADD COLUMN user_lang TEXT default 'unknown';
ALTER TABLE access ADD COLUMN app_version TEXT default 'unknown';
ALTER TABLE access ADD COLUMN user_lang TEXT default 'unknown';
