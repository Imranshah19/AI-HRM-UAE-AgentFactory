-- ══════════════════════════════════════════════════════════════════════════
-- AI-HRMS — PostgreSQL Initialization Script
-- Runs once when the postgres container is first created.
-- ══════════════════════════════════════════════════════════════════════════

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";    -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";     -- gen_random_uuid(), encryption
CREATE EXTENSION IF NOT EXISTS "pg_trgm";      -- Trigram indexes for ILIKE search
CREATE EXTENSION IF NOT EXISTS "unaccent";     -- Accent-insensitive search

-- Set default timezone
SET timezone = 'UTC';
