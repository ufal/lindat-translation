CREATE TABLE IF NOT EXISTS translations(src_lang TEXT, tgt_lang TEXT, src TEXT, tgt TEXT, author TEXT, frontend TEXT,
 inserted DATETIME default current_timestamp);
ALTER TABLE translations ADD ip_address TEXT default 'unknown';
