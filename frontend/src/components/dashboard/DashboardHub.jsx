import React, { useState, useEffect } from 'react';
import { 
  BarChart3, Activity, ShieldAlert, Cpu, 
  Clock, CheckCircle, RefreshCw, Layers
} from 'lucide-react';
import { getDashboardSummary } from '../../services/api';
import ProductionDashboard from './ProductionDashboard';
import QualityDashboard from './QualityDashboard';
import MachinePerformanceDashboard from './MachinePerformanceDashboard';

export default function DashboardHub({ dropdowns, refreshTrigger }) {
  const [activeSubTab, setActiveSubTab] = useState('production'); // 'production' | 'quality' | 'machines'
  const [summary, setSummary] = useState(null);
  const [loadingSummary, setLoadingSummary] = useState(true);

  const fetchSummary = async () => {
    try {
      const data = await getDashboardSummary();
      setSummary(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingSummary(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, [refreshTrigger]);

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2 className="card-title">Live Operational Dashboards & Recharts Telemetry</h2>
          <p className="card-subtitle">
            Near-real-time streaming analytics derived directly from live PostgreSQL records. Microsoft Power BI provides deep business intelligence.
          </p>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={fetchSummary} title="Refresh telemetry">
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {/* TOP-LEVEL EXECUTIVE TELEMETRY KPI BANNER */}
      {summary && (
        <div className="grid grid-cols-4 gap-3 mb-6">
          <div className="kpi-pill kpi-cycle" style={{ justifyContent: 'space-between' }}>
            <div>
              <div className="text-xs font-bold text-blue-900">PRODUCTION VERIFIED</div>
              <div className="text-2xl font-bold text-blue-900 mt-1">{summary.total_production_records} runs</div>
              <small className="text-blue-700">{summary.approved_records} Approved • {summary.pending_records} Pending</small>
            </div>
            <Activity size={28} className="text-blue-400" />
          </div>

          <div className="kpi-pill kpi-time" style={{ justifyContent: 'space-between' }}>
            <div>
              <div className="text-xs font-bold text-green-900">AVG CYCLE TIME</div>
              <div className="text-2xl font-bold text-green-900 mt-1">{summary.average_cycle_time_hours} hrs</div>
              <small className="text-green-700">{summary.total_testing_time_hours} hrs total testing</small>
            </div>
            <Clock size={28} className="text-green-400" />
          </div>

          <div className="kpi-pill" style={{ backgroundColor: '#fff1f2', border: '1px solid #fecaca', justifyContent: 'space-between' }}>
            <div>
              <div className="text-xs font-bold text-red-900">NON-CONFORMANCES</div>
              <div className="text-2xl font-bold text-red-900 mt-1">{summary.total_ncs} tickets</div>
              <small className="text-red-700">{summary.open_ncs} Active • NC Rate: {summary.nc_rate_percentage}%</small>
            </div>
            <ShieldAlert size={28} className="text-red-400" />
          </div>

          <div className="kpi-pill" style={{ backgroundColor: '#f5f3ff', border: '1px solid #ddd6fe', justifyContent: 'space-between' }}>
            <div>
              <div className="text-xs font-bold text-purple-900">REWORK DURATION</div>
              <div className="text-2xl font-bold text-purple-900 mt-1">{summary.total_rework_minutes} min</div>
              <small className="text-purple-700">{summary.total_machines_tested} machines tested</small>
            </div>
            <Cpu size={28} className="text-purple-400" />
          </div>
        </div>
      )}

      {/* SUB-DASHBOARD TABS */}
      <div className="tab-navigation mb-6" style={{ borderBottom: '2px solid #e2e8f0' }}>
        <button 
          className={`tab-btn ${activeSubTab === 'production' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('production')}
        >
          <BarChart3 size={16} /> Dashboard 1: Production Overview
        </button>
        <button 
          className={`tab-btn ${activeSubTab === 'quality' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('quality')}
        >
          <ShieldAlert size={16} /> Dashboard 2: Quality & NC Analytics
        </button>
        <button 
          className={`tab-btn ${activeSubTab === 'machines' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('machines')}
        >
          <Cpu size={16} /> Dashboard 3: Machine Performance
        </button>
      </div>

      {/* DASHBOARD CONTENT BODY */}
      {activeSubTab === 'production' && (
        <ProductionDashboard 
          dropdowns={dropdowns}
          refreshTrigger={refreshTrigger}
        />
      )}

      {activeSubTab === 'quality' && (
        <QualityDashboard 
          dropdowns={dropdowns}
          refreshTrigger={refreshTrigger}
        />
      )}

      {activeSubTab === 'machines' && (
        <MachinePerformanceDashboard 
          refreshTrigger={refreshTrigger}
        />
      )}
    </div>
  );
}

