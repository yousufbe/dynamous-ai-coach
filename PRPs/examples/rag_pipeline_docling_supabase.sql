-- Hybrid RAG ingestion schema for Docling + Supabase PGVector.
-- Run inside the Supabase/PostgreSQL database that backs the ingestion pipeline.

create extension if not exists vector;
create extension if not exists pg_trgm;

create schema if not exists rag;

create table if not exists rag.sources (
    id uuid primary key default gen_random_uuid(),
    location text not null unique,
    document_name text not null,
    document_type text not null,
    source_type text not null,
    content_hash text not null,
    status text not null default 'pending',
    metadata jsonb not null default '{}'::jsonb,
    error_message text,
    embedding_model text not null default 'Qwen/Qwen3-Embedding-0.6B',
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists rag.chunks (
    id uuid primary key default gen_random_uuid(),
    source_id uuid not null references rag.sources(id) on delete cascade,
    chunk_index integer not null,
    page_number integer,
    structural_type text,
    section_heading text,
    text text not null,
    text_tsv tsvector generated always as (to_tsvector('english', text)) stored,
    text_trgm text generated always as (text) stored,
    embedding vector(1024) not null,
    embedding_model text not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default timezone('utc', now()),
    unique(source_id, chunk_index)
);

create index if not exists idx_chunks_source_id on rag.chunks (source_id);
create index if not exists idx_chunks_text_tsv on rag.chunks using gin (text_tsv);
create index if not exists idx_chunks_text_trgm on rag.chunks using gin (text_trgm gin_trgm_ops);
create index if not exists idx_chunks_embedding on rag.chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100);

create or replace function rag.match_chunks(
    query_embedding vector(1024),
    match_count integer = 10,
    min_score float = 0.2
) returns table (
    chunk_id uuid,
    source_id uuid,
    document_name text,
    content text,
    score float,
    metadata jsonb
) language plpgsql as $$
begin
    return query
    select
        c.id,
        c.source_id,
        s.document_name,
        c.text,
        1 - (c.embedding <=> query_embedding) as score,
        c.metadata
    from rag.chunks c
    join rag.sources s on s.id = c.source_id
    where 1 - (c.embedding <=> query_embedding) >= min_score
    order by c.embedding <=> query_embedding
    limit match_count;
end;
$$;

comment on table rag.sources is 'Document-level metadata + ingestion status for Docling pipeline';
comment on table rag.chunks is 'Chunk-level storage with PGVector, tsvector, and trigram indexes for hybrid search';
