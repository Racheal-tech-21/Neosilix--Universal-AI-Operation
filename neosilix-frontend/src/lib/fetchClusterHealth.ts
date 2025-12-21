// src/lib/fetchClusterHealth.ts
export async function fetchClusterHealth() {
  const res = await fetch("/api/cluster/health");
  if (!res.ok) throw new Error("Failed to fetch cluster health");
  return res.json();
}
