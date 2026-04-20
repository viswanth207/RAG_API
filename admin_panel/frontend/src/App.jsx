import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  Activity, 
  Shield, 
  Database, 
  Users, 
  Settings, 
  LogOut, 
  ChevronRight,
  RefreshCw,
  Terminal,
  Zap
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// --- INTERNAL COMPONENTS ---

const Card = ({ title, value, subtext, icon: Icon, color }) => (
  <motion.div 
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className="bg-[#0f0f0f] border border-white/5 p-6 rounded-2xl flex items-center gap-6"
  >
    <div className={`p-4 rounded-xl ${color} bg-opacity-10 text-white`}>
      <Icon size={24} />
    </div>
    <div>
      <p className="text-gray-500 text-xs uppercase tracking-tighter font-bold">{title}</p>
      <h3 className="text-3xl font-black mt-1 text-white">{value}</h3>
      <p className="text-[10px] text-gray-600 mt-1 font-mono uppercase tracking-tighter">{subtext}</p>
    </div>
  </motion.div>
);

const SidebarItem = ({ icon: Icon, label, active, onClick }) => (
  <button 
    onClick={onClick}
    className={`w-full flex items-center gap-4 px-6 py-4 transition-all duration-300 relative group
      ${active ? 'text-purple-400' : 'text-gray-500 hover:text-gray-300'}`}
  >
    {active && (
      <motion.div 
        layoutId="activeTab"
        className="absolute left-0 w-1 h-8 bg-purple-500 rounded-r-full"
      />
    )}
    <Icon size={20} className={active ? 'drop-shadow-[0_0_8px_rgba(168,85,247,0.5)]' : ''} />
    <span className="text-sm font-bold tracking-tight">{label}</span>
  </button>
);

// --- MAIN APPLICATION ---

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [stats, setStats] = useState({ total_hits: 0, success_rate: 100, active_clients: 0, avg_latency_ms: 0 });
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('admin_token');
    if (token) setIsLoggedIn(true);
  }, []);

  useEffect(() => {
    if (isLoggedIn && activeTab === 'dashboard') {
      fetchStats();
      const interval = setInterval(fetchStats, 5000);
      return () => clearInterval(interval);
    }
  }, [isLoggedIn, activeTab]);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/admin/dashboard/summary');
      const data = await res.json();
      setStats(data);
      
      const resLogs = await fetch('/api/admin/logs');
      const logData = await resLogs.json();
      setLogs(logData);
    } catch (err) {
      console.error("Link Failure", err);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch('/api/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();
      if (res.ok) {
        localStorage.setItem('admin_token', data.access_token);
        setIsLoggedIn(true);
      } else {
        alert(data.detail);
      }
    } catch (err) {
      alert("Nuclear Link Error: Backend unreachable");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('admin_token');
    setIsLoggedIn(false);
  };

  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-[#050505] flex items-center justify-center p-6 bg-[radial-gradient(circle_at_center,rgba(88,28,135,0.05),transparent)]">
        <motion.div 
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="w-full max-w-md bg-[#0f0f0f] border border-white/5 p-10 rounded-3xl shadow-2xl"
        >
          <div className="flex flex-col items-center mb-8">
            <div className="w-16 h-16 bg-purple-500/10 rounded-2xl flex items-center justify-center text-purple-500 mb-4 border border-purple-500/20">
              <Shield size={32} />
            </div>
            <h1 className="text-2xl font-black tracking-tighter text-white">DATA MIND<span className="text-purple-500">.OS</span></h1>
            <p className="text-gray-500 text-xs mt-1 font-bold uppercase tracking-widest">Admin Control Port</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="text-[10px] text-gray-500 font-bold uppercase tracking-widest block mb-2 px-1">Identity</label>
              <input 
                type="text" 
                className="w-full bg-[#151515] border border-white/5 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50"
                placeholder="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
            <div>
              <label className="text-[10px] text-gray-500 font-bold uppercase tracking-widest block mb-2 px-1">Quantum Key</label>
              <input 
                type="password" 
                className="w-full bg-[#151515] border border-white/5 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-500/50"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <button 
              className="w-full bg-purple-600 hover:bg-purple-500 text-white font-bold py-3 rounded-xl transition-all shadow-[0_0_20px_rgba(147,51,234,0.3)] mt-6"
              disabled={loading}
            >
              {loading ? 'SYNCING...' : 'INITIATE ACCESS'}
            </button>
            <p className="text-center text-[10px] text-gray-600 mt-6 font-mono uppercase tracking-tighter">Satellite Monitoring 3.6.214.223</p>
          </form>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050505] flex text-white font-['Outfit']">
      {/* SIDEBAR */}
      <aside className="w-64 border-r border-white/5 flex flex-col pt-8 bg-[#080808]">
        <div className="px-8 mb-12">
          <h1 className="text-xl font-black tracking-tighter">DATA MIND<span className="text-purple-500">.OS</span></h1>
        </div>

        <nav className="flex-1">
          <SidebarItem icon={BarChart3} label="Neural Hub" active={activeTab === 'dashboard'} onClick={() => setActiveTab('dashboard')} />
          <SidebarItem icon={Users} label="Identity Vault" active={activeTab === 'users'} onClick={() => setActiveTab('users')} />
          <SidebarItem icon={Database} label="System Data" active={activeTab === 'system'} onClick={() => setActiveTab('system')} />
          <SidebarItem icon={Terminal} label="Neural Logs" active={activeTab === 'logs'} onClick={() => setActiveTab('logs')} />
          <SidebarItem icon={Settings} label="Protocols" active={activeTab === 'settings'} onClick={() => setActiveTab('settings')} />
        </nav>

        <div className="p-8">
          <button 
            onClick={handleLogout}
            className="flex items-center gap-3 text-gray-500 hover:text-red-400 font-bold text-sm transition-colors"
          >
            <LogOut size={18} />
            <span>Terminate Link</span>
          </button>
        </div>
      </aside>

      {/* MAIN CONTENT */}
      <main className="flex-1 p-8 overflow-y-auto">
        <header className="flex justify-between items-center mb-12">
          <div>
            <h2 className="text-2xl font-black tracking-tight uppercase">
              {activeTab === 'dashboard' ? 'Control Overview' : activeTab}
            </h2>
            <p className="text-gray-500 text-xs mt-1">Satellite Node 3.6.214.223 is Online</p>
          </div>
          <div className="flex gap-4">
             <div className="bg-[#101010] border border-white/5 px-4 py-2 rounded-xl flex items-center gap-3">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.5)]"></div>
                <span className="text-xs font-bold text-gray-300">CORE.PROCESS_STABLE</span>
             </div>
          </div>
        </header>

        {activeTab === 'dashboard' && (
          <div className="space-y-12">
            {/* STATS */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <Card title="Traffic Volume" value={stats.total_hits.toLocaleString()} subtext="Lifetime hits" icon={Zap} color="bg-yellow-500" />
              <Card title="Pulse Success" value={`${stats.success_rate}%`} subtext="Network health" icon={Activity} color="bg-green-500" />
              <Card title="Active Scanners" value={stats.active_clients} subtext="Client identities" icon={Users} color="bg-purple-500" />
              <Card title="Average Latency" value={`${stats.avg_latency_ms}ms`} subtext="Response speed" icon={RefreshCw} color="bg-blue-500" />
            </div>

            {/* LIVE FEED */}
            <div className="bg-[#0f0f0f] border border-white/5 rounded-3xl p-8 min-h-[500px]">
              <div className="flex justify-between items-center mb-8">
                <h3 className="text-lg font-black tracking-tight flex items-center gap-3">
                  <Terminal size={20} className="text-purple-500" />
                  NEURAL LINK AUDIT
                </h3>
              </div>
              <div className="overflow-x-auto text-xs">
                <table className="w-full text-left">
                  <thead>
                    <tr className="text-gray-500 uppercase tracking-widest font-black border-b border-white/5">
                      <th className="pb-4">Timestamp</th>
                      <th className="pb-4">Endpoint</th>
                      <th className="pb-4">Origin IP</th>
                      <th className="pb-4">Status</th>
                      <th className="pb-4 text-right">Latency</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((log, i) => (
                      <motion.tr 
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.05 }}
                        key={log._id} 
                        className="border-b border-white/5 hover:bg-white/5 transition-colors group"
                      >
                        <td className="py-4 text-gray-600 font-mono italic">{new Date(log.timestamp).toLocaleTimeString()}</td>
                        <td className="py-4 font-bold text-gray-300">
                          <span className="bg-white/5 px-2 py-1 rounded text-[10px] text-purple-400 mr-2 border border-white/10 uppercase tracking-tighter">{log.method}</span>
                          {log.endpoint}
                        </td>
                        <td className="py-4 text-gray-500 font-mono">{log.metadata?.ip}</td>
                        <td className="py-4">
                          <span className={`font-black ${log.status_code < 400 ? 'text-green-500' : 'text-red-500'}`}>
                            {log.status_code}
                          </span>
                        </td>
                        <td className="py-4 text-right font-mono font-bold text-gray-600">{Math.round(log.latency_ms)}ms</td>
                      </motion.tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
