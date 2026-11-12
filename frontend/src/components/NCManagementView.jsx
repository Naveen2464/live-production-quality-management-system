import React, { useState, useEffect } from 'react';
import { 
  AlertOctagon, Search, Filter, Wrench, Eye, CheckCircle2,
  Clock, AlertTriangle, ShieldCheck, ChevronLeft, ChevronRight, X
} from 'lucide-react';
import { getNCRecords } from '../services/api';
import NCDetailModal from './NCDetailModal';
import ReworkModal from './ReworkModal';

export default function NCManagementView({ dropdowns, refreshTrigger, currentRole, currentUserId }) {
  const [ncs, setNcs] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Filters
  const [statusVal, setStatusVal] = useState('');
  const [classification, setClassification] = useState('');
  const [machineId, setMachineId] = useState('');
  const [search, setSearch] = useState('');

  // Modals
  const [selectedNcId, setSelectedNcId] = useState(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [reworkModalOpen, setReworkModalOpen] = useState(false);
  const [ncForRework, setNcForRework] = useState(null);

  const fetchNcs = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getNCRecords({
        page,
        page_size: pageSize,
        status: statusVal,
        classification,
        machine_id: machineId,
        search
      });
      setNcs(data.items);
      setTotalCount(data.total_count);
      setTotalPages(data.total_pages);
    } catch (err) {
      setError(err.message || 'Error fetching NC records');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNcs();
  }, [page, pageSize, statusVal, classification, machineId, refreshTrigger]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchNcs();
  };

  const handleResetFilters = () => {
    setStatusVal('');
    setClassification('');
    setMachineId('');
    setSearch('');
    setPage(1);
  };

  const openDetail = (id) => {
    setSelectedNcId(id);
    setDetailModalOpen(true);
  };

  const openRework = (nc) => {
    setNcForRework(nc);
    setReworkModalOpen(true);
  };

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2 className="card-title">Non-Conformance (NC) & Quality Case Tracking</h2>
          <p className="card-subtitle">
            Manage ISO 9001 non-conformance lifecycle: OPEN → IN PROGRESS → UNDER REVIEW → CLOSED.
          </p>
        </div>
        <div className="table-header-meta">
          <span className="badge badge-info">Active Role: {currentRole}</span>
        </div>
      </div>

      {/* FILTER CONTROLS */}
      <div className="table-filters-bar">
        <form onSubmit={handleSearchSubmit} className="search-form">
          <div className="search-input-wrap">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="Search NC Number, Issue, Machine..."
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
            value={statusVal}
            onChange={(e) => { setStatusVal(e.target.value); setPage(1); }}
          >
            <option value="">All Statuses</option>
            <option value="OPEN">OPEN</option>
            <option value="IN_PROGRESS">IN PROGRESS</option>
            <option value="UNDER_REVIEW">UNDER REVIEW</option>
            <option value="CLOSED">CLOSED</option>
          </select>

          <select 
            className="form-select filter-select"
            value={classification}
            onChange={(e) => { setClassification(e.target.value); setPage(1); }}
          >
            <option value="">All Classifications</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="MAJOR">MAJOR</option>
            <option value="MINOR">MINOR</option>
          </select>

          <select 
            className="form-select filter-select"
            value={machineId}
            onChange={(e) => { setMachineId(e.target.value); setPage(1); }}
          >
            <option value="">All Machines</option>
            {dropdowns?.machines?.map(m => (
              <option key={m.id} value={m.id}>{m.code}</option>
            ))}
          </select>

          {(search || statusVal || classification || machineId) && (
            <button className="btn btn-ghost" onClick={handleResetFilters}>
              <X size={14} /> Clear
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
              <th>NC Number</th>
              <th>Date</th>
              <th>Machine</th>
              <th>Title / Defect</th>
              <th>Category</th>
              <th>Classification</th>
              <th>Status</th>
              <th>Rework Time</th>
              <th>Quality Engineer</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={10} className="text-center py-6">
                  <div className="loading-spinner" /> Loading NC cases...
                </td>
              </tr>
            ) : ncs.length === 0 ? (
              <tr>
                <td colSpan={10} className="text-center py-6 text-muted">
                  No Non-Conformance cases found matching criteria.
                </td>
              </tr>
            ) : (
              ncs.map(nc => (
                <tr key={nc.id} className={nc.status === 'CLOSED' ? 'bg-slate-50' : ''}>
                  <td className="font-mono font-bold text-primary">{nc.nc_number}</td>
                  <td>{nc.created_at ? new Date(nc.created_at).toLocaleDateString() : 'N/A'}</td>
                  <td>
                    <div className="font-semibold">{nc.machine_code || `M-${nc.machine_id}`}</div>
                    <small className="text-muted">{nc.machine_name}</small>
                  </td>
                  <td>
                    <div className="cell-truncate font-medium" title={nc.title}>{nc.title}</div>
                    <small className="cell-truncate text-muted" title={nc.description}>{nc.description}</small>
                  </td>
                  <td>{nc.defect_category}</td>
                  <td>
                    <span className={`status-pill pill-${nc.classification.toLowerCase()}`}>
                      {nc.classification}
                    </span>
                  </td>
                  <td>
                    <span className={`status-badge badge-nc-${nc.status.toLowerCase().replace('_', '-')}`}>
                      {nc.status === 'CLOSED' && <CheckCircle2 size={12} />}
                      {nc.status === 'UNDER_REVIEW' && <ShieldCheck size={12} />}
                      {nc.status === 'IN_PROGRESS' && <Clock size={12} />}
                      {nc.status === 'OPEN' && <AlertTriangle size={12} />}
                      {nc.status.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="font-mono text-right font-semibold">
                    {nc.total_rework_minutes > 0 ? (
                      <span className="text-primary">{nc.total_rework_minutes}m</span>
                    ) : (
                      <span className="text-muted">0m</span>
                    )}
                  </td>
                  <td>
                    <small>{nc.quality_engineer_name || 'QA Lead'}</small>
                  </td>
                  <td>
                    <div className="action-buttons">
                      <button 
                        className="btn-action btn-approve"
                        title="View Case File & RCA"
                        onClick={() => openDetail(nc.id)}
                      >
                        <Eye size={13} /> View / RCA
                      </button>
                      {nc.status !== 'CLOSED' && (
                        <button 
                          className="btn-action btn-secondary"
                          title="Log Rework Minutes"
                          onClick={() => openRework(nc)}
                        >
                          <Wrench size={13} /> Rework
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* PAGINATION */}
      <div className="table-pagination">
        <div className="pagination-info">
          Page <strong>{page}</strong> of <strong>{totalPages || 1}</strong> ({totalCount} total NC tickets)
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

      {/* NC DETAIL & RCA MODAL */}
      <NCDetailModal
        isOpen={detailModalOpen}
        ncId={selectedNcId}
        onClose={() => setDetailModalOpen(false)}
        onUpdated={fetchNcs}
        currentRole={currentRole}
        currentUserId={currentUserId}
      />

      {/* REWORK MODAL */}
      <ReworkModal
        isOpen={reworkModalOpen}
        nc={ncForRework}
        dropdowns={dropdowns}
        onClose={() => setReworkModalOpen(false)}
        onReworkLogged={fetchNcs}
        currentUserId={currentUserId}
      />
    </div>
  );
}

