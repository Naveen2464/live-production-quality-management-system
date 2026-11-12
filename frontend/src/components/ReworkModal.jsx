import React, { useState } from 'react';
import { Wrench, X, Clock, CheckCircle } from 'lucide-react';
import { createReworkRecord } from '../services/api';

export default function ReworkModal({ isOpen, onClose, nc, onReworkLogged, currentUserId = 3, dropdowns }) {
  const [reworkMinutes, setReworkMinutes] = useState(30);
  const [description, setDescription] = useState('');
  const [reworkDoneById, setReworkDoneById] = useState(currentUserId);
  const [status, setStatus] = useState('COMPLETED');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen || !nc) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!description.trim()) {
      setError('Detailed description of rework activity is required.');
      return;
    }
    setSubmitting(true);
    setError('');

    try {
      const payload = {
        nc_record_id: nc.id,
        production_record_id: nc.production_record_id || null,
        machine_id: nc.machine_id,
        rework_minutes: parseFloat(reworkMinutes),
        rework_description: description,
        rework_done_by_id: parseInt(reworkDoneById),
        completion_date: new Date().toISOString().split('T')[0],
        rework_status: status,
        notes: notes
      };

      await createReworkRecord(payload);
      if (onReworkLogged) onReworkLogged();
      onClose();
    } catch (err) {
      setError(err.message || 'Error logging rework');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-container" style={{ maxWidth: '540px' }}>
        <div className="modal-header" style={{ backgroundColor: '#eff6ff' }}>
          <div className="modal-title-wrap" style={{ color: '#1e40af' }}>
            <Wrench size={20} className="text-primary" />
            <h3>Log Rework for {nc.nc_number}</h3>
          </div>
          <button className="btn-close" onClick={onClose}><X size={18} /></button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <p className="modal-desc">
              Record corrective rework minutes, repair actions, and technician assignment. Rework time synchronizes with linked production run.
            </p>

            {error && <div className="alert-banner alert-error">{error}</div>}

            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <label className="form-label"><Clock size={14} /> Rework Time (Minutes) *</label>
              <input
                type="number"
                step="5"
                min="1"
                required
                className="form-input"
                value={reworkMinutes}
                onChange={(e) => setReworkMinutes(e.target.value)}
              />
            </div>

            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <label className="form-label">Technician Performing Rework *</label>
              <select
                className="form-select"
                value={reworkDoneById}
                onChange={(e) => setReworkDoneById(e.target.value)}
              >
                {dropdowns?.operators?.map(o => (
                  <option key={o.id} value={o.id}>{o.label}</option>
                ))}
              </select>
            </div>

            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <label className="form-label">Corrective Work Performed *</label>
              <textarea
                className="form-textarea"
                rows={3}
                placeholder="e.g., Replaced non-drive end bearing with SKF 6308-2Z, re-greased, and aligned coupling..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                required
              />
            </div>

            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <label className="form-label">Rework Initial Status</label>
              <select
                className="form-select"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                <option value="IN_PROGRESS">IN_PROGRESS (Ongoing Repair)</option>
                <option value="COMPLETED">COMPLETED (Pending QA Verification)</option>
                <option value="VERIFIED">VERIFIED (QA Inspection Done)</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Notes & Technical Observations</label>
              <input
                type="text"
                className="form-input"
                placeholder="Dial gauge readings, torque applied, etc."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Saving...' : 'Save Rework Record'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

