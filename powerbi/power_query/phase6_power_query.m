/* =================================================================================
   LIVE PRODUCTION & QUALITY MANAGEMENT SYSTEM
   Phase 6: Power Query M Scripts for PostgreSQL 16
   File: powerbi/power_query/phase6_power_query.m
   Database: nidec_production_db
   User: nidec_reporting_user
   ================================================================================= */

// Power BI Parameter Configuration
// In Power BI Desktop: Home -> Manage Parameters -> New Parameter
// Parameter Name: ServerName (Type: Text, Current Value: "localhost" or company PostgreSQL host)
// Parameter Name: DatabaseName (Type: Text, Current Value: "nidec_production_db")

// =================================================================================
// 1. DIMENSION QUERIES
// =================================================================================

// 1.1 vw_dim_date
let
    Source = Value.NativeQuery(
        PostgreSQL.Database(ServerName, DatabaseName),
        "SELECT date_key, full_date, calendar_year, calendar_quarter, quarter_name, month_name, month_number, year_month, day_of_month, day_name, day_of_week, is_weekend FROM vw_dim_date",
        null,
        [EnableFolding = true]
    ),
    #"Changed Type" = Table.TransformColumnTypes(Source, {
        {"date_key", Int64.Type},
        {"full_date", type date},
        {"calendar_year", Int64.Type},
        {"calendar_quarter", Int64.Type},
        {"quarter_name", type text},
        {"month_name", type text},
        {"month_number", Int64.Type},
        {"year_month", type text},
        {"day_of_month", Int64.Type},
        {"day_name", type text},
        {"day_of_week", Int64.Type},
        {"is_weekend", Int64.Type}
    })
in
    #"Changed Type"

// 1.2 vw_dim_machine
let
    Source = Value.NativeQuery(
        PostgreSQL.Database(ServerName, DatabaseName),
        "SELECT machine_key, machine_code, machine_name, model, line_name, is_active FROM vw_dim_machine",
        null,
        [EnableFolding = true]
    ),
    #"Changed Type" = Table.TransformColumnTypes(Source, {
        {"machine_key", Int64.Type},
        {"machine_code", type text},
        {"machine_name", type text},
        {"model", type text},
        {"line_name", type text},
        {"is_active", Int64.Type}
    })
in
    #"Changed Type"

// 1.3 vw_dim_customer
let
    Source = Value.NativeQuery(
        PostgreSQL.Database(ServerName, DatabaseName),
        "SELECT customer_key, customer_code, customer_name, contact_person, email, phone, is_active FROM vw_dim_customer",
        null,
        [EnableFolding = true]
    ),
    #"Changed Type" = Table.TransformColumnTypes(Source, {
        {"customer_key", Int64.Type},
        {"customer_code", type text},
        {"customer_name", type text},
        {"contact_person", type text},
        {"email", type text},
        {"phone", type text},
        {"is_active", Int64.Type}
    })
in
    #"Changed Type"

// 1.4 vw_dim_frame
let
    Source = Value.NativeQuery(
        PostgreSQL.Database(ServerName, DatabaseName),
        "SELECT frame_key, frame_code, frame_name, description, is_active FROM vw_dim_frame",
        null,
        [EnableFolding = true]
    ),
    #"Changed Type" = Table.TransformColumnTypes(Source, {
        {"frame_key", Int64.Type},
        {"frame_code", type text},
        {"frame_name", type text},
        {"description", type text},
        {"is_active", Int64.Type}
    })
in
    #"Changed Type"

// 1.5 vw_dim_shift
let
    Source = Value.NativeQuery(
        PostgreSQL.Database(ServerName, DatabaseName),
        "SELECT shift_key, shift_name, start_time, end_time, shift_window, description, is_active FROM vw_dim_shift",
        null,
        [EnableFolding = true]
    ),
    #"Changed Type" = Table.TransformColumnTypes(Source, {
        {"shift_key", Int64.Type},
        {"shift_name", type text},
        {"start_time", type text},
        {"end_time", type text},
        {"shift_window", type text},
        {"description", type text},
        {"is_active", Int64.Type}
    })
in
    #"Changed Type"

// 1.6 vw_dim_personnel
let
    Source = Value.NativeQuery(
        PostgreSQL.Database(ServerName, DatabaseName),
        "SELECT user_key, username, full_name, email, role_name, department, is_active, is_ad_user FROM vw_dim_personnel",
        null,
        [EnableFolding = true]
    ),
    #"Changed Type" = Table.TransformColumnTypes(Source, {
        {"user_key", Int64.Type},
        {"username", type text},
        {"full_name", type text},
        {"email", type text},
        {"role_name", type text},
        {"department", type text},
        {"is_active", Int64.Type},
        {"is_ad_user", Int64.Type}
    })
in
    #"Changed Type"

// 1.7 vw_dim_defect_category
let
    Source = Value.NativeQuery(
        PostgreSQL.Database(ServerName, DatabaseName),
        "SELECT category_name, primary_domain FROM vw_dim_defect_category",
        null,
        [EnableFolding = true]
    ),
    #"Changed Type" = Table.TransformColumnTypes(Source, {
        {"category_name", type text},
        {"primary_domain", type text}
    })
in
    #"Changed Type"

// 1.8 vw_dim_severity
let
    Source = Value.NativeQuery(
        PostgreSQL.Database(ServerName, DatabaseName),
        "SELECT severity_name, severity_rank, priority_tier FROM vw_dim_severity",
        null,
        [EnableFolding = true]
    ),
    #"Changed Type" = Table.TransformColumnTypes(Source, {
        {"severity_name", type text},
        {"severity_rank", Int64.Type},
        {"priority_tier", type text}
    })
in
    #"Changed Type"


// =================================================================================
// 2. FACT QUERIES
// =================================================================================

// 2.1 vw_fact_production
let
    Source = Value.NativeQuery(
        PostgreSQL.Database(ServerName, DatabaseName),
        "SELECT production_run_key, date_key, production_date, machine_key, frame_key, shift_key, customer_key, operator_key, supervisor_key, approved_by_key, static_time_minutes, mounting_time_minutes, rotational_time_minutes, dismantling_time_minutes, total_testing_time_minutes, cycle_time_hours, rework_time_minutes, test_result, approval_status, is_pass, is_fail, is_nc_raised, is_approved, is_pending, is_rejected, created_at, updated_at FROM vw_fact_production",
        null,
        [EnableFolding = true]
    ),
    #"Changed Type" = Table.TransformColumnTypes(Source, {
        {"production_run_key", Int64.Type},
        {"date_key", Int64.Type},
        {"production_date", type date},
        {"machine_key", Int64.Type},
        {"frame_key", Int64.Type},
        {"shift_key", Int64.Type},
        {"customer_key", Int64.Type},
        {"operator_key", Int64.Type},
        {"supervisor_key", Int64.Type},
        {"approved_by_key", Int64.Type},
        {"static_time_minutes", type number},
        {"mounting_time_minutes", type number},
        {"rotational_time_minutes", type number},
        {"dismantling_time_minutes", type number},
        {"total_testing_time_minutes", type number},
        {"cycle_time_hours", type number},
        {"rework_time_minutes", type number},
        {"test_result", type text},
        {"approval_status", type text},
        {"is_pass", Int64.Type},
        {"is_fail", Int64.Type},
        {"is_nc_raised", Int64.Type},
        {"is_approved", Int64.Type},
        {"is_pending", Int64.Type},
        {"is_rejected", Int64.Type},
        {"created_at", type datetimezone},
        {"updated_at", type datetimezone}
    })
in
    #"Changed Type"

// 2.2 vw_fact_quality_nc
let
    Source = Value.NativeQuery(
        PostgreSQL.Database(ServerName, DatabaseName),
        "SELECT nc_key, nc_number, production_run_key, quality_record_key, date_key, nc_date, machine_key, customer_key, frame_key, shift_key, quality_engineer_key, closed_by_key, title, defect_category, severity, responsible_department, status, is_open, is_in_progress, is_under_review, is_closed, resolution_duration_hours, logged_rework_minutes, root_cause, corrective_action, preventive_action, closure_notes, created_at, closed_at FROM vw_fact_quality_nc",
        null,
        [EnableFolding = true]
    ),
    #"Changed Type" = Table.TransformColumnTypes(Source, {
        {"nc_key", Int64.Type},
        {"nc_number", type text},
        {"production_run_key", Int64.Type},
        {"quality_record_key", Int64.Type},
        {"date_key", Int64.Type},
        {"nc_date", type date},
        {"machine_key", Int64.Type},
        {"customer_key", Int64.Type},
        {"frame_key", Int64.Type},
        {"shift_key", Int64.Type},
        {"quality_engineer_key", Int64.Type},
        {"closed_by_key", Int64.Type},
        {"title", type text},
        {"defect_category", type text},
        {"severity", type text},
        {"responsible_department", type text},
        {"status", type text},
        {"is_open", Int64.Type},
        {"is_in_progress", Int64.Type},
        {"is_under_review", Int64.Type},
        {"is_closed", Int64.Type},
        {"resolution_duration_hours", type number},
        {"logged_rework_minutes", type number},
        {"root_cause", type text},
        {"corrective_action", type text},
        {"preventive_action", type text},
        {"closure_notes", type text},
        {"created_at", type datetimezone},
        {"closed_at", type datetimezone}
    })
in
    #"Changed Type"

// 2.3 vw_fact_rework
let
    Source = Value.NativeQuery(
        PostgreSQL.Database(ServerName, DatabaseName),
        "SELECT rework_key, nc_key, production_run_key, machine_key, date_key, rework_date, technician_key, verifier_key, rework_minutes, rework_hours, rework_status, rework_description, is_completed, is_verified, created_at, updated_at FROM vw_fact_rework",
        null,
        [EnableFolding = true]
    ),
    #"Changed Type" = Table.TransformColumnTypes(Source, {
        {"rework_key", Int64.Type},
        {"nc_key", Int64.Type},
        {"production_run_key", Int64.Type},
        {"machine_key", Int64.Type},
        {"date_key", Int64.Type},
        {"rework_date", type date},
        {"technician_key", Int64.Type},
        {"verifier_key", Int64.Type},
        {"rework_minutes", type number},
        {"rework_hours", type number},
        {"rework_status", type text},
        {"rework_description", type text},
        {"is_completed", Int64.Type},
        {"is_verified", Int64.Type},
        {"created_at", type datetimezone},
        {"updated_at", type datetimezone}
    })
in
    #"Changed Type"

