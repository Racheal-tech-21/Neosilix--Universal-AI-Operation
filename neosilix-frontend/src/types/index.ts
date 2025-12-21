export interface Stats {
  cpu: number;
  memory: number;
  disk: number;
  network_recv: number;
  network_sent: number;
  uptime_percentage: number;
  total_systems: number;
  anomalies: number;
  heals_last_24h: number;
  ai_engine_status: string;
  total_users?: number;
  total_websites?: number;
  system_uptime?: number;
  user_websites?: number;
  user_anomalies?: number;
  processes?: number;
  uptime?: number;
}

export interface ClusterNode {
  name: string;
  status: "Healthy" | "Degraded" | "Unreachable";
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  intelligence_level?: string;
  confidence?: number;
  question_type?: string;
  system_health?: number;
  recommendations?: any[];
  predicted_issues?: any[];
  targets_analysis?: any;
  user_id?: string;
}

export interface SystemLog {
  id: string;
  message: string;
  timestamp: string;
  level: "success" | "error" | "info" | "warning";
}
