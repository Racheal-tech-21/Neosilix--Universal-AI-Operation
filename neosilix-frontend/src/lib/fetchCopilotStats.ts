// src/lib/fetchCopilotStats.ts

export async function fetchCopilotStats() {
  const res = await fetch("/api/stats");
  if (!res.ok) {
    throw new Error("Failed to fetch stats");
  }
  const data = await res.json();

  // Transform into [{ name, value }] format for frontend safely
  const formattedStats = Object.entries(data)
    .filter(([key]) => ["cpu", "memory", "disk", "network"].includes(key))
    .map(([key, value]) => {
      const num = Number(value); // parse as number
      return {
        name: key,
        value: isNaN(num) ? 0 : parseFloat(num.toFixed(2))
      };
    });

  return formattedStats;
}

export async function fetchCopilotLogs() {
  try {
    const response = await fetch("/api/copilot/logs");
    if (!response.ok) throw new Error("Failed to fetch logs");
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Failed to fetch copilot logs:", error);
    return [];
  }
}
