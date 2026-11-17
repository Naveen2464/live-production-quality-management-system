import React, { useState, useEffect } from 'react';
import { 
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, 
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer 
} from 'recharts';
import { AlertOctagon, Clock, ShieldAlert, CheckCircle2, Filter, X } from 'lucide-react';
import { getQualityAnalytics } from '../../services/api';

const SEVERITY_COLORS = {
  'CRITICAL': '#7f1d1d',
  'HIGH': '#dc2626',
  'MAJOR': '#ea580c',
  'MEDIUM': '#d97706',
  'MINOR': '#64748b',
  'LOW': '#16a34a'
};

const PALETTE = ['#dc2626', '#ea580c', '#d97706', '#2563eb', '#9333ea', '#0891b2', '#16a34a'];

export default function QualityDashboard({ dropdowns, refreshTrigger }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Filters
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [machineId, setMachineId] = useState('');

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await getQualityAnalytics({
        start_date: startDate,
        end_date: endDate,
        machine_id: machineId
      });
      setData(res);
    } catch (err) {
      setError(err.message || 'Failed to fetch quality analytics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [startDate, endDate, machineId, refreshTrigger]);

  const handleReset = () => {
    setStartDate('');
    setEndDate('');
    setMachineId('');
  };

  return (
    <div>
      {/* FILTER BAR */}
      <div className="table-filters-bar mb-4">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Filter size={16} className="text-muted" />
          <span className="text-xs font-bold text-slate-700">Quality Filters:</span>
        </div>

        <div className="filter-dropdowns">
          <input 
            type="date"
            className="form-input filter-select"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            title="Start Date"
          />
          <input 
            type="date"
            className="form-input filter-select"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            title="End Date"
          />

          <select 
            className="form-select filter-select"
            value={machineId}
            onChange={(e) => setMachineId(e.target.value)}
          >
            <option value="">All Machines</option>
            {dropdowns?.machines?.map(m => (
              <option key={m.id} value={m.id}>{m.code}</option>
            ))}
          </select>

          {(startDate || endDate || machineId) && (
            <button className="btn btn-ghost btn-sm" onClick={handleReset}>
              <X size={14} /> Reset
            </button>
          )}
        </div>
      </div>

      {error && <div className="alert-banner alert-error mb-4">{error}</div>}

      {loading ? (
        <div className="center-loader py-12">
          <div className="loading-spinner" />
          <p>Compiling live quality & NC analytics...</p>
        </div>
      ) : data ? (
        <div>
          {/* KPI CARDS */}
          <div className="grid grid-cols-4 gap-3 mb-6">
            <div className="card-inner">
              <div className="text-xs text-muted font-bold">TOTAL NON-CONFORMANCES</div>
              <div className="text-2xl font-bold text-slate-800 mt-1">{data.total_ncs}</div>
              <small className="text-muted">NC Rate: <strong>{data.nc_rate_percentage}%</strong> of production</small>
            </div>
            <div className="card-inner">
              <div className="text-xs text-red-700 font-bold">ACTIVE OPEN NCs</div>
              <div className="text-2xl font-bold text-red-700 mt-1">{data.open_ncs + data.in_progress_ncs}</div>
              <small className="text-muted">{data.open_ncs} Open • {data.in_progress_ncs} In Progress</small>
            </div>
            <div className="card-inner">
              <div className="text-xs text-purple-700 font-bold">UNDER REVIEW</div>
              <div className="text-2xl font-bold text-purple-700 mt-1">{data.under_review_ncs}</div>
              <small className="text-muted">Awaiting QA verification signoff</small>
            </div>
            <div className="card-inner">
              <div className="text-xs text-green-700 font-bold">CLOSED & RESOLVED</div>
              <div className="text-2xl font-bold text-green-700 mt-1">{data.closed_ncs}</div>
              <small className="text-muted">{data.total_rework_minutes} total rework minutes</small>
            </div>
          </div>

          {/* CHARTS ROW 1: Defect Category & Severity Breakdown */}
          <div className="grid grid-cols-2 gap-4 mb-6" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
            <div className="card-inner">
              <h4 className="font-semibold mb-3">Defect Distribution by Category</h4>
              <div style={{ width: '100%', height: 260 }}>
                {data.category_distribution.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.category_distribution} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                      <XAxis type="number" tick={{ fontSize: 11 }} />
                      <YAxis dataKey="category" type="category" tick={{ fontSize: 11 }} width={90} />
                      <Tooltip formatter={(value) => [`${value} issues`, 'Count']} />
                      <Bar dataKey="count" fill="#dc2626" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-center text-muted text-xs pt-24">No category defects recorded.</p>
                )}
              </div>
            </div>

            <div className="card-inner">
              <h4 className="font-semibold mb-3">Severity & Classification Share</h4>
              <div style={{ width: '100%', height: 260 }}>
                {data.severity_distribution.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={data.severity_distribution}
                        dataKey="count"
                        nameKey="category"
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={85}
                        label={({ category, percent }) => `${category} (${(percent * 100).toFixed(0)}%)`}
                      >
                        {data.severity_distribution.map((entry, index) => (
                          <Cell 
                            key={`cell-${index}`} 
                            fill={SEVERITY_COLORS[entry.category] || PALETTE[index % PALETTE.length]} 
                          />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-center text-muted text-xs pt-24">No classification data.</p>
                )}
              </div>
            </div>
          </div>

          {/* CHARTS ROW 2: Monthly Trends & Department Issues */}
          <div className="grid grid-cols-2 gap-4" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
            <div className="card-inner">
              <h4 className="font-semibold mb-3">Monthly NC Occurrence Trend</h4>
              <div style={{ width: '100%', height: 240 }}>
                {data.monthly_nc_trends.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data.monthly_nc_trends}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Line type="monotone" dataKey="count" name="NC Cases Raised" stroke="#ea580c" strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-center text-muted text-xs pt-20">No monthly NC trends available.</p>
                )}
              </div>
            </div>

            <div className="card-inner">
              <h4 className="font-semibold mb-3">Department-Wise Quality Defects</h4>
              <div style={{ width: '100%', height: 240 }}>
                {data.department_distribution.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.department_distribution}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="category" tick={{ fontSize: 10 }} interval={0} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Bar dataKey="count" name="Issues Attributed" fill="#9333ea" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-center text-muted text-xs pt-20">No department attribution data.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

