import { useEffect, useState } from "react";
import { fetchCopilotStats } from "../lib/fetchCopilotStats";
import {
  AlertTriangle,
  Activity,
  ShieldCheck,
  Loader,
  BrainCog,
  CheckCircle2,
} from "lucide-react";

export default function CopilotInsights() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const result = await fetchCopilotStats();
        setData(result);
      } catch (err) {
        console.error("Failed to fetch metrics:", err);
      } finally {
        setLoading(false);
      }
    }

    loadData();
    const interval = setInterval(loadData, 10000); // auto-refresh every 10s
    return () => clearInterval(interval);
  }, []);

  if (loading || !data) {
    return (
      <div className="p-6 bg-zinc-900 text-white rounded-2xl shadow-xl animate-pulse flex items-center gap-4">
        <Loader className="animate-spin" /> Loading Copilot Insights...
      </div>
    );
  }

  const {
    anomaly_count,
    healed_count,
    overall_health_score,
    ai_confidence,
    last_decision_reason,
  } = data;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-6">
      <div className="bg-zinc-900 text-white rounded-2xl p-6 shadow-lg border border-zinc-700">
        <div className="flex items-center gap-3 text-yellow-400">
          <AlertTriangle className="w-6 h-6" />
          <span className="text-lg font-semibold">Anomalies Detected</span>
        </div>
        <p className="mt-2 text-3xl font-bold">{anomaly_count}</p>
      </div>

      <div className="bg-zinc-900 text-white rounded-2xl p-6 shadow-lg border border-zinc-700">
        <div className="flex items-center gap-3 text-green-400">
          <ShieldCheck className="w-6 h-6" />
          <span className="text-lg font-semibold">Healing Actions</span>
        </div>
        <p className="mt-2 text-3xl font-bold">{healed_count}</p>
      </div>

      <div className="bg-zinc-900 text-white rounded-2xl p-6 shadow-lg border border-zinc-700">
        <div className="flex items-center gap-3 text-blue-400">
          <Activity className="w-6 h-6" />
          <span className="text-lg font-semibold">Health Score</span>
        </div>
        <p className="mt-2 text-3xl font-bold">{overall_health_score}%</p>
      </div>

      <div className="bg-zinc-900 text-white rounded-2xl p-6 shadow-lg border border-zinc-700">
        <div className="flex items-center gap-3 text-cyan-400">
          <BrainCog className="w-6 h-6" />
          <span className="text-lg font-semibold">AI Confidence</span>
        </div>
        <p className="mt-2 text-3xl font-bold">{ai_confidence}%</p>
      </div>

      <div className="col-span-full bg-zinc-950 text-white rounded-2xl p-6 shadow-xl border border-zinc-700">
        <div className="flex items-center gap-3 text-purple-400">
          <CheckCircle2 className="w-6 h-6" />
          <span className="text-lg font-semibold">Last Decision Reason</span>
        </div>
        <p className="mt-4 text-base text-zinc-300 italic">
          {last_decision_reason || "AI has not made a decision yet."}
        </p>
      </div>
    </div>
  );
}
