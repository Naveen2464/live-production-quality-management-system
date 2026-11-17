import React, { useState, useEffect } from 'react';
import { 
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, 
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer 
} from 'recharts';
import { Activity, Clock, Cpu, Calendar, Filter, X } from 'lucide-react';
import { getProductionAnalytics } from '../../services/api';

const COLORS = ['#2563eb', '#16a34a', '#d97706', '#9333ea', '#dc2626', '#0891b2', '#475569'];

export default function ProductionDashboard({ dropdowns, refreshTrigger }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Filters
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [machineId, setMachineId] = useState('');
  const [shiftId, setShiftId] = useState('');
  const [customerId, setCustomerId] = useState('');

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await getProductionAnalytics({
        start_date: startDate,
        end_date: endDate,
        machine_id: machineId,
        shift_id: shiftId,
        customer_id: customerId
      });
      setData(res);
    } catch (err) {
      setError(err.message || 'Failed to fetch production analytics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [startDate, endDate, machineId, shiftId, customerId, refreshTrigger]);

  const handleReset = () => {
    setStartDate('');
    setEndDate('');
    setMachineId('');
    setShiftId('');
    setCustomerId('');
  };

  return (
    <div>
      {/* FILTER BAR */}
      <div className="table-filters-bar mb-4">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Filter size={16} className="text-muted" />
          <span className="text-xs font-bold text-slate-700">Analytics Filters:</span>
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

          <select 
            className="form-select filter-select"
            value={shiftId}
            onChange={(e) => setShiftId(e.target.value)}
          >
            <option value="">All Shifts</option>
            {dropdowns?.shifts?.map(s => (
              <option key={s.id} value={s.id}>{s.code}</option>
            ))}
          </select>

          <select 
            className="form-select filter-select"
            value={customerId}
            onChange={(e) => setCustomerId(e.target.value)}
          >
            <option value="">All Customers</option>
            {dropdowns?.customers?.map(c => (
              <option key={c.id} value={c.id}>{c.label}</option>
            ))}
          </select>

          {(startDate || endDate || machineId || shiftId || customerId) && (
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
          <p>Compiling live production statistics...</p>
        </div>
      ) : data ? (
        <div>
          {/* KPI METRIC CARDS */}
          <div className="grid grid-cols-4 gap-3 mb-6">
            <div className="card-inner">
              <div className="text-xs text-muted font-bold">TOTAL PRODUCTION RUNS</div>
              <div className="text-2xl font-bold text-slate-800 mt-1">{data.total_production}</div>
              <small className="text-muted">Recorded test batches</small>
            </div>
            <div className="card-inner">
              <div className="text-xs text-muted font-bold">ACTIVE TEST BEDS</div>
              <div className="text-2xl font-bold text-primary mt-1">{data.total_machines_tested}</div>
              <small className="text-muted">Distinct rigs in period</small>
            </div>
            <div className="card-inner">
              <div className="text-xs text-muted font-bold">AVERAGE CYCLE TIME</div>
              <div className="text-2xl font-bold text-green-700 mt-1">{data.average_cycle_time_hours} hrs</div>
              <small className="text-muted">{Math.round(data.average_cycle_time_hours * 60)} minutes / unit</small>
            </div>
            <div className="card-inner">
              <div className="text-xs text-muted font-bold">TOTAL TESTING TIME</div>
              <div className="text-2xl font-bold text-amber-700 mt-1">{Math.round(data.total_testing_minutes / 60)} hrs</div>
              <small className="text-muted">{data.total_testing_minutes} total minutes</small>
            </div>
          </div>

          {/* CHARTS ROW 1: Daily Trends & Machine-wise Production */}
          <div className="grid grid-cols-2 gap-4 mb-6" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
            <div className="card-inner">
              <h4 className="font-semibold mb-3">Daily Production Volume & Cycle Time Trend</h4>
              <div style={{ width: '100%', height: 260 }}>
                {data.daily_trends.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data.daily_trends}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                      <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
                      <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Legend />
                      <Line yAxisId="left" type="monotone" dataKey="count" name="Units Produced" stroke="#2563eb" strokeWidth={2} activeDot={{ r: 6 }} />
                      <Line yAxisId="right" type="monotone" dataKey="secondary_value" name="Avg Cycle (hrs)" stroke="#16a34a" strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-center text-muted text-xs pt-24">No daily entries for selected filter.</p>
                )}
              </div>
            </div>

            <div className="card-inner">
              <h4 className="font-semibold mb-3">Machine-Wise Production Distribution</h4>
              <div style={{ width: '100%', height: 260 }}>
                {data.machine_wise_production.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.machine_wise_production}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Bar dataKey="count" name="Units Tested" fill="#2563eb" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-center text-muted text-xs pt-24">No machine volume data.</p>
                )}
              </div>
            </div>
          </div>

          {/* CHARTS ROW 2: Monthly Trends & Shift Distribution */}
          <div className="grid grid-cols-2 gap-4" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
            <div className="card-inner">
              <h4 className="font-semibold mb-3">Monthly Output History</h4>
              <div style={{ width: '100%', height: 240 }}>
                {data.monthly_trends.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.monthly_trends}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Bar dataKey="count" name="Monthly Tests" fill="#16a34a" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-center text-muted text-xs pt-20">No monthly data available.</p>
                )}
              </div>
            </div>

            <div className="card-inner">
              <h4 className="font-semibold mb-3">Shift-Wise Production Share</h4>
              <div style={{ width: '100%', height: 240 }}>
                {data.shift_wise_production.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={data.shift_wise_production}
                        dataKey="count"
                        nameKey="label"
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        label={({ label, percent }) => `${label} (${(percent * 100).toFixed(0)}%)`}
                      >
                        {data.shift_wise_production.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-center text-muted text-xs pt-20">No shift breakdown data.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

