#!/bin/bash
echo "🎯 Neosilix AI Ops - Management System"
echo "======================================"

case "$1" in
    dummy)
        echo "🚀 Starting in DUMMY mode (Demo/Presentation)"
        cd api
        export MONITORING_MODE=dummy
        export DUMMY_SCENARIO=normal_operations
        ../start-monitoring.sh
        sleep 10
        python3 app.py
        ;;
        
    real)
        echo "🔧 Starting in REAL mode (Production)"
        cd api
        export MONITORING_MODE=real
        ../start-monitoring.sh
        sleep 10
        python3 app.py
        ;;
        
    start-monitoring)
        echo "📊 Starting monitoring stack only"
        ./start-monitoring.sh
        ;;
        
    stop-monitoring)
        echo "🛑 Stopping monitoring stack"
        docker-compose -f docker-compose.monitoring.yml down
        ;;
        
    status)
        echo "🔍 System Status"
        echo "----------------"
        echo "Monitoring Stack:"
        docker-compose -f docker-compose.monitoring.yml ps
        echo ""
        echo "Flask App:"
        pgrep -f "python3 app.py" && echo "✅ Running" || echo "❌ Stopped"
        ;;
        
    logs)
        echo "📋 Showing logs (Ctrl+C to exit)"
        docker-compose -f docker-compose.monitoring.yml logs -f
        ;;
        
    switch-scenario)
        SCENARIO=${2:-normal_operations}
        echo "🔄 Switching to scenario: $SCENARIO"
        curl -X POST "http://localhost:5000/api/monitoring/switch-scenario/$SCENARIO" 2>/dev/null || echo "⚠️  Flask app not running"
        ;;
        
    config)
        echo "⚙️  Current Configuration"
        echo "-----------------------"
        echo "Mode: $MONITORING_MODE"
        echo "Scenario: $DUMMY_SCENARIO"
        echo ""
        echo "Available Scenarios:"
        echo "  normal_operations, registration_peak, exam_period, security_incident, system_maintenance"
        ;;
        
    *)
        echo "Usage: $0 {dummy|real|start-monitoring|stop-monitoring|status|logs|switch-scenario|config}"
        echo ""
        echo "Modes:"
        echo "  dummy           - Start with demo data (presentations)"
        echo "  real            - Start with real monitoring data"
        echo ""
        echo "Monitoring:"
        echo "  start-monitoring - Start only monitoring stack"
        echo "  stop-monitoring  - Stop monitoring stack" 
        echo "  status          - Check system status"
        echo "  logs            - View monitoring logs"
        echo ""
        echo "Demo Controls:"
        echo "  switch-scenario <name> - Change demo scenario"
        echo "  config          - Show current configuration"
        echo ""
        echo "🌐 Access URLs:"
        echo "  Flask App:      http://localhost:5000"
        echo "  Grafana:        http://localhost:3002 (admin/neosilix_grafana_2025)"
        echo "  Zabbix:         http://localhost:3001 (Admin/zabbix)"
        echo "  Prometheus:     http://localhost:9090"
        exit 1
        ;;
esac
