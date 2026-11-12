import React, { useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';

export default function RejectReasonModal({ isOpen, onClose, onConfirm, recordId }) {
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!reason.trim()) {
      setError('A detailed rejection reason is mandatory.');
      return;
    }
    setError('');
    onConfirm(reason);
    setReason('');
  };

  return (
    <div className="modal-overlay">
      <div className="modal-container">
        <div className="modal-header">
          <div className="modal-title-wrap">
            <AlertTriangle className="icon-warning" size={20} />
            <h3>Reject Production Record #{recordId}</h3>
          </div>
          <button className="btn-close" onClick={onClose}><X size={18} /></button>
        </div>
        
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <p className="modal-desc">
              Please enter the specific defect, vibration observation, or technical discrepancy 
              requiring this record to be rejected:
            </p>
            {error && <div className="alert-box alert-danger">{error}</div>}
            <textarea
              className="form-textarea"
              rows={4}
              placeholder="e.g., Abnormal motor temperature surge (>75°C) during rotational cycle..."
              value={reason}
              onChange={(e) => { setReason(e.target.value); setError(''); }}
              required
            />
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-danger">Confirm Rejection</button>
          </div>
        </form>
      </div>
    </div>
  );
}

