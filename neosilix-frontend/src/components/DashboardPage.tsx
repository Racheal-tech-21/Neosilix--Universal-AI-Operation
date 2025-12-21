import React, { useEffect, useState, FormEvent } from "react"; 
import { getUser, authHeader, User } from "../utils/auth";
import axios from "axios";
import {
  HeartPulse,
  Activity,
  RefreshCcw,
  ShieldCheck,
  Brain,
  AlertTriangle,
  Cpu,
  HardDrive,
  Network,
  Bell,
  X,
  CheckCircle,
  AlertCircle,
  Info,
  Zap,
  Server,
  Database,
  Globe,
} from "lucide-react";

const API_URL = "http://localhost:5000/api";

const devopsQuotes = [
  "Automation doesn't replace you. It frees you.",
  "Good monitoring prevents bad mornings.",
  "Ship fast. Fail fast. Learn faster.",
  "If it isn't monitored, it doesn't exist.",
  "DevOps is not a role. It's a culture.",
  "Think CI/CD. Think faster delivery.",
  "Logs tell stories. Read them.",
  "Scaling without visibility is a gamble.",
  "A broken pipeline is worse than no pipeline.",
  "Resilience is built, not assumed.",
  "Every deploy is a chance to learn.",
  "Security must live in the pipeline, not outside it.",
  "Observability beats assumptions.",
];

// Enhanced Alert interface matching backend structure
interface Alert {
  id: number;
  type: string;
  severity: 'low' | 'medium' | 'high' | 'critical' | 'information' | 'warning' | 'average' | 'disaster';
  message: string;
  timestamp: string;
  component?: string;
  target_name?: string;
  acknowledged: boolean;
  suggested_fix?: string;
  ml_generated?: boolean;
  eventid?: string;
  host?: string;
  clock?: string;
  name?: string;
  priority?: string;
}

interface NotificationState {
  alerts: Alert[];
  unreadCount: number;
  lastUpdated: string;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<any>(null);
  const [quote, setQuote] = useState<string>("");
  const [news, setNews] = useState<string[]>([]);
  const [websites, setWebsites] = useState<{ id: number; url: string }[]>([]);
  const [newWebsite, setNewWebsite] = useState<string>("");
  const [metrics, setMetrics] = useState<any>({});
  const [user, setUser] = useState<User | null>(getUser());
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [alertStats, setAlertStats] = useState<any>(null);
  
  // Notification state
  const [notifications, setNotifications] = useState<NotificationState>({
    alerts: [],
    unreadCount: 0,
    lastUpdated: new Date().toISOString()
  });
  const [showNotifications, setShowNotifications] = useState(false);
  const [isLoadingAlerts, setIsLoadingAlerts] = useState(false);
  const [alertError, setAlertError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  // Helper function to map Zabbix severity levels
  const mapZabbixSeverity = (severity: string): Alert['severity'] => {
    const severityMap: { [key: string]: Alert['severity'] } = {
      '0': 'information',
      '1': 'information',
      '2': 'warning',
      '3': 'average',
      '4': 'high',
      '5': 'disaster'
    };
    return severityMap[severity] || 'medium';
  };

  // Production-level sample alerts with detailed information
  const getProductionSampleAlerts = (): Alert[] => [
    {
      id: 1,
      type: 'high_cpu',
      severity: 'high',
      message: 'CPU usage above 85% on web-server-01 for 15 minutes',
      timestamp: new Date(Date.now() - 5 * 60000).toISOString(),
      component: 'web-server-01',
      acknowledged: false,
      suggested_fix: 'Check for runaway processes using "top" command. Consider scaling horizontally or optimizing application code. Current CPU: 87%, Threshold: 80%',
      ml_generated: true
    },
    {
      id: 2,
      type: 'database_connection_pool',
      severity: 'critical',
      message: 'Database connection pool exhausted - 95% utilization',
      timestamp: new Date(Date.now() - 2 * 60000).toISOString(),
      component: 'primary-db',
      acknowledged: false,
      suggested_fix: 'Increase connection pool size from 100 to 200 connections. Optimize long-running queries. Consider implementing connection pooling at application level.'
    },
    {
      id: 3,
      type: 'disk_space',
      severity: 'high',
      message: 'Disk usage at 92% on storage-server-02',
      timestamp: new Date(Date.now() - 10 * 60000).toISOString(),
      component: 'storage-server-02',
      acknowledged: true,
      suggested_fix: 'Clean up temporary files in /tmp directory. Archive old logs. Consider expanding storage capacity by 50GB. Current usage: 46GB/50GB'
    },
    {
      id: 4,
      type: 'network_latency',
      severity: 'medium',
      message: 'Increased network latency detected between data centers - average 150ms',
      timestamp: new Date(Date.now() - 15 * 60000).toISOString(),
      component: 'network-core-01',
      acknowledged: false,
      suggested_fix: 'Check network congestion and routing tables. Verify BGP peering sessions. Monitor for packet loss. Current latency: 150ms, Normal: 50ms',
      ml_generated: true
    },
    {
      id: 5,
      type: 'memory_leak',
      severity: 'high',
      message: 'Potential memory leak detected in application service - memory usage growing 2MB/min',
      timestamp: new Date(Date.now() - 8 * 60000).toISOString(),
      component: 'app-service-03',
      acknowledged: false,
      suggested_fix: 'Profile application memory usage with heap dump analysis. Restart service and monitor memory growth pattern. Check for unclosed database connections.',
      ml_generated: true
    },
    {
      id: 6,
      type: 'service_down',
      severity: 'disaster',
      message: 'Primary database service unreachable - connection timeout',
      timestamp: new Date(Date.now() - 3 * 60000).toISOString(),
      component: 'primary-db',
      acknowledged: false,
      suggested_fix: 'Immediate failover to secondary database. Check database process status and restart if needed. Verify network connectivity between application and database layers.'
    },
    {
      id: 7,
      type: 'security_breach',
      severity: 'critical',
      message: 'Multiple failed login attempts detected from suspicious IP',
      timestamp: new Date(Date.now() - 7 * 60000).toISOString(),
      component: 'auth-service',
      acknowledged: false,
      suggested_fix: 'Block IP address 192.168.1.100 in firewall. Review authentication logs for patterns. Consider implementing rate limiting and IP whitelisting.'
    },
    {
      id: 8,
      type: 'backup_failed',
      severity: 'high',
      message: 'Nightly backup failed - insufficient disk space',
      timestamp: new Date(Date.now() - 25 * 60000).toISOString(),
      component: 'backup-server',
      acknowledged: false,
      suggested_fix: 'Free up 20GB space on backup volume. Verify backup retention policy. Consider implementing incremental backups to reduce storage requirements.'
    }
  ];

  // Enhanced alert fetching with real backend integration
  const fetchAlerts = async () => {
    if (!user) return;
    
    setIsLoadingAlerts(true);
    try {
      // Fetch enhanced alerts from backend
      const [enhancedRes, zabbixRes, monitoringRes] = await Promise.allSettled([
        axios.get(`${API_URL}/alerts/enhanced`, { headers: authHeader() }),
        axios.get(`${API_URL}/monitoring/zabbix/alerts`, { headers: authHeader() }),
        axios.get(`${API_URL}/monitoring/alerts`, { headers: authHeader() })
      ]);

      let allAlerts: Alert[] = [];

      // Process enhanced alerts
      if (enhancedRes.status === 'fulfilled' && enhancedRes.value.data.alerts) {
        allAlerts = [...allAlerts, ...enhancedRes.value.data.alerts];
      }

      // Process Zabbix alerts
      if (zabbixRes.status === 'fulfilled' && zabbixRes.value.data) {
        const zabbixAlerts: Alert[] = zabbixRes.value.data.map((alert: any) => ({
          id: alert.eventid || Math.random() * 10000,
          type: 'zabbix_alert',
          severity: mapZabbixSeverity(alert.severity || alert.priority),
          message: alert.name || alert.description || 'Zabbix Alert',
          timestamp: alert.clock ? new Date(parseInt(alert.clock) * 1000).toISOString() : new Date().toISOString(),
          component: alert.host || 'Zabbix System',
          acknowledged: alert.acknowledged === true || alert.acknowledged === '1',
          eventid: alert.eventid,
          ml_generated: false
        }));
        allAlerts = [...allAlerts, ...zabbixAlerts];
      }

      // Process monitoring alerts
      if (monitoringRes.status === 'fulfilled' && monitoringRes.value.data) {
        const monitoringAlerts: Alert[] = monitoringRes.value.data.map((alert: any) => ({
          id: alert.id || Math.random() * 10000,
          type: alert.type || 'monitoring_alert',
          severity: alert.severity || 'medium',
          message: alert.message || 'Monitoring Alert',
          timestamp: alert.timestamp || new Date().toISOString(),
          component: alert.host || alert.target_name || 'Monitoring System',
          acknowledged: alert.acknowledged || false,
          suggested_fix: alert.suggested_fix,
          ml_generated: alert.ml_generated || false
        }));
        allAlerts = [...allAlerts, ...monitoringAlerts];
      }

      // Remove duplicates based on ID and message
      const uniqueAlerts = allAlerts.filter((alert, index, self) =>
        index === self.findIndex(a => 
          a.id === alert.id && a.message === alert.message
        )
      );

      // Sort by severity and timestamp
      const sortedAlerts = uniqueAlerts.sort((a, b) => {
        const severityOrder = { 
          critical: 0, disaster: 1, high: 2, average: 3, medium: 4, warning: 5, low: 6, information: 7 
        };
        const aOrder = severityOrder[a.severity] || 8;
        const bOrder = severityOrder[b.severity] || 8;
        
        if (aOrder !== bOrder) return aOrder - bOrder;
        return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
      });

      const unreadCount = sortedAlerts.filter(alert => !alert.acknowledged).length;

      setNotifications({
        alerts: sortedAlerts,
        unreadCount,
        lastUpdated: new Date().toISOString()
      });
      setAlertError(null);
    } catch (err) {
      console.error("Failed to fetch alerts:", err);
      setAlertError("Failed to load alerts from monitoring systems");
      // Fallback to detailed sample data
      setNotifications({
        alerts: getProductionSampleAlerts(),
        unreadCount: getProductionSampleAlerts().filter(alert => !alert.acknowledged).length,
        lastUpdated: new Date().toISOString()
      });
    } finally {
      setIsLoadingAlerts(false);
    }
  };

  // Enhanced error handling with retry logic
  const fetchAlertsWithRetry = async () => {
    try {
      await fetchAlerts();
      setRetryCount(0);
      setAlertError(null);
    } catch (err) {
      const newRetryCount = retryCount + 1;
      setRetryCount(newRetryCount);
      
      if (newRetryCount <= 3) {
        setTimeout(() => fetchAlertsWithRetry(), 10000 * newRetryCount); // Increased to 10 seconds
      } else {
        setAlertError('Unable to connect to alert services. Please check your connection.');
      }
    }
  };

  // Fetch alert statistics
  const fetchAlertStats = async () => {
    if (!user) return;
    
    try {
      const res = await axios.get(`${API_URL}/alerts/stats`, { 
        headers: authHeader() 
      });
      setAlertStats(res.data);
    } catch (err) {
      console.error("Failed to fetch alert stats:", err);
    }
  };

  // Acknowledge an alert with real API call
  const acknowledgeAlert = async (alertId: number) => {
    try {
      await axios.post(`${API_URL}/alerts/${alertId}/acknowledge`, {}, { 
        headers: authHeader() 
      });
      
      setNotifications(prev => ({
        ...prev,
        alerts: prev.alerts.map(alert => 
          alert.id === alertId ? { ...alert, acknowledged: true } : alert
        ),
        unreadCount: Math.max(0, prev.unreadCount - 1)
      }));
    } catch (err) {
      console.error("Failed to acknowledge alert:", err);
      // Fallback: update locally even if API fails
      setNotifications(prev => ({
        ...prev,
        alerts: prev.alerts.map(alert => 
          alert.id === alertId ? { ...alert, acknowledged: true } : alert
        ),
        unreadCount: Math.max(0, prev.unreadCount - 1)
      }));
    }
  };

  // Enhanced severity colors
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
      case 'disaster': 
        return 'border-red-500 bg-red-500/10';
      case 'high': 
        return 'border-orange-500 bg-orange-500/10';
      case 'medium':
      case 'average':
        return 'border-yellow-500 bg-yellow-500/10';
      case 'warning':
        return 'border-yellow-400 bg-yellow-400/10';
      case 'low': 
        return 'border-blue-500 bg-blue-500/10';
      case 'information':
        return 'border-gray-500 bg-gray-500/10';
      default: 
        return 'border-gray-500 bg-gray-500/10';
    }
  };

  // Enhanced severity icons
  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
      case 'disaster': 
        return <AlertCircle className="w-4 h-4 text-red-400" />;
      case 'high': 
        return <AlertTriangle className="w-4 h-4 text-orange-400" />;
      case 'medium':
      case 'average':
        return <Info className="w-4 h-4 text-yellow-400" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-yellow-300" />;
      case 'low': 
        return <CheckCircle className="w-4 h-4 text-blue-400" />;
      case 'information':
        return <Info className="w-4 h-4 text-gray-400" />;
      default: 
        return <Bell className="w-4 h-4 text-gray-400" />;
    }
  };

  // Get component icon
  const getComponentIcon = (componentType?: string) => {
    if (!componentType) return <Server className="w-4 h-4" />;
    
    if (componentType.includes('db') || componentType.includes('database')) 
      return <Database className="w-4 h-4" />;
    if (componentType.includes('web') || componentType.includes('server')) 
      return <Server className="w-4 h-4" />;
    if (componentType.includes('network') || componentType.includes('router')) 
      return <Globe className="w-4 h-4" />;
    if (componentType.includes('cache')) 
      return <Zap className="w-4 h-4" />;
    if (componentType.includes('auth') || componentType.includes('security'))
      return <ShieldCheck className="w-4 h-4" />;
    if (componentType.includes('backup'))
      return <HardDrive className="w-4 h-4" />;
    
    return <Server className="w-4 h-4" />;
  };

  // Separate Alert Item Component for better organization
  const AlertItem = ({ alert, onAcknowledge }: { alert: Alert; onAcknowledge: (id: number) => void }) => {
    const [expanded, setExpanded] = useState(false);

    // Get detailed description based on alert type
    const getAlertDescription = () => {
      switch (alert.type) {
        case 'high_cpu':
          return 'High CPU usage indicates potential performance bottlenecks. Monitor process utilization and consider optimization.';
        case 'database_connection_pool':
          return 'Database connection pool exhaustion can lead to application timeouts and degraded performance.';
        case 'disk_space':
          return 'Low disk space can cause system instability and service failures. Immediate action recommended.';
        case 'network_latency':
          return 'Increased network latency affects application responsiveness and user experience.';
        case 'memory_leak':
          return 'Memory leaks gradually consume system resources and can lead to out-of-memory errors.';
        case 'service_down':
          return 'Service unavailability impacts system functionality and requires immediate investigation.';
        case 'security_breach':
          return 'Security incidents require immediate attention to prevent unauthorized access and data breaches.';
        case 'backup_failed':
          return 'Backup failures risk data loss and should be resolved promptly to maintain data protection.';
        default:
          return 'System alert requiring attention to maintain optimal performance and reliability.';
      }
    };

    return (
      <div
        className={`p-3 mb-2 rounded-lg border-l-4 ${
          alert.acknowledged 
            ? 'bg-gray-800 border-gray-600' 
            : 'bg-gray-800 border-l-4 ' + getSeverityColor(alert.severity)
        } cursor-pointer hover:bg-gray-750 transition-colors`}
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex justify-between items-start mb-2">
          <div className="flex items-center space-x-2 flex-1 min-w-0">
            {getSeverityIcon(alert.severity)}
            <span className={`text-sm font-medium capitalize truncate ${
              alert.severity === 'critical' || alert.severity === 'disaster' ? 'text-red-400' :
              alert.severity === 'high' ? 'text-orange-400' :
              alert.severity === 'medium' || alert.severity === 'average' ? 'text-yellow-400' : 
              alert.severity === 'warning' ? 'text-yellow-300' : 'text-blue-400'
            }`}>
              {alert.severity}
            </span>
            {alert.ml_generated && (
              <span className="text-xs bg-purple-500 text-white px-2 py-1 rounded-full flex-shrink-0">
                AI
              </span>
            )}
          </div>
          <div className="flex items-center space-x-2 flex-shrink-0 ml-2">
            {!alert.acknowledged && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onAcknowledge(alert.id);
                }}
                className="text-xs text-gray-400 hover:text-green-400 transition-colors"
                title="Acknowledge alert"
              >
                <CheckCircle className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
        
        <p className="text-sm text-white mb-2 line-clamp-2">{alert.message}</p>
        
        {alert.component && (
          <div className="flex items-center space-x-1 text-xs text-gray-400 mb-2">
            {getComponentIcon(alert.component)}
            <span className="truncate">{alert.component}</span>
          </div>
        )}
        
        {expanded && (
          <div className="space-y-2">
            <div className="text-xs text-gray-300 bg-gray-700/50 p-2 rounded">
              <strong>Description:</strong> {getAlertDescription()}
            </div>
            
            {alert.suggested_fix && !alert.acknowledged && (
              <div className="text-xs text-cyan-400 bg-cyan-900/20 p-2 rounded">
                💡 <strong>Recommended Action:</strong> {alert.suggested_fix}
              </div>
            )}
            
            <div className="text-xs text-gray-400 flex justify-between">
              <span>Alert Type: {alert.type}</span>
              <span>Detected: {new Date(alert.timestamp).toLocaleString()}</span>
            </div>
          </div>
        )}
        
        <div className="flex justify-between items-center mt-2">
          <div className="text-xs text-gray-500">
            {new Date(alert.timestamp).toLocaleTimeString()}
          </div>
          {alert.acknowledged ? (
            <div className="text-xs text-green-400 flex items-center space-x-1">
              <CheckCircle className="w-3 h-3" />
              <span>Acknowledged</span>
            </div>
          ) : (
            <div className="text-xs text-gray-500">
              {expanded ? 'Click to collapse' : 'Click for details'}
            </div>
          )}
        </div>
      </div>
    );
  };

  // Enhanced Notification Bell Component
  const NotificationBell = () => {
    const [filterSeverity, setFilterSeverity] = useState<string>('all');
    
    const filteredAlerts = filterSeverity === 'all' 
      ? notifications.alerts 
      : notifications.alerts.filter(alert => alert.severity === filterSeverity);

    const getSeverityCounts = () => {
      const counts = { 
        critical: 0, 
        disaster: 0,
        high: 0, 
        medium: 0, 
        average: 0,
        warning: 0,
        low: 0, 
        information: 0 
      };
      notifications.alerts.forEach(alert => {
        if (counts.hasOwnProperty(alert.severity)) {
          counts[alert.severity as keyof typeof counts]++;
        }
      });
      return counts;
    };

    const severityCounts = getSeverityCounts();

    const getSystemHealthStatus = () => {
      const criticalCount = severityCounts.critical + severityCounts.disaster;
      const highCount = severityCounts.high;
      
      if (criticalCount > 0) return { status: 'Critical', color: 'text-red-400', bg: 'bg-red-500/20' };
      if (highCount > 0) return { status: 'Degraded', color: 'text-orange-400', bg: 'bg-orange-500/20' };
      if (severityCounts.medium > 0 || severityCounts.average > 0) return { status: 'Stable', color: 'text-yellow-400', bg: 'bg-yellow-500/20' };
      return { status: 'Healthy', color: 'text-green-400', bg: 'bg-green-500/20' };
    };

    const healthStatus = getSystemHealthStatus();

    return (
      <div className="relative">
        <button
          onClick={() => setShowNotifications(!showNotifications)}
          className="relative p-2 text-gray-400 hover:text-white transition-colors group"
          title="System Alerts"
        >
          <Bell className="w-6 h-6 group-hover:scale-110 transition-transform" />
          {notifications.unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center animate-pulse">
              {notifications.unreadCount > 99 ? '99+' : notifications.unreadCount}
            </span>
          )}
        </button>

        {showNotifications && (
          <div className="absolute right-0 top-12 w-96 bg-gray-900 border border-gray-700 rounded-lg shadow-xl z-50 max-h-96 overflow-y-auto">
            {/* Header with filters and health status */}
            <div className="p-4 border-b border-gray-700">
              <div className="flex justify-between items-center mb-3">
                <div>
                  <h3 className="font-semibold text-white">System Alerts</h3>
                  <div className={`text-xs px-2 py-1 rounded mt-1 inline-block ${healthStatus.bg} ${healthStatus.color}`}>
                    System Status: {healthStatus.status}
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-400">
                    {notifications.unreadCount} unread
                  </span>
                  <button
                    onClick={() => setShowNotifications(false)}
                    className="text-gray-400 hover:text-white transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
              
              {/* Severity Filter */}
              <div className="flex space-x-1 flex-wrap gap-1">
                {['all', 'critical', 'disaster', 'high', 'medium'].map(severity => (
                  <button
                    key={severity}
                    onClick={() => setFilterSeverity(severity)}
                    className={`px-2 py-1 text-xs rounded capitalize ${
                      filterSeverity === severity
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    {severity} {severity !== 'all' && `(${severityCounts[severity as keyof typeof severityCounts] || 0})`}
                  </button>
                ))}
              </div>
            </div>

            {/* Alerts List */}
            <div className="p-2">
              {isLoadingAlerts ? (
                <div className="text-center py-4 text-gray-400">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-cyan-500 mx-auto mb-2"></div>
                  <p>Loading alerts...</p>
                </div>
              ) : filteredAlerts.length === 0 ? (
                <div className="text-center py-4 text-gray-400">
                  <CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-500" />
                  <p>No active alerts</p>
                  <p className="text-xs mt-1">All systems are healthy</p>
                </div>
              ) : (
                filteredAlerts.map((alert) => (
                  <AlertItem 
                    key={alert.id} 
                    alert={alert} 
                    onAcknowledge={acknowledgeAlert}
                  />
                ))
              )}
            </div>

            {/* Footer */}
            <div className="p-3 border-t border-gray-700 bg-gray-800">
              <div className="flex justify-between items-center text-xs text-gray-400">
                <span>Last updated: {new Date(notifications.lastUpdated).toLocaleTimeString()}</span>
                <button 
                  onClick={fetchAlertsWithRetry}
                  className="text-cyan-400 hover:text-cyan-300 transition-colors flex items-center space-x-1"
                  disabled={isLoadingAlerts}
                >
                  <RefreshCcw className={`w-3 h-3 ${isLoadingAlerts ? 'animate-spin' : ''}`} />
                  <span>Refresh</span>
                </button>
              </div>
              {alertError && (
                <div className="text-xs text-red-400 mt-2">
                  ⚠️ {alertError}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  const fetchWebsites = async () => {
    if (!user || user.is_admin) return;
    try {
      const res = await axios.get(
        `${API_URL}/stats/users/${user.id}/websites`,
        { headers: authHeader() }
      );
      setWebsites(res.data);
      for (const w of res.data) {
        const metricsRes = await axios.get(
          `${API_URL}/stats/users/${user.id}/metrics?website=${encodeURIComponent(w.url)}`,
          { headers: authHeader() }
        );
        setMetrics((prev: any) => ({
          ...prev,
          [w.url]: metricsRes.data,
        }));
      }
    } catch (err) {
      console.error("Failed to fetch websites:", err);
    }
  };

  const fetchDashboardStats = async () => {
    if (!user) return null;
    try {
      const res = await axios.get(`${API_URL}/stats/dashboard`, { 
        headers: authHeader() 
      });
      return res.data;
    } catch (err) {
      console.error("Failed to fetch stats:", err);
      return null;
    }
  };
  
  const handleAddWebsite = async (e: FormEvent) => {
    e.preventDefault();
    if (!newWebsite || !user) return;
    try {
      await axios.post(
        `${API_URL}/stats/users/${user.id}/websites`,
        { url: newWebsite },
        { headers: authHeader() }
      );
      setNewWebsite("");
      fetchWebsites();
    } catch (err) {
      console.error("Failed to add website:", err);
    }
  };

  const fetchTechNews = async () => {
    try {
      const res = await fetch(
        "https://api.rss2json.com/v1/api.json?rss_url=https://techcrunch.com/feed/"
      );
      const data = await res.json();
      const headlines = data.items.slice(0, 5).map((item: any) => item.title || "");
      setNews(headlines);
    } catch (err) {
      console.error("Failed to fetch tech news:", err);
      setNews(["Tech news temporarily unavailable"]);
    }
  };

  // Refresh all data
  const refreshAllData = async () => {
    await fetchAlertsWithRetry();
    await fetchAlertStats();
    const statsData = await fetchDashboardStats();
    if (statsData) setStats(statsData);
    setLastRefresh(new Date());
  };

  // Refresh data periodically - reduced frequency
  useEffect(() => {
    const interval = setInterval(() => {
      refreshAllData();
    }, 60000); // Refresh every 60 seconds instead of 30

    return () => clearInterval(interval);
  }, [user]);

  // Real-time alert updates when notifications are open - reduced frequency
  useEffect(() => {
    const alertPollingInterval = setInterval(() => {
      if (showNotifications) {
        fetchAlertsWithRetry();
      }
    }, 30000); // Poll every 30 seconds when notifications are open instead of 10

    return () => clearInterval(alertPollingInterval);
  }, [showNotifications, user]);

  useEffect(() => {
    const init = async () => {
      setIsLoading(true);
      const currentUser = getUser();
      if (!currentUser) {
        window.location.href = "/login";
        return;
      }
      setUser(currentUser);

      if (
        currentUser.plan === "trial" &&
        currentUser.trial_ends &&
        new Date(currentUser.trial_ends).getTime() < Date.now()
      ) {
        window.location.href = "/payment";
        return;
      }

      try {
        const statsData = await fetchDashboardStats();
        if (statsData) {
          setStats(statsData);
        } else {
          setStats(null);
        }
      } catch (err) {
        console.error(err);
        setStats(null);
      }

      setQuote(devopsQuotes[Math.floor(Math.random() * devopsQuotes.length)]);
      await fetchTechNews();
      await fetchAlertsWithRetry();
      await fetchAlertStats();
      setIsLoading(false);
    };
    init();
  }, []);

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-500 mx-auto mb-4"></div>
          <p className="text-gray-400">Loading dashboard...</p>
          <p className="text-sm text-gray-500 mt-2">Preparing your AI-powered monitoring experience</p>
        </div>
      </div>
    );
  }

  // ADMIN VIEW
  if (user?.is_admin) {
    const adminCards = [
      { icon: <HeartPulse className="text-pink-500 w-5 h-5" />, label: "System Health", value: "AI Monitoring Active" },
      { icon: <Activity className="text-green-500 w-5 h-5" />, label: "Current Uptime", value: stats ? `${stats.uptime_percentage || 0}%` : "Loading..." },
      { icon: <ShieldCheck className="text-yellow-400 w-5 h-5" />, label: "Anomalies Detected", value: stats ? stats.anomalies || 0 : "Loading..." },
      { icon: <RefreshCcw className="text-blue-400 w-5 h-5" />, label: "Auto-Heals (24h)", value: stats ? stats.heals_last_24h || 0 : "Loading..." },
      { icon: <Brain className="text-purple-500 w-5 h-5" />, label: "AI Engine Status", value: stats?.ai_engine_status === "running" ? "Running" : "Offline" },
    ];

    return (
      <div className="min-h-screen bg-gray-950 text-white flex flex-col">
        <div className="p-6 flex-grow">
          {/* Header with refresh and notifications */}
          <div className="flex justify-between items-center mb-6">
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
                Neosilix AI Ops Dashboard - Admin
              </h1>
              <p className="text-sm text-gray-400 mt-1">
                Last updated: {lastRefresh.toLocaleTimeString()}
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <button 
                onClick={refreshAllData}
                className="flex items-center space-x-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
                title="Refresh data"
              >
                <RefreshCcw className="w-4 h-4" />
                <span className="text-sm">Refresh</span>
              </button>
              <NotificationBell />
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="bg-yellow-900/50 border border-yellow-700 rounded-lg p-4 mb-6">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="w-5 h-5 text-yellow-400" />
                <span className="text-yellow-300">{error}</span>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
            {adminCards.map((card, idx) => (
              <div key={idx} className="bg-gradient-to-tr from-gray-800 via-gray-900 to-black border border-gray-700 rounded-xl p-5 shadow-md hover:shadow-xl transition duration-200">
                <div className="flex items-center space-x-3 mb-3">
                  {card.icon}
                  <h2 className="text-lg font-semibold">{card.label}</h2>
                </div>
                <p className="text-xl font-bold">{card.value}</p>
              </div>
            ))}
          </div>

          <div className="bg-gradient-to-br from-blue-900 via-indigo-900 to-purple-900 rounded-xl p-6 border border-gray-700 mb-6">
            <h2 className="text-2xl font-semibold mb-3">DevOps Daily Inspiration</h2>
            <p className="italic text-gray-300">"{quote}"</p>
          </div>

          <div className="bg-gradient-to-br from-gray-800 via-gray-900 to-black rounded-xl p-6 border border-gray-700">
            <h2 className="text-2xl font-semibold mb-3">Latest Tech News</h2>
            <ul className="text-sm text-gray-300 space-y-2">
              {news.length ? news.map((n, i) => <li key={i}>• {n}</li>) : <li className="text-gray-500">Loading tech news...</li>}
            </ul>
          </div>
        </div>

        <footer className="text-center py-4 text-xs text-gray-500 border-t border-gray-800 select-none">
          © 2025 Neosilix by Racheal Inc. All rights reserved.
        </footer>

        {/* Click outside to close notifications */}
        {showNotifications && (
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setShowNotifications(false)}
          />
        )}
      </div>
    );
  }

  // USER VIEW
  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col">
      <div className="p-6 flex-grow">
        {/* Header with refresh and notifications */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
              Neosilix AI Ops Dashboard
            </h1>
            <p className="text-sm text-gray-400 mt-1">
              Last updated: {lastRefresh.toLocaleTimeString()}
            </p>
          </div>
          <div className="flex items-center space-x-4">
            <button 
              onClick={refreshAllData}
              className="flex items-center space-x-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
              title="Refresh data"
            >
              <RefreshCcw className="w-4 h-4" />
              <span className="text-sm">Refresh</span>
            </button>
            <NotificationBell />
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-yellow-900/50 border border-yellow-700 rounded-lg p-4 mb-6">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-5 h-5 text-yellow-400" />
              <span className="text-yellow-300">{error}</span>
            </div>
          </div>
        )}

        {/* Only show user websites if not admin */}
        {!user?.is_admin && (
          <>
            <form onSubmit={handleAddWebsite} className="flex gap-2 mb-6">
              <input 
                type="url" 
                placeholder="https://neosilix.com" 
                value={newWebsite} 
                onChange={e => setNewWebsite(e.target.value)} 
                required 
                className="flex-1 px-4 py-2 rounded-lg bg-gray-800 border border-gray-700 text-white placeholder-gray-400 focus:border-cyan-500 focus:outline-none transition-colors"
              />
              <button type="submit" className="bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded-lg transition-colors">
                Add Website
              </button>
            </form>

            {websites.map(w => (
              <div key={w.id} className="mb-4 bg-gray-800 p-4 rounded-xl border border-gray-700 hover:border-gray-600 transition-colors">
                <h3 className="font-semibold mb-2">{w.url}</h3>
                <ul className="text-sm">
                  {metrics[w.url]?.length ? metrics[w.url].map((m: any, i: number) => {
                    const isAnomaly = (m.metric_name === "status_code" && m.metric_value !== 200) || (m.metric_name === "latency_ms" && m.metric_value > 1000);
                    return (
                      <li key={i} className={`${isAnomaly ? "text-red-500 font-semibold" : "text-green-400"}`}>
                        {m.metric_name}: {m.metric_value}
                      </li>
                    );
                  }) : <li className="text-gray-400">No metrics yet</li>}
                </ul>
              </div>
            ))}
          </>
        )}

        <div className="bg-gradient-to-br from-blue-900 via-indigo-900 to-purple-900 rounded-xl p-6 border border-gray-700 mb-6">
          <h2 className="text-2xl font-semibold mb-3">DevOps Daily Inspiration</h2>
          <p className="italic text-gray-300">"{quote}"</p>
        </div>

        <div className="bg-gradient-to-br from-gray-800 via-gray-900 to-black rounded-xl p-6 border border-gray-700">
          <h2 className="text-2xl font-semibold mb-3">Latest Tech News</h2>
          <ul className="text-sm text-gray-300 space-y-2">
            {news.length ? news.map((n, i) => <li key={i}>• {n}</li>) : <li className="text-gray-500">Loading tech news...</li>}
          </ul>
        </div>
      </div>

      <footer className="text-center py-4 text-xs text-gray-500 border-t border-gray-800 select-none">
        © 2025 Neosilix by Racheal Inc. All rights reserved.
      </footer>

      {/* Click outside to close notifications */}
      {showNotifications && (
        <div 
          className="fixed inset-0 z-40" 
          onClick={() => setShowNotifications(false)}
        />
      )}
    </div>
  );
}
