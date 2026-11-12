import React from 'react';
import { Activity, Shield, Users, Radio } from 'lucide-react';

export default function Header({ currentRole, onRoleChange, wsConnected = true }) {
  const roles = [
    { id: 'Operator', label: 'Operator (Suresh M.)', userId: 3 },
    { id: 'Supervisor', label: 'Supervisor (Rajesh K.)', userId: 2 },
    { id: 'Quality Engineer', label: 'Quality Eng (Priya S.)', userId: 4 },
    { id: 'Management', label: 'Management (Vikram D.)', userId: 5 },
    { id: 'Administrator', label: 'Administrator (IT Admin)', userId: 1 },
  ];

  return (
    <header className="app-header">
      <div className="header-brand">
        <div className="brand-logo">
          <Activity size={24} className="brand-icon" />
        </div>
        <div>
          <div className="brand-title">LIVE PRODUCTION & QUALITY MANAGEMENT</div>
          <div className="brand-subtitle">Industrial Operations Platform • PostgreSQL 16 & Power BI Ready</div>
        </div>
      </div>

      <div className="header-actions">
        {/* Live WebSocket Status Pill */}
        <div className={`ws-status-pill ${wsConnected ? 'ws-connected' : 'ws-disconnected'}`}>
          <Radio size={12} className={wsConnected ? 'pulse' : ''} />
          <span>{wsConnected ? 'Live Real-Time Push' : 'Reconnecting...'}</span>
        </div>

        {/* Role Switcher */}
        <div className="role-switcher">
          <Shield size={16} className="role-icon" />
          <span className="role-label">Active Role:</span>
          <select 
            className="form-select role-select"
            value={currentRole}
            onChange={(e) => onRoleChange(e.target.value)}
          >
            {roles.map(r => (
              <option key={r.id} value={r.id}>{r.label}</option>
            ))}
          </select>
        </div>
      </div>
    </header>
  );
}

