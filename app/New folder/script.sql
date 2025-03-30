drop table if exists users cascade;
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    role varchar not null check (role in ('admin', 'teacher'),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

select * from users