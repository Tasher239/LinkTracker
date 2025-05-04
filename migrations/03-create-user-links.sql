-- Liquibase formatted SQL
-- changeset yourname:03
CREATE TABLE IF NOT EXISTS user_links (
    user_id BIGINT NOT NULL REFERENCES users(tg_chat_id) ON DELETE CASCADE,
    link_id INTEGER NOT NULL REFERENCES links(id) ON DELETE CASCADE,
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    filters TEXT[] DEFAULT ARRAY[]::TEXT[],
    PRIMARY KEY (user_id, link_id)
);
