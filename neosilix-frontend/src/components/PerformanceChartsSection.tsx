import React from "react";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { CpuIcon, Network } from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from "recharts";

interface PerformanceChartsSectionProps {
  performanceData: any[];
}

// Error Boundary for charts
class ChartErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-4 bg-red-900/20 border border-red-500/30 rounded-lg text-red-200">
          <p>Chart rendering error. Data is still being processed.</p>
        </div>
      );
    }
    return this.props.children;
  }
}

const PerformanceChartsSection = React.memo(({ performanceData }: PerformanceChartsSectionProps) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Performance Chart */}
      <Card className="bg-gradient-to-tr from-gray-900 to-black border border-cyan-500/20 rounded-2xl p-4 ring-1 ring-cyan-400/20 hover:ring-cyan-400/40 transition-all duration-300">
        <CardHeader>
          <CardTitle className="text-lg font-semibold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent flex items-center gap-2">
            <CpuIcon className="w-5 h-5" />
            Performance Trends
          </CardTitle>
        </CardHeader>
        <CardContent className="h-80">
          <ChartErrorBoundary>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={performanceData}>
                <defs>
                  <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="memoryGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ec4899" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#ec4899" stopOpacity={0}/>
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
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.5)'
                  }}
                />
                <Area type="monotone" dataKey="cpu" stroke="#f59e0b" fill="url(#cpuGradient)" name="CPU" strokeWidth={2} />
                <Area type="monotone" dataKey="memory" stroke="#ec4899" fill="url(#memoryGradient)" name="Memory" strokeWidth={2} />
                <Legend />
              </AreaChart>
            </ResponsiveContainer>
          </ChartErrorBoundary>
        </CardContent>
      </Card>

      {/* Network Chart */}
      <Card className="bg-gradient-to-tr from-gray-900 to-black border border-cyan-500/20 rounded-2xl p-4 ring-1 ring-cyan-400/20 hover:ring-cyan-400/40 transition-all duration-300">
        <CardHeader>
          <CardTitle className="text-lg font-semibold bg-gradient-to-r from-green-400 to-blue-400 bg-clip-text text-transparent flex items-center gap-2">
            <Network className="w-5 h-5" />
            Network Usage
          </CardTitle>
        </CardHeader>
        <CardContent className="h-80">
          <ChartErrorBoundary>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={performanceData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                <XAxis dataKey="name" stroke="#9CA3AF" fontSize={12} />
                <YAxis stroke="#9CA3AF" fontSize={12} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1F2937', 
                    border: '1px solid #374151',
                    borderRadius: '8px'
                  }}
                />
                <Bar dataKey="network_recv" fill="#10b981" name="Received" radius={[4, 4, 0, 0]} />
                <Bar dataKey="network_sent" fill="#3b82f6" name="Sent" radius={[4, 4, 0, 0]} />
                <Legend />
              </BarChart>
            </ResponsiveContainer>
          </ChartErrorBoundary>
        </CardContent>
      </Card>
    </div>
  );
});

PerformanceChartsSection.displayName = 'PerformanceChartsSection';
export default PerformanceChartsSection;
