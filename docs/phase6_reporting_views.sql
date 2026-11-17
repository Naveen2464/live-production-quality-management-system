-- ====================================================================
-- LIVE PRODUCTION & QUALITY MANAGEMENT SYSTEM
-- Phase 6: Consolidated Star Schema Reporting Views & Security
-- File: docs/phase6_reporting_views.sql
-- Compatible with: PostgreSQL 16 (and SQLite dev fallback via create_reporting_views.py)
-- ====================================================================

-- 1. DIMENSION DATE VIEW
CREATE OR REPLACE VIEW vw_dim_date AS
SELECT
    CAST(TO_CHAR(d, 'YYYYMMDD') AS INTEGER) AS date_key,
    d::DATE AS full_date,
    CAST(EXTRACT(YEAR FROM d) AS INTEGER) AS calendar_year,
    CAST(EXTRACT(QUARTER FROM d) AS INTEGER) AS calendar_quarter,
    'Q' || CAST(EXTRACT(QUARTER FROM d) AS VARCHAR) AS quarter_name,
    TRIM(TO_CHAR(d, 'Month')) AS month_name,
    CAST(EXTRACT(MONTH FROM d) AS INTEGER) AS month_number,
    TO_CHAR(d, 'YYYY-MM') AS year_month,
    CAST(EXTRACT(DAY FROM d) AS INTEGER) AS day_of_month,
    TRIM(TO_CHAR(d, 'Day')) AS day_name,
    CAST(EXTRACT(ISODOW FROM d) AS INTEGER) AS day_of_week,
    CASE WHEN EXTRACT(ISODOW FROM d) IN (6, 7) THEN 1 ELSE 0 END AS is_weekend
FROM generate_series(
    '2025-01-01'::DATE,
    '2030-12-31'::DATE,
    '1 day'::INTERVAL
) AS d;

-- 2. DIMENSION MACHINE VIEW
CREATE OR REPLACE VIEW vw_dim_machine AS
SELECT
    m.id AS machine_key,
    m.machine_code,
    m.name AS machine_name,
    COALESCE(m.model, 'Standard') AS model,
    COALESCE(m.line_name, 'Main Line') AS line_name,
    CASE WHEN m.is_active THEN 1 ELSE 0 END AS is_active
FROM machines m;

-- 3. DIMENSION CUSTOMER VIEW
CREATE OR REPLACE VIEW vw_dim_customer AS
SELECT
    c.id AS customer_key,
    c.customer_code,
    c.customer_name,
    COALESCE(c.contact_person, 'N/A') AS contact_person,
    COALESCE(c.email, 'N/A') AS email,
    COALESCE(c.phone, 'N/A') AS phone,
    CASE WHEN c.is_active THEN 1 ELSE 0 END AS is_active
FROM customers c;

-- 4. DIMENSION FRAME VIEW
CREATE OR REPLACE VIEW vw_dim_frame AS
SELECT
    f.id AS frame_key,
    f.frame_code,
    f.frame_name,
    COALESCE(f.description, 'Standard Frame') AS description,
    CASE WHEN f.is_active THEN 1 ELSE 0 END AS is_active
FROM frames f;

-- 5. DIMENSION SHIFT VIEW
CREATE OR REPLACE VIEW vw_dim_shift AS
SELECT
    s.id AS shift_key,
    s.shift_name,
    s.start_time,
    s.end_time,
    s.start_time || ' - ' || s.end_time AS shift_window,
    COALESCE(s.description, s.shift_name) AS description,
    CASE WHEN s.is_active THEN 1 ELSE 0 END AS is_active
FROM shifts s;

-- 6. DIMENSION PERSONNEL VIEW
CREATE OR REPLACE VIEW vw_dim_personnel AS
SELECT
    u.id AS user_key,
    u.username,
    u.full_name,
    COALESCE(u.email, 'N/A') AS email,
    r.name AS role_name,
    COALESCE(u.department, 'Operations') AS department,
    CASE WHEN u.is_active THEN 1 ELSE 0 END AS is_active,
    CASE WHEN u.is_ad_user THEN 1 ELSE 0 END AS is_ad_user
FROM users u
JOIN roles r ON u.role_id = r.id;

-- 7. DIMENSION DEFECT CATEGORY VIEW
CREATE OR REPLACE VIEW vw_dim_defect_category AS
SELECT
    cat.category_name,
    CASE
        WHEN cat.category_name ILIKE '%Electrical%' OR cat.category_name ILIKE '%Insulation%' OR cat.category_name ILIKE '%Resistance%' THEN 'Electrical'
        WHEN cat.category_name ILIKE '%Mechanical%' OR cat.category_name ILIKE '%Vibration%' OR cat.category_name ILIKE '%Bearing%' THEN 'Mechanical'
        WHEN cat.category_name ILIKE '%Frame%' OR cat.category_name ILIKE '%Housing%' OR cat.category_name ILIKE '%Body%' THEN 'Structural'
        WHEN cat.category_name ILIKE '%Assembly%' OR cat.category_name ILIKE '%Fitting%' THEN 'Assembly'
        ELSE 'General'
    END AS primary_domain
FROM (
    SELECT DISTINCT defect_category AS category_name FROM quality_records WHERE defect_category IS NOT NULL
    UNION
    SELECT DISTINCT defect_category AS category_name FROM nc_records WHERE defect_category IS NOT NULL
) cat;

-- 8. DIMENSION SEVERITY VIEW
CREATE OR REPLACE VIEW vw_dim_severity AS
SELECT
    sev.severity_name,
    CASE
        WHEN UPPER(sev.severity_name) = 'CRITICAL' THEN 1
        WHEN UPPER(sev.severity_name) = 'HIGH' THEN 2
        WHEN UPPER(sev.severity_name) = 'MAJOR' THEN 2
        WHEN UPPER(sev.severity_name) = 'MEDIUM' THEN 3
        WHEN UPPER(sev.severity_name) = 'MODERATE' THEN 3
        WHEN UPPER(sev.severity_name) = 'MINOR' THEN 4
        WHEN UPPER(sev.severity_name) = 'LOW' THEN 5
        ELSE 6
    END AS severity_rank,
    CASE
        WHEN UPPER(sev.severity_name) IN ('CRITICAL', 'HIGH', 'MAJOR') THEN 'High Priority'
        WHEN UPPER(sev.severity_name) IN ('MEDIUM', 'MODERATE') THEN 'Medium Priority'
        ELSE 'Low Priority'
    END AS priority_tier
FROM (
    SELECT DISTINCT severity AS severity_name FROM quality_records WHERE severity IS NOT NULL
    UNION
    SELECT DISTINCT classification AS severity_name FROM nc_records WHERE classification IS NOT NULL
) sev;

-- 9. FACT PRODUCTION VIEW
CREATE OR REPLACE VIEW vw_fact_production AS
SELECT
    pr.id AS production_run_key,
    CAST(TO_CHAR(pr.date, 'YYYYMMDD') AS INTEGER) AS date_key,
    pr.date AS production_date,
    pr.machine_id AS machine_key,
    pr.frame_id AS frame_key,
    pr.shift_id AS shift_key,
    pr.customer_id AS customer_key,
    pr.operator_id AS operator_key,
    pr.supervisor_id AS supervisor_key,
    pr.approved_by_id AS approved_by_key,
    CAST(pr.static_time AS DOUBLE PRECISION) AS static_time_minutes,
    CAST(pr.mounting_time AS DOUBLE PRECISION) AS mounting_time_minutes,
    CAST(pr.rotational_time AS DOUBLE PRECISION) AS rotational_time_minutes,
    CAST(pr.dismantling_time AS DOUBLE PRECISION) AS dismantling_time_minutes,
    CAST(pr.total_testing_time AS DOUBLE PRECISION) AS total_testing_time_minutes,
    CAST(pr.cycle_time_hours AS DOUBLE PRECISION) AS cycle_time_hours,
    CAST(pr.rework_time AS DOUBLE PRECISION) AS rework_time_minutes,
    pr.test_result,
    pr.approval_status,
    CASE WHEN UPPER(pr.test_result) = 'PASS' THEN 1 ELSE 0 END AS is_pass,
    CASE WHEN UPPER(pr.test_result) = 'FAIL' THEN 1 ELSE 0 END AS is_fail,
    CASE WHEN pr.nc_raised THEN 1 ELSE 0 END AS is_nc_raised,
    CASE WHEN UPPER(pr.approval_status) = 'APPROVED' THEN 1 ELSE 0 END AS is_approved,
    CASE WHEN UPPER(pr.approval_status) = 'PENDING' THEN 1 ELSE 0 END AS is_pending,
    CASE WHEN UPPER(pr.approval_status) = 'REJECTED' THEN 1 ELSE 0 END AS is_rejected,
    pr.created_at,
    pr.updated_at
FROM production_records pr;

-- 10. FACT QUALITY & NC VIEW
CREATE OR REPLACE VIEW vw_fact_quality_nc AS
SELECT
    nc.id AS nc_key,
    nc.nc_number,
    nc.production_record_id AS production_run_key,
    nc.quality_record_id AS quality_record_key,
    CAST(TO_CHAR(COALESCE(nc.created_at::DATE, qr.date_of_occurrence, pr.date), 'YYYYMMDD') AS INTEGER) AS date_key,
    COALESCE(nc.created_at::DATE, qr.date_of_occurrence, pr.date) AS nc_date,
    nc.machine_id AS machine_key,
    pr.customer_id AS customer_key,
    pr.frame_id AS frame_key,
    pr.shift_id AS shift_key,
    nc.quality_engineer_id AS quality_engineer_key,
    nc.closed_by_id AS closed_by_key,
    nc.title,
    nc.defect_category,
    nc.classification AS severity,
    nc.responsible_department,
    nc.status,
    CASE WHEN UPPER(nc.status) = 'OPEN' THEN 1 ELSE 0 END AS is_open,
    CASE WHEN UPPER(nc.status) = 'IN_PROGRESS' THEN 1 ELSE 0 END AS is_in_progress,
    CASE WHEN UPPER(nc.status) = 'UNDER_REVIEW' THEN 1 ELSE 0 END AS is_under_review,
    CASE WHEN UPPER(nc.status) = 'CLOSED' THEN 1 ELSE 0 END AS is_closed,
    CASE 
        WHEN nc.closed_at IS NOT NULL 
        THEN ROUND(CAST(EXTRACT(EPOCH FROM (nc.closed_at - nc.created_at)) / 3600.0 AS NUMERIC), 2)
        ELSE NULL 
    END AS resolution_duration_hours,
    CAST(COALESCE(qr.rework_minutes, 0.0) AS DOUBLE PRECISION) AS logged_rework_minutes,
    COALESCE(nc.root_cause, 'Not documented') AS root_cause,
    COALESCE(nc.corrective_action, 'Not documented') AS corrective_action,
    COALESCE(nc.preventive_action, 'Not documented') AS preventive_action,
    nc.closure_notes,
    nc.created_at,
    nc.closed_at
FROM nc_records nc
LEFT JOIN quality_records qr ON nc.quality_record_id = qr.id
LEFT JOIN production_records pr ON nc.production_record_id = pr.id;

-- 11. FACT REWORK VIEW
CREATE OR REPLACE VIEW vw_fact_rework AS
SELECT
    rw.id AS rework_key,
    rw.nc_record_id AS nc_key,
    rw.production_record_id AS production_run_key,
    rw.machine_id AS machine_key,
    CAST(TO_CHAR(COALESCE(rw.completion_date, rw.created_at::DATE), 'YYYYMMDD') AS INTEGER) AS date_key,
    COALESCE(rw.completion_date, rw.created_at::DATE) AS rework_date,
    rw.rework_done_by_id AS technician_key,
    rw.verified_by_id AS verifier_key,
    CAST(rw.rework_minutes AS DOUBLE PRECISION) AS rework_minutes,
    CAST(ROUND(rw.rework_minutes / 60.0, 2) AS DOUBLE PRECISION) AS rework_hours,
    rw.rework_status,
    rw.rework_description,
    CASE WHEN UPPER(rw.rework_status) = 'COMPLETED' THEN 1 ELSE 0 END AS is_completed,
    CASE WHEN rw.verified_by_id IS NOT NULL THEN 1 ELSE 0 END AS is_verified,
    rw.created_at,
    rw.updated_at
FROM rework_records rw;

-- 12. SECURITY & PERMISSIONS
-- Note: Credentials must be loaded securely via environment variables or secret manager.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'nidec_reporting_user') THEN
        CREATE ROLE nidec_reporting_user WITH LOGIN;
        -- Set password dynamically via deployment automation:
        -- ALTER ROLE nidec_reporting_user WITH PASSWORD '${NIDEC_REPORTING_PASSWORD}';
    END IF;
END
$$;

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM nidec_reporting_user;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM nidec_reporting_user;

GRANT CONNECT ON DATABASE nidec_production_db TO nidec_reporting_user;
GRANT USAGE ON SCHEMA public TO nidec_reporting_user;

GRANT SELECT ON vw_dim_date TO nidec_reporting_user;
GRANT SELECT ON vw_dim_machine TO nidec_reporting_user;
GRANT SELECT ON vw_dim_customer TO nidec_reporting_user;
GRANT SELECT ON vw_dim_frame TO nidec_reporting_user;
GRANT SELECT ON vw_dim_shift TO nidec_reporting_user;
GRANT SELECT ON vw_dim_personnel TO nidec_reporting_user;
GRANT SELECT ON vw_dim_defect_category TO nidec_reporting_user;
GRANT SELECT ON vw_dim_severity TO nidec_reporting_user;

GRANT SELECT ON vw_fact_production TO nidec_reporting_user;
GRANT SELECT ON vw_fact_quality_nc TO nidec_reporting_user;
GRANT SELECT ON vw_fact_rework TO nidec_reporting_user;

REVOKE SELECT ON users FROM nidec_reporting_user;
REVOKE SELECT ON audit_logs FROM nidec_reporting_user;

