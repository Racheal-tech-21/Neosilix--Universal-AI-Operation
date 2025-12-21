import React, { useEffect, useState, useRef, useCallback, useMemo, lazy, Suspense } from "react";
import { fetchClusterHealth } from "../lib/fetchClusterHealth";
import { Brain, Sparkles, Zap } from "lucide-react";
import { toast } from "sonner";
import clsx from "clsx";
import { getToken, getUser } from "../utils/auth";
import { Button } from "./ui/button";
// Lazy load components
const StatCardsSection = lazy(() => import("./StatCardsSection"));
const PerformanceChartsSection = lazy(() => import("./PerformanceChartsSection"));
const ResourceChartsSection = lazy(() => import("./ResourceChartsSection"));
const ChatInterface = lazy(() => import("./ChatInterface"));

// Error Boundary Component
class ErrorBoundary extends React.Component<{children: React.ReactNode}, {hasError: boolean}> {
  constructor(props: {children: React.ReactNode}) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Chart Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-4 bg-red-900/20 border border-red-500/30 rounded-lg text-red-200">
          <p>Chart rendering error. Data is still being processed.</p>
        </div>
      );
    }
    return this.props.children;
  }
}

// Fallback components
const StatCardsFallback = () => (
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
    {[...Array(6)].map((_, i) => (
      <div key={i} className="h-40 bg-gray-800/50 rounded-2xl animate-pulse" />
    ))}
  </div>
);

const ChartFallback = () => (
  <div className="h-80 bg-gray-800/50 rounded-2xl animate-pulse flex items-center justify-center">
    <div className="text-gray-400">Loading charts...</div>
  </div>
);

const ResourceChartsFallback = () => (
  <div className="space-y-8">
    <div className="h-64 bg-gray-800/50 rounded-2xl animate-pulse" />
    <div className="h-64 bg-gray-800/50 rounded-2xl animate-pulse" />
  </div>
);

export default function CopilotPage() {
  const [stats, setStats] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [logs, setLogs] = useState<any[]>([]);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cluster, setCluster] = useState<any[]>([]);
  const [isAdmin, setIsAdmin] = useState(false);
  const [chatMessages, setChatMessages] = useState<any[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isChatExpanded, setIsChatExpanded] = useState(false);
  const [isChatMinimized, setIsChatMinimized] = useState(false);
  const [aiIntelligence, setAiIntelligence] = useState("advanced_neural");
  const statsIntervalRef = useRef<NodeJS.Timeout>();

  const token = getToken();
  const user = getUser();

  useEffect(() => {
    if (user && user.is_admin) {
      setIsAdmin(true);
    }
  }, [user]);

  // Check if AI backend is healthy
  const checkAIHealth = async () => {
    try {
      const res = await fetch("http://localhost:5000/api/health");
      if (res.ok) {
        console.log("Neosilix AI Backend Connected");
        toast.success("Neosilix AI Backend Connected Successfully");
        return true;
      } else {
        throw new Error(`HTTP ${res.status}`);
      }
    } catch (error) {
      console.error("AI backend not reachable:", error);
      toast.error("Neosilix AI Backend Unavailable - Start Flask with: python app.py");
      return false;
    }
  };

  const sendMessage = async (message: string) => {
    if (!message.trim()) return;

    const userMessage = {
      id: Date.now().toString(),
      role: "user" as const,
      content: message,
      timestamp: new Date(),
    };

    setChatMessages(prev => [...prev, userMessage]);
    setChatInput("");
    setIsLoading(true);

    try {
      const currentToken = getToken();
      
      if (!currentToken) {
        throw new Error("No authentication token found. Please log in again.");
      }

      console.log("Sending AI request:", message);

      const response = await fetch("http://localhost:5000/api/ask-anything", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          Authorization: `Bearer ${currentToken}`
        },
        body: JSON.stringify({ question: message }),
      });

      console.log("Response status:", response.status);

      if (!response.ok) {
        const errorText = await response.text();
        console.error("Server error:", errorText);
        
        if (response.status === 401) {
          throw new Error("Authentication failed. Please log in again.");
        }
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const data = await response.json();
      console.log("AI Response:", data);

      const assistantMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant" as const,
        content: data.response || data.message || "I've processed your request. How can I assist you further?",
        timestamp: new Date(),
        intelligence_level: data.intelligence_level || data.method || "advanced_neural",
        confidence: data.confidence || 0.9,
        question_type: data.question_type,
        system_health: data.system_health,
        recommendations: data.recommendations,
        predicted_issues: data.predicted_issues,
        targets_analysis: data.targets_analysis,
        user_id: data.user_id
      };

      setChatMessages(prev => [...prev, assistantMessage]);
      setAiIntelligence(data.intelligence_level || "advanced_neural");
      
      if (data.recommendations && data.recommendations.length > 0) {
        toast.success(`AI provided ${data.recommendations.length} recommendations`);
      } else if (data.question_type === 'target_creation') {
        toast.success("Target creation request processed");
      } else if (data.processing_time) {
        toast.success(`AI processed in ${data.processing_time}s`);
      } else {
        toast.success("Neosilix AI responded successfully");
      }
      
    } catch (error: any) {
      console.error("Chat error:", error);
      
      let errorMessage = "I'm experiencing connectivity issues. ";
      
      if (error.message.includes("Authentication failed") || error.message.includes("No authentication token")) {
        errorMessage = "Authentication issue. Please log in again.";
      } else if (error.message.includes('Failed to fetch')) {
        errorMessage += "Cannot reach the Neosilix AI backend. Please ensure it's running on http://localhost:5000";
      } else {
        errorMessage += `Error: ${error.message}`;
      }
      
      const errorMessageChat = {
        id: (Date.now() + 1).toString(),
        role: "assistant" as const,
        content: errorMessage,
        timestamp: new Date(),
        intelligence_level: "degraded",
        confidence: 0.3
      };
      
      setChatMessages(prev => [...prev, errorMessageChat]);
      toast.error("Failed to connect to Neosilix AI: " + error.message);
    } finally {
      setIsLoading(false);
    }
  };

  // Optimized data fetching
  const fetchStats = useCallback(async () => {
    try {
      const endpoint = isAdmin ? "/api/admin/stats" : "/api/user/stats";
      const res = await fetch(`http://localhost:5000${endpoint}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      
      if (!res.ok) throw new Error("Failed to fetch stats");
      
      const data = await res.json();
      
      setStats(data);
      setHistory(prev => {
        const newEntry = {
          timestamp: new Date().toLocaleTimeString(),
          cpu: data.cpu || 0,
          memory: data.memory || 0,
          disk: data.disk || 0,
          network_recv: (data.network_recv || 0) / 1024 / 1024,
          network_sent: (data.network_sent || 0) / 1024 / 1024,
        };
        return [...prev.slice(-29), newEntry];
      });
      setError(null);
    } catch (err) {
      console.error("Stats fetch error:", err);
      setError("Failed to fetch system metrics");
    }
  }, [token, isAdmin]);

  const fetchLogs = useCallback(async () => {
    if (!user) return;
    
    try {
      const endpoint = "/api/logs/comprehensive";
      const res = await fetch(`http://localhost:5000${endpoint}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      
      if (!res.ok) {
        const mockLogs = [
          {
            id: "1",
            message: "Neosilix AI Neural Networks initialized successfully",
            timestamp: new Date().toLocaleString(),
            level: "success"
          },
          {
            id: "2", 
            message: `Monitoring ${stats?.total_systems || 0} systems`,
            timestamp: new Date().toLocaleString(),
            level: "info"
          },
          {
            id: "3",
            message: "Ready for infrastructure analysis",
            timestamp: new Date().toLocaleString(), 
            level: "info"
          }
        ];
        setLogs(mockLogs);
        return;
      }
      
      const data = await res.json();
      setLogs(data.logs || data);
    } catch (error) {
      console.error("Failed to fetch logs:", error);
      const mockLogs = [
        {
          id: "1",
          message: "Neosilix AI Assistant Active - Neosilix Processing Online",
          timestamp: new Date().toLocaleString(),
          level: "success"
        }
      ];
      setLogs(mockLogs);
    }
  }, [token, user, stats]);

  const fetchCluster = useCallback(async () => {
    if (!isAdmin) return;
    
    try {
      const data = await fetchClusterHealth();
      setCluster(data);
    } catch {
      // Silent fail for cluster health
    }
  }, [isAdmin]);

  const fetchAllData = useCallback(async () => {
    await fetchStats();
    await fetchLogs();
    await fetchCluster();
  }, [fetchStats, fetchLogs, fetchCluster]);

  useEffect(() => {
    let isMounted = true;

    const initializeData = async () => {
      await checkAIHealth();
      await fetchAllData();
      
      if (isMounted) {
        statsIntervalRef.current = setInterval(fetchAllData, 15000);
      }
    };

    initializeData();
    
    return () => {
      isMounted = false;
      if (statsIntervalRef.current) {
        clearInterval(statsIntervalRef.current);
      }
    };
  }, [fetchAllData]);

  const handleAuth = () => {
    const token = prompt("Enter Neosilix Access Token");
    if (token) {
      setAuthToken(token);
      toast.success("Authenticated - Advanced intelligence activated");
    } else {
      toast.warning("Access token required for full processing");
    }
  };

  const handleChatToggle = () => {
    setIsChatOpen(!isChatOpen);
    if (!isChatOpen) {
      setIsChatMinimized(false);
      setIsChatExpanded(false);
    }
  };

  const handleMinimize = () => {
    setIsChatMinimized(!isChatMinimized);
    if (isChatExpanded && !isChatMinimized) {
      setIsChatExpanded(false);
    }
  };

  const handleExpand = () => {
    setIsChatExpanded(!isChatExpanded);
    if (isChatMinimized && !isChatExpanded) {
      setIsChatMinimized(false);
    }
  };

  const handleClose = () => {
    setIsChatOpen(false);
    setIsChatMinimized(false);
    setIsChatExpanded(false);
  };

  // Memoized data transformations
  const performanceData = useMemo(() => {
    return history.map((entry, index) => ({
      name: `T-${30 - index}`,
      ...entry,
      ai_trend: entry.cpu > 70 ? "high" : entry.cpu > 50 ? "medium" : "low"
    }));
  }, [history]);

  const resourceUsageData = useMemo(() => stats ? [
    { name: 'CPU', value: stats.cpu || 0, color: '#f59e0b', trend: (stats.cpu || 0) > 80 ? 'high' : 'normal' },
    { name: 'Memory', value: stats.memory || 0, color: '#ec4899', trend: (stats.memory || 0) > 85 ? 'high' : 'normal' },
    { name: 'Disk', value: stats.disk || 0, color: '#3b82f6', trend: (stats.disk || 0) > 90 ? 'high' : 'normal' },
  ] : [], [stats]);

  const systemHealthData = useMemo(() => stats ? [
    { name: 'Anomalies', value: stats.anomalies || 0, color: '#ef4444' },
    { name: 'Auto-heals', value: stats.heals_last_24h || 0, color: '#10b981' },
    { name: 'Uptime', value: stats.uptime_percentage || 0, color: '#06b6d4' },
  ] : [], [stats]);

  const getIntelligenceColor = useCallback((level: string) => {
    switch(level) {
      case 'advanced_neural': return 'from-purple-500 to-pink-500';
      case 'intelligent_analysis': return 'from-blue-500 to-cyan-500';
      case 'degraded': return 'from-gray-500 to-gray-600';
      default: return 'from-cyan-500 to-blue-500';
    }
  }, []);

  const getIntelligenceText = useCallback((level: string) => {
    switch(level) {
      case 'advanced_neural': return 'Advanced Neural Processing';
      case 'intelligent_analysis': return 'AI Intelligence Active';
      case 'degraded': return 'Basic Analysis Mode';
      default: return 'AI Processing';
    }
  }, []);

  const quickQuestions = useMemo(() => [
    "What's my current system health?",
    "Show me all monitoring targets",
    "Analyze CPU performance trends", 
    "Check for any system anomalies",
    "How's my memory usage?",
    "What infrastructure issues need attention?",
    "Add web server frontend01 192.168.1.100",
    "Create database server db-primary 192.168.1.20",
    "Monitor network device switch01 192.168.1.1",
    "Analyze my monitoring targets health"
  ], []);

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col p-6 md:p-10 overflow-hidden">
      <div className="flex flex-col items-start gap-3 mb-8">
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-4">
            <div className="relative">
              <Brain className="h-20 w-20 text-cyan-400" />
            </div>
            <div>
              <h1 className="text-4xl md:text-5xl font-extrabold bg-gradient-to-r from-cyan-400 via-purple-500 to-pink-500 bg-clip-text text-transparent select-none">
                Neosilix AI Center
              </h1>
              <p className="text-cyan-300 italic mt-1 text-sm md:text-base flex items-center gap-2">
                <Sparkles className="w-4 h-4" />
                Neosilix Infrastructure Intelligence
                <Sparkles className="w-4 h-4" />
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            {!authToken && (
              <Button
                onClick={handleAuth}
                className="bg-gradient-to-r from-green-400 to-cyan-500 text-black font-bold px-6 py-2 rounded-xl shadow-lg hover:scale-105 transition-all duration-300 hover:shadow-cyan-500/25"
              >
                <Zap className="w-4 h-4 mr-2" />
                Perform Heal Service
              </Button>
            )}
            
            <Button
              onClick={handleChatToggle}
              className={clsx(
                "bg-gradient-to-r from-purple-500 to-pink-500 text-white font-bold px-6 py-2 rounded-xl shadow-lg hover:scale-105 transition-all duration-300 flex items-center gap-2",
                isChatOpen && "ring-2 ring-purple-400 shadow-purple-500/50"
              )}
            >
              <Brain className="w-4 h-4" />
              Neosilix AI 
            </Button>
          </div>
        </div>

        {user && (
          <div className="flex items-center gap-4">
            <p className="text-cyan-300 italic text-sm md:text-base">
              Neosilix Access: <span className="font-semibold text-white">{user.name}</span>
              {isAdmin && (
                <span className="ml-2 bg-gradient-to-r from-purple-600 to-pink-600 px-3 py-1 rounded-full text-xs font-bold">
                  ADMIN ACCESS
                </span>
              )}
            </p>
            <div className="flex items-center gap-2 text-xs text-cyan-400">
              <div className="w-2 h-2 bg-green-500 rounded-full" />
              AI Intelligence: {getIntelligenceText(aiIntelligence)}
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="bg-gradient-to-r from-red-800 to-pink-800 text-red-100 font-semibold mb-8 p-4 rounded-xl shadow-inner select-none border border-red-500/30">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4" />
            {error}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8 mb-12">
        <div className="xl:col-span-2 space-y-8">
          {/* Stat Cards Section */}
          <Suspense fallback={<StatCardsFallback />}>
            <ErrorBoundary>
              <StatCardsSection stats={stats} />
            </ErrorBoundary>
          </Suspense>

          {/* Performance Charts Section */}
          <Suspense fallback={<ChartFallback />}>
            <ErrorBoundary>
              <PerformanceChartsSection performanceData={performanceData} />
            </ErrorBoundary>
          </Suspense>
        </div>

        {/* Resource Charts Section */}
        <Suspense fallback={<ResourceChartsFallback />}>
          <ErrorBoundary>
            <ResourceChartsSection
              resourceUsageData={resourceUsageData}
              systemHealthData={systemHealthData}
              cluster={cluster}
              isAdmin={isAdmin}
              stats={stats}
            />
          </ErrorBoundary>
        </Suspense>
      </div>

      {/* Chat Interface */}
      {isChatOpen && (
  <Suspense fallback={<div className="fixed bottom-4 right-4 w-96 h-[600px] bg-gray-800 rounded-2xl animate-pulse" />}>
    <ChatInterface
      isOpen={isChatOpen}
      onClose={handleClose}
      sendMessage={sendMessage}
      chatMessages={chatMessages}
      chatInput={chatInput}
      setChatInput={setChatInput}
      isLoading={isLoading}
      isChatExpanded={isChatExpanded}
      isChatMinimized={isChatMinimized}
      handleMinimize={handleMinimize}
      handleExpand={handleExpand}
      aiIntelligence={aiIntelligence}
      getIntelligenceColor={getIntelligenceColor}
      getIntelligenceText={getIntelligenceText}
      quickQuestions={quickQuestions}
    />
  </Suspense>
)}
    </div>
  );
}
