# LIVE PRODUCTION & QUALITY MANAGEMENT SYSTEM
# PHASE 6: POWER BI CONNECTIVITY, GATEWAY & REFRESH SPECIFICATION

**Document Version**: 1.0  
**Target Environment**: Microsoft Power BI Desktop / Power BI Service  
**PostgreSQL Version**: 16.x  
**Database**: `nidec_production_db`  
**Dedicated Reporting User**: `nidec_reporting_user`  

---

## 1. PostgreSQL Database Connection Parameters

When configuring Microsoft Power BI Desktop to ingest data from the Live Production & Quality Management System, use the following connection specifications:

| Parameter | Recommended Value (Production) | Local / Test Value | Notes |
| :--- | :--- | :--- | :--- |
| **Server** | `db.internal.nidec.com` (or IP) | `localhost:5432` | Internal corporate network host |
| **Database** | `nidec_production_db` | `nidec_production_db` | Main operational database |
| **Port** | `5432` | `5432` | Default PostgreSQL listening port |
| **Data Connectivity Mode** | **Import** (or DirectQuery) | **Import** | See comparison in Section 3 |
| **User Name** | `nidec_reporting_user` | `nidec_reporting_user` | Read-only reporting account |
| **Password** | Stored in Key Vault / IT Secret Manager | `${NIDEC_REPORTING_PASSWORD}` | Injected via secure environment variable; never hardcoded |
| **Encryption Level** | `Require` or `Verify-Full` | `Prefer` / `Disable` | Mandate SSL in corporate environments |

---

## 2. PostgreSQL Connector & Driver Installation

To enable Microsoft Power BI Desktop and the On-Premises Data Gateway to connect to PostgreSQL 16:

1. **Install Npgsql / .NET Data Provider for PostgreSQL**:
   - Download the official Npgsql MSI installer (version 4.0.10 or compatible with Power BI's .NET Framework requirements).
   - Ensure **GAC (Global Assembly Cache)** deployment is checked during setup.
2. **Alternative: Microsoft PostgreSQL Connector**:
   - Power BI Desktop includes a built-in PostgreSQL connector (`Home` $\to$ `Get Data` $\to$ `PostgreSQL database`).
   - If prompted for `Npgsql.dll`, verify that the Npgsql library is installed in the GAC or placed in the Power BI Desktop `bin` folder.
3. **Verify TCP Port Openness**:
   - Ensure the client machine or On-Premises Gateway server can reach port 5432 on the PostgreSQL host:
     ```powershell
     Test-NetConnection -ComputerName <postgresql_host> -Port 5432
     ```

---

## 3. Storage Mode Selection: Import vs. DirectQuery

The Star Schema views are designed to support both storage models seamlessly:

### Mode A: Import Mode (Recommended for Executive Dashboards)
- **How it Works**: VertiPaq loads data from `vw_fact_*` and `vw_dim_*` views into memory with columnar compression.
- **Advantages**:
  - Highest possible DAX execution speed (<100ms per visual filter).
  - Full support for all DAX functions, including complex time-intelligence (`DATEADD`, `SAMEPERIODLASTYEAR`).
  - Offline report authoring and presentation capability.
- **Refresh Strategy**: Scheduled refresh via the On-Premises Data Gateway (e.g., every 2 hours or shift-end: 06:00, 14:00, 22:00).

### Mode B: DirectQuery Mode (Recommended for Shop-Floor Status Displays)
- **How it Works**: Every slicer change or page load sends a live SQL `SELECT` to the PostgreSQL reporting views.
- **Advantages**:
  - Zero data latency; changes saved in the web app appear immediately upon report refresh.
  - No database data stored in Microsoft Power BI cloud storage.
- **Optimization in Place**:
  - Our views provide 1/0 integer flags (`is_pass`, `is_closed`) and integer date keys (`YYYYMMDD`), preventing heavy string parsing over DirectQuery.

---

## 4. On-Premises Data Gateway Configuration

For Power BI Service (cloud) dashboards to refresh against the internal company PostgreSQL server without exposing the database to the public internet:

```
[ Power BI Service (Cloud) ]
             |
             | Outbound HTTPS (Port 443)
             v
[ Microsoft On-Premises Data Gateway ] (Installed on Internal Server / VM)
             |
             | Inbound TCP Port 5432
             v
[ PostgreSQL 16 Server: nidec_production_db ]
```

### Gateway Installation & Registration Steps:
1. Provision a dedicated Windows Server (or IT-approved VM) on the internal corporate LAN with continuous network connectivity to PostgreSQL host `db.internal.nidec.com:5432`.
2. Download and install the **Standard On-Premises Data Gateway** from the Microsoft Power BI portal.
3. Sign in using the corporate Power BI Tenant Administrator or Gateway Administrator account.
4. Name the gateway (e.g., `NIDEC-PROD-GATEWAY-01`) and define a secure recovery key.
5. In Power BI Service (`Manage Connections and Gateways`):
   - Add a new Data Source under `NIDEC-PROD-GATEWAY-01`.
   - Data Source Type: **PostgreSQL**.
   - Server: `db.internal.nidec.com`.
   - Database: `nidec_production_db`.
   - Authentication Method: **Basic**.
   - Username: `nidec_reporting_user`.
   - Password: `<secure_reporting_password>`.
   - Privacy Level: `Organizational`.

---

## 5. Scheduled Refresh Schedule

To align with company manufacturing shift schedules:

| Refresh Slot | Trigger Time | Shift Alignment | Purpose |
| :--- | :--- | :--- | :--- |
| **Shift A Morning Handover** | `06:30 AM` | Shift A Start | Captures night shift and handover numbers |
| **Shift A Midday Review** | `11:00 AM` | Shift A Midday | Real-time tracking of morning output |
| **Shift B Afternoon Handover** | `14:30 PM` | Shift B Start | Complete verification of Shift A final numbers |
| **Shift B Evening Review** | `18:30 PM` | Shift B Midday | Mid-shift quality and cycle-time review |
| **Shift C Night Handover** | `22:30 PM` | Shift C Start | Shift B final numbers & daily summary |
| **Daily Executive Snapshot** | `01:00 AM` | Off-Peak | Nightly full reconciliation & backup confirmation |

---

## 6. Security, Credential Isolation & Rotation Policy

- **Role Dedicated to BI**: `nidec_reporting_user` has NO permission to perform `INSERT`, `UPDATE`, `DELETE`, or `DROP`.
- **Zero Schema Access**: The reporting user cannot inspect `audit_logs` or `users` password hashes.
- **Connection Isolation**: The web application connects via `nidec_app_user` with full CRUD permissions, keeping reporting query overhead physically isolated from operational database connection pools.
- **Credential Storage**: Credentials must never be stored in plain text or committed to version control. Set environment variables on the gateway or client machine:
  ```bash
  export NIDEC_REPORTING_USER="nidec_reporting_user"
  export NIDEC_REPORTING_PASSWORD="<retrieved_from_enterprise_vault>"
  ```
- **Scheduled Credential Rotation Policy**:
  1. Corporate security policy mandates rotation of `nidec_reporting_user` credentials every 90 days.
  2. IT Database Administrator executes:
     ```sql
     ALTER ROLE nidec_reporting_user WITH PASSWORD '${NEW_ROTATED_REPORTING_PASSWORD}';
     ```
  3. Update the Power BI Service Data Gateway connection credentials under **Manage Connections and Gateways** -> **Data Sources** -> **Edit Credentials**.
  4. Scheduled refreshes resume without modifying report visuals, queries, or DAX measures.

