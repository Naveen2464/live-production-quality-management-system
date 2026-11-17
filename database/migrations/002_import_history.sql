-- ====================================================================
-- LIVE PRODUCTION & QUALITY MANAGEMENT SYSTEM
-- PostgreSQL 16 Migration: 002_import_history.sql
-- ====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS import_history (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    total_rows INTEGER DEFAULT 0 NOT NULL,
    valid_rows INTEGER DEFAULT 0 NOT NULL,
    rejected_rows INTEGER DEFAULT 0 NOT NULL,
    duplicate_rows INTEGER DEFAULT 0 NOT NULL,
    status VARCHAR(50) DEFAULT 'COMPLETED' NOT NULL,
    imported_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    imported_by_username VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS import_errors (
    id SERIAL PRIMARY KEY,
    import_history_id INTEGER NOT NULL REFERENCES import_history(id) ON DELETE CASCADE,
    row_number INTEGER NOT NULL,
    raw_data JSONB,
    error_type VARCHAR(100) NOT NULL,
    error_message TEXT NOT NULL,
    field_name VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_import_history_created ON import_history(created_at);
CREATE INDEX IF NOT EXISTS idx_import_history_type ON import_history(file_type);
CREATE INDEX IF NOT EXISTS idx_import_errors_batch ON import_errors(import_history_id);

COMMIT;

