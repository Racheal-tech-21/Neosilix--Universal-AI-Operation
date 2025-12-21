import React from "react";
import { Card } from "./ui/card";
import { Cpu, MemoryStick, HardDrive, Download, Upload, Brain } from "lucide-react";
import clsx from "clsx";

interface StatCardsSectionProps {
  stats: any;
}

const StatCardsSection = React.memo(({ stats }: StatCardsSectionProps) => {
  const statCards = [
    {
      icon: <Cpu className="w-7 h-7 text-yellow-400" />,
      label: "CPU Intelligence",
      value: stats?.cpu ?? 0,
      unit: "%",
      color: "text-yellow-400",
      ai_insight: stats?.cpu && stats.cpu > 80 ? "High Load" : stats?.cpu && stats.cpu > 60 ? "Moderate" : "Optimal"
    },
    {
      icon: <MemoryStick className="w-7 h-7 text-pink-500" />,
      label: "Memory Analysis",
      value: stats?.memory ?? 0,
      unit: "%",
      color: "text-pink-500",
      ai_insight: stats?.memory && stats.memory > 85 ? "Critical" : stats?.memory && stats.memory > 70 ? "Watch" : "Stable"
    },
    {
      icon: <HardDrive className="w-7 h-7 text-blue-500" />,
      label: "Storage AI",
      value: stats?.disk ?? 0,
      unit: "%",
      color: "text-blue-500",
      ai_insight: stats?.disk && stats.disk > 90 ? "Full" : stats?.disk && stats.disk > 80 ? "Limited" : "Healthy"
    },
    {
      icon: <Download className="w-7 h-7 text-green-400" />,
      label: "Network In",
      value: stats?.network_recv ? (stats.network_recv / 1024 / 1024).toFixed(2) : 0,
      unit: "MB/s",
      color: "text-green-400",
      ai_insight: "Optimal Flow"
    },
    {
      icon: <Upload className="w-7 h-7 text-green-600" />,
      label: "Network Out",
      value: stats?.network_sent ? (stats.network_sent / 1024 / 1024).toFixed(2) : 0,
      unit: "MB/s",
      color: "text-green-600",
      ai_insight: "Balanced"
    },
    {
      icon: <Brain className="w-7 h-7 text-purple-500" />,
      label: "AI Processing",
      value: stats?.uptime_percentage ?? 0,
      unit: "%",
      color: "text-purple-500",
      ai_insight: "Neural Active"
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {statCards.map(({ icon, label, value, unit, color, ai_insight }, idx) => (
        <Card
          key={idx}
          className="bg-gradient-to-tr from-gray-800 via-gray-900 to-black border border-cyan-500/20 rounded-2xl shadow-2xl hover:shadow-cyan-500/10 transition-all duration-300 cursor-default select-none p-5 flex flex-col space-y-3 ring-1 ring-cyan-400/20 hover:ring-cyan-400/40 group"
        >
          <div className="flex items-center justify-between">
            <div className={clsx("p-2 rounded-xl bg-gray-800/50", color)}>
              {icon}
            </div>
            <div className="text-xs font-mono px-2 py-1 bg-gray-800 rounded-lg text-cyan-300">
              {ai_insight}
            </div>
          </div>
          <div className="flex-1">
            <p className="text-sm text-gray-400 tracking-wide">{label}</p>
            <h2 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
              {typeof value === 'number' ? value.toFixed(2) : value} {unit}
            </h2>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-1">
            <div 
              className={clsx(
                "h-1 rounded-full transition-all duration-500",
                color.replace('text-', 'bg-')
              )}
              style={{ width: `${Math.min(100, typeof value === 'number' ? value : 0)}%` }}
            />
          </div>
        </Card>
      ))}
    </div>
  );
});

StatCardsSection.displayName = 'StatCardsSection';
export default StatCardsSection;
