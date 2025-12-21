import { useState, useEffect } from 'react';
import { zabbixService, ZabbixHost, ZabbixMetric, ZabbixProblem } from '../services/zabbixService';

interface MonitoringData {
  hosts: ZabbixHost[];
  metrics: { [hostid: string]: ZabbixMetric[] };
  problems: ZabbixProblem[];
  loading: boolean;
  error: string | null;
}

export const useZabbixMonitoring = (refreshInterval = 30000): MonitoringData => {
  const [data, setData] = useState<MonitoringData>({
    hosts: [],
    metrics: {},
    problems: [],
    loading: true,
    error: null
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        setData(prev => ({ ...prev, loading: true, error: null }));
        
        const [hosts, problems, metrics] = await Promise.all([
          zabbixService.getHosts(),
          zabbixService.getProblems(),
          zabbixService.getAllMetrics()
        ]);
        
        setData({
          hosts,
          metrics,
          problems,
          loading: false,
          error: null
        });
      } catch (err) {
        console.error('Monitoring data fetch error:', err);
        setData(prev => ({
          ...prev,
          loading: false,
          error: err instanceof Error ? err.message : 'Failed to fetch monitoring data'
        }));
      }
    };

    fetchData();
    const interval = setInterval(fetchData, refreshInterval);
    
    return () => clearInterval(interval);
  }, [refreshInterval]);

  return data;
};

export type { ZabbixHost, ZabbixMetric, ZabbixProblem };
