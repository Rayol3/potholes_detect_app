import { useState } from 'react';
import { LayoutDashboard, Tag, Settings } from 'lucide-react';
import Dashboard from './Dashboard';
import Labeler from './Labeler';
import './index.css';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="brand">
          <LayoutDashboard className="brand-icon" size={28} />
          <span>Antigravity</span>
        </div>
        
        <nav>
          <div 
            className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            <LayoutDashboard size={20} />
            <span>Dashboard</span>
          </div>
          <div 
            className={`nav-item ${activeTab === 'labeler' ? 'active' : ''}`}
            onClick={() => setActiveTab('labeler')}
          >
            <Tag size={20} />
            <span>FastLabel</span>
          </div>
          <div 
            className={`nav-item ${activeTab === 'settings' ? 'active' : ''}`}
            onClick={() => setActiveTab('settings')}
          >
            <Settings size={20} />
            <span>Settings</span>
          </div>
        </nav>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        <div className="page-header">
          <h1>
            {activeTab === 'dashboard' && 'System Dashboard'}
            {activeTab === 'labeler' && 'FastLabel Annotation'}
            {activeTab === 'settings' && 'Settings'}
          </h1>
        </div>

        {activeTab === 'dashboard' && <Dashboard />}
        {activeTab === 'labeler' && <Labeler />}
        {activeTab === 'settings' && (
          <div className="glass-panel">
            <h2>System Settings</h2>
            <p style={{ color: 'var(--text-muted)', marginTop: '12px' }}>
              Settings configuration will be implemented here.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
