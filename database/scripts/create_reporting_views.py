"""
Database Script: create_reporting_views.py
Applies reporting views to PostgreSQL (production) or SQLite (local development/testing).
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from sqlalchemy import text
from app.db.session import engine

def apply_views():
    dialect_name = engine.dialect.name
    print(f"Deploying Star Schema Reporting Views to {dialect_name} database...")
    
    with engine.connect() as conn:
        if dialect_name == "postgresql":
            migration_path = os.path.join(os.path.dirname(__file__), "..", "migrations", "003_reporting_views.sql")
            with open(migration_path, "r", encoding="utf-8") as f:
                sql_content = f.read()
            conn.execute(text(sql_content))
            conn.commit()
            print("Successfully deployed PostgreSQL reporting views and configured nidec_reporting_user.")
        else:
            # SQLite-compatible view statements for testing/local dev
            print("Applying SQLite-compatible reporting views for local testing...")
            
            # 1. Dim Date (recursive CTE for 2025 to 2030)
            conn.execute(text("DROP VIEW IF EXISTS vw_dim_date;"))
            conn.execute(text("""
                CREATE VIEW vw_dim_date AS
                WITH RECURSIVE date_series(d) AS (
                    SELECT DATE('2025-01-01')
                    UNION ALL
                    SELECT DATE(d, '+1 day')
                    FROM date_series
                    WHERE d < DATE('2030-12-31')
                )
                SELECT
                    CAST(strftime('%Y%m%d', d) AS INTEGER) AS date_key,
                    d AS full_date,
                    CAST(strftime('%Y', d) AS INTEGER) AS calendar_year,
                    CAST(((CAST(strftime('%m', d) AS INTEGER) - 1) / 3) + 1 AS INTEGER) AS calendar_quarter,
                    'Q' || CAST(((CAST(strftime('%m', d) AS INTEGER) - 1) / 3) + 1 AS TEXT) AS quarter_name,
                    CASE strftime('%m', d)
                        WHEN '01' THEN 'January' WHEN '02' THEN 'February' WHEN '03' THEN 'March'
                        WHEN '04' THEN 'April'   WHEN '05' THEN 'May'      WHEN '06' THEN 'June'
                        WHEN '07' THEN 'July'    WHEN '08' THEN 'August'   WHEN '09' THEN 'September'
                        WHEN '10' THEN 'October' WHEN '11' THEN 'November' WHEN '12' THEN 'December'
                    END AS month_name,
                    CAST(strftime('%m', d) AS INTEGER) AS month_number,
                    strftime('%Y-%m', d) AS year_month,
                    CAST(strftime('%d', d) AS INTEGER) AS day_of_month,
                    CASE strftime('%w', d)
                        WHEN '0' THEN 'Sunday'    WHEN '1' THEN 'Monday'   WHEN '2' THEN 'Tuesday'
                        WHEN '3' THEN 'Wednesday' WHEN '4' THEN 'Thursday' WHEN '5' THEN 'Friday'
                        WHEN '6' THEN 'Saturday'
                    END AS day_name,
                    CAST(CASE strftime('%w', d) WHEN '0' THEN '7' ELSE strftime('%w', d) END AS INTEGER) AS day_of_week,
                    CASE WHEN strftime('%w', d) IN ('0', '6') THEN 1 ELSE 0 END AS is_weekend
                FROM date_series;
            """))
            
            # 2. Dim Machine
            conn.execute(text("DROP VIEW IF EXISTS vw_dim_machine;"))
            conn.execute(text("""
                CREATE VIEW vw_dim_machine AS
                SELECT
                    m.id AS machine_key,
                    m.machine_code,
                    m.name AS machine_name,
                    COALESCE(m.model, 'Standard') AS model,
                    COALESCE(m.line_name, 'Main Line') AS line_name,
                    CASE WHEN m.is_active THEN 1 ELSE 0 END AS is_active
                FROM machines m;
            """))

            # 3. Dim Customer
            conn.execute(text("DROP VIEW IF EXISTS vw_dim_customer;"))
            conn.execute(text("""
                CREATE VIEW vw_dim_customer AS
                SELECT
                    c.id AS customer_key,
                    c.customer_code,
                    c.customer_name,
                    COALESCE(c.contact_person, 'N/A') AS contact_person,
                    COALESCE(c.email, 'N/A') AS email,
                    COALESCE(c.phone, 'N/A') AS phone,
                    CASE WHEN c.is_active THEN 1 ELSE 0 END AS is_active
                FROM customers c;
            """))

            # 4. Dim Frame
            conn.execute(text("DROP VIEW IF EXISTS vw_dim_frame;"))
            conn.execute(text("""
                CREATE VIEW vw_dim_frame AS
                SELECT
                    f.id AS frame_key,
                    f.frame_code,
                    f.frame_name,
                    COALESCE(f.description, 'Standard Frame') AS description,
                    CASE WHEN f.is_active THEN 1 ELSE 0 END AS is_active
                FROM frames f;
            """))

            # 5. Dim Shift
            conn.execute(text("DROP VIEW IF EXISTS vw_dim_shift;"))
            conn.execute(text("""
                CREATE VIEW vw_dim_shift AS
                SELECT
                    s.id AS shift_key,
                    s.shift_name,
                    s.start_time,
                    s.end_time,
                    s.start_time || ' - ' || s.end_time AS shift_window,
                    COALESCE(s.description, s.shift_name) AS description,
                    CASE WHEN s.is_active THEN 1 ELSE 0 END AS is_active
                FROM shifts s;
            """))

            # 6. Dim Personnel
            conn.execute(text("DROP VIEW IF EXISTS vw_dim_personnel;"))
            conn.execute(text("""
                CREATE VIEW vw_dim_personnel AS
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
            """))

            # 7. Dim Defect Category
            conn.execute(text("DROP VIEW IF EXISTS vw_dim_defect_category;"))
            conn.execute(text("""
                CREATE VIEW vw_dim_defect_category AS
                SELECT
                    cat.category_name,
                    CASE
                        WHEN cat.category_name LIKE '%Electrical%' OR cat.category_name LIKE '%Insulation%' OR cat.category_name LIKE '%Resistance%' THEN 'Electrical'
                        WHEN cat.category_name LIKE '%Mechanical%' OR cat.category_name LIKE '%Vibration%' OR cat.category_name LIKE '%Bearing%' THEN 'Mechanical'
                        WHEN cat.category_name LIKE '%Frame%' OR cat.category_name LIKE '%Housing%' OR cat.category_name LIKE '%Body%' THEN 'Structural'
                        WHEN cat.category_name LIKE '%Assembly%' OR cat.category_name LIKE '%Fitting%' THEN 'Assembly'
                        ELSE 'General'
                    END AS primary_domain
                FROM (
                    SELECT DISTINCT defect_category AS category_name FROM quality_records WHERE defect_category IS NOT NULL
                    UNION
                    SELECT DISTINCT defect_category AS category_name FROM nc_records WHERE defect_category IS NOT NULL
                ) cat;
            """))

            # 8. Dim Severity
            conn.execute(text("DROP VIEW IF EXISTS vw_dim_severity;"))
            conn.execute(text("""
                CREATE VIEW vw_dim_severity AS
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
            """))

            # 9. Fact Production
            conn.execute(text("DROP VIEW IF EXISTS vw_fact_production;"))
            conn.execute(text("""
                CREATE VIEW vw_fact_production AS
                SELECT
                    pr.id AS production_run_key,
                    CAST(strftime('%Y%m%d', pr.date) AS INTEGER) AS date_key,
                    pr.date AS production_date,
                    pr.machine_id AS machine_key,
                    pr.frame_id AS frame_key,
                    pr.shift_id AS shift_key,
                    pr.customer_id AS customer_key,
                    pr.operator_id AS operator_key,
                    pr.supervisor_id AS supervisor_key,
                    pr.approved_by_id AS approved_by_key,
                    CAST(pr.static_time AS REAL) AS static_time_minutes,
                    CAST(pr.mounting_time AS REAL) AS mounting_time_minutes,
                    CAST(pr.rotational_time AS REAL) AS rotational_time_minutes,
                    CAST(pr.dismantling_time AS REAL) AS dismantling_time_minutes,
                    CAST(pr.total_testing_time AS REAL) AS total_testing_time_minutes,
                    CAST(pr.cycle_time_hours AS REAL) AS cycle_time_hours,
                    CAST(pr.rework_time AS REAL) AS rework_time_minutes,
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
            """))

            # 10. Fact Quality NC
            conn.execute(text("DROP VIEW IF EXISTS vw_fact_quality_nc;"))
            conn.execute(text("""
                CREATE VIEW vw_fact_quality_nc AS
                SELECT
                    nc.id AS nc_key,
                    nc.nc_number,
                    nc.production_record_id AS production_run_key,
                    nc.quality_record_id AS quality_record_key,
                    CAST(strftime('%Y%m%d', COALESCE(DATE(nc.created_at), qr.date_of_occurrence, pr.date)) AS INTEGER) AS date_key,
                    COALESCE(DATE(nc.created_at), qr.date_of_occurrence, pr.date) AS nc_date,
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
                        THEN ROUND((julianday(nc.closed_at) - julianday(nc.created_at)) * 24.0, 2)
                        ELSE NULL 
                    END AS resolution_duration_hours,
                    CAST(COALESCE(qr.rework_minutes, 0.0) AS REAL) AS logged_rework_minutes,
                    COALESCE(nc.root_cause, 'Not documented') AS root_cause,
                    COALESCE(nc.corrective_action, 'Not documented') AS corrective_action,
                    COALESCE(nc.preventive_action, 'Not documented') AS preventive_action,
                    nc.closure_notes,
                    nc.created_at,
                    nc.closed_at
                FROM nc_records nc
                LEFT JOIN quality_records qr ON nc.quality_record_id = qr.id
                LEFT JOIN production_records pr ON nc.production_record_id = pr.id;
            """))

            # 11. Fact Rework
            conn.execute(text("DROP VIEW IF EXISTS vw_fact_rework;"))
            conn.execute(text("""
                CREATE VIEW vw_fact_rework AS
                SELECT
                    rw.id AS rework_key,
                    rw.nc_record_id AS nc_key,
                    rw.production_record_id AS production_run_key,
                    rw.machine_id AS machine_key,
                    CAST(strftime('%Y%m%d', COALESCE(rw.completion_date, DATE(rw.created_at))) AS INTEGER) AS date_key,
                    COALESCE(rw.completion_date, DATE(rw.created_at)) AS rework_date,
                    rw.rework_done_by_id AS technician_key,
                    rw.verified_by_id AS verifier_key,
                    CAST(rw.rework_minutes AS REAL) AS rework_minutes,
                    CAST(ROUND(rw.rework_minutes / 60.0, 2) AS REAL) AS rework_hours,
                    rw.rework_status,
                    rw.rework_description,
                    CASE WHEN UPPER(rw.rework_status) = 'COMPLETED' THEN 1 ELSE 0 END AS is_completed,
                    CASE WHEN rw.verified_by_id IS NOT NULL THEN 1 ELSE 0 END AS is_verified,
                    rw.created_at,
                    rw.updated_at
                FROM rework_records rw;
            """))
            conn.commit()
            print("Successfully deployed SQLite reporting views for testing and dev environment.")

if __name__ == "__main__":
    apply_views()
