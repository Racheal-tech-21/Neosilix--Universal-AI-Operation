import React from "react";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { Server } from "lucide-react";
import clsx from "clsx";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";

interface ResourceChartsSectionProps {
  resourceUsageData: any[];
  systemHealthData: any[];
  cluster: any[];
  isAdmin: boolean;
  stats: any;
}

const ResourceChartsSection = React.memo(({ 
  resourceUsageData, 
  systemHealthData, 
  cluster, 
  isAdmin,
  stats 
}: ResourceChartsSectionProps) => {
  return (
    <div className="space-y-8">
      {/* Resource Analysis */}
      <Card className="bg-gradient-to-tr from-gray-900 to-black border border-cyan-500/20 rounded-2xl p-4 ring-1 ring-cyan-400/20 hover:ring-cyan-400/40 transition-all duration-300">
        <CardHeader>
          <CardTitle className="text-lg font-semibold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
            Resource Analysis
          </CardTitle>
        </CardHeader>
        <CardContent className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={resourceUsageData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value }) => `${name}: ${value}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {resourceUsageData.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={entry.color}
                    className={clsx({
                      "opacity-80": entry.trend === 'high',
                      "opacity-60": entry.trend === 'normal'
                    })}
                  />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Health Metrics */}
      <Card className="bg-gradient-to-tr from-gray-900 to-black border border-cyan-500/20 rounded-2xl p-4 ring-1 ring-cyan-400/20 hover:ring-cyan-400/40 transition-all duration-300">
        <CardHeader>
          <CardTitle className="text-lg font-semibold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
            Health Metrics
          </CardTitle>
        </CardHeader>
        <CardContent className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={systemHealthData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" horizontal={false} opacity={0.3} />
              <XAxis type="number" stroke="#9CA3AF" fontSize={12} />
              <YAxis type="category" dataKey="name" stroke="#9CA3AF" width={80} fontSize={12} />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#1F2937', 
                  border: '1px solid #374151',
                  borderRadius: '8px'
                }}
              />
              <Bar dataKey="value" fill="#8884d8" radius={[0, 4, 4, 0]}>
                {systemHealthData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Cluster Health */}
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
                      "bg-gradient-to-r from-green-500 to-green-600 text-green-100 shadow-lg shadow-green-500/25": node.status === "Healthy",
                      "bg-gradient-to-r from-yellow-500 to-yellow-600 text-yellow-100 shadow-lg shadow-yellow-500/25": node.status === "Degraded",
                      "bg-gradient-to-r from-red-500 to-red-600 text-red-100 shadow-lg shadow-red-500/25": node.status === "Unreachable",
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
    </div>
  );
});

ResourceChartsSection.displayName = 'ResourceChartsSection';
export default ResourceChartsSection;
