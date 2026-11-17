import React, { useState, useEffect } from 'react';
import { 
  FileSpreadsheet, Upload, CheckCircle2, AlertTriangle, Download, 
  Database, RefreshCw, FileText, Check, ShieldCheck, ArrowRight, X
} from 'lucide-react';
import { 
  validateExcelUpload, confirmImport, getImportHistory, 
  getImportErrors, getImportErrorsDownloadUrl,
  getProductionExportUrl, getQualityExportUrl 
} from '../services/api';

export default function ExcelMigrationView({ currentRole, currentUserId }) {
  const [file, setFile] = useState(null);
  const [fileType, setFileType] = useState('PRODUCTION');
  const [uploading, setUploading] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [activePreviewTab, setActivePreviewTab] = useState('valid'); // 'valid' | 'rejected'
  
  const [confirming, setConfirming] = useState(false);
  const [commitSummary, setCommitSummary] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');

  // History
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [selectedHistoryErrors, setSelectedHistoryErrors] = useState(null);
  const [viewingHistoryId, setViewingHistoryId] = useState(null);

  const fetchHistory = async () => {
    setLoadingHistory(true);
    try {
      const data = await getImportHistory();
      setHistory(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      if (!selected.name.toLowerCase().endsWith('.xlsx') && !selected.name.toLowerCase().endsWith('.xls')) {
        setErrorMsg('Invalid file format. Please select an Excel workbook (.xlsx or .xls).');
        setFile(null);
        return;
      }
      setFile(selected);
      setErrorMsg('');
      setValidationResult(null);
      setCommitSummary(null);
    }
  };

  const handleValidate = async (e) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setErrorMsg('');
    setCommitSummary(null);

    try {
      const result = await validateExcelUpload(file, fileType);
      setValidationResult(result);
      if (result.rejected_count > 0 && result.valid_count === 0) {
        setActivePreviewTab('rejected');
      } else {
        setActivePreviewTab('valid');
      }
    } catch (err) {
      setErrorMsg(err.message || 'Validation failed');
    } finally {
      setUploading(false);
    }
  };

  const handleConfirmCommit = async () => {
    if (!validationResult || !validationResult.batch_id) return;
    setConfirming(true);
    setErrorMsg('');

    try {
      const res = await confirmImport(
        validationResult.batch_id,
        currentUserId || 1,
        'admin',
        currentRole || 'Administrator'
      );
      setCommitSummary(res);
      setValidationResult(null);
      setFile(null);
      fetchHistory();
    } catch (err) {
      setErrorMsg(err.message || 'Error committing import');
    } finally {
      setConfirming(false);
    }
  };

  const viewHistoryErrors = async (historyId) => {
    setViewingHistoryId(historyId);
    try {
      const errors = await getImportErrors(historyId);
      setSelectedHistoryErrors(errors);
    } catch (err) {
      alert(`Error fetching errors: ${err.message}`);
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2 className="card-title">Excel Data Migration Engine (Pandas Powered)</h2>
          <p className="card-subtitle">
            Upload, validate and migrate historical workbooks: <strong>Production.xlsx</strong> and <strong>Quality_NC_s_tracking.xlsx</strong>.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <a 
            href={getProductionExportUrl()} 
            className="btn btn-secondary btn-sm"
            download
            title="Export full production dataset to Excel"
          >
            <Download size={14} /> Export Production.xlsx
          </a>
          <a 
            href={getQualityExportUrl()} 
            className="btn btn-secondary btn-sm"
            download
            title="Export full Quality & NC dataset to Excel"
          >
            <Download size={14} /> Export Quality_NC.xlsx
          </a>
        </div>
      </div>

      {errorMsg && <div className="alert-banner alert-error mb-4">{errorMsg}</div>}
      
      {commitSummary && (
        <div className="alert-banner alert-success mb-4">
          <CheckCircle2 size={18} />
          <div>
            <strong>Import Completed Successfully!</strong>
            <div>{commitSummary.message}</div>
            <small>Import Batch #{commitSummary.import_history_id} • All valid records persisted to PostgreSQL with audit trail.</small>
          </div>
        </div>
      )}

      {/* UPLOAD FORM */}
      <div className="card-inner mb-6">
        <form onSubmit={handleValidate} className="form-grid">
          <div className="form-group" style={{ gridColumn: 'span 2' }}>
            <label className="form-label">Workbook Target</label>
            <select 
              className="form-select"
              value={fileType}
              onChange={(e) => { setFileType(e.target.value); setValidationResult(null); }}
            >
              <option value="PRODUCTION">Production Workbook (Production.xlsx)</option>
              <option value="QUALITY">Quality & NC Tracking (Quality_NC_s_tracking.xlsx)</option>
            </select>
          </div>

          <div className="form-group" style={{ gridColumn: 'span 2' }}>
            <label className="form-label">Select Excel File (.xlsx / .xls)</label>
            <input 
              type="file" 
              accept=".xlsx, .xls"
              className="form-input"
              onChange={handleFileChange}
              required
            />
          </div>

          <div className="form-actions full-width" style={{ marginTop: '0.5rem' }}>
            <button 
              type="submit" 
              className="btn btn-primary"
              disabled={uploading || !file}
            >
              <Upload size={15} /> {uploading ? 'Analyzing with Pandas...' : 'Upload & Validate Spreadsheet'}
            </button>
          </div>
        </form>
      </div>

      {/* VALIDATION SUMMARY CARD */}
      {validationResult && (
        <div className="validation-summary-box mb-6 p-4 bg-slate-50 border rounded">
          <div className="flex justify-between items-center mb-3">
            <div>
              <h3 className="text-base font-bold text-slate-800">
                Validation Summary for "{validationResult.file_name}"
              </h3>
              <p className="text-xs text-muted">
                Worksheet: <strong>{validationResult.detected_sheet}</strong> • Detected Columns: {validationResult.detected_columns?.length}
              </p>
            </div>
            {validationResult.can_commit && (
              <button 
                className="btn btn-primary"
                disabled={confirming}
                onClick={handleConfirmCommit}
              >
                <Check size={16} /> {confirming ? 'Committing...' : `Confirm & Commit (${validationResult.valid_count} Records)`}
              </button>
            )}
          </div>

          <div className="grid grid-cols-4 gap-3 mb-4">
            <div className="kpi-pill" style={{ backgroundColor: '#f1f5f9' }}>
              <div>
                <div className="text-xs text-muted font-bold">TOTAL ROWS</div>
                <div className="text-xl font-bold">{validationResult.total_rows}</div>
              </div>
            </div>
            <div className="kpi-pill kpi-time">
              <div>
                <div className="text-xs text-green-700 font-bold">READY TO IMPORT</div>
                <div className="text-xl font-bold text-green-800">{validationResult.valid_count}</div>
              </div>
            </div>
            <div className="kpi-pill" style={{ backgroundColor: '#fff1f2', color: '#991b1b', border: '1px solid #fecaca' }}>
              <div>
                <div className="text-xs text-red-700 font-bold">REJECTED ROWS</div>
                <div className="text-xl font-bold text-red-800">{validationResult.rejected_count}</div>
              </div>
            </div>
            <div className="kpi-pill" style={{ backgroundColor: '#fffbeb', color: '#b45309', border: '1px solid #fde68a' }}>
              <div>
                <div className="text-xs text-amber-700 font-bold">DUPLICATE RUNS</div>
                <div className="text-xl font-bold text-amber-800">{validationResult.duplicate_count}</div>
              </div>
            </div>
          </div>

          {/* PREVIEW TABS */}
          <div className="tab-navigation mb-3" style={{ borderBottom: '1px solid #cbd5e1' }}>
            <button 
              className={`tab-btn ${activePreviewTab === 'valid' ? 'active' : ''}`}
              onClick={() => setActivePreviewTab('valid')}
            >
              Valid Records Preview ({validationResult.valid_count})
            </button>
            <button 
              className={`tab-btn ${activePreviewTab === 'rejected' ? 'active' : ''}`}
              onClick={() => setActivePreviewTab('rejected')}
            >
              Rejected Rows & Error Report ({validationResult.rejected_count})
            </button>
          </div>

          {/* TAB 1: VALID RECORDS PREVIEW */}
          {activePreviewTab === 'valid' && (
            <div>
              {validationResult.sample_valid_rows?.length > 0 ? (
                <div className="table-responsive">
                  <table className="data-table">
                    <thead>
                      <tr>
                        {Object.keys(validationResult.sample_valid_rows[0]).map(col => (
                          <th key={col}>{col.replace('_', ' ').toUpperCase()}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {validationResult.sample_valid_rows.map((row, i) => (
                        <tr key={i}>
                          {Object.values(row).map((val, j) => (
                            <td key={j}>{String(val !== null ? val : '')}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-muted text-xs p-3">No valid records to display.</p>
              )}
            </div>
          )}

          {/* TAB 2: REJECTED ROWS REPORT */}
          {activePreviewTab === 'rejected' && (
            <div>
              {validationResult.rejected_rows?.length > 0 ? (
                <div className="table-responsive">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Excel Row</th>
                        <th>Error Category</th>
                        <th>Target Field</th>
                        <th>Rejection Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {validationResult.rejected_rows.map((err, i) => (
                        <tr key={i} className="row-rejected">
                          <td className="font-mono font-bold">Row #{err.row_number}</td>
                          <td><span className="badge badge-danger">{err.error_type}</span></td>
                          <td><strong>{err.field_name || 'N/A'}</strong></td>
                          <td className="text-red-900">{err.error_message}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-3 text-green-700 font-semibold text-xs">
                  Zero rejected records! Every row passed strict validation.
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* IMPORT HISTORY TABLE */}
      <div>
        <h3 className="font-semibold text-base mb-3">Historical Migration Batches</h3>
        {loadingHistory ? (
          <p className="text-muted text-xs">Loading import history...</p>
        ) : history.length === 0 ? (
          <p className="text-muted text-xs">No historical imports recorded yet.</p>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Batch ID</th>
                  <th>File Name</th>
                  <th>Type</th>
                  <th>Total Rows</th>
                  <th>Valid</th>
                  <th>Rejected</th>
                  <th>Duplicates</th>
                  <th>Imported By</th>
                  <th>Timestamp</th>
                  <th>Error Log</th>
                </tr>
              </thead>
              <tbody>
                {history.map(h => (
                  <tr key={h.id}>
                    <td className="font-mono font-bold">#{h.id}</td>
                    <td>{h.file_name}</td>
                    <td><span className="badge badge-info">{h.file_type}</span></td>
                    <td className="font-mono text-right">{h.total_rows}</td>
                    <td className="font-mono text-right text-green-700 font-bold">{h.valid_rows}</td>
                    <td className="font-mono text-right text-red-700 font-bold">{h.rejected_rows}</td>
                    <td className="font-mono text-right text-amber-700">{h.duplicate_rows}</td>
                    <td>{h.imported_by_username}</td>
                    <td>{new Date(h.created_at).toLocaleString()}</td>
                    <td>
                      {h.rejected_rows > 0 ? (
                        <div style={{ display: 'flex', gap: '0.25rem' }}>
                          <button 
                            className="btn-action btn-reject"
                            onClick={() => viewHistoryErrors(h.id)}
                            title="View rejected rows"
                          >
                            <FileText size={12} /> View ({h.rejected_rows})
                          </button>
                          <a 
                            href={getImportErrorsDownloadUrl(h.id)} 
                            className="btn-action btn-secondary"
                            download
                            title="Download CSV Error Report"
                          >
                            <Download size={12} /> CSV
                          </a>
                        </div>
                      ) : (
                        <span className="text-muted text-xs">Clean (0 errors)</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* MODAL FOR VIEWING HISTORICAL ERRORS */}
      {selectedHistoryErrors && (
        <div className="modal-overlay">
          <div className="modal-container" style={{ maxWidth: '750px', maxHeight: '80vh', overflowY: 'auto' }}>
            <div className="modal-header">
              <div className="modal-title-wrap">
                <AlertTriangle size={20} className="icon-warning" />
                <h3>Rejected Rows for Import Batch #{viewingHistoryId}</h3>
              </div>
              <button className="btn-close" onClick={() => setSelectedHistoryErrors(null)}><X size={18} /></button>
            </div>
            <div className="modal-body">
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Row</th>
                      <th>Error Type</th>
                      <th>Field</th>
                      <th>Message</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedHistoryErrors.map((e, idx) => (
                      <tr key={idx} className="row-rejected">
                        <td className="font-mono font-bold">#{e.row_number}</td>
                        <td><span className="badge badge-danger">{e.error_type}</span></td>
                        <td>{e.field_name}</td>
                        <td>{e.error_message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            <div className="modal-footer">
              <a 
                href={getImportErrorsDownloadUrl(viewingHistoryId)} 
                className="btn btn-secondary btn-sm"
                download
              >
                <Download size={14} /> Download Full CSV Report
              </a>
              <button className="btn btn-secondary btn-sm" onClick={() => setSelectedHistoryErrors(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

