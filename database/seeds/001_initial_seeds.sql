-- ====================================================================
-- SEED DATA: LIVE PRODUCTION & QUALITY MANAGEMENT SYSTEM
-- ====================================================================

-- 1. ROLES
INSERT INTO roles (id, name, description) VALUES
(1, 'Administrator', 'Full system administration, user management, master data control'),
(2, 'Supervisor', 'Production review, record approval, shift monitoring'),
(3, 'Quality Engineer', 'NC case management, defect tracking, rework verification and closure'),
(4, 'Management', 'Executive dashboard review, Power BI analytics, reports'),
(5, 'Operator', 'Daily production testing data entry, personal submission history')
ON CONFLICT (id) DO NOTHING;

-- 2. MASTER DATA: SHIFTS
INSERT INTO shifts (id, shift_name, start_time, end_time, description) VALUES
(1, 'Shift A', '06:00', '14:00', 'Morning shift (06:00 to 14:00)'),
(2, 'Shift B', '14:00', '22:00', 'Afternoon/Evening shift (14:00 to 22:00)'),
(3, 'Shift C', '22:00', '06:00', 'Night shift (22:00 to 06:00)')
ON CONFLICT (id) DO NOTHING;

-- 3. MASTER DATA: FRAMES
INSERT INTO frames (id, frame_code, frame_name, description) VALUES
(1, 'FR-063', 'Frame 63', 'Frame size 63mm shaft height'),
(2, 'FR-071', 'Frame 71', 'Frame size 71mm shaft height'),
(3, 'FR-080', 'Frame 80', 'Frame size 80mm shaft height'),
(4, 'FR-090', 'Frame 90', 'Frame size 90mm shaft height'),
(5, 'FR-100', 'Frame 100', 'Frame size 100mm shaft height'),
(6, 'FR-112', 'Frame 112', 'Frame size 112mm shaft height'),
(7, 'FR-132', 'Frame 132', 'Frame size 132mm shaft height')
ON CONFLICT (id) DO NOTHING;

-- 4. MASTER DATA: MACHINES
INSERT INTO machines (id, machine_code, name, model, line_name) VALUES
(1, 'M-101', 'Test Bed 01 - Dyno Alpha', 'TD-250kW', 'Line 1 - Heavy Motors'),
(2, 'M-102', 'Test Bed 02 - Dyno Beta', 'TD-250kW', 'Line 1 - Heavy Motors'),
(3, 'M-103', 'Test Bed 03 - High Speed', 'TD-400kW', 'Line 2 - Precision Motors'),
(4, 'M-201', 'Rotational Rig 01', 'RR-100', 'Line 2 - Precision Motors'),
(5, 'M-202', 'Rotational Rig 02', 'RR-150', 'Line 3 - Standard Motors'),
(6, 'M-301', 'Static Inspection Bench 01', 'SB-50', 'Line 3 - Standard Motors')
ON CONFLICT (id) DO NOTHING;

-- 5. MASTER DATA: CUSTOMERS
INSERT INTO customers (id, customer_code, customer_name, contact_person, email, phone) VALUES
(1, 'CUST-ABB', 'ABB Power & Industrial Grids', 'Ramesh Sharma', 'ramesh.sharma@abb.com', '+91 9876543210'),
(2, 'CUST-SIEM', 'Siemens Energy India', 'Kavita Nair', 'kavita.nair@siemens.com', '+91 9876543211'),
(3, 'CUST-SCHN', 'Schneider Electric Manufacturing', 'Arun Patel', 'arun.patel@se.com', '+91 9876543212'),
(4, 'CUST-DANF', 'Danfoss Power Solutions', 'Deepak Verma', 'deepak.v@danfoss.com', '+91 9876543213'),
(5, 'CUST-KIRL', 'Kirloskar Electric Co.', 'Sanjay Rao', 'sanjay.rao@kirloskar.com', '+91 9876543214')
ON CONFLICT (id) DO NOTHING;

-- 6. INITIAL USERS (Password for all seeded users: Admin@123)
-- Hash: $2b$12$AjJc.XftvWshEdeVmmkPC.0z0YtxkkrOBERjk8HxNPnDE.KVRtG.q
INSERT INTO users (id, username, full_name, email, hashed_password, role_id, is_active, is_ad_user, department) VALUES
(1, 'admin', 'System Administrator', 'admin@nidec-system.com', '$2b$12$AjJc.XftvWshEdeVmmkPC.0z0YtxkkrOBERjk8HxNPnDE.KVRtG.q', 1, TRUE, FALSE, 'IT & Systems'),
(2, 'supervisor_rajesh', 'Rajesh K. (Production Supervisor)', 'rajesh.k@nidec-system.com', '$2b$12$AjJc.XftvWshEdeVmmkPC.0z0YtxkkrOBERjk8HxNPnDE.KVRtG.q', 2, TRUE, FALSE, 'Production Line 1'),
(3, 'operator_suresh', 'Suresh M. (Lead Operator)', 'suresh.m@nidec-system.com', '$2b$12$AjJc.XftvWshEdeVmmkPC.0z0YtxkkrOBERjk8HxNPnDE.KVRtG.q', 5, TRUE, FALSE, 'Production Testing'),
(4, 'qe_priya', 'Priya S. (Senior Quality Engineer)', 'priya.s@nidec-system.com', '$2b$12$AjJc.XftvWshEdeVmmkPC.0z0YtxkkrOBERjk8HxNPnDE.KVRtG.q', 3, TRUE, FALSE, 'Quality Assurance'),
(5, 'mgmt_vikram', 'Vikram Deshmukh (Plant General Manager)', 'vikram.d@nidec-system.com', '$2b$12$AjJc.XftvWshEdeVmmkPC.0z0YtxkkrOBERjk8HxNPnDE.KVRtG.q', 4, TRUE, FALSE, 'Plant Management')
ON CONFLICT (id) DO NOTHING;

