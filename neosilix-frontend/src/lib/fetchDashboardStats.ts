export async function fetchDashboardStats() {
  try {
    const token = localStorage.getItem("token");
    const res = await fetch("/api/stats", {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error(`Failed to fetch dashboard stats: ${res.status}`);
    const data = await res.json();

    return {
      uptime_percentage: data.uptime_percentage ?? 0,
      total_systems: data.total_systems ?? 0,
      anomalies: data.anomalies ?? 0,
      heals_last_24h: data.heals_last_24h ?? 0,
      critical_alerts: data.critical_alerts ?? 0,
      ai_engine_status: data.ai_engine_status ?? "unknown",
      infra: data.infra ?? {
        cpu: data.cpu ?? 0,
        memory: data.memory ?? 0,
        disk: data.disk ?? 0,
        network_recv: data.network_recv ?? 0,
        network_sent: data.network_sent ?? 0,
      },
    };
  } catch (err) {
    console.error("Error fetching dashboard stats:", err);
    return null;
  }
}
