import React, { useState, useEffect } from 'react';
import { 
  X, AlertOctagon, CheckCircle2, Clock, ArrowRight, ShieldCheck, 
  Wrench, Save, Check
} from 'lucide-react';
import { updateNCRecord, transitionNCStatus, getNCRecordById } from '../services/api';

export default function NCDetailModal({ isOpen, onClose, ncId, onUpdated, currentRole, currentUserId }) {
  const [nc, setNc] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // RCA fields
  const [rootCause, setRootCause] = useState('');
  const [correctiveAction, setCorrectiveAction] = useState('');
  const [preventiveAction, setPreventiveAction] = useState('');
  const [savingRca, setSavingRca] = useState(false);

  // Closure state
  const [closingMode, setClosingMode] = useState(false);
  const [closureNotes, setClosureNotes] = useState('');
  const [transitioning, setTransitioning] = useState(false);

  const fetchDetail = async () => {
    if (!ncId) return;
    setLoading(true);
    setError('');
    try {
      const data = await getNCRecordById(ncId);
      setNc(data);
      setRootCause(data.root_cause || '');
      setCorrectiveAction(data.corrective_action || '');
      setPreventiveAction(data.preventive_action || '');
    } catch (err) {
      setError(err.message || 'Error fetching NC details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && ncId) {
      fetchDetail();
      setClosingMode(false);
      setClosureNotes('');
      setSuccess('');
    }
  }, [isOpen, ncId]);

  if (!isOpen || !ncId) return null;

  const handleSaveRca = async (e) => {
    e.preventDefault();
    setSavingRca(true);
    setError('');
    setSuccess('');
    try {
      await updateNCRecord(ncId, {
        root_cause: rootCause,
        corrective_action: correctiveAction,
        preventive_action: preventiveAction
      });
      setSuccess('Root Cause Analysis & CAPA updated successfully.');
      fetchDetail();
      if (onUpdated) onUpdated();
    } catch (err) {
      setError(err.message || 'Error updating RCA');
    } finally {
      setSavingRca(false);
    }
  };

  const handleStatusTransition = async (targetStatus) => {
    if (targetStatus === 'CLOSED' && !closingMode) {
      setClosingMode(true);
      return;
    }

    setTransitioning(true);
    setError('');
    setSuccess('');

    try {
      await transitionNCStatus(
        ncId,
        targetStatus,
        currentUserId || 4,
        currentRole,
        closingMode ? closureNotes : null,
        rootCause,
        correctiveAction
      );
      setSuccess(`NC successfully transitioned to ${targetStatus}!`);
      setClosingMode(false);
      fetchDetail();
      if (onUpdated) onUpdated();
    } catch (err) {
      setError(err.message || `Failed to transition status to ${targetStatus}`);
    } finally {
      setTransitioning(false);
    }
  };

  const isQEOrAdmin = currentRole === 'Quality Engineer' || currentRole === 'Administrator';

  return (
    <div className="modal-overlay">
      <div className="modal-container" style={{ maxWidth: '800px', maxHeight: '90vh', overflowY: 'auto' }}>
        {/* MODAL HEADER */}
        <div className="modal-header" style={{ backgroundColor: '#f8fafc' }}>
          <div className="modal-title-wrap">
            <AlertOctagon size={22} className="text-danger" />
            <div>
              <h3>{nc ? `${nc.nc_number}: ${nc.title}` : 'NC Details'}</h3>
              <small className="text-muted">
                Machine: {nc?.machine_code} • Classification: <strong className={`classification-${nc?.classification?.toLowerCase()}`}>{nc?.classification}</strong>
              </small>
            </div>
          </div>
          <button className="btn-close" onClick={onClose}><X size={18} /></button>
        </div>

        {loading ? (
          <div className="center-loader py-12">
            <div className="loading-spinner" />
            <p>Loading NC case file...</p>
          </div>
        ) : nc ? (
          <div className="modal-body" style={{ padding: '1.5rem' }}>
            {error && <div className="alert-banner alert-error mb-4">{error}</div>}
            {success && <div className="alert-banner alert-success mb-4">{success}</div>}

            {/* STATUS WORKFLOW STEPPER */}
            <div className="nc-stepper mb-6">
              <div className={`step-item ${nc.status === 'OPEN' ? 'step-active' : 'step-completed'}`}>
                <div className="step-number">1</div>
                <div className="step-label">OPEN</div>
              </div>
              <div className="step-divider" />
              <div className={`step-item ${nc.status === 'IN_PROGRESS' ? 'step-active' : (['UNDER_REVIEW', 'CLOSED'].includes(nc.status) ? 'step-completed' : '')}`}>
                <div className="step-number">2</div>
                <div className="step-label">IN PROGRESS</div>
              </div>
              <div className="step-divider" />
              <div className={`step-item ${nc.status === 'UNDER_REVIEW' ? 'step-active' : (nc.status === 'CLOSED' ? 'step-completed' : '')}`}>
                <div className="step-number">3</div>
                <div className="step-label">UNDER REVIEW</div>
              </div>
              <div className="step-divider" />
              <div className={`step-item ${nc.status === 'CLOSED' ? 'step-active' : ''}`}>
                <div className="step-number">4</div>
                <div className="step-label">CLOSED</div>
              </div>
            </div>

            {/* WORKFLOW TRANSITION BUTTONS */}
            <div className="status-action-bar mb-6">
              <span className="text-xs font-semibold text-muted">Workflow Actions:</span>

              {nc.status === 'OPEN' && (
                <button 
                  className="btn btn-secondary btn-sm"
                  disabled={transitioning}
                  onClick={() => handleStatusTransition('IN_PROGRESS')}
                >
                  <ArrowRight size={14} /> Start Investigation (IN_PROGRESS)
                </button>
              )}

              {nc.status === 'IN_PROGRESS' && (
                <button 
                  className="btn btn-secondary btn-sm"
                  disabled={transitioning}
                  onClick={() => handleStatusTransition('UNDER_REVIEW')}
                >
                  <ArrowRight size={14} /> Submit for Review (UNDER_REVIEW)
                </button>
              )}

              {nc.status === 'UNDER_REVIEW' && !closingMode && (
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button 
                    className="btn btn-ghost btn-sm"
                    disabled={transitioning}
                    onClick={() => handleStatusTransition('IN_PROGRESS')}
                  >
                    Reopen for Rework
                  </button>
                  <button 
                    className="btn btn-primary btn-sm"
                    disabled={transitioning || !isQEOrAdmin}
                    title={!isQEOrAdmin ? 'Only Quality Engineers and Administrators can close NC cases' : ''}
                    onClick={() => setClosingMode(true)}
                  >
                    <ShieldCheck size={14} /> Verify & Close NC
                  </button>
                </div>
              )}

              {nc.status === 'CLOSED' && (
                <span className="badge badge-approved">
                  <CheckCircle2 size={14} /> Formally Closed & Verified by {nc.closed_by_name || 'Quality Lead'}
                </span>
              )}
            </div>

            {/* CLOSURE PROMPT (when closingMode is active) */}
            {closingMode && (
              <div className="closure-box mb-6">
                <div className="closure-title">
                  <ShieldCheck size={18} className="text-primary" />
                  <h4>Quality Engineer Sign-off & Closure Verification</h4>
                </div>
                <p className="text-xs text-muted mb-3">
                  Under standard ISO 9001 quality regulations, closing an NC requires formal sign-off confirming 
                  that the defect has been corrected and vibration/electrical performance has been re-tested.
                </p>
                <textarea
                  className="form-textarea mb-3"
                  rows={3}
                  placeholder="Enter verification notes: e.g., Motor re-tested on Dyno Beta; vibration reduced to 1.1 mm/s RMS. Approved for dispatch."
                  value={closureNotes}
                  onChange={(e) => setClosureNotes(e.target.value)}
                  required
                />
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                  <button className="btn btn-secondary btn-sm" onClick={() => setClosingMode(false)}>
                    Cancel
                  </button>
                  <button 
                    className="btn btn-danger btn-sm"
                    disabled={transitioning || !closureNotes.trim()}
                    onClick={() => handleStatusTransition('CLOSED')}
                  >
                    <Check size={14} /> Confirm Formal NC Closure
                  </button>
                </div>
              </div>
            )}

            {/* PROBLEM DESCRIPTION SUMMARY */}
            <div className="card-inner mb-6">
              <h4 className="font-semibold mb-2">Defect Statement</h4>
              <p className="text-sm bg-slate-50 p-3 rounded border">{nc.description}</p>
              <div className="grid grid-cols-3 gap-2 mt-3 text-xs text-muted">
                <div><strong>Category:</strong> {nc.defect_category}</div>
                <div><strong>Dept:</strong> {nc.responsible_department}</div>
                <div><strong>Total Rework Logged:</strong> <span className="font-semibold text-primary">{nc.total_rework_minutes} min</span></div>
              </div>
            </div>

            {/* ROOT CAUSE ANALYSIS & CAPA FORM */}
            <form onSubmit={handleSaveRca} className="card-inner mb-6">
              <div className="flex justify-between items-center mb-3">
                <h4 className="font-semibold">Root Cause Analysis & Corrective Actions (CAPA)</h4>
                {nc.status !== 'CLOSED' && (
                  <button type="submit" className="btn btn-secondary btn-sm" disabled={savingRca}>
                    <Save size={14} /> {savingRca ? 'Saving...' : 'Save RCA'}
                  </button>
                )}
              </div>

              <div className="form-group mb-3">
                <label className="form-label text-xs">Root Cause Analysis (RCA)</label>
                <textarea
                  className="form-textarea"
                  rows={2}
                  disabled={nc.status === 'CLOSED'}
                  placeholder="e.g., Dynamic imbalance caused by uneven thermal expansion during rotor curing..."
                  value={rootCause}
                  onChange={(e) => setRootCause(e.target.value)}
                />
              </div>

              <div className="form-group mb-3">
                <label className="form-label text-xs">Corrective Action Taken</label>
                <textarea
                  className="form-textarea"
                  rows={2}
                  disabled={nc.status === 'CLOSED'}
                  placeholder="e.g., Re-balanced rotor on rig M-201 and applied 15g balance weight..."
                  value={correctiveAction}
                  onChange={(e) => setCorrectiveAction(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label text-xs">Preventive Action (To Prevent Recurrence)</label>
                <textarea
                  className="form-textarea"
                  rows={2}
                  disabled={nc.status === 'CLOSED'}
                  placeholder="e.g., Updated standard operating procedure for stator oven temperature profile..."
                  value={preventiveAction}
                  onChange={(e) => setPreventiveAction(e.target.value)}
                />
              </div>
            </form>

            {/* REWORK HISTORY TABLE */}
            <div className="card-inner">
              <h4 className="font-semibold mb-3">Rework Tasks & Labor Logged ({nc.rework_records?.length || 0})</h4>
              {nc.rework_records && nc.rework_records.length > 0 ? (
                <div className="table-responsive">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Technician</th>
                        <th>Rework Minutes</th>
                        <th>Actions Taken</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {nc.rework_records.map(r => (
                        <tr key={r.id}>
                          <td className="font-mono">#{r.id}</td>
                          <td>{r.rework_done_by_name || `Tech #${r.rework_done_by_id}`}</td>
                          <td className="font-mono text-right font-semibold">{r.rework_minutes}m</td>
                          <td>{r.rework_description}</td>
                          <td>
                            <span className={`status-badge badge-${r.rework_status === 'VERIFIED' ? 'approved' : (r.rework_status === 'COMPLETED' ? 'info' : 'pending')}`}>
                              {r.rework_status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-muted text-xs">No rework tasks logged for this ticket yet.</p>
              )}
            </div>

            {/* CLOSURE SUMMARY (IF CLOSED) */}
            {nc.status === 'CLOSED' && nc.closure_notes && (
              <div className="closure-summary mt-4 p-3 bg-green-50 border border-green-200 rounded">
                <div className="font-semibold text-green-900 text-sm">Closure Sign-Off Notes:</div>
                <div className="text-xs text-green-800 mt-1">{nc.closure_notes}</div>
                <div className="text-xs text-muted mt-2">Closed on {new Date(nc.closed_at).toLocaleString()}</div>
              </div>
            )}
          </div>
        ) : null}

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Close Case File</button>
        </div>
      </div>
    </div>
  );
}

