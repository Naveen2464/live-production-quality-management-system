import React, { useState, useEffect } from 'react';
import { 
  Search, Filter, Check, X, ChevronLeft, ChevronRight,
  AlertCircle, ShieldCheck, Clock, CheckCircle2, XCircle
} from 'lucide-react';
import { getProductionRecords, approveProductionRecord } from '../services/api';
import RejectReasonModal from './RejectReasonModal';

export default function ProductionTable({ dropdowns, refreshTrigger, currentRole = 'Supervisor', currentSupervisorId = 2 }) {
  const [records, setRecords] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Filters
  const [search, setSearch] = useState('');
  const [machineId, setMachineId] = useState('');
  const [shiftId, setShiftId] = useState('');
  const [approvalStatus, setApprovalStatus] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // Rejection modal
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [selectedRecordId, setSelectedRecordId] = useState(null);

  const fetchRecords = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getProductionRecords({
        page,
        page_size: pageSize,
        search,
        machine_id: machineId,
        shift_id: shiftId,
        approval_status: approvalStatus,
        start_date: startDate,
        end_date: endDate
      });
      setRecords(data.items);
      setTotalCount(data.total_count);
      setTotalPages(data.total_pages);
    } catch (err) {
      setError(err.message || 'Failed to fetch production records');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecords();
  }, [page, pageSize, machineId, shiftId, approvalStatus, startDate, endDate, refreshTrigger]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchRecords();
  };

  const handleResetFilters = () => {
    setSearch('');
    setMachineId('');
    setShiftId('');
    setApprovalStatus('');
    setStartDate('');
    setEndDate('');
    setPage(1);
  };

  const handleApprove = async (recordId) => {
    try {
      await approveProductionRecord(recordId, 'APPROVE', currentSupervisorId);
      fetchRecords();
    } catch (err) {
      alert(`Approval error: ${err.message}`);
    }
  };

  const openRejectModal = (recordId) => {
    setSelectedRecordId(recordId);
    setRejectModalOpen(true);
  };

  const handleConfirmReject = async (reason) => {
    try {
      await approveProductionRecord(selectedRecordId, 'REJECT', currentSupervisorId, reason);
      setRejectModalOpen(false);
      setSelectedRecordId(null);
      fetchRecords();
    } catch (err) {
      alert(`Rejection error: ${err.message}`);
    }
  };

  return (
    <div className="card production-table-card">
      <div className="card-header">
        <div>
          <h2 className="card-title">Production & Testing Registry</h2>
          <p className="card-subtitle">
            Showing {records.length} of {totalCount} total verified test runs across production lines.
          </p>
        </div>
        <div className="table-header-meta">
          <span className="badge badge-info">Role: {currentRole}</span>
        </div>
      </div>

      {/* FILTER CONTROLS */}
      <div className="table-filters-bar">
        <form onSubmit={handleSearchSubmit} className="search-form">
          <div className="search-input-wrap">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="Search Machine code, Customer..."
              className="form-input search-input"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <button type="submit" className="btn btn-secondary">Search</button>
        </form>

        <div className="filter-dropdowns">
          <select 
            className="form-select filter-select"
            value={machineId}
            onChange={(e) => { setMachineId(e.target.value); setPage(1); }}
          >
            <option value="">All Machines</option>
            {dropdowns.machines.map(m => (
              <option key={m.id} value={m.id}>{m.code}</option>
            ))}
          </select>

          <select 
            className="form-select filter-select"
            value={shiftId}
            onChange={(e) => { setShiftId(e.target.value); setPage(1); }}
          >
            <option value="">All Shifts</option>
            {dropdowns.shifts.map(s => (
              <option key={s.id} value={s.id}>{s.code}</option>
            ))}
          </select>

          <select 
            className="form-select filter-select"
            value={approvalStatus}
            onChange={(e) => { setApprovalStatus(e.target.value); setPage(1); }}
          >
            <option value="">All Statuses</option>
            <option value="PENDING">PENDING</option>
            <option value="APPROVED">APPROVED</option>
            <option value="REJECTED">REJECTED</option>
          </select>

          {(search || machineId || shiftId || approvalStatus || startDate || endDate) && (
            <button className="btn btn-ghost" onClick={handleResetFilters}>
              <X size={14} /> Clear Filters
            </button>
          )}
        </div>
      </div>

      {error && <div className="alert-banner alert-error">{error}</div>}

      {/* DATA TABLE */}
      <div className="table-responsive">
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Date</th>
              <th>Machine</th>
              <th>Frame</th>
              <th>Shift</th>
              <th>Customer</th>
              <th>Total (min)</th>
              <th>Cycle (hrs)</th>
              <th>Result</th>
              <th>NC</th>
              <th>Status</th>
              <th>Workflow Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={12} className="text-center py-6">
                  <div className="loading-spinner" /> Loading production records...
                </td>
              </tr>
            ) : records.length === 0 ? (
              <tr>
                <td colSpan={12} className="text-center py-6 text-muted">
                  No production records found matching criteria.
                </td>
              </tr>
            ) : (
              records.map(r => (
                <tr key={r.id} className={r.approval_status === 'REJECTED' ? 'row-rejected' : ''}>
                  <td className="font-mono font-semibold">#{r.id}</td>
                  <td>{r.date}</td>
                  <td>
                    <div className="font-semibold">{r.machine?.machine_code || `M-${r.machine_id}`}</div>
                    <small className="text-muted">{r.machine?.name}</small>
                  </td>
                  <td>{r.frame?.frame_code || r.frame_id}</td>
                  <td>
                    <span className="shift-tag">{r.shift?.shift_name || `Shift ${r.shift_id}`}</span>
                  </td>
                  <td>
                    <div className="cell-truncate" title={r.customer?.customer_name}>
                      {r.customer?.customer_name || `Cust-${r.customer_id}`}
                    </div>
                  </td>
                  <td className="font-mono text-right">{r.total_testing_time}m</td>
                  <td className="font-mono text-right font-semibold">{r.cycle_time_hours}h</td>
                  <td>
                    <span className={`status-pill pill-${r.test_result.toLowerCase()}`}>
                      {r.test_result}
                    </span>
                  </td>
                  <td className="text-center">
                    {r.nc_raised ? (
                      <span className="badge badge-danger">YES</span>
                    ) : (
                      <span className="text-muted">No</span>
                    )}
                  </td>
                  <td>
                    <span className={`status-badge badge-${r.approval_status.toLowerCase()}`}>
                      {r.approval_status === 'APPROVED' && <CheckCircle2 size={12} />}
                      {r.approval_status === 'PENDING' && <Clock size={12} />}
                      {r.approval_status === 'REJECTED' && <XCircle size={12} />}
                      {r.approval_status}
                    </span>
                    {r.rejection_reason && (
                      <div className="rejection-hint" title={r.rejection_reason}>
                        Reason: {r.rejection_reason.substring(0, 24)}...
                      </div>
                    )}
                  </td>
                  <td>
                    {(currentRole === 'Supervisor' || currentRole === 'Administrator') ? (
                      <div className="action-buttons">
                        {r.approval_status !== 'APPROVED' && (
                          <button 
                            className="btn-action btn-approve"
                            title="Approve Record"
                            onClick={() => handleApprove(r.id)}
                          >
                            <Check size={14} /> Approve
                          </button>
                        )}
                        {r.approval_status !== 'REJECTED' && (
                          <button 
                            className="btn-action btn-reject"
                            title="Reject Record"
                            onClick={() => openRejectModal(r.id)}
                          >
                            <X size={14} /> Reject
                          </button>
                        )}
                      </div>
                    ) : (
                      <span className="text-muted text-xs">Read Only</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* PAGINATION CONTROLS */}
      <div className="table-pagination">
        <div className="pagination-info">
          Page <strong>{page}</strong> of <strong>{totalPages || 1}</strong> ({totalCount} total entries)
        </div>
        <div className="pagination-controls">
          <select 
            className="form-select select-sm"
            value={pageSize}
            onChange={(e) => { setPageSize(parseInt(e.target.value)); setPage(1); }}
          >
            <option value={5}>5 / page</option>
            <option value={10}>10 / page</option>
            <option value={25}>25 / page</option>
            <option value={50}>50 / page</option>
          </select>
          <button 
            className="btn btn-secondary btn-sm"
            disabled={page <= 1}
            onClick={() => setPage(p => Math.max(1, p - 1))}
          >
            <ChevronLeft size={16} /> Prev
          </button>
          <button 
            className="btn btn-secondary btn-sm"
            disabled={page >= totalPages}
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
          >
            Next <ChevronRight size={16} />
          </button>
        </div>
      </div>

      {/* REJECTION REASON MODAL */}
      <RejectReasonModal
        isOpen={rejectModalOpen}
        recordId={selectedRecordId}
        onClose={() => setRejectModalOpen(false)}
        onConfirm={handleConfirmReject}
      />
    </div>
  );
}

