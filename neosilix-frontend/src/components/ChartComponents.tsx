import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { ScrollArea } from "./ui/scroll-area";
import { Server, TerminalSquare } from "lucide-react";
import clsx from 'clsx';

interface ChartComponentsProps {
  performanceData: any[];
  stats: any;
  isAdmin: boolean;
  cluster: any[];
  logs: any[];
}

export default function ChartComponents({ 
  performanceData, 
  stats, 
  isAdmin, 
  cluster, 
  logs 
}: ChartComponentsProps) {
  const resourceUsageData = stats ? [
    { name: 'CPU', value: stats.cpu, color: '#f59e0b' },
    { name: 'Memory', value: stats.memory, color: '#ec4899' },
    { name: 'Disk', value: stats.disk, color: '#3b82f6' },
  ] : [];

  return (
    <>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="bg-gradient-to-tr from-gray-900 to-black border border-cyan-500/20 rounded-2xl p-4 ring-1 ring-cyan-400/20 hover:ring-cyan-400/40 transition-all duration-300">
          <CardHeader>
            <CardTitle className="text-lg font-semibold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent flex items-center gap-2">
              <TerminalSquare className="w-5 h-5" />
              Activity Logs
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-64 pr-4">
              <div className="space-y-3 text-sm">
                {logs.length > 0 ? (
                  logs.map((log) => (
                    <div key={log.id} className="border-b border-gray-700/50 pb-3 last:border-b-0 group hover:bg-gray-800/30 rounded-lg p-2 transition-all duration-200">
                      <div className="font-semibold text-white group-hover:text-cyan-100 transition-colors">{log.message}</div>
                      <div className="text-xs text-gray-400 mt-1">{log.timestamp}</div>
                      <div
                        className={clsx("text-xs font-semibold mt-1 inline-block px-2 py-1 rounded-lg transition-all", {
                          "bg-green-900/30 text-green-400 group-hover:bg-green-900/50": log.level === "success",
                          "bg-red-900/30 text-red-400 group-hover:bg-red-900/50": log.level === "error",
                          "bg-blue-900/30 text-blue-400 group-hover:bg-blue-900/50": log.level === "info",
                          "bg-yellow-900/30 text-yellow-400 group-hover:bg-yellow-900/50": log.level === "warning",
                        })}
                      >
                        {log.level.toUpperCase()}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-8">
                    <TerminalSquare className="w-12 h-12 text-cyan-400 mx-auto mb-3 animate-pulse" />
                    <p className="italic text-cyan-300">Initializing activity logs</p>
                  </div>
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-tr from-gray-900 to-black border border-cyan-500/20 rounded-2xl p-4 ring-1 ring-cyan-400/20 hover:ring-cyan-400/40 transition-all duration-300">
          <CardHeader>
            <CardTitle className="text-lg font-semibold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent flex items-center gap-2">
              <Server className="w-5 h-5" />
              Performance Trends
            </CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={performanceData}>
                <defs>
                  <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                <XAxis dataKey="name" stroke="#9CA3AF" fontSize={12} />
                <YAxis stroke="#9CA3AF" fontSize={12} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1F2937', 
                    border: '1px solid #374151',
                    borderRadius: '8px',
                  }}
                />
                <Area type="monotone" dataKey="cpu" stroke="#f59e0b" fill="url(#cpuGradient)" name="CPU" strokeWidth={2} />
                <Legend />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {isAdmin && cluster.length > 0 && (
        <Card className="bg-gradient-to-tr from-gray-900 to-black border border-cyan-500/20 rounded-2xl ring-1 ring-cyan-400/20 hover:ring-cyan-400/40 transition-all duration-300">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 bg-gradient-to-r from-green-400 to-cyan-400 bg-clip-text text-transparent">
              <Server className="w-5 h-5" /> Cluster Health
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {cluster.map((node, idx) => (
                <li key={idx} className="flex justify-between items-center p-3 bg-gray-800/50 rounded-xl hover:bg-gray-800/70 transition-all duration-200 group">
                  <span className="font-medium text-cyan-100 group-hover:text-white">{node.name}</span>
                  <span
                    className={clsx("px-3 py-1 rounded-full text-xs font-bold transition-all duration-300 group-hover:scale-105", {
                      "bg-gradient-to-r from-green-500 to-green-600 text-green-100": node.status === "Healthy",
                      "bg-gradient-to-r from-yellow-500 to-yellow-600 text-yellow-100": node.status === "Degraded",
                      "bg-gradient-to-r from-red-500 to-red-600 text-red-100": node.status === "Unreachable",
                    })}
                  >
                    {node.status}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </>
  );
}
