-- ZANA ID: Identity & Multi-tenancy Schema
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 1. Identity Tables
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    dna_metadata JSONB DEFAULT '{}',
    is_master BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS invitations (
    token TEXT PRIMARY KEY,
    created_by UUID REFERENCES users(id),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Ensure Core Tables exist for RLS application
CREATE TABLE IF NOT EXISTS episodes (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id   TEXT NOT NULL,
    timestamp    TIMESTAMPTZ NOT NULL DEFAULT now(),
    event_type   TEXT NOT NULL,
    subject      TEXT NOT NULL,
    context      JSONB,
    outcome      TEXT,
    outcome_type TEXT,
    embedding    vector(384),
    tags         TEXT[],
    project      TEXT
);

-- 3. Multi-tenancy Enhancements
ALTER TABLE episodes ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES users(id);

-- 4. Row-Level Security (RLS)
ALTER TABLE episodes ENABLE ROW LEVEL SECURITY;

-- Drop policy if exists to allow re-run
DROP POLICY IF EXISTS user_isolation ON episodes;
CREATE POLICY user_isolation ON episodes 
    USING (owner_id = current_setting('zana.current_user_id', true)::uuid);
