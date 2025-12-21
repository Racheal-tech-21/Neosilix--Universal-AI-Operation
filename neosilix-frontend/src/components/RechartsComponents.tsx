import React from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
} from "recharts";

// Performance Line Chart
export const PerformanceChart = React.memo(({ data }: { data: any[] }) => {
  if (!data.length) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        No data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
        <XAxis 
          dataKey="name" 
          stroke="#9CA3AF" 
          fontSize={11}
          tick={{ fill: '#9CA3AF' }}
        />
        <YAxis 
          stroke="#9CA3AF" 
          fontSize={11}
          tick={{ fill: '#9CA3AF' }}
          domain={[0, 100]}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1F2937',
            border: '1px solid #374151',
            borderRadius: '6px',
          }}
          labelStyle={{ color: '#D1D5DB' }}
        />
        <Legend />
        <Line
          type="monotone"
          dataKey="cpu"
          stroke="#f59e0b"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
          name="CPU %"
        />
        <Line
          type="monotone"
          dataKey="memory"
          stroke="#ec4899"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
          name="Memory %"
        />
      </LineChart>
    </ResponsiveContainer>
  );
});

// Network Bar Chart
export const NetworkChart = React.memo(({ data }: { data: any[] }) => {
  if (!data.length) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        No data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
        <XAxis 
          dataKey="name" 
          stroke="#9CA3AF" 
          fontSize={11}
          tick={{ fill: '#9CA3AF' }}
        />
        <YAxis 
          stroke="#9CA3AF" 
          fontSize={11}
          tick={{ fill: '#9CA3AF' }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1F2937',
            border: '1px solid #374151',
            borderRadius: '6px',
          }}
          formatter={(value) => [`${Number(value).toFixed(2)} MB/s`, '']}
        />
        <Legend />
        <Bar
          dataKey="received"
          fill="#10b981"
          name="Received"
          radius={[4, 4, 0, 0]}
          maxBarSize={30}
        />
        <Bar
          dataKey="sent"
          fill="#3b82f6"
          name="Sent"
          radius={[4, 4, 0, 0]}
          maxBarSize={30}
        />
      </BarChart>
    </ResponsiveContainer>
  );
});

// Resource Pie Chart
export const ResourceChart = React.memo(({ data }: { data: any[] }) => {
  if (!data.length) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        No data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={(entry) => `${entry.name}: ${entry.value}%`}
          outerRadius={80}
          fill="#8884d8"
          dataKey="value"
          paddingAngle={2}
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            backgroundColor: '#1F2937',
            border: '1px solid #374151',
            borderRadius: '6px',
          }}
          formatter={(value) => [`${value}%`, 'Usage']}
        />
      </PieChart>
    </ResponsiveContainer>
  );
});

// Health Bar Chart
export const HealthChart = React.memo(({ data }: { data: any[] }) => {
  if (!data.length) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        No data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" horizontal={false} opacity={0.3} />
        <XAxis 
          type="number" 
          stroke="#9CA3AF" 
          fontSize={11}
          tick={{ fill: '#9CA3AF' }}
        />
        <YAxis 
          type="category" 
          dataKey="name" 
          stroke="#9CA3AF" 
          width={80}
          fontSize={11}
          tick={{ fill: '#9CA3AF' }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1F2937',
            border: '1px solid #374151',
            borderRadius: '6px',
          }}
        />
        <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={40}>
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
});

// Default export with named exports
export default {
  PerformanceChart,
  NetworkChart,
  ResourceChart,
  HealthChart,
};
