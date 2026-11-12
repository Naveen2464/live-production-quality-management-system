import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import ProductionEntryForm from './components/ProductionEntryForm';
import ProductionTable from './components/ProductionTable';
import NCManagementView from './components/NCManagementView';
import QualityDefectForm from './components/QualityDefectForm';
import { getMasterDropdowns } from './services/api';
import { PlusCircle, ListFilter, AlertOctagon, ShieldAlert, Database } from 'lucide-react';
import './App.css';

export default function App() {
  const [currentRole, setCurrentRole] = useState('Quality Engineer');
  const [activeTab, setActiveTab] = useState('nc'); // 'entry' | 'table' | 'nc' | 'defect'
  const [dropdowns, setDropdowns] = useState(null);
  const [loadingDropdowns, setLoadingDropdowns] = useState(true);
  const [dropdownError, setDropdownError] = useState('');
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [wsConnected, setWsConnected] = useState(false);

  // Map roles to user IDs
  const roleUserMap = {
    'Operator': 3,
    'Supervisor': 2,
    'Quality Engineer': 4,
    'Management': 5,
    'Administrator': 1
  };
  const currentUserId = roleUserMap[currentRole] || 4;

  // Load master dropdowns on mount
  useEffect(() => {
    async function loadData() {
      try {
        const data = await getMasterDropdowns();
        setDropdowns(data);
      } catch (err) {
        setDropdownError(err.message || 'Error connecting to backend API');
      } finally {
        setLoadingDropdowns(false);
      }
    }
    loadData();
  }, []);

  // WebSocket Live Updates Connection
  useEffect(() => {
    let ws;
    let reconnectTimer;

    function connectWs() {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/dashboard`;
      
      try {
        ws = new WebSocket(wsUrl);
        ws.onopen = () => {
          setWsConnected(true);
        };
        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type && (msg.type.startsWith('PRODUCTION_') || msg.type.startsWith('NC_') || msg.type.startsWith('QUALITY_') || msg.type.startsWith('REWORK_'))) {
              // Trigger table refresh
              setRefreshTrigger(prev => prev + 1);
            }
          } catch (e) {
            // Heartbeat or ping
          }
        };
        ws.onclose = () => {
          setWsConnected(false);
          reconnectTimer = setTimeout(connectWs, 4000);
        };
        ws.onerror = () => {
          ws.close();
        };
      } catch (err) {
        reconnectTimer = setTimeout(connectWs, 4000);
      }
    }

    connectWs();
    return () => {
      if (ws) ws.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, []);

  const handleRecordCreated = () => {
    setRefreshTrigger(prev => prev + 1);
    setActiveTab('table');
  };

  const handleDefectLogged = () => {
    setRefreshTrigger(prev => prev + 1);
    setActiveTab('nc');
  };

  return (
    <div className="app-layout">
      <Header 
        currentRole={currentRole} 
        onRoleChange={setCurrentRole} 
        wsConnected={wsConnected} 
      />

      <main className="main-content">
        {/* Navigation Tabs */}
        <div className="tab-navigation">
          <button 
            className={`tab-btn ${activeTab === 'nc' ? 'active' : ''}`}
            onClick={() => setActiveTab('nc')}
          >
            <AlertOctagon size={16} /> NC Workflow & Tracking
          </button>
          <button 
            className={`tab-btn ${activeTab === 'defect' ? 'active' : ''}`}
            onClick={() => setActiveTab('defect')}
          >
            <ShieldAlert size={16} /> Log Defect / Incident
          </button>
          <button 
            className={`tab-btn ${activeTab === 'entry' ? 'active' : ''}`}
            onClick={() => setActiveTab('entry')}
          >
            <PlusCircle size={16} /> Production Entry Form
          </button>
          <button 
            className={`tab-btn ${activeTab === 'table' ? 'active' : ''}`}
            onClick={() => setActiveTab('table')}
          >
            <ListFilter size={16} /> Production Records & Approvals
          </button>
        </div>

        {/* Content Body */}
        {loadingDropdowns ? (
          <div className="center-loader">
            <div className="loading-spinner" />
            <p>Connecting to backend and loading master records...</p>
          </div>
        ) : dropdownError ? (
          <div className="alert-banner alert-error">
            <Database size={20} />
            <div>
              <strong>Database Connection Notice:</strong>
              <div>{dropdownError}</div>
              <small>Ensure FastAPI server is running on http://127.0.0.1:8000</small>
            </div>
          </div>
        ) : (
          <div className="tab-content">
            {activeTab === 'nc' && (
              <NCManagementView
                dropdowns={dropdowns}
                refreshTrigger={refreshTrigger}
                currentRole={currentRole}
                currentUserId={currentUserId}
              />
            )}

            {activeTab === 'defect' && (
              <QualityDefectForm
                dropdowns={dropdowns}
                onDefectLogged={handleDefectLogged}
                currentUserId={currentUserId}
              />
            )}

            {activeTab === 'entry' && (
              <ProductionEntryForm
                dropdowns={dropdowns}
                onRecordCreated={handleRecordCreated}
                currentUserId={currentUserId}
                currentSupervisorId={2}
              />
            )}

            {activeTab === 'table' && (
              <ProductionTable
                dropdowns={dropdowns}
                refreshTrigger={refreshTrigger}
                currentRole={currentRole}
                currentSupervisorId={2}
              />
            )}
          </div>
        )}
      </main>
    </div>
  );
}
