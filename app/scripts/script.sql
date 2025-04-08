drop table if exists users cascade;
drop table if exists applications cascade;
drop table if exists documents cascade;
drop table if exists ocr_results cascade;
drop table if exists analysis_results cascade;

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    role varchar not null check (role in ('admin', 'teacher')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

insert into users(name, username, password_hash, role) values 
('سأغادر غدا', 'user1', '$2a$12$i76sbEizvAADgm/nDcccvOGSixa9kjzd2qmmlTVADYQ.fUxo4J51q', 'teacher');


select * from users;

select * from documents;

select * from applications;