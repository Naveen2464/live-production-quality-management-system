import React, { useState, useEffect } from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer 
} from 'recharts';
import { Cpu, CheckCircle2, AlertTriangle, Clock, Wrench } from 'lucide-react';
import { getMachinePerformanceAnalytics } from '../../services/api';

export default function MachinePerformanceDashboard({ refreshTrigger }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await getMachinePerformanceAnalytics();
      setData(res);
    } catch (err) {
      setError(err.message || 'Failed to fetch machine analytics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [refreshTrigger]);

  return (
    <div>
      {error && <div className="alert-banner alert-error mb-4">{error}</div>}

      {loading ? (
        <div className="center-loader py-12">
          <div className="loading-spinner" />
          <p>Analyzing machine cycle times and test bed pass rates...</p>
        </div>
      ) : data ? (
        <div>
          {/* MACHINE PERFORMANCE COMPARISON CHART */}
          <div className="card-inner mb-6">
            <h4 className="font-semibold mb-3">Machine Performance Comparison (Test Runs vs Quality NCs)</h4>
            <div style={{ width: '100%', height: 280 }}>
              {data.machines?.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.machines}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="machine_code" tick={{ fontSize: 11 }} />
                    <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
                    <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Legend />
                    <Bar yAxisId="left" dataKey="total_tests" name="Total Runs" fill="#2563eb" radius={[4, 4, 0, 0]} />
                    <Bar yAxisId="left" dataKey="pass_tests" name="Pass Units" fill="#16a34a" radius={[4, 4, 0, 0]} />
                    <Bar yAxisId="right" dataKey="total_ncs" name="NCs Raised" fill="#dc2626" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-center text-muted text-xs pt-24">No machine data available.</p>
              )}
            </div>
          </div>

          {/* MACHINE BENCHMARK MATRIX TABLE */}
          <div className="card-inner">
            <h4 className="font-semibold mb-3">Machine & Test Bed Benchmarking Matrix</h4>
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Machine Code</th>
                    <th>Station Name</th>
                    <th>Tests Performed</th>
                    <th>Pass / Fail</th>
                    <th>Pass Rate</th>
                    <th>Avg Cycle Time</th>
                    <th>Total Testing</th>
                    <th>NCs Logged</th>
                    <th>Rework Time</th>
                  </tr>
                </thead>
                <tbody>
                  {data.machines?.map(m => (
                    <tr key={m.machine_id}>
                      <td className="font-mono font-bold text-primary">{m.machine_code}</td>
                      <td>{m.machine_name}</td>
                      <td className="font-mono text-right font-semibold">{m.total_tests}</td>
                      <td className="font-mono text-center">
                        <span className="text-green-700 font-bold">{m.pass_tests}</span> / <span className="text-red-700 font-bold">{m.fail_tests}</span>
                      </td>
                      <td>
                        <span className={`status-badge ${m.pass_rate_percentage >= 90 ? 'badge-approved' : 'badge-pending'}`}>
                          {m.pass_rate_percentage}%
                        </span>
                      </td>
                      <td className="font-mono text-right font-semibold">{m.average_cycle_time_hours}h</td>
                      <td className="font-mono text-right text-muted">{Math.round(m.total_testing_time_minutes)}m</td>
                      <td className="text-center">
                        {m.total_ncs > 0 ? (
                          <span className="badge badge-danger">{m.total_ncs}</span>
                        ) : (
                          <span className="text-muted text-xs">0</span>
                        )}
                      </td>
                      <td className="font-mono text-right">
                        {m.total_rework_minutes > 0 ? (
                          <span className="font-bold text-amber-700">{m.total_rework_minutes}m</span>
                        ) : (
                          <span className="text-muted">0m</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

