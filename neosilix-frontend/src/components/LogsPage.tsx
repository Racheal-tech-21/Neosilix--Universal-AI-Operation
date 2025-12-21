import React, { useEffect, useState } from "react";
import { Server, AlertTriangle, ShieldCheck, Activity, TerminalSquare, Filter, Download, RefreshCw, User, Users, Search, Clock, FileText } from "lucide-react";
import { toast } from "sonner";
import clsx from "clsx";
import { ScrollArea } from "./ui/scroll-area";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { Button } from "./ui/button";

interface ComprehensiveLog {
  id: number;
  timestamp: string;
  level: string;
  category: string;
  message: string;
  user_id: number | null;
  metadata: any;
  source: string;
}

interface LogStats {
  total_logs: number;
  by_level: Record<string, number>;
  by_category: Record<string, number>;
  recent_activity: Array<{
    timestamp: string;
    level: string;
    category: string;
    message: string;
  }>;
}

const levelColors = {
  info: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  success: "bg-green-500/20 text-green-400 border-green-500/30",
  warning: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  error: "bg-red-500/20 text-red-400 border-red-500/30",
  default: "bg-gray-500/20 text-gray-400 border-gray-500/30",
};

const categoryColors = {
  user_activity: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  performance: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  infrastructure: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30",
  error: "bg-red-500/20 text-red-400 border-red-500/30",
  security: "bg-pink-500/20 text-pink-400 border-pink-500/30",
  ai_engine: "bg-indigo-500/20 text-indigo-400 border-indigo-500/30",
  legacy: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  default: "bg-gray-500/20 text-gray-400 border-gray-500/30",
};

const levelIcons = {
  info: Activity,
  success: ShieldCheck,
  warning: AlertTriangle,
  error: AlertTriangle,
  default: FileText,
};

// API functions for both admin and users
const fetchComprehensiveLogs = async (category: string = "all", level: string = "all"): Promise<ComprehensiveLog[]> => {
  try {
    const token = localStorage.getItem("token");
    if (!token) {
      console.error("No token found in localStorage");
      throw new Error("Please log in to access logs");
    }

    const params = new URLSearchParams();
    if (category !== "all") params.append("category", category);
    if (level !== "all") params.append("level", level);

    const response = await fetch(`http://localhost:5000/api/logs/system?${params.toString()}`, {
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      credentials: 'include',
    });

    if (response.status === 401) {
      toast.error("Session expired. Please log in again.");
      localStorage.removeItem("token");
      return [];
    }

    if (!response.ok) {
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        const errorData = await response.json();
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
      } else {
        const errorText = await response.text();
        throw new Error(`Server returned ${response.status}: ${errorText.substring(0, 100)}`);
      }
    }

    const contentType = response.headers.get("content-type");
    if (!contentType || !contentType.includes("application/json")) {
      throw new Error("Server returned non-JSON response");
    }

    const logs = await response.json();
    return logs;
  } catch (error) {
    console.error("Error fetching comprehensive logs:", error);
    if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
      toast.error("Cannot connect to server. Please check if the server is running.");
    } else {
      toast.error(error instanceof Error ? error.message : "Failed to fetch logs");
    }
    return [];
  }
};

const fetchLogStatistics = async (): Promise<LogStats | null> => {
  try {
    const token = localStorage.getItem("token");
    if (!token) {
      console.error("No token found in localStorage");
      throw new Error("No authentication token");
    }

    const response = await fetch("http://localhost:5000/api/logs/stats", {
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      credentials: 'include',
    });

    if (response.status === 401) {
      toast.error("Session expired. Please log in again.");
      localStorage.removeItem("token");
      return null;
    }

    if (!response.ok) {
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        const errorData = await response.json();
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
      } else {
        const errorText = await response.text();
        throw new Error(`Server returned ${response.status}: ${errorText.substring(0, 100)}`);
      }
    }

    const contentType = response.headers.get("content-type");
    if (!contentType || !contentType.includes("application/json")) {
      throw new Error("Server returned non-JSON response");
    }

    const stats = await response.json();
    return stats;
  } catch (error) {
    console.error("Error fetching log statistics:", error);
    if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
      toast.error("Cannot connect to server. Please check if the server is running.");
    } else {
      toast.error(error instanceof Error ? error.message : "Failed to fetch log statistics");
    }
    return null;
  }
};

// Check user role and info
const getUserInfo = async (): Promise<{ isAdmin: boolean; userId: number | null }> => {
  try {
    const token = localStorage.getItem("token");
    if (!token) {
      return { isAdmin: false, userId: null };
    }

    const response = await fetch("http://localhost:5000/auth/verify", {
      headers: {
        "Authorization": `Bearer ${token}`,
      },
      credentials: 'include',
    });

    if (response.ok) {
      const contentType = response.headers.get("content-type");
      if (!contentType || !contentType.includes("application/json")) {
        return { isAdmin: false, userId: null };
      }
      
      const data = await response.json();
      return { 
        isAdmin: data.is_admin || false, 
        userId: data.user_id || null 
      };
    }
    
    return { isAdmin: false, userId: null };
  } catch (error) {
    console.error("Error in getUserInfo:", error);
    return { isAdmin: false, userId: null };
  }
};

const LogsPage = () => {
  const [logs, setLogs] = useState<ComprehensiveLog[]>([]);
  const [logStats, setLogStats] = useState<LogStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [selectedLevel, setSelectedLevel] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [userInfo, setUserInfo] = useState<{ isAdmin: boolean; userId: number | null }>({ isAdmin: false, userId: null });

  const categories = [
    "all", "user_activity", "performance", "infrastructure", 
    "error", "security", "ai_engine", "legacy"
  ];

  const levels = ["all", "info", "success", "warning", "error"];

  const loadData = async () => {
    setLoading(true);
    try {
      // Get user info first
      const userData = await getUserInfo();
      setUserInfo(userData);

      const [l, statsData] = await Promise.all([
        fetchComprehensiveLogs(selectedCategory, selectedLevel),
        fetchLogStatistics()
      ]);
      
      setLogs(l);
      setLogStats(statsData);
    } catch (error) {
      console.error("Error loading logs:", error);
      if (error instanceof Error) {
        toast.error(`Error loading data: ${error.message}`);
      } else {
        toast.error("Error loading logs data");
      }
    } finally {
      setLoading(false);
      setInitialLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedCategory, selectedLevel]);

  // Handle favicon to prevent CORS issues
  useEffect(() => {
    const link = document.querySelector("link[rel*='icon']") as HTMLLinkElement || document.createElement('link');
    link.type = 'image/x-icon';
    link.rel = 'shortcut icon';
    link.href = '/favicon.ico';
    document.head.appendChild(link);
  }, []);

  const exportLogs = () => {
    const dataStr = JSON.stringify(logs, null, 2);
    const dataBlob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `neosilix-logs-${new Date().toISOString().split("T")[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.success("Logs exported successfully");
  };

  const getLevelColor = (level: string) => {
    return levelColors[level as keyof typeof levelColors] || levelColors.default;
  };

  const getCategoryColor = (category: string) => {
    return categoryColors[category as keyof typeof categoryColors] || categoryColors.default;
  };

  const getLevelIcon = (level: string) => {
    const IconComponent = levelIcons[level as keyof typeof levelIcons] || levelIcons.default;
    return <IconComponent className="w-3 h-3" />;
  };

  const formatMetadata = (metadata: any): string => {
    if (!metadata || Object.keys(metadata).length === 0) return "";
    
    const items = [];
    if (metadata.action) items.push(`Action: ${metadata.action}`);
    if (metadata.metric_name) items.push(`Metric: ${metadata.metric_name}`);
    if (metadata.metric_value) items.push(`Value: ${metadata.metric_value}`);
    if (metadata.component) items.push(`Component: ${metadata.component}`);
    if (metadata.error_type) items.push(`Error: ${metadata.error_type}`);
    
    return items.join(" • ");
  };

  // Filter logs based on user role for display
  const getFilteredLogs = () => {
    let filtered = logs;
    
    // Apply role-based filtering
    if (!userInfo.isAdmin) {
      filtered = filtered.filter(log => log.user_id === userInfo.userId || log.user_id === null);
    }
    
    // Apply search filter
    if (searchTerm) {
      filtered = filtered.filter(log => 
        log.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.category.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.level.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.source.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }
    
    return filtered;
  };

  const filteredLogs = getFilteredLogs();

  if (initialLoading) {
    return (
      <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-12 h-12 animate-spin text-cyan-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-300">Loading System Logs...</h2>
          <p className="text-gray-500 mt-2">Please wait while we load your logs data</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col p-6 md:p-10">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6 mb-8">
        <div className="flex items-center gap-3">
          <div className="relative">
            <TerminalSquare className="h-10 w-10 text-cyan-400" />
            <div className="absolute -inset-1 bg-cyan-400/20 rounded-lg blur-sm"></div>
          </div>
          <div>
            <h1 className="text-4xl font-extrabold bg-gradient-to-r from-cyan-400 to-pink-500 bg-clip-text text-transparent drop-shadow-lg select-none">
              System Logs
            </h1>
            <p className="text-gray-400 text-sm mt-1">
              {userInfo.isAdmin ? "Administrative monitoring dashboard" : "Personal activity monitoring"}
            </p>
          </div>
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <input
              type="text"
              placeholder="Search logs..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-gray-800 border border-gray-600 rounded-lg pl-10 pr-4 py-2 text-white focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-all w-full sm:w-64"
            />
          </div>
          <div className="flex gap-2">
            <Button
              onClick={exportLogs}
              variant="outline"
              size="sm"
              className="flex items-center gap-2 border-gray-600 hover:bg-gray-700"
              disabled={filteredLogs.length === 0}
            >
              <Download className="w-4 h-4" />
              Export
            </Button>
            <Button
              onClick={loadData}
              variant="outline"
              size="sm"
              className="flex items-center gap-2 border-gray-600 hover:bg-gray-700"
              disabled={loading}
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>
        </div>
      </div>

      {/* User Role Info */}
      <Card className="bg-gradient-to-tr from-gray-800/80 via-gray-900/80 to-black/80 border border-gray-700 rounded-2xl shadow-2xl backdrop-blur-sm mb-8">
        <CardContent className="p-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              {userInfo.isAdmin ? (
                <>
                  <div className="relative">
                    <ShieldCheck className="w-10 h-10 text-green-400" />
                    <div className="absolute -inset-1 bg-green-400/20 rounded-full blur-sm"></div>
                  </div>
                  <div>
                    <h3 className="font-bold text-green-400 text-lg">Administrator Access</h3>
                    <p className="text-sm text-gray-400">Full system monitoring across all users and services</p>
                  </div>
                </>
              ) : (
                <>
                  <div className="relative">
                    <User className="w-10 h-10 text-blue-400" />
                    <div className="absolute -inset-1 bg-blue-400/20 rounded-full blur-sm"></div>
                  </div>
                  <div>
                    <h3 className="font-bold text-blue-400 text-lg">Personal System Monitoring</h3>
                    <p className="text-sm text-gray-400">Viewing your personal system logs and activities</p>
                  </div>
                </>
              )}
            </div>
            <div className="text-right">
              <div className="text-sm text-gray-400">User ID: <span className="font-mono text-white">{userInfo.userId || 'N/A'}</span></div>
              <div className="text-xs text-gray-500">Displaying {filteredLogs.length} logs</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Log Statistics */}
      {logStats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card className="bg-gradient-to-br from-gray-800/90 via-gray-900/90 to-black/90 border border-gray-700 rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-300 cursor-default select-none group">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-3">
                <div className="p-2 bg-blue-500/20 rounded-lg">
                  <Activity className="w-5 h-5 text-blue-400" />
                </div>
                <span>Log Summary</span>
                {!userInfo.isAdmin && <span className="text-xs text-blue-400 bg-blue-500/20 px-2 py-1 rounded">Your Data</span>}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between items-center p-3 bg-gray-800/50 rounded-lg">
                  <span className="text-gray-400">Total Logs:</span>
                  <span className="font-bold text-xl text-white">{logStats.total_logs}</span>
                </div>
                {Object.entries(logStats.by_level).map(([level, count]) => (
                  <div key={level} className="flex justify-between items-center">
                    <div className="flex items-center gap-2">
                      <span className={clsx(
                        "w-2 h-2 rounded-full",
                        level === 'error' ? 'bg-red-400' :
                        level === 'warning' ? 'bg-yellow-400' :
                        level === 'success' ? 'bg-green-400' : 'bg-blue-400'
                      )}></span>
                      <span className="text-gray-400 capitalize">{level}:</span>
                    </div>
                    <span className="font-bold text-white">{count}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-gray-800/90 via-gray-900/90 to-black/90 border border-gray-700 rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-300 cursor-default select-none group">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-3">
                <div className="p-2 bg-purple-500/20 rounded-lg">
                  <FileText className="w-5 h-5 text-purple-400" />
                </div>
                <span>Categories</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {Object.entries(logStats.by_category).map(([category, count]) => (
                  <div key={category} className="flex justify-between items-center">
                    <div className="flex items-center gap-2">
                      <span className={clsx(
                        "w-2 h-2 rounded-full",
                        category === 'error' ? 'bg-red-400' :
                        category === 'security' ? 'bg-pink-400' :
                        category === 'performance' ? 'bg-orange-400' :
                        category === 'user_activity' ? 'bg-purple-400' : 'bg-cyan-400'
                      )}></span>
                      <span className="text-gray-400 capitalize">{category.replace('_', ' ')}:</span>
                    </div>
                    <span className="font-bold text-white">{count}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-gray-800/90 via-gray-900/90 to-black/90 border border-gray-700 rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-300 cursor-default select-none group">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-3">
                <div className="p-2 bg-green-500/20 rounded-lg">
                  <Clock className="w-5 h-5 text-green-400" />
                </div>
                <span>Recent Activity</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 max-h-48 overflow-y-auto custom-scrollbar">
                {logStats.recent_activity.map((activity, idx) => (
                  <div key={idx} className="p-3 bg-gray-800/30 rounded-lg border-l-4 border-l-gray-600 hover:border-l-cyan-400 transition-all duration-200">
                    <div className="flex justify-between items-start mb-2">
                      <span className="capitalize text-gray-300 font-medium text-sm">{activity.category.replace('_', ' ')}</span>
                      <span className={clsx(
                        "text-xs px-2 py-1 rounded font-medium flex items-center gap-1",
                        activity.level === 'error' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                        activity.level === 'warning' ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' :
                        activity.level === 'success' ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 
                        'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                      )}>
                        {getLevelIcon(activity.level)}
                        {activity.level}
                      </span>
                    </div>
                    <p className="text-gray-400 text-xs leading-relaxed line-clamp-2">{activity.message}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card className="bg-gradient-to-tr from-gray-800/80 via-gray-900/80 to-black/80 border border-gray-700 rounded-2xl shadow-xl mb-8">
        <CardHeader>
          <CardTitle className="flex items-center gap-3 text-lg">
            <div className="p-2 bg-cyan-500/20 rounded-lg">
              <Filter className="w-5 h-5 text-cyan-400" />
            </div>
            <span>Filters</span>
            {!userInfo.isAdmin && <span className="text-xs text-blue-400 bg-blue-500/20 px-2 py-1 rounded">Your data only</span>}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-6">
            <div className="flex-1">
              <label className="text-sm text-gray-400 block mb-3 font-medium">Category</label>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="w-full bg-gray-800 border border-gray-600 rounded-xl px-4 py-3 text-white focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-all hover:border-gray-500"
                disabled={loading}
              >
                {categories.map(cat => (
                  <option key={cat} value={cat}>
                    {cat === 'all' ? 'All Categories' : cat.replace('_', ' ')}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label className="text-sm text-gray-400 block mb-3 font-medium">Level</label>
              <select
                value={selectedLevel}
                onChange={(e) => setSelectedLevel(e.target.value)}
                className="w-full bg-gray-800 border border-gray-600 rounded-xl px-4 py-3 text-white focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-all hover:border-gray-500"
                disabled={loading}
              >
                {levels.map(level => (
                  <option key={level} value={level}>
                    {level === 'all' ? 'All Levels' : level}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Logs Table */}
      <Card className="bg-gradient-to-tr from-gray-800/80 via-gray-900/80 to-black/80 border border-gray-700 rounded-2xl shadow-xl flex flex-col flex-grow">
        <CardHeader className="border-b border-gray-700">
          <CardTitle className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-cyan-500/20 rounded-lg">
                <TerminalSquare className="w-5 h-5 text-cyan-400" />
              </div>
              <div>
                <span>System Logs</span>
                <span className="ml-2 text-cyan-400 font-mono bg-cyan-500/20 px-2 py-1 rounded text-sm">
                  {filteredLogs.length} entries
                </span>
              </div>
              {userInfo.isAdmin ? (
                <span className="text-xs text-green-400 bg-green-500/20 px-2 py-1 rounded">All users</span>
              ) : (
                <span className="text-xs text-blue-400 bg-blue-500/20 px-2 py-1 rounded">Your system</span>
              )}
            </div>
            {loading && (
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <RefreshCw className="w-4 h-4 animate-spin" />
                Updating...
              </div>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0 flex-1">
          <ScrollArea className="h-[600px]">
            <table className="w-full text-left text-sm text-gray-200 border-collapse">
              <thead className="bg-gray-800/80 text-gray-400 uppercase tracking-wide select-none sticky top-0 backdrop-blur-sm z-10">
                <tr>
                  {["Time", "Level", "Category", "Message", "User", "Source"].map((header) => (
                    <th key={header} className="px-6 py-4 font-semibold border-b border-gray-700 text-xs">
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredLogs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-20 text-center text-gray-500">
                      <div className="flex flex-col items-center gap-3">
                        <FileText className="w-12 h-12 text-gray-600" />
                        <div>
                          <p className="text-lg font-medium text-gray-400 mb-1">No logs found</p>
                          <p className="text-sm text-gray-500">
                            {searchTerm ? "Try adjusting your search terms" : "No logs available for selected filters"}
                          </p>
                        </div>
                      </div>
                    </td>
                  </tr>
                ) : (
                  filteredLogs.map((log) => {
                    const levelColor = getLevelColor(log.level);
                    const categoryColor = getCategoryColor(log.category);
                    const metadataText = formatMetadata(log.metadata);
                    const isUserLog = log.user_id === userInfo.userId;

                    return (
                      <tr
                        key={log.id}
                        className={clsx(
                          "border-b border-gray-700/50 hover:bg-gray-800/50 transition-all duration-200 cursor-pointer group",
                          isUserLog && "bg-blue-500/10 hover:bg-blue-500/20"
                        )}
                        title={`${log.level} - ${log.category} - ${log.source} ${isUserLog ? '(Your activity)' : ''}`}
                      >
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="font-mono text-xs text-gray-300 group-hover:text-white transition-colors">
                            {new Date(log.timestamp).toLocaleDateString()}
                          </div>
                          <div className="font-mono text-xs text-gray-500 group-hover:text-gray-400 transition-colors">
                            {new Date(log.timestamp).toLocaleTimeString()}
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className={clsx(
                            "inline-flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-semibold capitalize transition-all group-hover:scale-105",
                            levelColor
                          )}>
                            {getLevelIcon(log.level)}
                            {log.level}
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={clsx(
                              "inline-block px-3 py-2 rounded-lg border text-xs font-semibold text-white capitalize transition-all group-hover:scale-105",
                              categoryColor
                            )}
                          >
                            {log.category.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="px-6 py-4 max-w-md">
                          <div className="font-medium text-gray-100 group-hover:text-white transition-colors">
                            {log.message}
                          </div>
                          {metadataText && (
                            <div className="text-xs text-gray-400 mt-2 flex items-center gap-2">
                              <div className="w-1 h-1 bg-gray-500 rounded-full"></div>
                              {metadataText}
                            </div>
                          )}
                          {isUserLog && (
                            <div className="text-xs text-blue-400 mt-2 flex items-center gap-2">
                              <User className="w-3 h-3" />
                              Your activity
                            </div>
                          )}
                        </td>
                        <td className="px-6 py-4">
                          <div className={clsx(
                            "text-sm font-medium px-3 py-1 rounded-full inline-block",
                            log.user_id ? (
                              log.user_id === userInfo.userId ? 
                                "bg-blue-500/20 text-blue-400" : 
                                (userInfo.isAdmin ? "bg-purple-500/20 text-purple-400" : "bg-gray-500/20 text-gray-400")
                            ) : "bg-gray-500/20 text-gray-400"
                          )}>
                            {log.user_id ? 
                              (log.user_id === userInfo.userId ? 
                                "You" : 
                                (userInfo.isAdmin ? `User ${log.user_id}` : "Other user")
                              ) : 
                              "System"
                            }
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-xs text-gray-400 font-mono bg-gray-800/50 px-2 py-1 rounded border border-gray-700">
                            {log.source}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Footer */}
      <footer className="text-center py-6 text-xs text-gray-500 border-t border-gray-800/50 select-none mt-8">
        <div className="flex items-center justify-center gap-2">
          <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse"></div>
          © 2025 Neosilix by Racheal Inc. All rights reserved.
        </div>
      </footer>

      {/* Custom Scrollbar Styles */}
      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(75, 85, 99, 0.2);
          border-radius: 3px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(156, 163, 175, 0.5);
          border-radius: 3px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(156, 163, 175, 0.7);
        }
      `}</style>
    </div>
  );
};

export default LogsPage;
