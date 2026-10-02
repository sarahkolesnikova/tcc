-- Anomaly Detector — esquema do Supabase (rode no SQL Editor do projeto).
-- Também é reaproveitado pelo fallback local (SQLite), que ignora as linhas de RLS.

create table if not exists files (
    id          uuid primary key,
    filename    text not null,
    storage_key text not null,
    size_bytes  bigint not null,
    sha256      text not null,
    rows        integer not null,
    columns     jsonb not null,
    created_at  timestamptz not null
);

create index if not exists files_created_at_idx on files (created_at);

-- Histórico permanente de análises (sobrevive à limpeza dos arquivos).
create table if not exists analyses (
    id          uuid primary key,
    file_id     uuid not null,
    filename    text not null,
    sha256      text not null,
    parameters  jsonb not null,
    summary     jsonb not null,
    created_at  timestamptz not null
);

create index if not exists analyses_file_idx on analyses (file_id);

-- Acesso só pelo backend (chave service_role). Nenhuma política pública.
alter table files enable row level security;
alter table analyses enable row level security;

-- Bucket privado para os arquivos enviados:
-- Storage → New bucket → nome "uploads", Public = desligado.
