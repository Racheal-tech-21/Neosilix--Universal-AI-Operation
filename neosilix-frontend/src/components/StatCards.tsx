import React from "react";
import { Cpu, MemoryStick, HardDrive, Download, Upload, Brain } from "lucide-react";
import clsx from "clsx";

const StatCards = ({ stats }: { stats: any }) => {
  const cards = [
    {
      icon: <Cpu className="w-5 h-5" />,
      label: "CPU",
      value: stats?.cpu ?? 0,
      unit: "%",
      color: "text-yellow-400",
      bgColor: "bg-yellow-400/10",
    },
    {
      icon: <MemoryStick className="w-5 h-5" />,
      label: "Memory",
      value: stats?.memory ?? 0,
      unit: "%",
      color: "text-pink-500",
      bgColor: "bg-pink-500/10",
    },
    {
      icon: <HardDrive className="w-5 h-5" />,
      label: "Storage",
      value: stats?.disk ?? 0,
      unit: "%",
      color: "text-blue-500",
      bgColor: "bg-blue-500/10",
    },
    {
      icon: <Download className="w-5 h-5" />,
      label: "Network In",
      value: stats?.network_recv ? (stats.network_recv / 1024 / 1024).toFixed(2) : 0,
      unit: "MB/s",
      color: "text-green-400",
      bgColor: "bg-green-400/10",
    },
    {
      icon: <Upload className="w-5 h-5" />,
      label: "Network Out",
      value: stats?.network_sent ? (stats.network_sent / 1024 / 1024).toFixed(2) : 0,
      unit: "MB/s",
      color: "text-green-600",
      bgColor: "bg-green-600/10",
    },
    {
      icon: <Brain className="w-5 h-5" />,
      label: "AI Status",
      value: stats?.uptime_percentage ?? 0,
      unit: "%",
      color: "text-purple-500",
      bgColor: "bg-purple-500/10",
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {cards.map((card, idx) => (
        <div
          key={idx}
          className="bg-gray-800/50 border border-gray-700 rounded-xl p-4 hover:border-gray-600 transition-colors"
        >
          <div className="flex items-center justify-between mb-3">
            <div className={clsx("p-2 rounded-lg", card.bgColor, card.color)}>
              {card.icon}
            </div>
            <div className="text-xs px-2 py-1 bg-gray-700 rounded text-gray-300">
              Live
            </div>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-white">
              {card.value} <span className="text-lg">{card.unit}</span>
            </div>
            <div className="text-sm text-gray-400 mt-1">{card.label}</div>
          </div>
          <div className="mt-3 w-full bg-gray-700 rounded-full h-1.5">
            <div
              className={clsx("h-1.5 rounded-full transition-all duration-500", card.bgColor)}
              style={{
                width: `${Math.min(100, typeof card.value === 'number' ? card.value : parseFloat(card.value) || 0)}%`,
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
};

export default StatCards;
