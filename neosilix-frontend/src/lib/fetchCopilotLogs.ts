export async function fetchCopilotLogs(user?: any, token?: string) {
  if (!user) return [];

  const url = user.is_admin
    ? "/api/copilot/logs"
    : `/api/user-copilot-logs/${user.id}`;

  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!res.ok) throw new Error("Failed to fetch logs");

  const data = await res.json();

  // Sort logs by timestamp descending
  const sortedLogs = data.sort(
    (a: any, b: any) =>
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  // Normalize log format
  return sortedLogs.map((log: any, index: number) => ({
    id: `${log.timestamp}-${index}`,
    timestamp: log.timestamp ?? new Date().toISOString(),
    message: log.message ?? "No message",
    level: log.level ?? "info",
  }));
}
