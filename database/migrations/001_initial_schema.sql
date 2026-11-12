-- ====================================================================
-- LIVE PRODUCTION & QUALITY MANAGEMENT SYSTEM
-- PostgreSQL 16 Normalized Database Schema Migration
-- Migration: 001_initial_schema.sql
-- ====================================================================

BEGIN;

-- 1. ROLES TABLE
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 2. USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_ad_user BOOLEAN DEFAULT FALSE NOT NULL,
    department VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 3. MACHINES TABLE
CREATE TABLE IF NOT EXISTS machines (
    id SERIAL PRIMARY KEY,
    machine_code VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    model VARCHAR(100),
    line_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 4. CUSTOMERS TABLE
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    customer_code VARCHAR(100) UNIQUE NOT NULL,
    customer_name VARCHAR(200) NOT NULL,
    contact_person VARCHAR(150),
    email VARCHAR(150),
    phone VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 5. FRAMES TABLE
CREATE TABLE IF NOT EXISTS frames (
    id SERIAL PRIMARY KEY,
    frame_code VARCHAR(100) UNIQUE NOT NULL,
    frame_name VARCHAR(150) NOT NULL,
    description VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 6. SHIFTS TABLE
CREATE TABLE IF NOT EXISTS shifts (
    id SERIAL PRIMARY KEY,
    shift_name VARCHAR(50) UNIQUE NOT NULL,
    start_time VARCHAR(10) NOT NULL,
    end_time VARCHAR(10) NOT NULL,
    description VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 7. PRODUCTION RECORDS TABLE
CREATE TABLE IF NOT EXISTS production_records (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    machine_id INTEGER NOT NULL REFERENCES machines(id) ON DELETE RESTRICT,
    frame_id INTEGER NOT NULL REFERENCES frames(id) ON DELETE RESTRICT,
    shift_id INTEGER NOT NULL REFERENCES shifts(id) ON DELETE RESTRICT,
    operator_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    supervisor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    
    static_time NUMERIC(10, 2) DEFAULT 0.0 NOT NULL,
    mounting_time NUMERIC(10, 2) DEFAULT 0.0 NOT NULL,
    rotational_time NUMERIC(10, 2) DEFAULT 0.0 NOT NULL,
    dismantling_time NUMERIC(10, 2) DEFAULT 0.0 NOT NULL,
    
    total_testing_time NUMERIC(10, 2) DEFAULT 0.0 NOT NULL,
    cycle_time_hours NUMERIC(10, 4) DEFAULT 0.0 NOT NULL,
    
    test_result VARCHAR(50) DEFAULT 'PASS' NOT NULL,
    nc_raised BOOLEAN DEFAULT FALSE NOT NULL,
    rework_time NUMERIC(10, 2) DEFAULT 0.0 NOT NULL,
    
    approval_status VARCHAR(50) DEFAULT 'PENDING' NOT NULL,
    approved_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    approved_at TIMESTAMP WITH TIME ZONE,
    rejection_reason TEXT,
    notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 8. QUALITY RECORDS TABLE
CREATE TABLE IF NOT EXISTS quality_records (
    id SERIAL PRIMARY KEY,
    production_record_id INTEGER REFERENCES production_records(id) ON DELETE SET NULL,
    machine_id INTEGER NOT NULL REFERENCES machines(id) ON DELETE RESTRICT,
    defect_description TEXT NOT NULL,
    defect_category VARCHAR(100) NOT NULL,
    date_of_occurrence DATE NOT NULL,
    responsible_department VARCHAR(100) NOT NULL,
    severity VARCHAR(50) DEFAULT 'MEDIUM' NOT NULL,
    rework_minutes NUMERIC(10, 2) DEFAULT 0.0 NOT NULL,
    created_by_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 9. NC RECORDS TABLE (Non-conformance cases)
CREATE TABLE IF NOT EXISTS nc_records (
    id SERIAL PRIMARY KEY,
    nc_number VARCHAR(50) UNIQUE NOT NULL,
    quality_record_id INTEGER REFERENCES quality_records(id) ON DELETE SET NULL,
    production_record_id INTEGER REFERENCES production_records(id) ON DELETE SET NULL,
    machine_id INTEGER NOT NULL REFERENCES machines(id) ON DELETE RESTRICT,
    
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    defect_category VARCHAR(100) NOT NULL,
    classification VARCHAR(50) DEFAULT 'MAJOR' NOT NULL,
    responsible_department VARCHAR(100) NOT NULL,
    quality_engineer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    
    status VARCHAR(50) DEFAULT 'OPEN' NOT NULL,
    root_cause TEXT,
    corrective_action TEXT,
    preventive_action TEXT,
    
    closed_at TIMESTAMP WITH TIME ZONE,
    closed_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    closure_notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 10. REWORK RECORDS TABLE
CREATE TABLE IF NOT EXISTS rework_records (
    id SERIAL PRIMARY KEY,
    nc_record_id INTEGER NOT NULL REFERENCES nc_records(id) ON DELETE CASCADE,
    production_record_id INTEGER REFERENCES production_records(id) ON DELETE SET NULL,
    machine_id INTEGER NOT NULL REFERENCES machines(id) ON DELETE RESTRICT,
    
    rework_minutes NUMERIC(10, 2) DEFAULT 0.0 NOT NULL,
    rework_description TEXT NOT NULL,
    rework_done_by_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    verified_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    completion_date DATE,
    
    rework_status VARCHAR(50) DEFAULT 'PENDING' NOT NULL,
    notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 11. AUDIT LOGS TABLE
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    username VARCHAR(100) NOT NULL,
    role VARCHAR(50),
    action VARCHAR(50) NOT NULL,
    module VARCHAR(50) NOT NULL,
    record_id VARCHAR(50),
    
    previous_values JSONB,
    new_values JSONB,
    ip_address VARCHAR(50),
    user_agent VARCHAR(255),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- INDEXES FOR HIGH-PERFORMANCE QUERYING & POWER BI DIRECTQUERY
CREATE INDEX IF NOT EXISTS idx_prod_date ON production_records(date);
CREATE INDEX IF NOT EXISTS idx_prod_machine ON production_records(machine_id);
CREATE INDEX IF NOT EXISTS idx_prod_shift ON production_records(shift_id);
CREATE INDEX IF NOT EXISTS idx_prod_customer ON production_records(customer_id);
CREATE INDEX IF NOT EXISTS idx_prod_operator ON production_records(operator_id);
CREATE INDEX IF NOT EXISTS idx_prod_approval ON production_records(approval_status);
CREATE INDEX IF NOT EXISTS idx_prod_nc_raised ON production_records(nc_raised);

CREATE INDEX IF NOT EXISTS idx_qr_date ON quality_records(date_of_occurrence);
CREATE INDEX IF NOT EXISTS idx_qr_category ON quality_records(defect_category);
CREATE INDEX IF NOT EXISTS idx_qr_dept ON quality_records(responsible_department);

CREATE INDEX IF NOT EXISTS idx_nc_status ON nc_records(status);
CREATE INDEX IF NOT EXISTS idx_nc_machine ON nc_records(machine_id);
CREATE INDEX IF NOT EXISTS idx_nc_qe ON nc_records(quality_engineer_id);
CREATE INDEX IF NOT EXISTS idx_nc_classification ON nc_records(classification);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_module ON audit_logs(module);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);

COMMIT;

