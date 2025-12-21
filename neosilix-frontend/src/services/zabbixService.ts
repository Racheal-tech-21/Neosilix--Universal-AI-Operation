export interface ZabbixHost {
  hostid: string;
  host: string;
  name: string;
  status: string;
  interfaces: Array<{
    ip: string;
    port: string;
    type: string;
  }>;
  groups: Array<{
    name: string;
  }>;
}

export interface ZabbixMetric {
  itemid: string;
  name: string;
  key_: string;
  lastvalue: string;
  units: string;
  lastclock: string;
}

export interface ZabbixProblem {
  eventid: string;
  source: string;
  object: string;
  objectid: string;
  clock: string;
  ns: string;
  r_eventid: string;
  r_clock: string;
  r_ns: string;
  correlationid: string;
  userid: string;
  name: string;
  acknowledged: string;
  severity: string;
}

// Update this token with your actual Zabbix API token
const ZABBIX_API_URL = 'http://localhost/api_jsonrpc.php';
const ZABBIX_AUTH_TOKEN = 'cc21e75efea06b4dd2ed6bdf310c795b';

class ZabbixService {
  private async apiCall(method: string, params: any = {}) {
    try {
      const response = await fetch(ZABBIX_API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          jsonrpc: '2.0',
          method: method,
          params: params,
          id: 1,
          auth: ZABBIX_AUTH_TOKEN
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.error) {
        throw new Error(`Zabbix API error: ${data.error.message}`);
      }
      
      return data.result;
    } catch (error) {
      console.error('Zabbix API Error:', error);
      throw error;
    }
  }

  // Get all monitored hosts
  async getHosts(): Promise<ZabbixHost[]> {
    return this.apiCall('host.get', {
      output: ['hostid', 'host', 'name', 'status'],
      selectInterfaces: ['ip', 'port', 'type'],
      selectGroups: ['name'],
      filter: {
        status: 0 // Only enabled hosts
      }
    });
  }

  // Get host metrics
  async getHostMetrics(hostid: string): Promise<ZabbixMetric[]> {
    return this.apiCall('item.get', {
      output: ['itemid', 'name', 'key_', 'lastvalue', 'units', 'lastclock'],
      hostids: hostid,
      search: {
        key_: [
          'system.cpu.util',
          'vm.memory.size[pavailable]',
          'vfs.fs.size[/,pused]',
          'net.if.in[eth0]',
          'net.if.out[eth0]',
          'system.uptime',
          'system.num.proc'
        ]
      },
      sortfield: 'name'
    });
  }

  // Get problems/alerts
  async getProblems(): Promise<ZabbixProblem[]> {
    return this.apiCall('problem.get', {
      output: 'extend',
      selectAcknowledges: 'extend',
      selectTags: 'extend',
      recent: true,
      sortfield: ['eventid'],
      sortorder: 'DESC'
    });
  }

  // Get all metrics for all hosts
  async getAllMetrics(): Promise<{ [hostid: string]: ZabbixMetric[] }> {
    const hosts = await this.getHosts();
    const metrics: { [hostid: string]: ZabbixMetric[] } = {};
    
    // Get metrics for each host with error handling
    for (const host of hosts) {
      try {
        metrics[host.hostid] = await this.getHostMetrics(host.hostid);
      } catch (error) {
        console.error(`Failed to get metrics for host ${host.name}:`, error);
        metrics[host.hostid] = [];
      }
    }
    
    return metrics;
  }

  // Test API connection
  async testConnection(): Promise<boolean> {
    try {
      await this.apiCall('apiinfo.version', {});
      return true;
    } catch (error) {
      console.error('Zabbix connection test failed:', error);
      return false;
    }
  }
}

export const zabbixService = new ZabbixService();
