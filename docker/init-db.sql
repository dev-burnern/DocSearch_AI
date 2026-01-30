-- ============================================================
-- DocSearch AI - PostgreSQL Initialization Script
-- ============================================================

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create enums
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('admin', 'manager', 'user', 'viewer');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE classification AS ENUM ('public', 'internal', 'confidential', 'restricted');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE document_status AS ENUM ('pending', 'processing', 'ready', 'error', 'deleted');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE job_type AS ENUM ('extract', 'chunk', 'embed', 'full_process', 'reindex');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE job_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE permission AS ENUM ('read', 'write', 'delete', 'share', 'admin');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE audit_action AS ENUM (
        'login', 'logout', 'login_failed',
        'document_view', 'document_download', 'document_upload', 
        'document_delete', 'document_share',
        'search', 'chat',
        'user_create', 'user_update', 'user_delete',
        'permission_grant', 'permission_revoke',
        'admin_action'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE docsearch TO docsearch;
