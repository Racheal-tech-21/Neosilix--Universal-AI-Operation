'EOF'

### Access URLs:
- **Zabbix Dashboard**: http://localhost:3001
  - Username: `Admin`
  - Password: `zabbix`
- **Grafana**: http://localhost:3002
  - Username: `admin`
  - Password: `neosilix_grafana_2025`
- **Prometheus**: http://localhost:9090
- **Node Exporter**: http://localhost:9100

### Management Commands:
```bash
./manage-neosilix.sh start    # Start all services
./manage-neosilix.sh stop     # Stop all services  
./manage-neosilix.sh status   # Check status
./manage-neosilix.sh logs     # View logs
./manage-neosilix.sh restart  # Restart services

