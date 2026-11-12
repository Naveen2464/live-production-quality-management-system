import React, { useState } from 'react';
import { 
  AlertTriangle, CheckCircle, Send, RefreshCw, Cpu, 
  Calendar, Layers, ShieldAlert, Clock, Building
} from 'lucide-react';
import { createQualityRecord } from '../services/api';

export default function QualityDefectForm({ dropdowns, onDefectLogged, currentUserId = 4 }) {
  const todayStr = new Date().toISOString().split('T')[0];

  const initialForm = {
    machine_id: dropdowns?.machines?.[0]?.id || '',
    production_record_id: '',
    defect_description: '',
    defect_category: 'Electrical',
    severity: 'MEDIUM',
    date_of_occurrence: todayStr,
    responsible_department: 'Assembly',
    rework_minutes: 0,
    create_nc: true,
    nc_classification: 'MAJOR'
  };

  const [formData, setFormData] = useState(initialForm);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState({ text: '', type: '' });

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
    if (!formData.defect_description.trim()) {
      setMessage({ text: 'Please provide a detailed defect description.', type: 'error' });
      return;
    }

    setSubmitting(true);
    setMessage({ text: '', type: '' });

    try {
      const payload = {
        machine_id: parseInt(formData.machine_id),
        production_record_id: formData.production_record_id ? parseInt(formData.production_record_id) : null,
        defect_description: formData.defect_description,
        defect_category: formData.defect_category,
        date_of_occurrence: formData.date_of_occurrence,
        responsible_department: formData.responsible_department,
        severity: formData.severity,
        rework_minutes: parseFloat(formData.rework_minutes) || 0.0,
        create_nc: Boolean(formData.create_nc),
        nc_classification: formData.nc_classification
      };

      const result = await createQualityRecord(payload);
      setMessage({
        text: `Quality defect logged successfully (Record #${result.id})${result.nc_number ? ` with NC Case ${result.nc_number}` : ''}!`,
        type: 'success'
      });

      if (onDefectLogged) onDefectLogged(result);
    } catch (err) {
      setMessage({ text: err.message || 'Error logging quality defect', type: 'error' });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2 className="card-title">Log Quality Incident & Non-Conformance</h2>
          <p className="card-subtitle">
            Report testing anomalies, assembly defects, and calibration deviations. Automatically spawns an NC tracking case.
          </p>
        </div>
      </div>

      {message.text && (
        <div className={`alert-banner ${message.type === 'success' ? 'alert-success' : 'alert-error'}`}>
          {message.type === 'success' ? <CheckCircle size={18} /> : <AlertTriangle size={18} />}
          <span>{message.text}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="form-grid">
        {/* ROW 1: Machine, Production Link, Date, Dept */}
        <div className="form-group">
          <label className="form-label"><Cpu size={14} /> Machine / Test Rig *</label>
          <select
            name="machine_id"
            required
            className="form-select"
            value={formData.machine_id}
            onChange={handleChange}
          >
            {dropdowns?.machines?.map(m => (
              <option key={m.id} value={m.id}>{m.label}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label"><Layers size={14} /> Linked Production Run ID</label>
          <input
            type="number"
            name="production_record_id"
            placeholder="e.g. 1 (optional)"
            className="form-input"
            value={formData.production_record_id}
            onChange={handleChange}
          />
          <small className="help-text">Links defect directly to daily test batch.</small>
        </div>

        <div className="form-group">
          <label className="form-label"><Calendar size={14} /> Date of Occurrence *</label>
          <input
            type="date"
            name="date_of_occurrence"
            required
            className="form-input"
            value={formData.date_of_occurrence}
            onChange={handleChange}
          />
        </div>

        <div className="form-group">
          <label className="form-label"><Building size={14} /> Responsible Department *</label>
          <select
            name="responsible_department"
            className="form-select"
            value={formData.responsible_department}
            onChange={handleChange}
          >
            <option value="Production">Production Line</option>
            <option value="Quality Assurance">Quality Assurance</option>
            <option value="Assembly">Assembly & Stator Insertion</option>
            <option value="Maintenance">Plant Maintenance</option>
            <option value="R&D">R&D / Electrical Engineering</option>
          </select>
        </div>

        {/* ROW 2: Category, Severity, Estimated Rework, NC Classification */}
        <div className="form-group">
          <label className="form-label">Defect Category *</label>
          <select
            name="defect_category"
            className="form-select"
            value={formData.defect_category}
            onChange={handleChange}
          >
            <option value="Electrical">Electrical (Insulation / Phase / Resistance)</option>
            <option value="Mechanical">Mechanical (Vibration / Runout / Alignment)</option>
            <option value="Bearing Issue">Bearing Issue (Overheating / Noise / Fit)</option>
            <option value="Winding Defect">Winding Defect (Low Megger / Surge)</option>
            <option value="Frame Defect">Frame Defect (Flange / Ingress Seal)</option>
            <option value="Calibration">Calibration / Sensor Deviation</option>
          </select>
        </div>

        <div className="form-group">
          <label className="form-label"><ShieldAlert size={14} /> Severity Rating *</label>
          <select
            name="severity"
            className="form-select"
            value={formData.severity}
            onChange={handleChange}
          >
            <option value="LOW">LOW (Minor cosmetic or visual)</option>
            <option value="MEDIUM">MEDIUM (Reworkable deviation)</option>
            <option value="HIGH">HIGH (Major performance or vibration issue)</option>
            <option value="CRITICAL">CRITICAL (Safety violation / total breakdown)</option>
          </select>
        </div>

        <div className="form-group">
          <label className="form-label"><Clock size={14} /> Estimated Initial Rework (min)</label>
          <input
            type="number"
            step="5"
            min="0"
            name="rework_minutes"
            className="form-input"
            value={formData.rework_minutes}
            onChange={handleChange}
          />
        </div>

        <div className="form-group">
          <label className="form-label">NC Classification</label>
          <select
            name="nc_classification"
            className="form-select"
            value={formData.nc_classification}
            onChange={handleChange}
          >
            <option value="MINOR">MINOR Non-Conformance</option>
            <option value="MAJOR">MAJOR Non-Conformance</option>
            <option value="CRITICAL">CRITICAL Non-Conformance</option>
          </select>
        </div>

        {/* ROW 3: Defect Description */}
        <div className="form-group full-width">
          <label className="form-label">Detailed Defect Description *</label>
          <textarea
            name="defect_description"
            rows="3"
            required
            className="form-textarea"
            placeholder="Provide specific technical observations, measured vibration levels, megger readings, or structural anomalies..."
            value={formData.defect_description}
            onChange={handleChange}
          />
        </div>

        {/* Auto NC Checkbox */}
        <div className="form-group checkbox-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              name="create_nc"
              checked={formData.create_nc}
              onChange={handleChange}
            />
            <span className="checkbox-text">Automatically Spawn Formal Non-Conformance Case (Recommended)</span>
          </label>
        </div>

        <div className="form-actions full-width">
          <button type="button" className="btn btn-secondary" onClick={handleReset}>
            <RefreshCw size={15} /> Reset
          </button>
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            <Send size={15} /> {submitting ? 'Submitting...' : 'Log Incident & Issue NC'}
          </button>
        </div>
      </form>
    </div>
  );
}

