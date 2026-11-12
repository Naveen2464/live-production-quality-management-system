import React, { useState, useMemo } from 'react';
import { 
  Clock, CheckCircle, AlertCircle, RefreshCw, Send,
  Cpu, Wrench, Calendar, UserCheck, ShieldCheck, Building2
} from 'lucide-react';
import { createProductionRecord } from '../services/api';

export default function ProductionEntryForm({ dropdowns, onRecordCreated, currentUserId = 3, currentSupervisorId = 2 }) {
  const todayStr = new Date().toISOString().split('T')[0];

  const initialForm = {
    date: todayStr,
    machine_id: dropdowns.machines[0]?.id || '',
    frame_id: dropdowns.frames[0]?.id || '',
    shift_id: dropdowns.shifts[0]?.id || '',
    operator_id: currentUserId,
    supervisor_id: currentSupervisorId,
    customer_id: dropdowns.customers[0]?.id || '',
    static_time: 15.0,
    mounting_time: 10.0,
    rotational_time: 25.0,
    dismantling_time: 10.0,
    test_result: 'PASS',
    nc_raised: false,
    rework_time: 0.0,
    notes: ''
  };

  const [formData, setFormData] = useState(initialForm);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState({ text: '', type: '' });

  // Dynamic calculations:
  // Total Testing Time = Static + Mounting + Rotational + Dismantling
  // Cycle Time (hrs) = Total Testing Time / 60
  const totalTestingTime = useMemo(() => {
    const s = parseFloat(formData.static_time) || 0;
    const m = parseFloat(formData.mounting_time) || 0;
    const r = parseFloat(formData.rotational_time) || 0;
    const d = parseFloat(formData.dismantling_time) || 0;
    return Math.round((s + m + r + d) * 100) / 100;
  }, [formData.static_time, formData.mounting_time, formData.rotational_time, formData.dismantling_time]);

  const cycleTimeHours = useMemo(() => {
    return Math.round((totalTestingTime / 60.0) * 10000) / 10000;
  }, [totalTestingTime]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
    setMessage({ text: '', type: '' });
  };

  const handleReset = () => {
    setFormData(initialForm);
    setMessage({ text: '', type: '' });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setMessage({ text: '', type: '' });

    try {
      const payload = {
        date: formData.date,
        machine_id: parseInt(formData.machine_id),
        frame_id: parseInt(formData.frame_id),
        shift_id: parseInt(formData.shift_id),
        operator_id: parseInt(formData.operator_id),
        supervisor_id: parseInt(formData.supervisor_id),
        customer_id: parseInt(formData.customer_id),
        static_time: parseFloat(formData.static_time),
        mounting_time: parseFloat(formData.mounting_time),
        rotational_time: parseFloat(formData.rotational_time),
        dismantling_time: parseFloat(formData.dismantling_time),
        total_testing_time: totalTestingTime,
        cycle_time_hours: cycleTimeHours,
        test_result: formData.test_result,
        nc_raised: Boolean(formData.nc_raised),
        rework_time: parseFloat(formData.rework_time) || 0.0,
        notes: formData.notes
      };

      const result = await createProductionRecord(payload);
      setMessage({
        text: `Production record #${result.id} submitted successfully! Cycle Time: ${result.cycle_time_hours} hrs (${result.total_testing_time} min).`,
        type: 'success'
      });

      // Clear or notify parent
      if (onRecordCreated) {
        onRecordCreated(result);
      }
    } catch (err) {
      setMessage({
        text: err.message || 'Error submitting production record',
        type: 'error'
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card production-entry-card">
      <div className="card-header">
        <div>
          <h2 className="card-title">Production Testing Data Entry</h2>
          <p className="card-subtitle">
            Enter machine test run timing, quality metrics, and cycle parameters. All cycle times are validated by the backend.
          </p>
        </div>
        <div className="live-kpi-group">
          <div className="kpi-pill kpi-time">
            <Clock size={16} />
            <span>Total Testing: <strong>{totalTestingTime} min</strong></span>
          </div>
          <div className="kpi-pill kpi-cycle">
            <Cpu size={16} />
            <span>Cycle Time: <strong>{cycleTimeHours} hrs</strong></span>
          </div>
        </div>
      </div>

      {message.text && (
        <div className={`alert-banner ${message.type === 'success' ? 'alert-success' : 'alert-error'}`}>
          {message.type === 'success' ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
          <span>{message.text}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="form-grid">
        {/* ROW 1: Date, Machine, Frame, Shift */}
        <div className="form-group">
          <label className="form-label"><Calendar size={14} /> Date *</label>
          <input
            type="date"
            name="date"
            required
            className="form-input"
            value={formData.date}
            onChange={handleChange}
          />
        </div>

        <div className="form-group">
          <label className="form-label"><Cpu size={14} /> Machine Number *</label>
          <select
            name="machine_id"
            required
            className="form-select"
            value={formData.machine_id}
            onChange={handleChange}
          >
            {dropdowns.machines.map(m => (
              <option key={m.id} value={m.id}>{m.label}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label"><Wrench size={14} /> Frame *</label>
          <select
            name="frame_id"
            required
            className="form-select"
            value={formData.frame_id}
            onChange={handleChange}
          >
            {dropdowns.frames.map(f => (
              <option key={f.id} value={f.id}>{f.label}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label"><Clock size={14} /> Shift *</label>
          <select
            name="shift_id"
            required
            className="form-select"
            value={formData.shift_id}
            onChange={handleChange}
          >
            {dropdowns.shifts.map(s => (
              <option key={s.id} value={s.id}>{s.label}</option>
            ))}
          </select>
        </div>

        {/* ROW 2: Customer, Operator, Supervisor, Test Result */}
        <div className="form-group">
          <label className="form-label"><Building2 size={14} /> Customer *</label>
          <select
            name="customer_id"
            required
            className="form-select"
            value={formData.customer_id}
            onChange={handleChange}
          >
            {dropdowns.customers.map(c => (
              <option key={c.id} value={c.id}>{c.label}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label"><UserCheck size={14} /> Operator *</label>
          <select
            name="operator_id"
            required
            className="form-select"
            value={formData.operator_id}
            onChange={handleChange}
          >
            {dropdowns.operators.map(o => (
              <option key={o.id} value={o.id}>{o.label}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label"><ShieldCheck size={14} /> Supervisor *</label>
          <select
            name="supervisor_id"
            required
            className="form-select"
            value={formData.supervisor_id}
            onChange={handleChange}
          >
            {dropdowns.supervisors.map(s => (
              <option key={s.id} value={s.id}>{s.label}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">Test Result *</label>
          <select
            name="test_result"
            className="form-select"
            value={formData.test_result}
            onChange={handleChange}
          >
            <option value="PASS">PASS (Acceptable)</option>
            <option value="FAIL">FAIL (Non-Compliant)</option>
            <option value="CONDITIONAL">CONDITIONAL (Observation)</option>
          </select>
        </div>

        {/* ROW 3: Stage Times (minutes) */}
        <div className="form-section-header">Stage Testing Times (Minutes)</div>

        <div className="form-group">
          <label className="form-label">Static Testing Time (min) *</label>
          <input
            type="number"
            step="0.1"
            min="0"
            required
            name="static_time"
            className="form-input"
            value={formData.static_time}
            onChange={handleChange}
          />
        </div>

        <div className="form-group">
          <label className="form-label">Mounting Time (min) *</label>
          <input
            type="number"
            step="0.1"
            min="0"
            required
            name="mounting_time"
            className="form-input"
            value={formData.mounting_time}
            onChange={handleChange}
          />
        </div>

        <div className="form-group">
          <label className="form-label">Rotational Testing Time (min) *</label>
          <input
            type="number"
            step="0.1"
            min="0"
            required
            name="rotational_time"
            className="form-input"
            value={formData.rotational_time}
            onChange={handleChange}
          />
        </div>

        <div className="form-group">
          <label className="form-label">Dismantling Time (min) *</label>
          <input
            type="number"
            step="0.1"
            min="0"
            required
            name="dismantling_time"
            className="form-input"
            value={formData.dismantling_time}
            onChange={handleChange}
          />
        </div>

        {/* ROW 4: Quality & NC Flags */}
        <div className="form-group checkbox-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              name="nc_raised"
              checked={formData.nc_raised}
              onChange={handleChange}
            />
            <span className="checkbox-text">Non-Conformance Raised (NC Ticket)</span>
          </label>
          <small className="help-text">Check if defect or deviation was identified during test run.</small>
        </div>

        <div className="form-group">
          <label className="form-label">Rework Time (min)</label>
          <input
            type="number"
            step="0.5"
            min="0"
            name="rework_time"
            className="form-input"
            value={formData.rework_time}
            onChange={handleChange}
          />
        </div>

        <div className="form-group full-width">
          <label className="form-label">Notes & Observations</label>
          <textarea
            name="notes"
            rows="2"
            className="form-textarea"
            placeholder="Optional operator observations, vibration remarks, ambient temp, etc."
            value={formData.notes}
            onChange={handleChange}
          />
        </div>

        {/* Action Buttons */}
        <div className="form-actions full-width">
          <button type="button" className="btn btn-secondary" onClick={handleReset}>
            <RefreshCw size={15} /> Reset Form
          </button>
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            <Send size={15} /> {submitting ? 'Submitting...' : 'Submit Production Record'}
          </button>
        </div>
      </form>
    </div>
  );
}

