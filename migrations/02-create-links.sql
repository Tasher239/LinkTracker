-- Liquibase formatted SQL
-- changeset yourname:02
CREATE TABLE IF NOT EXISTS links(
    id SERIAL PRIMARY KEY,
    link_url TEXT NOT NULL UNIQUE
);
