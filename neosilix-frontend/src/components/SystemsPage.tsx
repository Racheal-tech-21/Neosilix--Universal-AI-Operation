import React, { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { 
  Cpu, HardDrive, MemoryStick, Network, Server, Activity, 
  Database, Plus, Trash2, Scan, Monitor, Container, AlertTriangle, 
  CheckCircle, X, Clock, RefreshCw, Brain, Sparkles, Zap, TerminalSquare,
  Download, Upload
} from "lucide-react";
import { Card } from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { ScrollArea } from "./ui/scroll-area";
import clsx from "clsx";

// Interfaces
interface AdminStats {
  cpu: number;
  memory: number;
  disk: number;
  network_recv: number;
  network_sent: number;
  total_users: number;
  total_websites: number;
  anomalies: number;
  heals_last_24h: number;
  uptime_percentage: number;
  ai_engine_status: string;
  system_uptime: number;
}

interface UserStats {
  cpu: number;
  memory: number;
  disk: number;
  network_recv: number;
  network_sent: number;
  processes: number;
  uptime: number;
  user_websites: number;
  user_anomalies: number;
  uptime_percentage: number;
}

interface MonitoringTarget {
  id: number;
  name: string;
  type: string;
  ip_address: string;
  subnet: string;
  status: string;
  priority: string;
  last_check: string;
  user_id: number;
  services_count: number;
  created_at: string;
}

interface HealthReport {
  target: MonitoringTarget;
  health: {
    status: string;
    issues: string[];
    suggestions: string[];
    last_checked: string;
  };
  services: any[];
  recommendations: any[];
  timestamp: string;
}

interface Alert {
  id: number;
  target_id: number;
  type: string;
  severity: string;
  message: string;
  suggested_fix: string;
  timestamp: string;
  acknowledged: boolean;
}

// TeslaAlert Component - Completely isolated
const TeslaAlert = React.memo(({ alert, onAcknowledge }: { alert: Alert; onAcknowledge: (id: number) => void }) => {
  const [isVisible, setIsVisible] = useState(true);

  const handleAcknowledge = useCallback(() => {
    setIsVisible(false);
    setTimeout(() => onAcknowledge(alert.id), 300);
  }, [alert.id, onAcknowledge]);

  if (!isVisible) return null;

  return (
    <div className={`relative overflow-hidden rounded-lg border-l-4 ${
      alert.severity === 'critical' ? 'border-red-500 bg-red-900/20' :
      alert.severity === 'warning' ? 'border-yellow-500 bg-yellow-900/20' :
      'border-blue-500 bg-blue-900/20'
    } p-4 mb-3 transition-all duration-300 ${
      !isVisible ? 'opacity-0 scale-95 max-h-0 mb-0' : 'opacity-100 scale-100 max-h-32 mb-3'
    }`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3">
          <div className={`p-2 rounded-full ${
            alert.severity === 'critical' ? 'bg-red-500/20 text-red-400' :
            alert.severity === 'warning' ? 'bg-yellow-500/20 text-yellow-400' :
            'bg-blue-500/20 text-blue-400'
          }`}>
            <AlertTriangle className="w-4 h-4" />
          </div>
          <div className="flex-1">
            <div className="flex items-center space-x-2 mb-1">
              <span className={`text-sm font-semibold ${
                alert.severity === 'critical' ? 'text-red-400' :
                alert.severity === 'warning' ? 'text-yellow-400' :
                'text-blue-400'
              }`}>
                {alert.severity.toUpperCase()}
              </span>
              <span className="text-xs text-gray-400 bg-gray-700 px-2 py-1 rounded">
                {alert.type}
              </span>
            </div>
            <p className="text-white font-medium text-sm mb-1">{alert.message}</p>
            <p className="text-gray-300 text-xs">{alert.suggested_fix}</p>
            <div className="flex items-center space-x-3 mt-2 text-xs text-gray-400">
              <div className="flex items-center space-x-1">
                <Clock className="w-3 h-3" />
                <span>{new Date(alert.timestamp).toLocaleTimeString()}</span>
              </div>
            </div>
          </div>
        </div>
        
        {!alert.acknowledged && (
          <button
            onClick={handleAcknowledge}
            className={`p-2 rounded-lg transition-colors ${
              alert.severity === 'critical' ? 'hover:bg-red-500/20 text-red-400' :
              alert.severity === 'warning' ? 'hover:bg-yellow-500/20 text-yellow-400' :
              'hover:bg-blue-500/20 text-blue-400'
            }`}
            title="Acknowledge Alert"
          >
            <CheckCircle className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
});

// Refresh Indicator
const RefreshIndicator = React.memo(({ isRefreshing, lastUpdated }: { isRefreshing: boolean; lastUpdated: string }) => (
  <div className="flex items-center gap-2 text-xs text-gray-400 mb-4">
    <div className={`flex items-center gap-1 ${isRefreshing ? 'text-cyan-400' : ''}`}>
      <RefreshCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin' : ''}`} />
      {isRefreshing ? 'Refreshing...' : 'Auto-refresh active'}
    </div>
    <span>•</span>
    <span>Last updated: {lastUpdated}</span>
  </div>
));

// COMPLETELY SEPARATE COMPONENT FOR TARGETS AND ALERTS
const MonitoringDashboard = React.memo(() => {
  const [targets, setTargets] = useState<MonitoringTarget[]>([]);
  const [healthReports, setHealthReports] = useState<{ [key: number]: HealthReport }>({});
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [scanningTargets, setScanningTargets] = useState<number[]>([]);
  const [showHealthModal, setShowHealthModal] = useState<number | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const [formData, setFormData] = useState({
    name: '',
    type: 'server',
    ip_address: '',
    subnet: '32',
    priority: 'medium'
  });

  // Get token - isolated from main component
  const getAuthData = useCallback(() => {
    const token = localStorage.getItem("token");
    const userData = localStorage.getItem("user");
    return {
      token,
      user: userData ? JSON.parse(userData) : null,
    };
  }, []);

  const { token } = getAuthData();

  // Fetch alerts - completely isolated
  const fetchAlerts = useCallback(async () => {
    if (!token) return;
    
    try {
      const res = await fetch('http://localhost:5000/api/alerts', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        setAlerts(data.alerts || []);
      }
    } catch (err) {
      console.error('Error fetching alerts:', err);
    }
  }, [token]);

  // Fetch targets - completely isolated
  const fetchTargets = useCallback(async () => {
    if (!token) return;
    
    try {
      const res = await fetch('http://localhost:5000/api/targets', {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (res.ok) {
        const data = await res.json();
        setTargets(data.targets || []);
      }
    } catch (err) {
      console.error('Error fetching targets:', err);
    }
  }, [token]);

  // Initial load only - no intervals
  useEffect(() => {
    if (token) {
      fetchTargets();
      fetchAlerts();
    }
  }, [token, fetchTargets, fetchAlerts]);

  // Add Target Form
  const AddTargetForm = React.memo(() => {
    if (!showAddForm) return null;

    const handleInputChange = useCallback((field: string, value: string) => {
      setFormData(prev => ({ ...prev, [field]: value }));
    }, []);

    const addTarget = async (e: React.FormEvent) => {
      e.preventDefault();
      if (!token) return;

      setIsSubmitting(true);
      try {
        const res = await fetch('http://localhost:5000/api/targets', {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(formData),
        });

        const data = await res.json();
        
        if (data.status === 'success') {
          setShowAddForm(false);
          setFormData({ name: '', type: 'server', ip_address: '', subnet: '32', priority: 'medium' });
          fetchTargets();
        } else {
          alert('Error: ' + (data.error || 'Failed to add target'));
        }
      } catch (err) {
        console.error('Error adding target:', err);
        alert('Failed to add target - network error');
      } finally {
        setIsSubmitting(false);
      }
    };

    return (
      <Card className="bg-gradient-to-tr from-gray-800 via-gray-900 to-black border border-cyan-500/20 rounded-2xl p-6 mb-6 ring-1 ring-cyan-400/20">
        <h3 className="text-lg font-semibold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent mb-4 flex items-center gap-2">
          <Plus className="w-5 h-5" />
          Add New Monitoring Target
        </h3>
        <form onSubmit={addTarget} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Name</label>
              <Input
                type="text"
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                className="w-full bg-gray-700/50 border-gray-600 focus:border-cyan-500"
                placeholder="Web Server 1"
                required
                disabled={isSubmitting}
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Type</label>
              <select
                value={formData.type}
                onChange={(e) => handleInputChange('type', e.target.value)}
                className="w-full bg-gray-700/50 border border-gray-600 rounded-lg px-3 py-2 text-white focus:border-cyan-500 focus:outline-none"
                disabled={isSubmitting}
              >
                <option value="server">Physical Server</option>
                <option value="vm">Virtual Machine</option>
                <option value="network">Network Device</option>
                <option value="container">Container</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">IP Address</label>
              <Input
                type="text"
                value={formData.ip_address}
                onChange={(e) => handleInputChange('ip_address', e.target.value)}
                className="w-full bg-gray-700/50 border-gray-600 focus:border-cyan-500"
                placeholder="192.168.1.100"
                required
                disabled={isSubmitting}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Subnet</label>
              <Input
                type="text"
                value={formData.subnet}
                onChange={(e) => handleInputChange('subnet', e.target.value)}
                className="w-full bg-gray-700/50 border-gray-600 focus:border-cyan-500"
                placeholder="24"
                disabled={isSubmitting}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Priority</label>
              <select
                value={formData.priority}
                onChange={(e) => handleInputChange('priority', e.target.value)}
                className="w-full bg-gray-700/50 border border-gray-600 rounded-lg px-3 py-2 text-white focus:border-cyan-500 focus:outline-none"
                disabled={isSubmitting}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
          </div>

          <div className="flex gap-3">
            <Button
              type="submit"
              disabled={isSubmitting}
              className="bg-gradient-to-r from-cyan-600 to-cyan-700 hover:from-cyan-700 hover:to-cyan-800 text-white px-4 py-2 rounded-xl disabled:opacity-50"
            >
              {isSubmitting ? 'Adding...' : 'Add Target'}
            </Button>
            <Button
              type="button"
              onClick={() => {
                setShowAddForm(false);
                setFormData({ name: '', type: 'server', ip_address: '', subnet: '32', priority: 'medium' });
              }}
              disabled={isSubmitting}
              variant="outline"
              className="bg-gray-700/50 border-gray-600 hover:bg-gray-600/50 text-white px-4 py-2 rounded-xl disabled:opacity-50"
            >
              Cancel
            </Button>
          </div>
        </form>
      </Card>
    );
  });

  const fetchHealthReport = useCallback(async (targetId: number) => {
    try {
      const res = await fetch(`http://localhost:5000/api/targets/${targetId}/health`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        setHealthReports(prev => ({ ...prev, [targetId]: data }));
      }
    } catch (err) {
      console.error('Error fetching health report:', err);
    }
  }, [token]);

  const performDeepScan = useCallback(async (targetId: number) => {
    setScanningTargets(prev => [...prev, targetId]);
    try {
      const res = await fetch(`http://localhost:5000/api/targets/${targetId}/deep-scan`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      
      if (res.ok) {
        const result = await res.json();
        alert(`Deep scan completed: ${result.message}\nStatus: ${result.target_status}`);
        await fetchHealthReport(targetId);
        fetchAlerts();
        fetchTargets();
      } else {
        const error = await res.json();
        alert(`Deep scan failed: ${error.error}`);
      }
    } catch (err) {
      console.error('Error performing deep scan:', err);
      alert('Deep scan failed - network error');
    } finally {
      setScanningTargets(prev => prev.filter(id => id !== targetId));
    }
  }, [token, fetchHealthReport, fetchAlerts, fetchTargets]);

  const scanTarget = useCallback(async (id: number) => {
    if (!token) return;
    
    setScanningTargets(prev => [...prev, id]);
    try {
      const res = await fetch(`http://localhost:5000/api/targets/${id}/scan`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (res.ok) {
        const result = await res.json();
        alert(`Quick scan completed: ${result.message}\nNew status: ${result.target_status}`);
        fetchTargets();
      } else {
        const error = await res.json();
        alert(`Quick scan failed: ${error.error}`);
      }
    } catch (err) {
      console.error('Error scanning target:', err);
      alert('Quick scan failed - network error');
    } finally {
      setScanningTargets(prev => prev.filter(targetId => targetId !== id));
    }
  }, [token, fetchTargets]);

  const acknowledgeAlert = useCallback(async (alertId: number) => {
    try {
      const res = await fetch(`http://localhost:5000/api/alerts/${alertId}/acknowledge`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.ok) {
        fetchAlerts();
      }
    } catch (err) {
      console.error('Error acknowledging alert:', err);
    }
  }, [token, fetchAlerts]);

  const deleteTarget = useCallback(async (id: number) => {
    if (!token || !window.confirm('Are you sure you want to delete this target?')) return;

    try {
      const res = await fetch(`http://localhost:5000/api/targets/${id}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (res.ok) {
        fetchTargets();
      }
    } catch (err) {
      console.error('Error deleting target:', err);
    }
  }, [token, fetchTargets]);

  const getTypeIcon = useCallback((type: string) => {
    switch (type) {
      case 'server': return <Server className="w-4 h-4" />;
      case 'vm': return <Monitor className="w-4 h-4" />;
      case 'network': return <Network className="w-4 h-4" />;
      case 'container': return <Container className="w-4 h-4" />;
      default: return <Server className="w-4 h-4" />;
    }
  }, []);

  const getStatusColor = useCallback((status: string) => {
    switch (status) {
      case 'healthy': return 'text-green-400';
      case 'warning': return 'text-yellow-400';
      case 'critical': return 'text-red-400';
      case 'offline': return 'text-gray-400';
      default: return 'text-gray-400';
    }
  }, []);

  const getStatusBgColor = useCallback((status: string) => {
    switch (status) {
      case 'healthy': return 'bg-green-400';
      case 'warning': return 'bg-yellow-400';
      case 'critical': return 'bg-red-400';
      case 'offline': return 'bg-gray-400';
      default: return 'bg-gray-400';
    }
  }, []);

  const getPriorityColor = useCallback((priority: string) => {
    switch (priority) {
      case 'critical': return 'bg-gradient-to-r from-red-500 to-pink-600';
      case 'high': return 'bg-gradient-to-r from-orange-500 to-red-500';
      case 'medium': return 'bg-gradient-to-r from-yellow-500 to-orange-500';
      case 'low': return 'bg-gradient-to-r from-green-500 to-emerald-500';
      default: return 'bg-gradient-to-r from-gray-500 to-gray-600';
    }
  }, []);

  const unacknowledgedAlerts = alerts.filter(a => !a.acknowledged);

  return (
    <div className="mb-12">
      {/* Alerts Section */}
      {unacknowledgedAlerts.length > 0 && (
        <Card className="bg-gradient-to-tr from-gray-900 to-black border border-cyan-500/20 rounded-2xl p-6 mb-6 ring-1 ring-cyan-400/20">
          <h3 className="text-xl font-bold text-amber-400 mb-4 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            Active Alerts ({unacknowledgedAlerts.length})
          </h3>
          <ScrollArea className="h-64">
            <div className="space-y-2">
              {unacknowledgedAlerts.slice(0, 5).map((alert) => (
                <TeslaAlert 
                  key={alert.id} 
                  alert={alert} 
                  onAcknowledge={acknowledgeAlert}
                />
              ))}
            </div>
          </ScrollArea>
        </Card>
      )}

      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent flex items-center gap-2">
          <TerminalSquare className="w-6 h-6" />
          Monitoring Targets
        </h2>
        <Button
          onClick={() => setShowAddForm(!showAddForm)}
          className="flex items-center gap-2 bg-gradient-to-r from-cyan-600 to-cyan-700 hover:from-cyan-700 hover:to-cyan-800 text-white px-4 py-2 rounded-xl"
        >
          <Plus className="w-4 h-4" />
          {showAddForm ? 'Cancel' : 'Add Target'}
        </Button>
      </div>

      <AddTargetForm />

      <Card className="bg-gradient-to-tr from-gray-900 to-black border border-cyan-500/20 rounded-2xl ring-1 ring-cyan-400/20 overflow-hidden">
        {targets.length === 0 ? (
          <div className="p-8 text-center text-gray-400">
            <Server className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>No monitoring targets configured yet.</p>
            <button
              onClick={() => setShowAddForm(true)}
              className="text-cyan-400 hover:text-cyan-300 mt-2"
            >
              Add your first target
            </button>
          </div>
        ) : (
          <ScrollArea className="h-96">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700 bg-gray-800/50">
                  <th className="text-left p-4 text-gray-400">Name</th>
                  <th className="text-left p-4 text-gray-400">Type</th>
                  <th className="text-left p-4 text-gray-400">IP Address</th>
                  <th className="text-left p-4 text-gray-400">Status</th>
                  <th className="text-left p-4 text-gray-400">Priority</th>
                  <th className="text-left p-4 text-gray-400">Last Check</th>
                  <th className="text-left p-4 text-gray-400">Actions</th>
                </tr>
              </thead>
              <tbody>
                {targets.map((target) => (
                  <tr key={target.id} className="border-b border-gray-700/50 hover:bg-gray-800/30 group">
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        {getTypeIcon(target.type)}
                        <span className="font-medium text-white group-hover:text-cyan-100">{target.name}</span>
                      </div>
                    </td>
                    <td className="p-4">
                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-gray-700 text-xs text-gray-300">
                        {target.type}
                      </span>
                    </td>
                    <td className="p-4 font-mono text-sm text-cyan-300">
                      {target.ip_address}/{target.subnet}
                    </td>
                    <td className="p-4">
                      <span className={`inline-flex items-center gap-1 ${getStatusColor(target.status)}`}>
                        <div className={`w-2 h-2 rounded-full ${getStatusBgColor(target.status)}`} />
                        {target.status}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-white text-xs ${getPriorityColor(target.priority)}`}>
                        {target.priority}
                      </span>
                    </td>
                    <td className="p-4 text-sm text-gray-400">
                      {target.last_check ? new Date(target.last_check).toLocaleString() : 'Never'}
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => fetchHealthReport(target.id).then(() => setShowHealthModal(target.id))}
                          className="p-2 text-green-400 hover:text-green-300 hover:bg-green-500/20 rounded-lg"
                          title="Health Report"
                        >
                          <Activity className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => performDeepScan(target.id)}
                          disabled={scanningTargets.includes(target.id)}
                          className="p-2 text-blue-400 hover:text-blue-300 hover:bg-blue-500/20 rounded-lg disabled:opacity-50"
                          title="Deep Scan"
                        >
                          <Scan className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => scanTarget(target.id)}
                          disabled={scanningTargets.includes(target.id)}
                          className="p-2 text-purple-400 hover:text-purple-300 hover:bg-purple-500/20 rounded-lg disabled:opacity-50"
                          title="Quick Scan"
                        >
                          <Activity className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => deleteTarget(target.id)}
                          className="p-2 text-red-400 hover:text-red-300 hover:bg-red-500/20 rounded-lg"
                          title="Delete Target"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </ScrollArea>
        )}
      </Card>

      {/* Health Report Modal */}
      {showHealthModal && healthReports[showHealthModal] && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 backdrop-blur-sm">
          <Card className="bg-gradient-to-tr from-gray-900 to-black border border-cyan-600 p-6 max-w-2xl w-full mx-4 ring-2 ring-cyan-400/30">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
                Health Report: {healthReports[showHealthModal].target.name}
              </h3>
              <button
                onClick={() => setShowHealthModal(null)}
                className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <ScrollArea className="h-96">
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-gray-400">Status</p>
                    <p className={`font-semibold ${
                      healthReports[showHealthModal].health.status === 'healthy' ? 'text-green-400' :
                      healthReports[showHealthModal].health.status === 'warning' ? 'text-yellow-400' :
                      'text-red-400'
                    }`}>
                      {healthReports[showHealthModal].health.status}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-400">Last Checked</p>
                    <p className="text-gray-300">
                      {new Date(healthReports[showHealthModal].health.last_checked).toLocaleString()}
                    </p>
                  </div>
                </div>

                {healthReports[showHealthModal].health.issues.length > 0 && (
                  <div>
                    <p className="text-gray-400 mb-2">Issues Detected</p>
                    <ul className="list-disc list-inside text-red-400 space-y-1">
                      {healthReports[showHealthModal].health.issues.map((issue, index) => (
                        <li key={index}>{issue}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {healthReports[showHealthModal].health.suggestions.length > 0 && (
                  <div>
                    <p className="text-gray-400 mb-2">Suggested Actions</p>
                    <ul className="list-disc list-inside text-yellow-400 space-y-1">
                      {healthReports[showHealthModal].health.suggestions.map((suggestion, index) => (
                        <li key={index}>{suggestion}</li>
                      ))}
                    </ul>
                </div>
              )}
            </div>
          </ScrollArea>
        </Card>
      </div>
    )}
  </div>
  );
});

// MAIN COMPONENT - ONLY HANDLES STATS
export default function SystemsPage() {
  const [adminStats, setAdminStats] = useState<AdminStats | null>(null);
  const [userStats, setUserStats] = useState<UserStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string>("");
  const [isAdmin, setIsAdmin] = useState(false);
  const [user, setUser] = useState<any>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [brainPulse, setBrainPulse] = useState(false);
  
  const statsRefreshIntervalRef = useRef<NodeJS.Timeout>();

  // Brain pulse animation
  useEffect(() => {
    const pulseInterval = setInterval(() => {
      setBrainPulse(true);
      setTimeout(() => setBrainPulse(false), 1000);
    }, 3000);

    return () => clearInterval(pulseInterval);
  }, []);

  // Get token and user from localStorage
  const getAuthData = useCallback(() => {
    const token = localStorage.getItem("token");
    const userData = localStorage.getItem("user");
    return {
      token,
      user: userData ? JSON.parse(userData) : null,
    };
  }, []);

  useEffect(() => {
    const { token, user: userData } = getAuthData();
    if (userData) {
      setUser(userData);
      setIsAdmin(userData.is_admin || false);
    }
  }, [getAuthData]);

  // ONLY FETCH STATS - completely separate from targets/alerts
  const fetchStats = useCallback(async (isBackgroundRefresh = false) => {
    const { token } = getAuthData();
    
    if (!token) {
      if (!isBackgroundRefresh) setError("Not authenticated");
      return;
    }

    if (!isBackgroundRefresh) {
      setIsRefreshing(true);
    }

    try {
      const endpoint = isAdmin ? "http://localhost:5000/api/admin/stats" : "http://localhost:5000/api/user/stats";
      const res = await fetch(endpoint, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });
      
      if (!res.ok) throw new Error(`Failed to fetch stats`);
      
      const data = await res.json();
      
      if (isAdmin) {
        setAdminStats(data);
      } else {
        setUserStats(data);
      }
      
      if (!isBackgroundRefresh) {
        setLastUpdated(new Date().toLocaleTimeString());
        setError(null);
      }
      
    } catch (err) {
      console.error("Stats fetch error:", err);
      if (!isBackgroundRefresh) {
        setError("Failed to fetch system metrics.");
      }
    } finally {
      if (!isBackgroundRefresh) {
        setIsRefreshing(false);
      }
    }
  }, [isAdmin, getAuthData]);

  // Auto-refresh ONLY for stats
  useEffect(() => {
    if (user) {
      fetchStats(false);
      
      statsRefreshIntervalRef.current = setInterval(() => {
        fetchStats(true);
      }, 10000);
      
      return () => {
        if (statsRefreshIntervalRef.current) {
          clearInterval(statsRefreshIntervalRef.current);
        }
      };
    }
  }, [user, fetchStats]);

  const handleManualRefresh = useCallback(async () => {
    await fetchStats(false);
  }, [fetchStats]);

  // Memoized stat cards
  const adminStatCards = useMemo(() => [
    {
      icon: <Cpu className="w-7 h-7 text-yellow-400" />,
      label: "Server CPU",
      value: adminStats?.cpu ?? 0,
      unit: "%",
      color: "text-yellow-400",
      gradient: "from-yellow-400 to-amber-500",
      ai_insight: adminStats?.cpu && adminStats.cpu > 80 ? "🔴 High Load" : adminStats?.cpu && adminStats.cpu > 60 ? "🟡 Moderate" : "🟢 Optimal"
    },
    {
      icon: <MemoryStick className="w-7 h-7 text-pink-500" />,
      label: "Server Memory",
      value: adminStats?.memory ?? 0,
      unit: "%",
      color: "text-pink-500",
      gradient: "from-pink-500 to-rose-500",
      ai_insight: adminStats?.memory && adminStats.memory > 85 ? "🔴 Critical" : adminStats?.memory && adminStats.memory > 70 ? "🟡 Watch" : "🟢 Stable"
    },
    {
      icon: <HardDrive className="w-7 h-7 text-blue-500" />,
      label: "Storage Usage",
      value: adminStats?.disk ?? 0,
      unit: "%",
      color: "text-blue-500",
      gradient: "from-blue-500 to-cyan-500",
      ai_insight: adminStats?.disk && adminStats.disk > 90 ? "🔴 Full" : adminStats?.disk && adminStats.disk > 80 ? "🟡 Limited" : "🟢 Healthy"
    },
    {
      icon: <Download className="w-7 h-7 text-green-400" />,
      label: "Network In",
      value: adminStats?.network_recv ? Math.round(adminStats.network_recv / 1024 / 1024) : 0,
      unit: "MB",
      color: "text-green-400",
      gradient: "from-green-400 to-emerald-500",
      ai_insight: "🟢 Optimal Flow"
    },
    {
      icon: <Upload className="w-7 h-7 text-green-600" />,
      label: "Network Out",
      value: adminStats?.network_sent ? Math.round(adminStats.network_sent / 1024 / 1024) : 0,
      unit: "MB",
      color: "text-green-600",
      gradient: "from-green-600 to-emerald-600",
      ai_insight: "🟢 Balanced"
    },
  ], [adminStats]);

  const userStatCards = useMemo(() => [
    {
      icon: <Cpu className="w-7 h-7 text-yellow-400" />,
      label: "CPU Usage",
      value: userStats?.cpu ?? 0,
      unit: "%",
      color: "text-yellow-400",
      gradient: "from-yellow-400 to-amber-500",
      ai_insight: userStats?.cpu && userStats.cpu > 80 ? "🔴 High Load" : userStats?.cpu && userStats.cpu > 60 ? "🟡 Moderate" : "🟢 Optimal"
    },
    {
      icon: <MemoryStick className="w-7 h-7 text-pink-500" />,
      label: "Memory Usage",
      value: userStats?.memory ?? 0,
      unit: "%",
      color: "text-pink-500",
      gradient: "from-pink-500 to-rose-500",
      ai_insight: userStats?.memory && userStats.memory > 85 ? "🔴 Critical" : userStats?.memory && userStats.memory > 70 ? "🟡 Watch" : "🟢 Stable"
    },
    {
      icon: <HardDrive className="w-7 h-7 text-blue-500" />,
      label: "Disk Usage",
      value: userStats?.disk ?? 0,
      unit: "%",
      color: "text-blue-500",
      gradient: "from-blue-500 to-cyan-500",
      ai_insight: userStats?.disk && userStats.disk > 90 ? "🔴 Full" : userStats?.disk && userStats.disk > 80 ? "🟡 Limited" : "🟢 Healthy"
    },
    {
      icon: <Server className="w-7 h-7 text-purple-500" />,
      label: "Processes",
      value: userStats?.processes ?? 0,
      unit: "",
      color: "text-purple-500",
      gradient: "from-purple-500 to-violet-500",
      ai_insight: "🟢 Normal"
    },
    {
      icon: <Activity className="w-7 h-7 text-green-500" />,
      label: "Uptime %",
      value: userStats?.uptime_percentage ?? 0,
      unit: "%",
      color: "text-green-500",
      gradient: "from-green-500 to-emerald-500",
      ai_insight: "🟢 Excellent"
    },
  ], [userStats]);

  const currentStatCards = isAdmin ? adminStatCards : userStatCards;
  const currentStats = isAdmin ? adminStats : userStats;

  const formatUptime = useCallback((seconds: number) => {
    const days = Math.floor(seconds / (24 * 3600));
    const hours = Math.floor((seconds % (24 * 3600)) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) return `${days}d ${hours}h ${minutes}m`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  }, []);

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col p-6 md:p-10 overflow-hidden">
      {/* Header */}
      <div className="flex flex-col items-start gap-3 mb-8">
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className={clsx(
                "absolute inset-0 bg-cyan-400 rounded-full blur-xl transition-all duration-1000",
                brainPulse ? "opacity-50 scale-110" : "opacity-30 scale-100"
              )} />
              <Server className={clsx(
                "h-20 w-20 text-cyan-400 drop-shadow-[0_0_25px_cyan] transition-all duration-1000",
                brainPulse ? "scale-110 text-cyan-300" : "scale-100"
              )} />
            </div>
            <div>
              <h1 className="text-4xl md:text-5xl font-extrabold bg-gradient-to-r from-cyan-400 via-purple-500 to-pink-500 bg-clip-text text-transparent drop-shadow-glow select-none animate-gradient">
                {isAdmin ? "Infrastructure Intelligence" : "System Intelligence"}
              </h1>
              <p className="text-cyan-300 italic mt-1 text-sm md:text-base flex items-center gap-2">
                <Sparkles className="w-4 h-4" />
                {isAdmin 
                  ? "Advanced Infrastructure Monitoring & Analytics"
                  : "Your Personal System Performance Dashboard"
                }
                <Sparkles className="w-4 h-4" />
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <RefreshIndicator isRefreshing={isRefreshing} lastUpdated={lastUpdated} />
            <Button
              onClick={handleManualRefresh}
              disabled={isRefreshing}
              className="flex items-center gap-2 bg-gradient-to-r from-cyan-600 to-cyan-700 hover:from-cyan-700 hover:to-cyan-800 text-white px-4 py-2 rounded-xl disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
              Refresh Stats
            </Button>
          </div>
        </div>

        {user && (
          <div className="flex items-center gap-4">
            <p className="text-cyan-300 italic text-sm md:text-base">
              System Access: <span className="font-semibold text-white">{user.name}</span>
              {isAdmin && (
                <span className="ml-2 bg-gradient-to-r from-purple-600 to-pink-600 px-3 py-1 rounded-full text-xs font-bold">
                  ADMIN SYSTEM ACCESS
                </span>
              )}
            </p>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-gradient-to-r from-red-800 to-pink-800 text-red-100 font-semibold mb-8 p-4 rounded-xl shadow-inner select-none border border-red-500/30">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4" />
            {error}
          </div>
        </div>
      )}

      {/* Stats Cards - Auto-refreshes */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
        {currentStatCards.map(({ icon, label, value, unit, color, gradient, ai_insight }, idx) => (
          <Card
            key={idx}
            className="bg-gradient-to-tr from-gray-800 via-gray-900 to-black border border-cyan-500/20 rounded-2xl shadow-2xl hover:shadow-cyan-500/10 transition-all duration-300 cursor-default select-none p-5 flex flex-col space-y-3 ring-1 ring-cyan-400/20 hover:ring-cyan-400/40 group"
          >
            <div className="flex items-center justify-between">
              <div className={clsx("p-2 rounded-xl bg-gray-800/50", color)}>
                {icon}
              </div>
              <div className="text-xs font-mono px-2 py-1 bg-gray-800 rounded-lg text-cyan-300">
                {ai_insight}
              </div>
            </div>
            <div className="flex-1">
              <p className="text-sm text-gray-400 tracking-wide">{label}</p>
              <h2 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
                {typeof value === 'number' ? value.toFixed(2) : value} {unit}
              </h2>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-1">
              <div 
                className={clsx(
                  "h-1 rounded-full transition-all duration-500",
                  `bg-gradient-to-r ${gradient}`
                )}
                style={{ width: `${Math.min(100, typeof value === 'number' ? value : 0)}%` }}
              />
            </div>
          </Card>
        ))}
      </div>

      {/* Additional Info Section - Also auto-refreshes */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 mb-12">
        {/* System Status */}
        <Card className="bg-gradient-to-tr from-gray-900 to-black border border-cyan-500/20 rounded-2xl p-6 ring-1 ring-cyan-400/20">
          <h3 className="text-lg font-semibold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5" />
            {isAdmin ? "Infrastructure Status" : "System Status"}
          </h3>
          <div className="space-y-4 text-sm">
            <div className="flex justify-between items-center p-3 bg-gray-800/50 rounded-lg">
              <span className="text-gray-400">Status</span>
              <span className="text-green-400 font-semibold bg-green-500/20 px-3 py-1 rounded-full">
                {isAdmin ? (adminStats?.ai_engine_status || "Operational") : "Operational"}
              </span>
            </div>
            <div className="flex justify-between items-center p-3 bg-gray-800/50 rounded-lg">
              <span className="text-gray-400">Last Updated</span>
              <span className="text-cyan-300">{lastUpdated || "Loading..."}</span>
            </div>
            {isAdmin ? (
              <>
                <div className="flex justify-between items-center p-3 bg-gray-800/50 rounded-lg">
                  <span className="text-gray-400">Total Users</span>
                  <span className="text-purple-300">{adminStats?.total_users || 0}</span>
                </div>
                <div className="flex justify-between items-center p-3 bg-gray-800/50 rounded-lg">
                  <span className="text-gray-400">Active Websites</span>
                  <span className="text-blue-300">{adminStats?.total_websites || 0}</span>
                </div>
                {adminStats?.system_uptime && (
                  <div className="flex justify-between items-center p-3 bg-gray-800/50 rounded-lg">
                    <span className="text-gray-400">System Uptime</span>
                    <span className="text-green-300">
                      {formatUptime(adminStats.system_uptime)}
                    </span>
                  </div>
                )}
              </>
            ) : (
              userStats?.uptime && (
                <div className="flex justify-between items-center p-3 bg-gray-800/50 rounded-lg">
                  <span className="text-gray-400">System Uptime</span>
                  <span className="text-green-300">
                      {formatUptime(userStats.uptime)}
                    </span>
                </div>
              )
            )}
          </div>
        </Card>

        {/* Analytics & Health */}
        <Card className="bg-gradient-to-tr from-gray-900 to-black border border-cyan-500/20 rounded-2xl p-6 ring-1 ring-cyan-400/20">
          <h3 className="text-lg font-semibold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent mb-4 flex items-center gap-2">
            <Database className="w-5 h-5" />
            {isAdmin ? "Infrastructure Analytics" : "System Health"}
          </h3>
          <div className="space-y-4 text-sm">
            <div className="flex items-center gap-4 p-3 bg-gray-800/50 rounded-lg">
              {isAdmin ? (
                <>
                  <Database className="w-8 h-8 text-purple-400" />
                  <div className="flex-1">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Anomalies Detected</span>
                      <span className="text-red-400 font-semibold">{adminStats?.anomalies || 0}</span>
                    </div>
                    <div className="flex justify-between mt-2">
                      <span className="text-gray-400">Auto-heals (24h)</span>
                      <span className="text-green-400 font-semibold">{adminStats?.heals_last_24h || 0}</span>
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <Activity className="w-8 h-8 text-blue-400" />
                  <div className="flex-1">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Your Websites</span>
                      <span className="text-cyan-300">{userStats?.user_websites || 0}</span>
                    </div>
                    <div className="flex justify-between mt-2">
                      <span className="text-gray-400">Active Issues</span>
                      <span className="text-red-400 font-semibold">{userStats?.user_anomalies || 0}</span>
                    </div>
                  </div>
                </>
              )}
            </div>
            <div className="pt-2">
              <div className="flex justify-between text-sm text-gray-400 mb-2">
                <span>Uptime Performance</span>
                <span>{isAdmin ? adminStats?.uptime_percentage : userStats?.uptime_percentage}%</span>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-3">
                <div 
                  className="bg-gradient-to-r from-cyan-400 to-pink-500 h-3 rounded-full transition-all duration-1000 ease-out shadow-lg shadow-cyan-500/25"
                  style={{ width: `${isAdmin ? adminStats?.uptime_percentage : userStats?.uptime_percentage || 0}%` }}
                ></div>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* COMPLETELY SEPARATE MONITORING DASHBOARD - NO AUTO-REFRESH */}
      <MonitoringDashboard />

      {/* Footer */}
      <footer className="text-center py-4 text-xs text-cyan-500 border-t border-cyan-800/30 select-none mt-auto">
        <div className="flex items-center justify-center gap-2">
          <Brain className="w-3 h-3" />
          © 2025 Neosilix AI by Racheal Inc. Advanced Infrastructure Intelligence
          <Brain className="w-3 h-3" />
        </div>
      </footer>
    </div>
  );
}
