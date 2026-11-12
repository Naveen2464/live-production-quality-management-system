const API_BASE = '/api/v1';

// -------------------------------------------------------------
// MASTER DATA
// -------------------------------------------------------------
export async function getMasterDropdowns() {
  const res = await fetch(`${API_BASE}/master/dropdowns`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch master dropdowns');
  }
  return res.json();
}

// -------------------------------------------------------------
// PRODUCTION APIS
// -------------------------------------------------------------
export async function getProductionRecords(params = {}) {
  const query = new URLSearchParams();
  Object.keys(params).forEach(k => {
    if (params[k] !== undefined && params[k] !== null && params[k] !== '') {
      query.append(k, params[k]);
    }
  });
  const res = await fetch(`${API_BASE}/production/?${query.toString()}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch production records');
  }
  return res.json();
}

export async function getProductionRecordById(id) {
  const res = await fetch(`${API_BASE}/production/${id}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch production record #${id}`);
  }
  return res.json();
}

export async function createProductionRecord(payload) {
  const res = await fetch(`${API_BASE}/production/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create production record');
  }
  return res.json();
}

export async function updateProductionRecord(id, payload) {
  const res = await fetch(`${API_BASE}/production/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to update production record #${id}`);
  }
  return res.json();
}

export async function approveProductionRecord(id, action, supervisorId, rejectionReason = null) {
  const res = await fetch(`${API_BASE}/production/${id}/approve`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      action,
      supervisor_id: supervisorId,
      rejection_reason: rejectionReason
    })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to ${action.toLowerCase()} production record #${id}`);
  }
  return res.json();
}

// -------------------------------------------------------------
// QUALITY RECORDS APIS
// -------------------------------------------------------------
export async function createQualityRecord(payload) {
  const res = await fetch(`${API_BASE}/quality/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to log quality defect');
  }
  return res.json();
}

export async function getQualityRecords(params = {}) {
  const query = new URLSearchParams();
  Object.keys(params).forEach(k => {
    if (params[k] !== undefined && params[k] !== null && params[k] !== '') {
      query.append(k, params[k]);
    }
  });
  const res = await fetch(`${API_BASE}/quality/?${query.toString()}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch quality records');
  }
  return res.json();
}

// -------------------------------------------------------------
// NON-CONFORMANCE (NC) APIS
// -------------------------------------------------------------
export async function createNCRecord(payload) {
  const res = await fetch(`${API_BASE}/quality/nc`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create NC ticket');
  }
  return res.json();
}

export async function getNCRecords(params = {}) {
  const query = new URLSearchParams();
  Object.keys(params).forEach(k => {
    if (params[k] !== undefined && params[k] !== null && params[k] !== '') {
      query.append(k, params[k]);
    }
  });
  const res = await fetch(`${API_BASE}/quality/nc?${query.toString()}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch NC records');
  }
  return res.json();
}

export async function getNCRecordById(id) {
  const res = await fetch(`${API_BASE}/quality/nc/${id}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch NC #${id}`);
  }
  return res.json();
}

export async function updateNCRecord(id, payload) {
  const res = await fetch(`${API_BASE}/quality/nc/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to update NC #${id}`);
  }
  return res.json();
}

export async function transitionNCStatus(id, targetStatus, userId, userRole, closureNotes = null, rootCause = null, correctiveAction = null) {
  const res = await fetch(`${API_BASE}/quality/nc/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      target_status: targetStatus,
      user_id: userId,
      user_role: userRole,
      closure_notes: closureNotes,
      root_cause: rootCause,
      corrective_action: correctiveAction
    })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to transition NC to ${targetStatus}`);
  }
  return res.json();
}

// -------------------------------------------------------------
// REWORK APIS
// -------------------------------------------------------------
export async function createReworkRecord(payload) {
  const res = await fetch(`${API_BASE}/quality/rework`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create rework record');
  }
  return res.json();
}

export async function updateReworkStatus(reworkId, status, verifiedById = null, notes = null) {
  const res = await fetch(`${API_BASE}/quality/rework/${reworkId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      rework_status: status,
      verified_by_id: verifiedById,
      notes: notes
    })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to update rework #${reworkId}`);
  }
  return res.json();
}
