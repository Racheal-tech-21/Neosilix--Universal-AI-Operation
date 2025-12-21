import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  Server, 
  AlertTriangle, 
  Cpu, 
  HardDrive, 
  Network, 
  Users, 
  RefreshCw, 
  ExternalLink,
  Shield,
  Monitor,
  Database,
  Cloud,
  Wifi,
  Globe,
  Mail,
  CheckCircle,
  XCircle,
  AlertCircle,
  BarChart3,
  Zap,
  Eye,
  Key,
  TrendingUp,
  Gauge,
  MemoryStick,
  HardDriveIcon,
  NetworkIcon,
  ShieldCheck,
  Clock,
  Laptop,
  BarChart4,
  LineChart,
  PieChart,
  ActivityIcon
} from 'lucide-react';

interface SystemMetrics {
  cpu: number;
  memory: number;
  disk: number;
  network_recv: number;
  network_sent: number;
  processes: number;
  server_name: string;
  uptime: number;
  uptime_percentage?: number;
  network_usage?: any;
}

interface MonitoringMetrics {
  total_hosts: number;
  online_hosts: number;
  active_alerts: number;
  student_portal_status: string;
  lms_status: string;
  university_website_status: string;
  email_status: string;
  total_network_devices: number;
  online_network_devices: number;
  main_router_status: string;
  core_switch_status: string;
  firewall_status: string;
  running_vms: number;
  total_vms: number;
  security_threats: number;
  network_connections: number;
  users_online: number;
  library_status: string;
  zabbix_connected: boolean;
  timestamp: string;
}

interface Alert {
  id: string;
  severity: string;
  message: string;
  timestamp: string;
  host: string;
  acknowledged: boolean;
}

interface MonitoringMode {
  mode: string;
  scenario: string;
  description: string;
  zabbix_connected: boolean;
}

interface ZabbixHost {
  hostid: string;
  host: string;
  name: string;
  status: string;
  interfaces: Array<{
    ip: string;
    port: string;
    type: string;
  }>;
}

interface ZabbixAlert {
  eventid: string;
  name: string;
  severity: string;
  clock: string;
  acknowledged: string;
}

// Mock data for charts and graphs
const mockChartData = {
  cpuUsage: [45, 52, 48, 65, 42, 55, 60, 58, 52, 49, 55, 62],
  memoryUsage: [65, 68, 72, 70, 68, 65, 72, 75, 70, 68, 72, 74],
  networkIn: [125, 145, 132, 168, 142, 155, 162, 148, 135, 142, 158, 165],
  networkOut: [89, 92, 85, 98, 88, 94, 102, 95, 89, 92, 96, 101],
  services: [
    { name: 'Student Portal', status: 'healthy', uptime: 99.9 },
    { name: 'LMS', status: 'healthy', uptime: 99.8 },
    { name: 'Website', status: 'healthy', uptime: 99.7 },
    { name: 'Email', status: 'healthy', uptime: 99.9 },
    { name: 'Library', status: 'healthy', uptime: 99.6 }
  ]
};

const UnifiedDashboard: React.FC = () => {
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | null>(null);
  const [monitoringMetrics, setMonitoringMetrics] = useState<MonitoringMetrics | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [monitoringMode, setMonitoringMode] = useState<MonitoringMode | null>(null);
  const [zabbixHosts, setZabbixHosts] = useState<ZabbixHost[]>([]);
  const [zabbixAlerts, setZabbixAlerts] = useState<ZabbixAlert[]>([]);
  const [activeTab, setActiveTab] = useState<'overview' | 'alerts' | 'hosts' | 'analytics'>('overview');

  // Fetch data functions
  const fetchSystemMetrics = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:5000/api/system-stats', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      if (!response.ok) throw new Error('Failed to fetch system metrics');
      const data = await response.json();
      setSystemMetrics(data);
    } catch (err) {
      console.error('Error fetching system metrics:', err);
    }
  };

  const fetchMonitoringMetrics = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:5000/api/monitoring/metrics', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      if (!response.ok) throw new Error('Failed to fetch monitoring metrics');
      const data = await response.json();
      setMonitoringMetrics(data);
    } catch (err) {
      console.error('Error fetching monitoring metrics:', err);
    }
  };

  const fetchAlerts = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:5000/api/monitoring/alerts', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      if (!response.ok) throw new Error('Failed to fetch alerts');
      const data = await response.json();
      setAlerts(data);
    } catch (err) {
      console.error('Error fetching alerts:', err);
    }
  };

  const fetchMonitoringMode = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:5000/api/monitoring/mode', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      if (!response.ok) throw new Error('Failed to fetch monitoring mode');
      const data = await response.json();
      setMonitoringMode(data);
    } catch (err) {
      console.error('Error fetching monitoring mode:', err);
    }
  };

  const fetchZabbixHosts = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:5000/api/monitoring/zabbix/hosts', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      if (!response.ok) throw new Error('Failed to fetch Zabbix hosts');
      const data = await response.json();
      setZabbixHosts(data);
    } catch (err) {
      console.error('Error fetching Zabbix hosts:', err);
    }
  };

  const fetchZabbixAlerts = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:5000/api/monitoring/zabbix/alerts', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      if (!response.ok) throw new Error('Failed to fetch Zabbix alerts');
      const data = await response.json();
      setZabbixAlerts(data);
    } catch (err) {
      console.error('Error fetching Zabbix alerts:', err);
    }
  };

  const refreshAllData = () => {
    fetchSystemMetrics();
    fetchMonitoringMetrics();
    fetchAlerts();
    fetchZabbixHosts();
    fetchZabbixAlerts();
  };

  useEffect(() => {
    const loadInitialData = async () => {
      setLoading(true);
      await Promise.all([
        fetchSystemMetrics(),
        fetchMonitoringMetrics(),
        fetchAlerts(),
        fetchMonitoringMode(),
        fetchZabbixHosts(),
        fetchZabbixAlerts()
      ]);
      setLoading(false);
    };

    loadInitialData();

    const interval = setInterval(refreshAllData, 30000);
    return () => clearInterval(interval);
  }, []);

  // Helper functions
  const getStatusIcon = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'healthy':
      case 'up':
      case 'online':
      case 'running':
        return <CheckCircle className="w-5 h-5 text-emerald-500" />;
      case 'down':
      case 'offline':
      case 'error':
        return <XCircle className="w-5 h-5 text-rose-500" />;
      default:
        return <AlertCircle className="w-5 h-5 text-amber-500" />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity?.toLowerCase()) {
      case 'critical':
      case 'disaster':
      case 'high':
        return 'bg-rose-500/10 text-rose-700 border-rose-200';
      case 'warning':
      case 'average':
      case 'medium':
        return 'bg-amber-500/10 text-amber-700 border-amber-200';
      case 'information':
      case 'low':
        return 'bg-cyan-500/10 text-cyan-700 border-cyan-200';
      default:
        return 'bg-slate-500/10 text-slate-700 border-slate-200';
    }
  };

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    return `${days}d ${hours}h`;
  };

  // Simple chart components
  const SimpleBarChart = ({ data, color = 'cyan', height = 40 }: { data: number[], color?: string, height?: number }) => {
    const max = Math.max(...data);
    return (
      <div className="flex items-end justify-between space-x-1" style={{ height: `${height}px` }}>
        {data.map((value, index) => (
          <div
            key={index}
            className={`flex-1 bg-${color}-500/20 rounded-t transition-all duration-500 hover:bg-${color}-500/40`}
            style={{ height: `${(value / max) * 100}%` }}
            title={`${value}%`}
          />
        ))}
      </div>
    );
  };

  const SimpleLineChart = ({ data, color = 'cyan', height = 60 }: { data: number[], color?: string, height?: number }) => {
    const max = Math.max(...data);
    const points = data.map((value, index) => {
      const x = (index / (data.length - 1)) * 100;
      const y = 100 - (value / max) * 100;
      return `${x},${y}`;
    }).join(' ');

    return (
      <div className="relative" style={{ height: `${height}px` }}>
        <svg viewBox="0 0 100 100" className="w-full h-full">
          <polyline
            fill="none"
            stroke={`rgb(6 182 212)`}
            strokeWidth="2"
            strokeLinecap="round"
            points={points}
          />
        </svg>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-cyan-50 via-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="relative">
            <div className="w-16 h-16 border-4 border-cyan-200 border-t-cyan-600 rounded-full animate-spin mx-auto mb-4"></div>
            <Shield className="w-6 h-6 text-cyan-600 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" />
          </div>
          <h2 className="text-xl font-semibold text-slate-700">Loading Dashboard...</h2>
          <p className="text-slate-500 mt-2">Initializing monitoring systems</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-cyan-50 via-blue-50 to-indigo-100 p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="bg-white/80 backdrop-blur-sm p-3 rounded-2xl shadow-lg border border-white/20">
              <Shield className="w-8 h-8 text-cyan-600" />
            </div>
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-600 to-blue-600 bg-clip-text text-transparent">
                NeoSilix Monitoring
              </h1>
              <p className="text-slate-600 mt-1 flex items-center space-x-2">
                <span>{monitoringMode?.mode || 'Real-time'} Monitoring</span>
                <span className="w-1 h-1 bg-slate-400 rounded-full"></span>
                <span>{monitoringMode?.scenario || 'Normal Operations'}</span>
                <span className="w-1 h-1 bg-slate-400 rounded-full"></span>
                <span className={`flex items-center space-x-1 ${monitoringMode?.zabbix_connected ? 'text-emerald-600' : 'text-rose-600'}`}>
                  <div className={`w-2 h-2 rounded-full ${monitoringMode?.zabbix_connected ? 'bg-emerald-500' : 'bg-rose-500'}`}></div>
                  <span>Zabbix: {monitoringMode?.zabbix_connected ? 'Connected' : 'Disconnected'}</span>
                </span>
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            <button
              onClick={refreshAllData}
              className="bg-white/80 backdrop-blur-sm p-3 rounded-2xl shadow-lg border border-white/20 hover:shadow-xl transition-all duration-200 hover:scale-105"
            >
              <RefreshCw className="w-5 h-5 text-slate-600" />
            </button>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-white/20 p-2 mb-6">
        <div className="flex space-x-1">
          {[
            { id: 'overview', label: 'Overview', icon: Activity },
            { id: 'alerts', label: 'Alerts', icon: AlertTriangle },
            { id: 'hosts', label: 'Hosts', icon: Server },
            { id: 'analytics', label: 'Analytics', icon: BarChart3 }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center space-x-2 px-4 py-3 rounded-xl transition-all duration-200 flex-1 justify-center ${
                activeTab === tab.id 
                  ? 'bg-gradient-to-r from-cyan-500 to-blue-500 text-white shadow-lg' 
                  : 'text-slate-600 hover:bg-white/50 hover:text-slate-800'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              <span className="font-medium">{tab.label}</span>
              {tab.id === 'alerts' && alerts.length > 0 && (
                <span className="bg-rose-500 text-white text-xs px-2 py-1 rounded-full">
                  {alerts.length}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="bg-rose-500/10 border border-rose-200 text-rose-700 px-4 py-3 rounded-xl mb-6 backdrop-blur-sm">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-5 h-5" />
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* System Metrics Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* CPU Usage */}
            <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-white/20 p-6 hover:shadow-xl transition-all duration-300">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-cyan-500/10 rounded-lg">
                    <Cpu className="w-5 h-5 text-cyan-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-700">CPU Usage</h3>
                    <p className="text-sm text-slate-500">Processor Load</p>
                  </div>
                </div>
                <span className="text-2xl font-bold text-cyan-600">{systemMetrics?.cpu?.toFixed(1)}%</span>
              </div>
              <SimpleLineChart data={mockChartData.cpuUsage} color="cyan" />
            </div>

            {/* Memory Usage */}
            <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-white/20 p-6 hover:shadow-xl transition-all duration-300">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-blue-500/10 rounded-lg">
                    <MemoryStick className="w-5 h-5 text-blue-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-700">Memory</h3>
                    <p className="text-sm text-slate-500">RAM Usage</p>
                  </div>
                </div>
                <span className="text-2xl font-bold text-blue-600">{systemMetrics?.memory?.toFixed(1)}%</span>
              </div>
              <SimpleLineChart data={mockChartData.memoryUsage} color="blue" />
            </div>

            {/* Disk Usage */}
            <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-white/20 p-6 hover:shadow-xl transition-all duration-300">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-violet-500/10 rounded-lg">
                    <HardDriveIcon className="w-5 h-5 text-violet-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-700">Disk</h3>
                    <p className="text-sm text-slate-500">Storage Usage</p>
                  </div>
                </div>
                <span className="text-2xl font-bold text-violet-600">{systemMetrics?.disk?.toFixed(1)}%</span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-2">
                <div 
                  className="bg-gradient-to-r from-violet-500 to-purple-500 h-2 rounded-full transition-all duration-1000" 
                  style={{ width: `${systemMetrics?.disk || 0}%` }}
                ></div>
              </div>
            </div>

            {/* Uptime */}
            <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-white/20 p-6 hover:shadow-xl transition-all duration-300">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-emerald-500/10 rounded-lg">
                    <Clock className="w-5 h-5 text-emerald-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-700">Uptime</h3>
                    <p className="text-sm text-slate-500">System Stability</p>
                  </div>
                </div>
                <span className="text-2xl font-bold text-emerald-600">{systemMetrics?.uptime_percentage?.toFixed(1)}%</span>
              </div>
              <div className="text-sm text-slate-600">
                {systemMetrics?.uptime ? formatUptime(systemMetrics.uptime) : '0d 0h'}
              </div>
            </div>
          </div>

          {/* Infrastructure Overview */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Services Status */}
            <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-white/20 p-6">
              <h3 className="font-semibold text-slate-700 mb-4 flex items-center space-x-2">
                <Globe className="w-5 h-5 text-cyan-600" />
                <span>University Services</span>
              </h3>
              <div className="space-y-3">
                {[
                  { name: 'Student Portal', status: monitoringMetrics?.student_portal_status },
                  { name: 'Learning Management', status: monitoringMetrics?.lms_status },
                  { name: 'University Website', status: monitoringMetrics?.university_website_status },
                  { name: 'Email System', status: monitoringMetrics?.email_status },
                  { name: 'Library System', status: monitoringMetrics?.library_status }
                ].map((service, index) => (
                  <div key={index} className="flex items-center justify-between p-3 bg-white/50 rounded-xl border border-white/20">
                    <div className="flex items-center space-x-3">
                      {getStatusIcon(service.status || 'unknown')}
                      <span className="font-medium text-slate-700">{service.name}</span>
                    </div>
                    <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                      service.status === 'healthy' 
                        ? 'bg-emerald-500/10 text-emerald-700' 
                        : 'bg-rose-500/10 text-rose-700'
                    }`}>
                      {service.status || 'Unknown'}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Infrastructure Status */}
            <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-white/20 p-6">
              <h3 className="font-semibold text-slate-700 mb-4 flex items-center space-x-2">
                <Server className="w-5 h-5 text-blue-600" />
                <span>Infrastructure Status</span>
              </h3>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gradient-to-br from-cyan-500 to-blue-500 rounded-xl p-4 text-white">
                    <div className="flex items-center justify-between">
                      <Users className="w-8 h-8 opacity-80" />
                      <span className="text-2xl font-bold">{monitoringMetrics?.users_online || 0}</span>
                    </div>
                    <p className="text-sm opacity-90 mt-2">Active Users</p>
                  </div>
                  <div className="bg-gradient-to-br from-violet-500 to-purple-500 rounded-xl p-4 text-white">
                    <div className="flex items-center justify-between">
                      <Laptop className="w-8 h-8 opacity-80" />
                      <span className="text-2xl font-bold">{monitoringMetrics?.running_vms || 0}/{monitoringMetrics?.total_vms || 0}</span>
                    </div>
                    <p className="text-sm opacity-90 mt-2">VMs Running</p>
                  </div>
                </div>
                
                <div className="space-y-3">
                  {[
                    { name: 'Main Router', status: monitoringMetrics?.main_router_status, icon: NetworkIcon },
                    { name: 'Core Switch', status: monitoringMetrics?.core_switch_status, icon: Gauge },
                    { name: 'Firewall', status: monitoringMetrics?.firewall_status, icon: ShieldCheck }
                  ].map((device, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-white/50 rounded-xl border border-white/20">
                      <div className="flex items-center space-x-3">
                        <device.icon className="w-4 h-4 text-slate-600" />
                        <span className="font-medium text-slate-700">{device.name}</span>
                      </div>
                      {getStatusIcon(device.status || 'unknown')}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'alerts' && (
        <div className="space-y-6">
          {/* System Alerts */}
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-white/20 p-6">
            <h3 className="font-semibold text-slate-700 mb-4 flex items-center space-x-2">
              <AlertTriangle className="w-5 h-5 text-rose-600" />
              <span>Active Alerts</span>
              <span className="bg-rose-500 text-white text-sm px-2 py-1 rounded-full">
                {alerts.length}
              </span>
            </h3>
            <div className="space-y-3">
              {alerts.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  <CheckCircle className="w-12 h-12 text-emerald-500 mx-auto mb-3 opacity-60" />
                  <p className="text-lg font-medium">No Active Alerts</p>
                  <p className="text-sm">All systems are operating normally</p>
                </div>
              ) : (
                alerts.map((alert) => (
                  <div
                    key={alert.id}
                    className={`p-4 rounded-xl border-2 backdrop-blur-sm ${getSeverityColor(alert.severity)}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <AlertTriangle className="w-5 h-5" />
                        <div>
                          <p className="font-medium">{alert.message}</p>
                          <p className="text-sm opacity-75">Host: {alert.host}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm opacity-75">
                          {new Date(alert.timestamp).toLocaleString()}
                        </div>
                        <div className="text-xs font-medium mt-1 capitalize">
                          {alert.severity}
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Zabbix Alerts */}
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-white/20 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-slate-700 flex items-center space-x-2">
                <Zap className="w-5 h-5 text-amber-600" />
                <span>Zabbix Monitoring Alerts</span>
                <span className="bg-amber-500 text-white text-sm px-2 py-1 rounded-full">
                  {zabbixAlerts.length}
                </span>
              </h3>
            </div>
            <div className="space-y-3">
              {zabbixAlerts.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  <CheckCircle className="w-12 h-12 text-emerald-500 mx-auto mb-3 opacity-60" />
                  <p>No Zabbix alerts</p>
                </div>
              ) : (
                zabbixAlerts.map((alert) => (
                  <div
                    key={alert.eventid}
                    className={`p-4 rounded-xl border-2 backdrop-blur-sm ${getSeverityColor(alert.severity)}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <AlertTriangle className="w-5 h-5" />
                        <div>
                          <p className="font-medium">{alert.name}</p>
                          <p className="text-sm opacity-75">
                            Acknowledged: {alert.acknowledged === '1' ? 'Yes' : 'No'}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm opacity-75">
                          {new Date(parseInt(alert.clock) * 1000).toLocaleString()}
                        </div>
                        <div className="text-xs font-medium mt-1 capitalize">
                          {alert.severity}
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'hosts' && (
        <div className="space-y-6">
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-white/20 p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-semibold text-slate-700 flex items-center space-x-2">
                <Server className="w-5 h-5 text-cyan-600" />
                <span>Zabbix Monitored Hosts</span>
                <span className="bg-cyan-500 text-white text-sm px-2 py-1 rounded-full">
                  {zabbixHosts.length} Hosts
                </span>
              </h3>
              <div className="text-sm text-slate-600">
                <span className="text-emerald-600 font-medium">
                  {zabbixHosts.filter(h => h.status === '0').length} Online
                </span>
                <span className="mx-2">•</span>
                <span className="text-rose-600 font-medium">
                  {zabbixHosts.filter(h => h.status !== '0').length} Offline
                </span>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {zabbixHosts.map((host) => (
                <div
                  key={host.hostid}
                  className="p-4 bg-white/50 rounded-xl border border-white/20 hover:shadow-lg transition-all duration-200"
                >
                  <div className="flex items-center space-x-3 mb-3">
                    {getStatusIcon(host.status)}
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-slate-800 truncate">{host.name}</p>
                      <p className="text-sm text-slate-600 truncate">{host.host}</p>
                    </div>
                  </div>
                  {host.interfaces.length > 0 && (
                    <div className="text-xs text-slate-500 mb-2">
                      IP: {host.interfaces[0].ip}
                    </div>
                  )}
                  <div className="flex justify-between items-center">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      host.status === '0' 
                        ? 'bg-emerald-500/10 text-emerald-700' 
                        : 'bg-rose-500/10 text-rose-700'
                    }`}>
                      {host.status === '0' ? 'Online' : 'Offline'}
                    </span>
                    <div className="text-xs text-slate-500">
                      Port: {host.interfaces[0]?.port || 'N/A'}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'analytics' && (
        <div className="space-y-6">
          {/* Performance Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-white/20 p-6">
              <h3 className="font-semibold text-slate-700 mb-4 flex items-center space-x-2">
                <LineChart className="w-5 h-5 text-cyan-600" />
                <span>CPU & Memory Trends</span>
              </h3>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm text-slate-600 mb-2">
                    <span>CPU Usage</span>
                    <span className="font-medium text-cyan-600">{systemMetrics?.cpu?.toFixed(1)}%</span>
                  </div>
                  <SimpleLineChart data={mockChartData.cpuUsage} color="cyan" height={60} />
                </div>
                <div>
                  <div className="flex justify-between text-sm text-slate-600 mb-2">
                    <span>Memory Usage</span>
                    <span className="font-medium text-blue-600">{systemMetrics?.memory?.toFixed(1)}%</span>
                  </div>
                  <SimpleLineChart data={mockChartData.memoryUsage} color="blue" height={60} />
                </div>
              </div>
            </div>

            <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-white/20 p-6">
              <h3 className="font-semibold text-slate-700 mb-4 flex items-center space-x-2">
                <ActivityIcon className="w-5 h-5 text-violet-600" />
                <span>Network Activity</span>
              </h3>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm text-slate-600 mb-2">
                    <span>Network In</span>
                    <span className="font-medium text-emerald-600">{systemMetrics?.network_recv} Mbps</span>
                  </div>
                  <SimpleBarChart data={mockChartData.networkIn} color="emerald" height={40} />
                </div>
                <div>
                  <div className="flex justify-between text-sm text-slate-600 mb-2">
                    <span>Network Out</span>
                    <span className="font-medium text-rose-600">{systemMetrics?.network_sent} Mbps</span>
                  </div>
                  <SimpleBarChart data={mockChartData.networkOut} color="rose" height={40} />
                </div>
              </div>
            </div>
          </div>

          {/* Service Health Overview */}
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-white/20 p-6">
            <h3 className="font-semibold text-slate-700 mb-4 flex items-center space-x-2">
              <PieChart className="w-5 h-5 text-amber-600" />
              <span>Service Health Overview</span>
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {mockChartData.services.map((service, index) => (
                <div key={index} className="text-center p-4 bg-white/50 rounded-xl border border-white/20">
                  <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-emerald-500/10 flex items-center justify-center">
                    <CheckCircle className="w-6 h-6 text-emerald-500" />
                  </div>
                  <h4 className="font-medium text-slate-700 text-sm mb-1">{service.name}</h4>
                  <div className="text-xs text-slate-500">Uptime: {service.uptime}%</div>
                  <div className="text-xs text-emerald-600 font-medium mt-1">Healthy</div>
                </div>
              ))}
            </div>
          </div>

          {/* Infrastructure Summary */}
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-white/20 p-6">
            <h3 className="font-semibold text-slate-700 mb-4 flex items-center space-x-2">
              <BarChart4 className="w-5 h-5 text-blue-600" />
              <span>Infrastructure Summary</span>
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-4 bg-gradient-to-br from-cyan-500 to-blue-500 rounded-xl text-white">
                <Server className="w-8 h-8 mx-auto mb-2 opacity-90" />
                <div className="text-2xl font-bold">{monitoringMetrics?.total_hosts || 0}</div>
                <div className="text-sm opacity-90">Total Hosts</div>
              </div>
              <div className="text-center p-4 bg-gradient-to-br from-emerald-500 to-green-500 rounded-xl text-white">
                <Laptop className="w-8 h-8 mx-auto mb-2 opacity-90" />
                <div className="text-2xl font-bold">{monitoringMetrics?.running_vms || 0}</div>
                <div className="text-sm opacity-90">Running VMs</div>
              </div>
              <div className="text-center p-4 bg-gradient-to-br from-violet-500 to-purple-500 rounded-xl text-white">
                <Network className="w-8 h-8 mx-auto mb-2 opacity-90" />
                <div className="text-2xl font-bold">{monitoringMetrics?.network_connections || 0}</div>
                <div className="text-sm opacity-90">Connections</div>
              </div>
              <div className="text-center p-4 bg-gradient-to-br from-amber-500 to-orange-500 rounded-xl text-white">
                <ShieldCheck className="w-8 h-8 mx-auto mb-2 opacity-90" />
                <div className="text-2xl font-bold">{monitoringMetrics?.security_threats || 0}</div>
                <div className="text-sm opacity-90">Security Alerts</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="mt-8 text-center text-slate-500 text-sm">
        <div className="flex items-center justify-center space-x-4">
          <span>Last updated: {monitoringMetrics?.timestamp ? new Date(monitoringMetrics.timestamp).toLocaleString() : 'Loading...'}</span>
          <span className="w-1 h-1 bg-slate-400 rounded-full"></span>
          <span>NeoSilix Monitoring v1.0</span>
          <span className="w-1 h-1 bg-slate-400 rounded-full"></span>
          <span>Zabbix: {monitoringMode?.zabbix_connected ? 'Connected' : 'Disconnected'}</span>
        </div>
      </div>
    </div>
  );
};

export default UnifiedDashboard;
