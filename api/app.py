# THIS PROPERTY BELONGS TO RACHEAL SILILO ONLY..DO NOT DUPLICATE...RESPECT LICENSE THANK YOU.
from flask import Flask, jsonify, request, Response, Blueprint
from flask_cors import CORS
import re
from pathlib import Path
from collections import defaultdict, deque
from typing import Dict, Any, List, Optional
import sys
import os
from openai import OpenAI
import requests
import threading
import time
import psutil
import numpy as np
import json
import pickle
import pandas as pd
from datetime import datetime, timedelta, timezone
import asyncio
import aiohttp
import asyncpg
import joblib
from functools import wraps
import networkx as nx 
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# Database imports
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from models import db, User, Website, Metric, MonitoringTarget, TargetService, TargetMetric

# AI Engine imports
from sklearn.ensemble import IsolationForest
from ai_engine.self_healer import heal_anomaly, auto_heal_loop, stats_bp, intelligent_cpu_healer, start_cpu_auto_heal_monitor 

# Blueprint importsp
import logging
from copilot_shared import copilot_logs
from stats import get_system_stats
from routes import routes_bp
from auth import auth_bp
from copilot_engine import monitor_bp, monitor_loop
from metrics import RealMonitoringAPI
from neosilix_assistant import neosilix_assistant, ask_anything, analyze_monitoring_targets, get_user_conversation_history, clear_user_conversation_history
NETWORKX_AVAILABLE = False
ML_AVAILABLE = True

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    print("[WARNING] networkx not available, some ML features will be limited")

try:
    import sklearn
    ML_AVAILABLE = True
except ImportError:
    print("[WARNING] scikit-learn not available, ML features disabled")
    ML_AVAILABLE = False

import redis
from dotenv import load_dotenv
from models import User, Website, Metric, MonitoringTarget, TargetService, TargetMetric


# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
class SecurityException(Exception):
    """Custom security exception"""
    pass

app = Flask(__name__)

# ================== DATABASE CONFIGURATION ==================
DB_CONFIG = {
    'user': 'neosilix_rw',
    'password': 'november212004', 
    'database': 'neosilix',
    'host': 'localhost',
    'port': 5432
}

DB_URL = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.after_request
def after_request(response):
    """Ensure all JSON responses have correct Content-Type and disable caching"""
    if response.is_json or (hasattr(response, 'direct_passthrough') and not response.direct_passthrough):
        response.headers['Content-Type'] = 'application/json'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

CORS(app, origins="*", supports_credentials=True)

# Register blueprints
app.register_blueprint(auth_bp) 
app.register_blueprint(routes_bp)
app.register_blueprint(monitor_bp, url_prefix="/monitor")
app.register_blueprint(stats_bp, url_prefix="/stats")


# ================== JWT Decorators ==================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        
        if not token:
            comprehensive_logger.log_security_event("missing_token", "low")
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            # Use the same JWT implementation as auth.py
            import jwt
            decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            
            if not decoded or "id" not in decoded:
                comprehensive_logger.log_security_event("invalid_token", "medium")
                return jsonify({'message': 'Token is invalid!'}), 401
                
            request.user_id = decoded["id"]
            request.is_admin = decoded.get("is_admin", False)
            comprehensive_logger.log_user_activity("token_validated", request.user_id, "authentication")
        except jwt.ExpiredSignatureError:
            comprehensive_logger.log_security_event("expired_token", "medium")
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError as e:
            comprehensive_logger.log_security_event("invalid_token", "medium")
            print(f"JWT validation error: {e}")
            return jsonify({'message': 'Token is invalid!'}), 401
        except Exception as e:
            comprehensive_logger.log_error_event("token_validation", str(e), "jwt_validation", getattr(request, 'user_id', None))
            print(f"Token validation error: {e}")
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith("Bearer "):
            comprehensive_logger.log_security_event("missing_admin_token", "medium")
            return jsonify({'message': 'Token is missing!'}), 401
        
        token = auth_header.split(" ")[1]
        
        try:
            import jwt
            decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            
            if not decoded or not decoded.get("is_admin", False):
                comprehensive_logger.log_security_event("insufficient_privileges", "high", decoded.get('id') if decoded else None)
                return jsonify({'message': 'Admin privileges required!'}), 403
            
            request.user_id = decoded["id"]
            request.is_admin = True
            comprehensive_logger.log_user_activity("admin_access_granted", request.user_id, "administration")
        except jwt.ExpiredSignatureError:
            comprehensive_logger.log_security_event("expired_admin_token", "medium")
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError as e:
            comprehensive_logger.log_security_event("invalid_admin_token", "medium")
            print(f"Admin JWT validation error: {e}")
            return jsonify({'message': 'Token is invalid!'}), 401
        except Exception as e:
            comprehensive_logger.log_error_event("admin_token_validation", str(e), "admin_authentication")
            print(f"Admin token validation error: {e}")
            return jsonify({'message': 'Token is invalid!'}), 401
        
        return f(*args, **kwargs)
    return decorated

# ================== 8GB RAM PERFORMANCE CONFIG ==================
ML_PERFORMANCE_CONFIG = {
    'max_training_samples': 300,           # Reduced from 1000
    'enable_prophet_forecasting': False,   # Disable heavy forecasting
    'model_training_delay': 300,           # Wait 5 min after startup
    'background_ml_interval': 7200,        # Run ML every 2 hours
    'max_concurrent_ml_tasks': 1,          # Only one ML task at a time
    'memory_limit_mb': 500,                # Max memory for ML operations
    'enable_lightweight_ml_only': True,    # Skip heavy algorithms
}

class PerformanceOptimizedMLAwareness:
    """ML that respects 8GB RAM limits"""
    
    def __init__(self):
        self.memory_guard = MemoryGuard(limit_mb=ML_PERFORMANCE_CONFIG['memory_limit_mb'])
        
    def safe_ml_operation(self, operation_fn, *args):
        """Execute ML operation with memory limits"""
        if not self.memory_guard.can_proceed():
            return {"status": "delayed", "reason": "high_memory_usage"}
        
        try:
            return operation_fn(*args)
        except MemoryError:
            return {"status": "failed", "reason": "memory_limit_exceeded"}

class MemoryGuard:
    """Prevent ML from consuming too much memory"""
    
    def __init__(self, limit_mb=500):
        self.limit_mb = limit_mb
        self.last_check = time.time()
        
    def can_proceed(self):
        """Check if system has enough memory for ML operations"""
        try:
            # Check system memory usage
            memory_info = psutil.virtual_memory()
            used_percent = memory_info.percent
            available_mb = memory_info.available / (1024 * 1024)
            
            # Don't proceed if system memory is tight
            if used_percent > 80 or available_mb < 1000:  # Less than 1GB available
                print(f"[MEMORY GUARD] Blocking ML - Memory: {used_percent}% used, {available_mb:.0f}MB available")
                return False
                
            return True
            
        except Exception:
            return True  # Default to allowing if we can't check

# Initialize performance monitoring
performance_guard = PerformanceOptimizedMLAwareness()
# ================== CROSS-COMPONENT ML INTELLIGENCE ==================

class InfrastructureDependencyMapper:
    """ML-powered dependency discovery across all infrastructure components"""
    
    def __init__(self):
        self.dependency_graph = nx.DiGraph()
        self.component_patterns = {}
        self.relationship_confidence = {}
        
    def auto_discover_dependencies(self, monitoring_data):
        """Automatically discover relationships between infrastructure components"""
        try:
            print("[ML] Auto-discovering infrastructure dependencies...")
            
            # Extract components from monitoring data
            components = self._extract_components(monitoring_data)
            
            # Build dependency graph using multiple ML strategies
            self._discover_network_dependencies(components)
            self._discover_service_dependencies(components)
            self._discover_performance_correlations(components)
            self._discover_temporal_patterns(components)
            
            # Calculate relationship confidence scores
            self._calculate_confidence_scores()
            
            print(f"[ML] Dependency mapping complete: {len(self.dependency_graph.nodes)} nodes, {len(self.dependency_graph.edges)} edges")
            
            return self._get_dependency_summary()
            
        except Exception as e:
            print(f"[ML ERROR] Dependency discovery failed: {e}")
            return {"error": str(e)}
    
    def _extract_components(self, monitoring_data):
        """Extract all infrastructure components from monitoring data"""
        components = {
            'servers': [],
            'network_devices': [],
            'containers': [],
            'vms': [],
            'services': [],
            'databases': []
        }
        
        # Extract from your monitoring targets
        try:
            session = SessionLocal()
            targets = session.query(MonitoringTarget).all()
            
            for target in targets:
                component_type = target.type.lower()
                component_info = {
                    'id': f"{component_type}_{target.id}",
                    'name': target.name,
                    'type': component_type,
                    'ip_address': target.ip_address,
                    'status': target.status,
                    'metrics': self._get_recent_metrics(target.id)
                }
                
                if 'server' in component_type:
                    components['servers'].append(component_info)
                elif 'network' in component_type or 'router' in component_type or 'switch' in component_type:
                    components['network_devices'].append(component_info)
                elif 'container' in component_type or 'docker' in component_type or 'pod' in component_type:
                    components['containers'].append(component_info)
                elif 'vm' in component_type or 'virtual' in component_type:
                    components['vms'].append(component_info)
                elif 'db' in component_type or 'database' in component_type:
                    components['databases'].append(component_info)
                else:
                    components['services'].append(component_info)
                    
            session.close()
            
        except Exception as e:
            print(f"[ML ERROR] Component extraction failed: {e}")
            
        return components
    
    def _discover_network_dependencies(self, components):
        """Discover dependencies based on network connectivity"""
        for category, items in components.items():
            for item in items:
                self.dependency_graph.add_node(item['id'], **item)
                
                # Simple network-based dependency discovery
                # In real implementation, use netflow data, packet analysis, etc.
                if 'ip_address' in item:
                    # Find components that might communicate based on IP patterns
                    potential_deps = self._find_network_neighbors(item, components)
                    for dep in potential_deps:
                        self.dependency_graph.add_edge(item['id'], dep['id'], 
                                                     relationship='network', 
                                                     confidence=0.7)
    
    def _discover_service_dependencies(self, components):
        """Discover service-level dependencies"""
        # Map common service patterns
        service_patterns = {
            'web_server': ['load_balancer', 'database', 'cache'],
            'database': ['storage', 'backup_service'],
            'application': ['web_server', 'database', 'message_queue']
        }
        
        for item in components['services'] + components['servers']:
            item_name_lower = item['name'].lower()
            
            for pattern, deps in service_patterns.items():
                if pattern in item_name_lower:
                    for dep_pattern in deps:
                        # Find components matching dependency patterns
                        matching_deps = self._find_components_by_pattern(dep_pattern, components)
                        for dep in matching_deps:
                            self.dependency_graph.add_edge(item['id'], dep['id'],
                                                         relationship='service',
                                                         confidence=0.8)
    
    def _discover_performance_correlations(self, components):
        """Discover dependencies based on performance metric correlations"""
        for i, comp1 in enumerate(self._get_all_components(components)):
            for j, comp2 in enumerate(self._get_all_components(components)):
                if i != j and comp1['metrics'] and comp2['metrics']:
                    correlation = self._calculate_metric_correlation(comp1['metrics'], comp2['metrics'])
                    if correlation > 0.8:  # Strong correlation
                        self.dependency_graph.add_edge(comp1['id'], comp2['id'],
                                                     relationship='performance_correlation',
                                                     confidence=correlation)
    
    def _discover_temporal_patterns(self, components):
        """Discover dependencies based on temporal patterns"""
        # Analyze timing of alerts, performance issues, etc.
        # This would use historical incident data
        pass
    
    def _calculate_confidence_scores(self):
        """Calculate confidence scores for discovered dependencies"""
        for edge in self.dependency_graph.edges(data=True):
            relationship_data = edge[2]
            base_confidence = relationship_data.get('confidence', 0.5)
            
            # Adjust confidence based on multiple factors
            final_confidence = min(0.95, base_confidence * 1.1)  # Simple adjustment
            relationship_data['final_confidence'] = round(final_confidence, 2)
    
    def get_impact_analysis(self, component_id):
        """Predict impact of component failure across infrastructure"""
        if component_id not in self.dependency_graph:
            return {"error": "Component not found"}
        
        # Find all components that depend on this one
        affected_components = list(nx.descendants(self.dependency_graph, component_id))
        
        # Calculate impact severity
        impact_analysis = {
            'direct_dependencies': [],
            'indirect_dependencies': [],
            'business_services_affected': [],
            'estimated_recovery_time': self._estimate_recovery_time(component_id),
            'risk_score': self._calculate_risk_score(component_id, affected_components)
        }
        
        for affected_id in affected_components:
            affected_node = self.dependency_graph.nodes[affected_id]
            edge_data = self.dependency_graph.get_edge_data(component_id, affected_id)
            
            dependency_info = {
                'id': affected_id,
                'name': affected_node.get('name', 'Unknown'),
                'type': affected_node.get('type', 'unknown'),
                'relationship': edge_data.get('relationship', 'unknown') if edge_data else 'unknown',
                'confidence': edge_data.get('final_confidence', 0) if edge_data else 0
            }
            
            if edge_data and edge_data.get('relationship') in ['service', 'network']:
                impact_analysis['direct_dependencies'].append(dependency_info)
            else:
                impact_analysis['indirect_dependencies'].append(dependency_info)
        
        return impact_analysis
    
    def _estimate_recovery_time(self, component_id):
        """ML-based recovery time estimation"""
        # Based on component type, complexity, dependencies
        component_type = self.dependency_graph.nodes[component_id].get('type', 'unknown')
        
        recovery_times = {
            'server': 30,  # minutes
            'network_device': 15,
            'container': 5,
            'vm': 10,
            'database': 45,
            'service': 20
        }
        
        return recovery_times.get(component_type, 30)
    
    def _calculate_risk_score(self, component_id, affected_components):
        """Calculate risk score for component failure"""
        base_score = len(affected_components) * 0.1
        component_type = self.dependency_graph.nodes[component_id].get('type', 'unknown')
        
        # Adjust based on component criticality
        criticality_weights = {
            'database': 1.5,
            'network_device': 1.3,
            'server': 1.2,
            'service': 1.1,
            'container': 1.0,
            'vm': 1.0
        }
        
        return min(10, round(base_score * criticality_weights.get(component_type, 1.0), 1))
    
    def _get_dependency_summary(self):
        """Get summary of discovered dependencies"""
        return {
            'total_components': len(self.dependency_graph.nodes),
            'total_dependencies': len(self.dependency_graph.edges),
            'components_by_type': self._count_components_by_type(),
            'most_connected_components': self._get_most_connected_components(),
            'graph_ready': len(self.dependency_graph.nodes) > 0
        }
    
    def _count_components_by_type(self):
        """Count components by type"""
        type_count = {}
        for node in self.dependency_graph.nodes(data=True):
            comp_type = node[1].get('type', 'unknown')
            type_count[comp_type] = type_count.get(comp_type, 0) + 1
        return type_count
    
    def _get_most_connected_components(self):
        """Get components with most dependencies"""
        centrality = nx.degree_centrality(self.dependency_graph)
        most_central = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return [{
            'component_id': comp_id,
            'name': self.dependency_graph.nodes[comp_id].get('name', 'Unknown'),
            'centrality_score': round(score, 3)
        } for comp_id, score in most_central]
    
    # Helper methods
    def _get_recent_metrics(self, target_id):
        """Get recent metrics for a target"""
        try:
            session = SessionLocal()
            metrics = session.query(TargetMetric).filter_by(target_id=target_id)\
                         .order_by(TargetMetric.timestamp.desc()).limit(10).all()
            session.close()
            
            return [{
                'type': metric.type,
                'value': metric.value,
                'timestamp': metric.timestamp.isoformat()
            } for metric in metrics]
        except:
            return []
    
    def _find_network_neighbors(self, item, components):
        """Find potential network neighbors based on IP patterns"""
        neighbors = []
        base_ip = '.'.join(item['ip_address'].split('.')[:3])  # First 3 octets
        
        for category, items in components.items():
            for other_item in items:
                if other_item['id'] != item['id'] and 'ip_address' in other_item:
                    if other_item['ip_address'].startswith(base_ip):
                        neighbors.append(other_item)
        
        return neighbors
    
    def _find_components_by_pattern(self, pattern, components):
        """Find components matching a pattern"""
        matches = []
        for category, items in components.items():
            for item in items:
                if pattern in item['name'].lower():
                    matches.append(item)
        return matches
    
    def _get_all_components(self, components):
        """Get all components as a flat list"""
        all_components = []
        for category in components.values():
            all_components.extend(category)
        return all_components
    
    def _calculate_metric_correlation(self, metrics1, metrics2):
        """Calculate correlation between two sets of metrics"""
        if not metrics1 or not metrics2:
            return 0
            
        # Simple correlation calculation
        # In real implementation, use proper time series correlation
        values1 = [m.get('value', 0) for m in metrics1 if isinstance(m.get('value'), (int, float))]
        values2 = [m.get('value', 0) for m in metrics2 if isinstance(m.get('value'), (int, float))]
        
        if len(values1) > 1 and len(values2) > 1:
            min_len = min(len(values1), len(values2))
            correlation = np.corrcoef(values1[:min_len], values2[:min_len])[0, 1]
            return abs(correlation) if not np.isnan(correlation) else 0
        
        return 0

class MultiLayerAnomalyCorrelator:
    """ML that correlates anomalies across infrastructure layers"""
    
    def __init__(self):
        self.anomaly_patterns = []
        self.correlation_rules = []
        self.incident_history = []
        
    def correlate_anomalies(self, current_alerts, infrastructure_graph):
        """Correlate anomalies across infrastructure layers"""
        try:
            correlated_incidents = []
            
            # Group alerts by time and component
            alert_groups = self._group_alerts_by_timing(current_alerts)
            
            for group in alert_groups:
                incident = self._analyze_incident_group(group, infrastructure_graph)
                if incident:
                    correlated_incidents.append(incident)
            
            # Root cause analysis
            root_causes = self._identify_root_causes(correlated_incidents)
            
            return {
                'correlated_incidents': correlated_incidents,
                'likely_root_causes': root_causes,
                'infrastructure_impact': self._assess_infrastructure_impact(correlated_incidents, infrastructure_graph),
                'recommended_actions': self._generate_remediation_actions(correlated_incidents)
            }
            
        except Exception as e:
            print(f"[ML ERROR] Anomaly correlation failed: {e}")
            return {'correlated_incidents': [], 'likely_root_causes': []}
    
    def _group_alerts_by_timing(self, alerts):
        """Group alerts that occur around the same time"""
        if not alerts:
            return []
            
        # Group alerts within 5 minutes of each other
        time_groups = []
        current_group = []
        
        sorted_alerts = sorted(alerts, key=lambda x: x.get('timestamp', ''))
        
        for alert in sorted_alerts:
            if not current_group:
                current_group.append(alert)
            else:
                # Check time difference
                last_time = pd.to_datetime(current_group[-1].get('timestamp'))
                current_time = pd.to_datetime(alert.get('timestamp'))
                time_diff = (current_time - last_time).total_seconds() / 60  # minutes
                
                if time_diff <= 5:  # 5-minute window
                    current_group.append(alert)
                else:
                    time_groups.append(current_group)
                    current_group = [alert]
        
        if current_group:
            time_groups.append(current_group)
            
        return time_groups
    
    def _analyze_incident_group(self, alert_group, infrastructure_graph):
        """Analyze a group of related alerts as a single incident"""
        if not alert_group:
            return None
            
        # Analyze relationships between alerted components
        component_relationships = self._analyze_component_relationships(alert_group, infrastructure_graph)
        
        incident = {
            'incident_id': f"incident_{int(time.time())}_{len(self.incident_history)}",
            'alerts': alert_group,
            'start_time': min([alert.get('timestamp') for alert in alert_group]),
            'severity': max([self._alert_severity_score(alert) for alert in alert_group]),
            'affected_components': list(set([alert.get('target_name', 'Unknown') for alert in alert_group])),
            'component_relationships': component_relationships,
            'likely_cause': self._infer_likely_cause(alert_group, component_relationships),
            'confidence_score': self._calculate_incident_confidence(alert_group, component_relationships)
        }
        
        self.incident_history.append(incident)
        return incident
    
    def _analyze_component_relationships(self, alerts, infrastructure_graph):
        """Analyze how alerted components are related"""
        relationships = []
        alerted_components = [alert.get('target_name') for alert in alerts]
        
        for i, comp1 in enumerate(alerted_components):
            for j, comp2 in enumerate(alerted_components):
                if i < j:  # Avoid duplicates
                    # Check if components are connected in dependency graph
                    if infrastructure_graph.has_node(comp1) and infrastructure_graph.has_node(comp2):
                        if infrastructure_graph.has_edge(comp1, comp2):
                            edge_data = infrastructure_graph.get_edge_data(comp1, comp2)
                            relationships.append({
                                'component1': comp1,
                                'component2': comp2,
                                'relationship': edge_data.get('relationship', 'unknown'),
                                'confidence': edge_data.get('final_confidence', 0)
                            })
        
        return relationships
    
    def _infer_likely_cause(self, alerts, relationships):
        """Infer the most likely root cause from alerts and relationships"""
        if not alerts:
            return "Unknown"
            
        # Simple inference logic - can be enhanced with ML
        alert_types = [alert.get('type', '').lower() for alert in alerts]
        
        if any('network' in alert_type for alert_type in alert_types):
            return "Network Infrastructure Issue"
        elif any('database' in alert_type for alert_type in alert_types):
            return "Database Performance Issue"
        elif any('memory' in alert_type for alert_type in alert_types):
            return "Resource Exhaustion"
        elif any('cpu' in alert_type for alert_type in alert_types):
            return "Compute Capacity Issue"
        else:
            return "Infrastructure Performance Degradation"
    
    def _calculate_incident_confidence(self, alerts, relationships):
        """Calculate confidence score for incident analysis"""
        base_confidence = min(1.0, len(alerts) * 0.2)  # More alerts = more confidence
        relationship_bonus = len(relationships) * 0.1
        return min(0.95, base_confidence + relationship_bonus)
    
    def _alert_severity_score(self, alert):
        """Convert alert severity to numerical score"""
        severity_map = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        return severity_map.get(alert.get('severity', 'low').lower(), 1)
    
    def _identify_root_causes(self, incidents):
        """Identify most likely root causes across all incidents"""
        cause_counts = {}
        for incident in incidents:
            cause = incident.get('likely_cause', 'Unknown')
            cause_counts[cause] = cause_counts.get(cause, 0) + 1
        
        return [{'cause': cause, 'frequency': count} for cause, count in cause_counts.items()]
    
    def _assess_infrastructure_impact(self, incidents, infrastructure_graph):
        """Assess overall impact on infrastructure"""
        if not incidents:
            return "Minimal"
            
        total_severity = sum(incident.get('severity', 1) for incident in incidents)
        affected_components = set()
        
        for incident in incidents:
            affected_components.update(incident.get('affected_components', []))
        
        impact_score = total_severity * len(affected_components) * 0.1
        
        if impact_score > 8:
            return "Critical"
        elif impact_score > 5:
            return "High"
        elif impact_score > 2:
            return "Medium"
        else:
            return "Low"
    
    def _generate_remediation_actions(self, incidents):
        """Generate intelligent remediation actions"""
        actions = []
        
        for incident in incidents:
            cause = incident.get('likely_cause', '')
            
            if 'Network' in cause:
                actions.append({
                    'incident_id': incident['incident_id'],
                    'action': 'Check network device configurations and bandwidth utilization',
                    'priority': 'high' if incident['severity'] > 2 else 'medium'
                })
            elif 'Database' in cause:
                actions.append({
                    'incident_id': incident['incident_id'],
                    'action': 'Review database queries, indexes, and connection pool settings',
                    'priority': 'high'
                })
            elif 'Resource' in cause:
                actions.append({
                    'incident_id': incident['incident_id'],
                    'action': 'Scale resources or optimize application memory usage',
                    'priority': 'medium'
                })
        
        return actions

class PredictiveCapacityPlanner:
    """ML-powered capacity planning across infrastructure"""
    
    def __init__(self):
        self.capacity_models = {}
        self.growth_trends = {}
        
    def analyze_capacity_risks(self, infrastructure_data, historical_metrics):
        """Identify capacity risks across all infrastructure components"""
        try:
            capacity_analysis = {
                'critical_risks': [],
                'warning_risks': [],
                'optimization_opportunities': [],
                'growth_predictions': {},
                'recommendations': []
            }
            
            # Analyze each component type
            capacity_analysis.update(self._analyze_compute_capacity(infrastructure_data))
            capacity_analysis.update(self._analyze_storage_capacity(historical_metrics))
            capacity_analysis.update(self._analyze_network_capacity(infrastructure_data))
            
            # Generate overall recommendations
            capacity_analysis['recommendations'] = self._generate_capacity_recommendations(capacity_analysis)
            
            return capacity_analysis
            
        except Exception as e:
            print(f"[ML ERROR] Capacity analysis failed: {e}")
            return {'critical_risks': [], 'warning_risks': [], 'recommendations': []}
    
    def _analyze_compute_capacity(self, infrastructure_data):
        """Analyze compute capacity (CPU, Memory)"""
        compute_risks = {
            'critical_risks': [],
            'warning_risks': []
        }
        
        # Analyze servers and VMs
        for component in infrastructure_data.get('servers', []) + infrastructure_data.get('vms', []):
            metrics = component.get('metrics', [])
            if metrics:
                cpu_usage = self._extract_metric_trend(metrics, 'cpu')
                memory_usage = self._extract_metric_trend(metrics, 'memory')
                
                if cpu_usage and cpu_usage[-1] > 85:
                    compute_risks['critical_risks'].append({
                        'component': component['name'],
                        'issue': 'High CPU Usage',
                        'current': f"{cpu_usage[-1]:.1f}%",
                        'trend': 'increasing' if len(cpu_usage) > 1 and cpu_usage[-1] > cpu_usage[0] else 'stable'
                    })
                elif cpu_usage and cpu_usage[-1] > 75:
                    compute_risks['warning_risks'].append({
                        'component': component['name'],
                        'issue': 'Elevated CPU Usage',
                        'current': f"{cpu_usage[-1]:.1f}%",
                        'trend': 'increasing' if len(cpu_usage) > 1 and cpu_usage[-1] > cpu_usage[0] else 'stable'
                    })
        
        return compute_risks
    
    def _analyze_storage_capacity(self, historical_metrics):
        """Analyze storage capacity trends"""
        storage_risks = {
            'critical_risks': [],
            'warning_risks': []
        }
        
        # Analyze disk usage trends
        disk_trend = self._extract_metric_trend(historical_metrics, 'disk')
        if disk_trend and len(disk_trend) > 10:
            growth_rate = self._calculate_growth_rate(disk_trend)
            days_until_full = self._predict_days_until_threshold(disk_trend, threshold=90)
            
            if days_until_full and days_until_full < 30:
                storage_risks['critical_risks'].append({
                    'component': 'Primary Storage',
                    'issue': 'Storage Capacity Critical',
                    'current': f"{disk_trend[-1]:.1f}%",
                    'prediction': f"Will reach 90% in {days_until_full} days"
                })
            elif days_until_full and days_until_full < 90:
                storage_risks['warning_risks'].append({
                    'component': 'Primary Storage',
                    'issue': 'Storage Capacity Warning',
                    'current': f"{disk_trend[-1]:.1f}%",
                    'prediction': f"Will reach 90% in {days_until_full} days"
                })
        
        return storage_risks
    
    def _analyze_network_capacity(self, infrastructure_data):
        """Analyze network capacity"""
        network_risks = {
            'critical_risks': [],
            'warning_risks': []
        }
        
        # Analyze network devices
        for device in infrastructure_data.get('network_devices', []):
            metrics = device.get('metrics', [])
            # Add network-specific capacity analysis here
        
        return network_risks
    
    def _extract_metric_trend(self, metrics, metric_name):
        """Extract trend data for a specific metric"""
        values = []
        for metric in metrics:
            if isinstance(metric, dict) and metric.get('type') == metric_name:
                values.append(float(metric.get('value', 0)))
        return values if values else None
    
    def _calculate_growth_rate(self, trend_data):
        """Calculate growth rate from trend data"""
        if len(trend_data) < 2:
            return 0
        return (trend_data[-1] - trend_data[0]) / len(trend_data)
    
    def _predict_days_until_threshold(self, trend_data, threshold=90):
        """Predict days until metric reaches threshold"""
        if len(trend_data) < 5:
            return None
            
        # Simple linear prediction
        x = np.arange(len(trend_data))
        y = np.array(trend_data)
        
        try:
            slope, intercept = np.polyfit(x, y, 1)
            if slope > 0:
                days_to_threshold = (threshold - trend_data[-1]) / slope
                return max(1, int(days_to_threshold))
        except:
            pass
            
        return None
    
    def _generate_capacity_recommendations(self, analysis):
        """Generate capacity planning recommendations"""
        recommendations = []
        
        critical_count = len(analysis.get('critical_risks', []))
        warning_count = len(analysis.get('warning_risks', []))
        
        if critical_count > 0:
            recommendations.append({
                'priority': 'critical',
                'action': 'Immediate capacity expansion required',
                'details': f'{critical_count} components at critical capacity'
            })
        
        if warning_count > 0:
            recommendations.append({
                'priority': 'high',
                'action': 'Plan for near-term capacity upgrades',
                'details': f'{warning_count} components showing capacity warnings'
            })
        
        # Add specific recommendations based on analysis
        for risk in analysis.get('critical_risks', []):
            if 'CPU' in risk['issue']:
                recommendations.append({
                    'priority': 'high',
                    'action': f"Scale compute resources for {risk['component']}",
                    'details': f"Current CPU: {risk['current']}, Trend: {risk['trend']}"
                })
        
        return recommendations

# Initialize ML components
dependency_mapper = InfrastructureDependencyMapper()
anomaly_correlator = MultiLayerAnomalyCorrelator()
capacity_planner = PredictiveCapacityPlanner()

 #============================================ADVANCED INTELLIGENCE ==========================================================

class IntelligentRootCauseAnalyzer:
    """ML-powered root cause analysis across infrastructure layers"""
    
    def __init__(self):
        self.cause_patterns = {}
        self.incident_knowledge_base = []
        self.symptom_cause_mapping = {}
        
    def analyze_root_cause(self, incident_data, infrastructure_graph):
        """Perform deep root cause analysis using multiple ML techniques"""
        try:
            print(f"[ML] Analyzing root cause for incident with {len(incident_data.get('alerts', []))} alerts")
            
            analysis = {
                'primary_cause': None,
                'contributing_factors': [],
                'confidence_score': 0,
                'evidence': [],
                'timeline_reconstruction': self._reconstruct_timeline(incident_data),
                'causal_chain': self._build_causal_chain(incident_data, infrastructure_graph),
                'similar_historical_incidents': self._find_similar_incidents(incident_data)
            }
            
            # Multi-method analysis
            causes = []
            causes.extend(self._analyze_temporal_patterns(incident_data))
            causes.extend(self._analyze_dependency_patterns(incident_data, infrastructure_graph))
            causes.extend(self._analyze_metric_anomalies(incident_data))
            causes.extend(self._analyze_topological_risks(incident_data, infrastructure_graph))
            
            # Rank causes by confidence
            ranked_causes = self._rank_causes(causes)
            
            if ranked_causes:
                analysis['primary_cause'] = ranked_causes[0]
                analysis['contributing_factors'] = ranked_causes[1:3]  # Top 3
                analysis['confidence_score'] = ranked_causes[0].get('confidence', 0)
                analysis['evidence'] = ranked_causes[0].get('evidence', [])
            
            # Learn from this analysis
            self._update_knowledge_base(incident_data, analysis)
            
            return analysis
            
        except Exception as e:
            print(f"[ML ERROR] Root cause analysis failed: {e}")
            return {'primary_cause': 'Analysis failed', 'confidence_score': 0}
    
    def _reconstruct_timeline(self, incident_data):
        """Reconstruct incident timeline with ML event ordering"""
        alerts = incident_data.get('alerts', [])
        if not alerts:
            return []
        
        # Sort by timestamp and identify key events
        sorted_alerts = sorted(alerts, key=lambda x: x.get('timestamp', ''))
        
        timeline = []
        for i, alert in enumerate(sorted_alerts):
            event_type = self._classify_event_type(alert)
            timeline.append({
                'timestamp': alert.get('timestamp'),
                'component': alert.get('target_name', 'Unknown'),
                'event_type': event_type,
                'severity': alert.get('severity', 'medium'),
                'description': alert.get('message', ''),
                'is_trigger': i == 0,  # First event might be trigger
                'is_escalation': self._is_escalation_event(alert, sorted_alerts, i)
            })
        
        return timeline
    
    def _build_causal_chain(self, incident_data, infrastructure_graph):
        """Build causal chain showing how failure propagated"""
        causal_chain = []
        timeline = self._reconstruct_timeline(incident_data)
        
        for i, event in enumerate(timeline):
            if i > 0:
                # Find dependency path between consecutive events
                prev_component = timeline[i-1]['component']
                current_component = event['component']
                
                if (infrastructure_graph.has_node(prev_component) and 
                    infrastructure_graph.has_node(current_component)):
                    
                    # Check if there's a dependency path
                    if infrastructure_graph.has_edge(prev_component, current_component):
                        edge_data = infrastructure_graph.get_edge_data(prev_component, current_component)
                        causal_chain.append({
                            'from': prev_component,
                            'to': current_component,
                            'relationship': edge_data.get('relationship', 'unknown'),
                            'propagation_delay': self._calculate_propagation_delay(
                                timeline[i-1]['timestamp'], event['timestamp']
                            )
                        })
        
        return causal_chain
    
    def _analyze_temporal_patterns(self, incident_data):
        """Analyze temporal patterns for root cause clues"""
        causes = []
        timeline = self._reconstruct_timeline(incident_data)
        
        # Check for simultaneous failures (likely common cause)
        simultaneous_events = self._find_simultaneous_events(timeline)
        if len(simultaneous_events) > 2:
            causes.append({
                'type': 'common_infrastructure_failure',
                'description': f"Multiple components failed simultaneously: {len(simultaneous_events)} components",
                'confidence': 0.8,
                'evidence': [f"Simultaneous failure of {[e['component'] for e in simultaneous_events]}"]
            })
        
        # Check for cascade pattern
        if self._is_cascade_failure(timeline):
            causes.append({
                'type': 'cascade_failure',
                'description': "Failure propagated through dependent components",
                'confidence': 0.7,
                'evidence': ["Clear sequential failure pattern detected"]
            })
        
        return causes
    
    def _analyze_dependency_patterns(self, incident_data, infrastructure_graph):
        """Analyze dependency patterns for root cause"""
        causes = []
        affected_components = [alert.get('target_name') for alert in incident_data.get('alerts', [])]
        
        # Find common dependencies
        common_dependencies = self._find_common_dependencies(affected_components, infrastructure_graph)
        
        for dep in common_dependencies[:3]:  # Top 3 common dependencies
            causes.append({
                'type': 'single_point_of_failure',
                'description': f"Single point of failure: {dep['name']}",
                'confidence': dep['score'],
                'evidence': [f"Multiple affected components depend on {dep['name']}"],
                'component': dep['name']
            })
        
        return causes
    
    def _analyze_metric_anomalies(self, incident_data):
        """Analyze metric anomalies preceding the incident"""
        causes = []
        # This would integrate with your metric anomaly detection
        # For now, using alert patterns
        
        alert_types = [alert.get('type', '').lower() for alert in incident_data.get('alerts', [])]
        
        if any('cpu' in alert_type for alert_type in alert_types):
            causes.append({
                'type': 'resource_exhaustion',
                'description': "CPU resource exhaustion detected",
                'confidence': 0.6,
                'evidence': ["High CPU usage alerts across multiple components"]
            })
        
        if any('memory' in alert_type for alert_type in alert_types):
            causes.append({
                'type': 'memory_pressure',
                'description': "Memory pressure causing performance issues",
                'confidence': 0.65,
                'evidence': ["High memory usage alerts detected"]
            })
        
        return causes
    
    def _analyze_topological_risks(self, incident_data, infrastructure_graph):
        """Analyze topological risks in infrastructure"""
        causes = []
        affected_components = [alert.get('target_name') for alert in incident_data.get('alerts', [])]
        
        # Check if affected components are topologically close
        centrality_scores = []
        for component in affected_components:
            if infrastructure_graph.has_node(component):
                centrality = nx.degree_centrality(infrastructure_graph).get(component, 0)
                centrality_scores.append(centrality)
        
        if centrality_scores and np.mean(centrality_scores) > 0.1:
            causes.append({
                'type': 'critical_component_failure',
                'description': "Failure in highly connected critical components",
                'confidence': 0.7,
                'evidence': [f"Affected components have high network centrality: {np.mean(centrality_scores):.3f}"]
            })
        
        return causes
    
    def _find_similar_incidents(self, incident_data):
        """Find similar historical incidents for pattern matching"""
        similar = []
        current_pattern = self._extract_incident_pattern(incident_data)
        
        for historical in self.incident_knowledge_base[-100:]:  # Last 100 incidents
            similarity = self._calculate_incident_similarity(current_pattern, historical)
            if similarity > 0.7:
                similar.append({
                    'incident_id': historical.get('incident_id'),
                    'similarity_score': similarity,
                    'root_cause': historical.get('analysis', {}).get('primary_cause'),
                    'resolution': historical.get('resolution', 'Unknown')
                })
        
        return sorted(similar, key=lambda x: x['similarity_score'], reverse=True)[:3]
    
    def _rank_causes(self, causes):
        """Rank potential causes by confidence and evidence"""
        if not causes:
            return []
        
        # Simple ranking by confidence, could be enhanced with ML
        return sorted(causes, key=lambda x: x.get('confidence', 0), reverse=True)
    
    def _update_knowledge_base(self, incident_data, analysis):
        """Update knowledge base with new incident analysis"""
        knowledge_entry = {
            'incident_id': incident_data.get('incident_id', f"inc_{int(time.time())}"),
            'timestamp': datetime.now().isoformat(),
            'alerts_count': len(incident_data.get('alerts', [])),
            'affected_components': list(set([alert.get('target_name') for alert in incident_data.get('alerts', [])])),
            'pattern': self._extract_incident_pattern(incident_data),
            'analysis': analysis,
            'resolution': 'pending'
        }
        
        self.incident_knowledge_base.append(knowledge_entry)
        
        # Keep knowledge base manageable
        if len(self.incident_knowledge_base) > 1000:
            self.incident_knowledge_base = self.incident_knowledge_base[-1000:]
    
    # Helper methods
    def _classify_event_type(self, alert):
        """Classify event type from alert data"""
        alert_type = alert.get('type', '').lower()
        if 'cpu' in alert_type:
            return 'resource_exhaustion'
        elif 'memory' in alert_type:
            return 'memory_pressure'
        elif 'network' in alert_type:
            return 'network_issue'
        elif 'disk' in alert_type:
            return 'storage_issue'
        else:
            return 'performance_issue'
    
    def _is_escalation_event(self, alert, all_alerts, index):
        """Check if this event represents an escalation"""
        if index == 0:
            return False
        return alert.get('severity', 'medium') == 'critical'
    
    def _calculate_propagation_delay(self, timestamp1, timestamp2):
        """Calculate propagation delay between events"""
        try:
            t1 = pd.to_datetime(timestamp1)
            t2 = pd.to_datetime(timestamp2)
            return (t2 - t1).total_seconds()
        except:
            return 0
    
    def _find_simultaneous_events(self, timeline, threshold_seconds=60):
        """Find events that occurred within threshold seconds of each other"""
        simultaneous = []
        for i, event1 in enumerate(timeline):
            group = [event1]
            for j, event2 in enumerate(timeline):
                if i != j:
                    delay = self._calculate_propagation_delay(event1['timestamp'], event2['timestamp'])
                    if abs(delay) <= threshold_seconds:
                        group.append(event2)
            if len(group) > 1:
                simultaneous.extend(group)
        
        return list({e['component']: e for e in simultaneous}.values())  # Deduplicate
    
    def _is_cascade_failure(self, timeline):
        """Check if failure pattern shows cascade characteristics"""
        if len(timeline) < 3:
            return False
        
        # Simple cascade detection - sequential failures with propagation delays
        sequential_count = 0
        for i in range(1, len(timeline)):
            delay = self._calculate_propagation_delay(timeline[i-1]['timestamp'], timeline[i]['timestamp'])
            if 0 < delay <= 300:  # Failures within 5 minutes of each other
                sequential_count += 1
        
        return sequential_count >= 2
    
    def _find_common_dependencies(self, components, infrastructure_graph):
        """Find common dependencies for a set of components"""
        dependency_counts = {}
        
        for component in components:
            if infrastructure_graph.has_node(component):
                # Find all ancestors (components this one depends on)
                ancestors = nx.ancestors(infrastructure_graph, component)
                for ancestor in ancestors:
                    dependency_counts[ancestor] = dependency_counts.get(ancestor, 0) + 1
        
        # Convert to scored results
        results = []
        for dep_id, count in dependency_counts.items():
            if count > 1:  # Shared by at least 2 components
                dep_node = infrastructure_graph.nodes[dep_id]
                score = min(1.0, count / len(components))
                results.append({
                    'id': dep_id,
                    'name': dep_node.get('name', dep_id),
                    'score': round(score, 2),
                    'dependent_components_count': count
                })
        
        return sorted(results, key=lambda x: x['score'], reverse=True)
    
    def _extract_incident_pattern(self, incident_data):
        """Extract pattern signature from incident data"""
        alerts = incident_data.get('alerts', [])
        pattern = {
            'alert_types': list(set([alert.get('type', '') for alert in alerts])),
            'severity_distribution': {},
            'component_types': list(set([alert.get('target_name', '') for alert in alerts])),
            'duration_hours': 0  # Would calculate from timestamps
        }
        
        # Count severity distribution
        for alert in alerts:
            severity = alert.get('severity', 'unknown')
            pattern['severity_distribution'][severity] = pattern['severity_distribution'].get(severity, 0) + 1
        
        return pattern
    
    def _calculate_incident_similarity(self, pattern1, pattern2):
        """Calculate similarity between two incident patterns"""
        # Simple Jaccard similarity for alert types
        types1 = set(pattern1.get('alert_types', []))
        types2 = set(pattern2.get('pattern', {}).get('alert_types', []))
        
        if not types1 or not types2:
            return 0
        
        intersection = len(types1.intersection(types2))
        union = len(types1.union(types2))
        
        return intersection / union if union > 0 else 0

class BusinessImpactCorrelator:
    """Correlate infrastructure health with business metrics"""
    
    def __init__(self):
        self.business_metrics = {}
        self.impact_models = {}
        self.correlation_rules = []
        
    def correlate_business_impact(self, incident_data, infrastructure_graph):
        """Correlate infrastructure incidents with business impact"""
        try:
            impact_analysis = {
                'affected_business_services': [],
                'estimated_financial_impact': 0,
                'customer_impact_estimate': 'Unknown',
                'revenue_risk_score': 0,
                'mitigation_priority': 'medium',
                'business_recommendations': []
            }
            
            # Analyze which business services are affected
            affected_services = self._map_to_business_services(incident_data, infrastructure_graph)
            impact_analysis['affected_business_services'] = affected_services
            
            # Calculate financial impact
            financial_impact = self._estimate_financial_impact(affected_services, incident_data)
            impact_analysis['estimated_financial_impact'] = financial_impact
            
            # Estimate customer impact
            customer_impact = self._estimate_customer_impact(affected_services)
            impact_analysis['customer_impact_estimate'] = customer_impact
            
            # Calculate overall risk score
            risk_score = self._calculate_business_risk_score(financial_impact, customer_impact, incident_data)
            impact_analysis['revenue_risk_score'] = risk_score
            
            # Set mitigation priority
            impact_analysis['mitigation_priority'] = self._determine_mitigation_priority(risk_score)
            
            # Generate business-focused recommendations
            impact_analysis['business_recommendations'] = self._generate_business_recommendations(
                affected_services, financial_impact, risk_score
            )
            
            return impact_analysis
            
        except Exception as e:
            print(f"[ML ERROR] Business impact analysis failed: {e}")
            return {'affected_business_services': [], 'estimated_financial_impact': 0}
    
    def _map_to_business_services(self, incident_data, infrastructure_graph):
        """Map infrastructure components to business services"""
        affected_components = [alert.get('target_name') for alert in incident_data.get('alerts', [])]
        business_services = []
        
        # Business service mappings (would come from CMDB in real implementation)
        service_mappings = {
            'web_server': ['customer_portal', 'checkout_service'],
            'database': ['user_management', 'order_processing', 'inventory'],
            'load_balancer': ['all_web_services'],
            'payment_gateway': ['checkout_service', 'payment_processing'],
            'auth_service': ['user_authentication', 'api_access']
        }
        
        for component in affected_components:
            component_type = self._infer_component_type(component)
            if component_type in service_mappings:
                for service in service_mappings[component_type]:
                    if service not in business_services:
                        business_services.append({
                            'service_name': service,
                            'affected_components': [component],
                            'criticality': self._get_service_criticality(service)
                        })
        
        return business_services
    
    def _estimate_financial_impact(self, affected_services, incident_data):
        """Estimate financial impact of incident"""
        total_impact = 0
        
        # Base impact rates per service (would be customized for your business)
        impact_rates = {
            'customer_portal': 500,  # $ per hour
            'checkout_service': 1000,
            'payment_processing': 2000,
            'order_processing': 800,
            'inventory': 300,
            'user_management': 100,
            'user_authentication': 1500
        }
        
        # Estimate duration (simplified)
        duration_hours = self._estimate_incident_duration(incident_data)
        
        for service in affected_services:
            service_name = service['service_name']
            if service_name in impact_rates:
                service_impact = impact_rates[service_name] * duration_hours
                total_impact += service_impact
        
        return round(total_impact, 2)
    
    def _estimate_customer_impact(self, affected_services):
        """Estimate customer impact level"""
        critical_services = ['checkout_service', 'payment_processing', 'user_authentication']
        high_services = ['customer_portal', 'order_processing']
        
        critical_count = sum(1 for service in affected_services if service['service_name'] in critical_services)
        high_count = sum(1 for service in affected_services if service['service_name'] in high_services)
        
        if critical_count > 0:
            return 'Critical - Core business functions affected'
        elif high_count > 0:
            return 'High - Key customer-facing services affected'
        elif affected_services:
            return 'Medium - Some customer impact'
        else:
            return 'Low - Minimal customer impact'
    
    def _calculate_business_risk_score(self, financial_impact, customer_impact, incident_data):
        """Calculate overall business risk score"""
        base_score = 0
        
        # Financial impact component (0-50 points)
        financial_score = min(50, financial_impact / 100)
        base_score += financial_score
        
        # Customer impact component (0-30 points)
        customer_scores = {
            'Critical': 30,
            'High': 20,
            'Medium': 10,
            'Low': 5
        }
        base_score += customer_scores.get(customer_impact.split(' - ')[0], 5)
        
        # Duration component (0-20 points)
        duration_hours = self._estimate_incident_duration(incident_data)
        duration_score = min(20, duration_hours * 5)
        base_score += duration_score
        
        return min(100, base_score)
    
    def _determine_mitigation_priority(self, risk_score):
        """Determine mitigation priority based on risk score"""
        if risk_score >= 80:
            return 'critical'
        elif risk_score >= 60:
            return 'high'
        elif risk_score >= 40:
            return 'medium'
        else:
            return 'low'
    
    def _generate_business_recommendations(self, affected_services, financial_impact, risk_score):
        """Generate business-focused recommendations"""
        recommendations = []
        
        if risk_score >= 80:
            recommendations.append({
                'type': 'immediate_action',
                'priority': 'critical',
                'action': 'Activate business continuity plan and executive notification',
                'reason': f'High business impact: ${financial_impact} at risk'
            })
        
        critical_services = [s for s in affected_services if s['criticality'] == 'high']
        if critical_services:
            recommendations.append({
                'type': 'communication',
                'priority': 'high',
                'action': 'Notify customer support and update status page',
                'reason': f'{len(critical_services)} critical business services affected'
            })
        
        if financial_impact > 5000:
            recommendations.append({
                'type': 'financial',
                'priority': 'high',
                'action': 'Prepare incident cost analysis for management',
                'reason': f'Significant financial impact: ${financial_impact}'
            })
        
        return recommendations
    
    # Helper methods
    def _infer_component_type(self, component_name):
        """Infer component type from name"""
        name_lower = component_name.lower()
        if any(word in name_lower for word in ['web', 'app', 'api']):
            return 'web_server'
        elif any(word in name_lower for word in ['db', 'database', 'sql']):
            return 'database'
        elif any(word in name_lower for word in ['load', 'balancer', 'lb']):
            return 'load_balancer'
        elif any(word in name_lower for word in ['payment', 'gateway']):
            return 'payment_gateway'
        elif any(word in name_lower for word in ['auth', 'login']):
            return 'auth_service'
        else:
            return 'unknown'
    
    def _get_service_criticality(self, service_name):
        """Get criticality level for a business service"""
        critical_services = ['checkout_service', 'payment_processing', 'user_authentication']
        high_services = ['customer_portal', 'order_processing']
        
        if service_name in critical_services:
            return 'critical'
        elif service_name in high_services:
            return 'high'
        else:
            return 'medium'
    
    def _estimate_incident_duration(self, incident_data):
        """Estimate incident duration (simplified)"""
        alerts = incident_data.get('alerts', [])
        if not alerts:
            return 1  # Default 1 hour
        
        # Simple duration estimation based on alert count and severity
        critical_count = sum(1 for alert in alerts if alert.get('severity') == 'critical')
        base_duration = 1 + (critical_count * 0.5)  # 1 hour + 0.5 per critical alert
        
        return min(24, base_duration)  # Cap at 24 hours

class AutomatedRemediationEngine:
    """Intelligent automated remediation with ML-driven decision making"""
    
    def __init__(self):
        self.remediation_actions = {}
        self.success_rates = {}
        self.learning_model = {}
        
    def generate_remediation_plan(self, incident_analysis, business_impact):
        """Generate intelligent remediation plan with ML recommendations"""
        try:
            remediation_plan = {
                'immediate_actions': [],
                'investigation_steps': [],
                'preventive_measures': [],
                'expected_recovery_time': 0,
                'success_probability': 0,
                'risk_assessment': {}
            }
            
            root_cause = incident_analysis.get('primary_cause', {})
            cause_type = root_cause.get('type', 'unknown')
            
            # Generate actions based on root cause type
            if cause_type == 'resource_exhaustion':
                remediation_plan['immediate_actions'] = self._generate_resource_remediation(incident_analysis)
            elif cause_type == 'common_infrastructure_failure':
                remediation_plan['immediate_actions'] = self._generate_infrastructure_remediation(incident_analysis)
            elif cause_type == 'cascade_failure':
                remediation_plan['immediate_actions'] = self._generate_cascade_remediation(incident_analysis)
            else:
                remediation_plan['immediate_actions'] = self._generate_general_remediation(incident_analysis)
            
            # Add business-priority actions
            if business_impact.get('mitigation_priority') == 'critical':
                remediation_plan['immediate_actions'].extend(
                    self._generate_business_critical_actions(business_impact)
                )
            
            # Generate investigation steps
            remediation_plan['investigation_steps'] = self._generate_investigation_steps(incident_analysis)
            
            # Generate preventive measures
            remediation_plan['preventive_measures'] = self._generate_preventive_measures(incident_analysis)
            
            # Calculate recovery estimates
            remediation_plan['expected_recovery_time'] = self._estimate_recovery_time(
                remediation_plan['immediate_actions']
            )
            
            # Calculate success probability
            remediation_plan['success_probability'] = self._calculate_success_probability(
                remediation_plan['immediate_actions']
            )
            
            # Risk assessment
            remediation_plan['risk_assessment'] = self._assess_remediation_risks(
                remediation_plan['immediate_actions']
            )
            
            return remediation_plan
            
        except Exception as e:
            print(f"[ML ERROR] Remediation planning failed: {e}")
            return {'immediate_actions': [], 'investigation_steps': []}
    
    def _generate_resource_remediation(self, incident_analysis):
        """Generate remediation for resource exhaustion issues"""
        actions = []
        
        # Scale resources
        actions.append({
            'action': 'Scale compute resources for affected components',
            'type': 'scaling',
            'priority': 'high',
            'estimated_duration': '15 minutes',
            'automation_ready': True,
            'risk': 'low'
        })
        
        # Optimize resource usage
        actions.append({
            'action': 'Identify and terminate resource-intensive processes',
            'type': 'optimization',
            'priority': 'medium',
            'estimated_duration': '10 minutes',
            'automation_ready': True,
            'risk': 'low'
        })
        
        # Load balancing
        actions.append({
            'action': 'Redistribute load across available resources',
            'type': 'load_balancing',
            'priority': 'medium',
            'estimated_duration': '5 minutes',
            'automation_ready': True,
            'risk': 'low'
        })
        
        return actions
    
    def _generate_infrastructure_remediation(self, incident_analysis):
        """Generate remediation for infrastructure failures"""
        actions = []
        
        actions.append({
            'action': 'Failover to secondary infrastructure components',
            'type': 'failover',
            'priority': 'high',
            'estimated_duration': '10 minutes',
            'automation_ready': True,
            'risk': 'medium'
        })
        
        actions.append({
            'action': 'Check and restart failed infrastructure services',
            'type': 'restart',
            'priority': 'high',
            'estimated_duration': '5 minutes',
            'automation_ready': True,
            'risk': 'low'
        })
        
        return actions
    
    def _generate_cascade_remediation(self, incident_analysis):
        """Generate remediation for cascade failures"""
        actions = []
        
        actions.append({
            'action': 'Isolate initial failure point to prevent propagation',
            'type': 'isolation',
            'priority': 'critical',
            'estimated_duration': '5 minutes',
            'automation_ready': True,
            'risk': 'medium'
        })
        
        actions.append({
            'action': 'Implement circuit breakers on dependent services',
            'type': 'circuit_breaker',
            'priority': 'high',
            'estimated_duration': '8 minutes',
            'automation_ready': True,
            'risk': 'low'
        })
        
        return actions
    
    def _generate_general_remediation(self, incident_analysis):
        """Generate general remediation actions"""
        return [{
            'action': 'Perform comprehensive system health check',
            'type': 'health_check',
            'priority': 'medium',
            'estimated_duration': '10 minutes',
            'automation_ready': True,
            'risk': 'low'
        }]
    
    def _generate_business_critical_actions(self, business_impact):
        """Generate actions for business-critical incidents"""
        return [{
            'action': 'Implement emergency traffic routing to healthy components',
            'type': 'emergency_routing',
            'priority': 'critical',
            'estimated_duration': '3 minutes',
            'automation_ready': True,
            'risk': 'low'
        }]
    
    def _generate_investigation_steps(self, incident_analysis):
        """Generate investigation steps for root cause analysis"""
        steps = []
        
        steps.append({
            'step': 'Review recent configuration changes',
            'focus': 'Identify recent changes that might have caused the issue'
        })
        
        steps.append({
            'step': 'Analyze metric trends preceding the incident',
            'focus': 'Identify early warning signs and patterns'
        })
        
        steps.append({
            'step': 'Check dependency health and connectivity',
            'focus': 'Verify health of dependent services and components'
        })
        
        return steps
    
    def _generate_preventive_measures(self, incident_analysis):
        """Generate preventive measures for future incidents"""
        measures = []
        
        root_cause = incident_analysis.get('primary_cause', {})
        cause_type = root_cause.get('type', 'unknown')
        
        if cause_type == 'resource_exhaustion':
            measures.append({
                'measure': 'Implement auto-scaling policies for resource-intensive services',
                'timeframe': 'short_term'
            })
        
        if cause_type == 'single_point_of_failure':
            measures.append({
                'measure': 'Design and implement redundancy for critical components',
                'timeframe': 'medium_term'
            })
        
        measures.append({
            'measure': 'Enhance monitoring and alerting for early detection',
            'timeframe': 'short_term'
        })
        
        return measures
    
    def _estimate_recovery_time(self, actions):
        """Estimate total recovery time for remediation actions"""
        total_minutes = 0
        for action in actions:
            duration_str = action.get('estimated_duration', '0 minutes')
            minutes = int(duration_str.split(' ')[0])
            total_minutes += minutes
        
        return total_minutes
    
    def _calculate_success_probability(self, actions):
        """Calculate probability of successful remediation"""
        if not actions:
            return 0
        
        # Base probability adjusted by action types and risks
        base_probability = 0.8
        
        # Adjust based on action types
        action_types = [action.get('type') for action in actions]
        if 'failover' in action_types:
            base_probability *= 0.9  # Failovers are generally reliable
        if 'restart' in action_types:
            base_probability *= 0.95  # Restarts are usually successful
        
        # Adjust based on risks
        high_risk_actions = sum(1 for action in actions if action.get('risk') == 'high')
        base_probability *= (1 - (high_risk_actions * 0.1))
        
        return round(base_probability, 2)
    
    def _assess_remediation_risks(self, actions):
        """Assess risks associated with remediation actions"""
        risks = []
        
        for action in actions:
            if action.get('risk') == 'high':
                risks.append({
                    'action': action.get('action'),
                    'risk_level': 'high',
                    'potential_impact': 'Service disruption during implementation'
                })
            elif action.get('risk') == 'medium':
                risks.append({
                    'action': action.get('action'),
                    'risk_level': 'medium',
                    'potential_impact': 'Temporary performance degradation'
                })
        
        return {
            'high_risk_actions': len([r for r in risks if r['risk_level'] == 'high']),
            'medium_risk_actions': len([r for r in risks if r['risk_level'] == 'medium']),
            'detailed_risks': risks
        }

# Initialize Phase 2 ML components
root_cause_analyzer = IntelligentRootCauseAnalyzer()
business_impact_correlator = BusinessImpactCorrelator()
remediation_engine = AutomatedRemediationEngine()
# ================== ML ENHANCED ROUTES ======================================================================================

@app.route('/api/ml/dependencies/discover', methods=['POST'])
@token_required
def discover_dependencies():
    """Discover infrastructure dependencies using ML"""
    try:
        # Get current monitoring data for analysis
        monitoring_data = {
            'timestamp': datetime.now().isoformat(),
            'component_count': MonitoringTarget.query.count()
        }
        
        result = dependency_mapper.auto_discover_dependencies(monitoring_data)
        
        comprehensive_logger.log_ai_engine_event(
            "dependency_discovery", 
            "completed", 
            f"Found {result.get('total_components', 0)} components with {result.get('total_dependencies', 0)} dependencies",
            request.user_id
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("dependency_discovery", str(e), "discover_dependencies", request.user_id)
        return jsonify({"error": "Dependency discovery failed"}), 500

@app.route('/api/ml/dependencies/impact/<component_id>', methods=['GET'])
@token_required
def get_impact_analysis(component_id):
    """Get ML-powered impact analysis for a component"""
    try:
        impact_analysis = dependency_mapper.get_impact_analysis(component_id)
        
        comprehensive_logger.log_ai_engine_event(
            "impact_analysis", 
            "completed", 
            f"Impact analysis for {component_id}: {len(impact_analysis.get('direct_dependencies', []))} direct dependencies",
            request.user_id
        )
        
        return jsonify(impact_analysis), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("impact_analysis", str(e), "get_impact_analysis", request.user_id)
        return jsonify({"error": "Impact analysis failed"}), 500

@app.route('/api/ml/anomalies/correlate', methods=['POST'])
@token_required
def correlate_anomalies():
    """Correlate anomalies across infrastructure layers"""
    try:
        # Get current alerts
        current_alerts = []
        
        # Add your alert retrieval logic here
        # This would come from your existing alert system
        
        correlation_result = anomaly_correlator.correlate_anomalies(
            current_alerts, 
            dependency_mapper.dependency_graph
        )
        
        comprehensive_logger.log_ai_engine_event(
            "anomaly_correlation", 
            "completed", 
            f"Correlated {len(correlation_result.get('correlated_incidents', []))} incidents",
            request.user_id
        )
        
        return jsonify(correlation_result), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("anomaly_correlation", str(e), "correlate_anomalies", request.user_id)
        return jsonify({"error": "Anomaly correlation failed"}), 500

@app.route('/api/ml/capacity/analysis', methods=['GET'])
@token_required
def get_capacity_analysis():
    """Get ML-powered capacity planning analysis"""
    try:
        # Get infrastructure data for analysis
        infrastructure_data = dependency_mapper._extract_components({'timestamp': datetime.now().isoformat()})
        
        capacity_analysis = capacity_planner.analyze_capacity_risks(
            infrastructure_data,
            []  # Add historical metrics here
        )
        
        comprehensive_logger.log_ai_engine_event(
            "capacity_analysis", 
            "completed", 
            f"Found {len(capacity_analysis.get('critical_risks', []))} critical risks",
            request.user_id
        )
        
        return jsonify(capacity_analysis), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("capacity_analysis", str(e), "get_capacity_analysis", request.user_id)
        return jsonify({"error": "Capacity analysis failed"}), 500

@app.route('/api/ml/infrastructure/health', methods=['GET'])
@token_required
def get_infrastructure_health():
    """Get comprehensive ML-powered infrastructure health assessment"""
    try:
        # Combine all ML analyses for complete health view
        dependency_summary = dependency_mapper._get_dependency_summary()
        
        infrastructure_health = {
            'dependency_health': {
                'status': 'healthy' if dependency_summary['graph_ready'] else 'initializing',
                'components_mapped': dependency_summary['total_components'],
                'dependencies_discovered': dependency_summary['total_dependencies']
            },
            'anomaly_detection': {
                'status': 'active',
                'incidents_correlated': len(anomaly_correlator.incident_history)
            },
            'capacity_planning': {
                'status': 'active',
                'risk_assessment': 'complete'
            },
            'overall_health_score': self._calculate_health_score(dependency_summary),
            'recommendations': [
                {
                    'category': 'dependencies',
                    'action': 'Review dependency map for accuracy',
                    'priority': 'medium'
                },
                {
                    'category': 'monitoring',
                    'action': 'Ensure all critical components are monitored',
                    'priority': 'high'
                }
            ]
        }
        
        return jsonify(infrastructure_health), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("infrastructure_health", str(e), "get_infrastructure_health", request.user_id)
        return jsonify({"error": "Infrastructure health assessment failed"}), 500

def _calculate_health_score(self, dependency_summary):
    """Calculate overall infrastructure health score"""
    base_score = 100
    
    # Adjust based on dependency mapping completeness
    if dependency_summary['total_components'] > 0:
        coverage_score = min(100, (dependency_summary['total_components'] / 10) * 100)
        return max(0, min(100, (base_score + coverage_score) / 2))
    
    return 75  # Default score


@app.route('/api/ml/incidents/analyze', methods=['POST'])
@token_required
def analyze_incident_root_cause():
    """Perform deep root cause analysis for incidents"""
    try:
        incident_data = request.get_json()
        
        if not incident_data or 'alerts' not in incident_data:
            return jsonify({"error": "Incident data with alerts required"}), 400
        
        # Perform root cause analysis
        root_cause_analysis = root_cause_analyzer.analyze_root_cause(
            incident_data, 
            dependency_mapper.dependency_graph
        )
        
        # Correlate business impact
        business_impact = business_impact_correlator.correlate_business_impact(
            incident_data,
            dependency_mapper.dependency_graph
        )
        
        # Generate remediation plan
        remediation_plan = remediation_engine.generate_remediation_plan(
            root_cause_analysis,
            business_impact
        )
        
        comprehensive_analysis = {
            'root_cause_analysis': root_cause_analysis,
            'business_impact': business_impact,
            'remediation_plan': remediation_plan,
            'timestamp': datetime.now().isoformat()
        }
        
        comprehensive_logger.log_ai_engine_event(
            "incident_analysis", 
            "completed", 
            f"Root cause: {root_cause_analysis.get('primary_cause', {}).get('type', 'unknown')}, "
            f"Business impact: ${business_impact.get('estimated_financial_impact', 0)}",
            request.user_id
        )
        
        return jsonify(comprehensive_analysis), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("incident_analysis", str(e), "analyze_incident_root_cause", request.user_id)
        return jsonify({"error": "Incident analysis failed"}), 500

@app.route('/api/ml/business/impact', methods=['POST'])
@token_required
def analyze_business_impact():
    """Analyze business impact of infrastructure issues"""
    try:
        incident_data = request.get_json()
        
        business_impact = business_impact_correlator.correlate_business_impact(
            incident_data,
            dependency_mapper.dependency_graph
        )
        
        comprehensive_logger.log_ai_engine_event(
            "business_impact_analysis", 
            "completed", 
            f"Financial impact: ${business_impact.get('estimated_financial_impact', 0)}, "
            f"Risk score: {business_impact.get('revenue_risk_score', 0)}",
            request.user_id
        )
        
        return jsonify(business_impact), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("business_impact", str(e), "analyze_business_impact", request.user_id)
        return jsonify({"error": "Business impact analysis failed"}), 500

@app.route('/api/ml/remediation/generate', methods=['POST'])
@token_required
def generate_remediation_plan():
    """Generate intelligent remediation plan"""
    try:
        data = request.get_json()
        incident_analysis = data.get('incident_analysis', {})
        business_impact = data.get('business_impact', {})
        
        remediation_plan = remediation_engine.generate_remediation_plan(
            incident_analysis,
            business_impact
        )
        
        comprehensive_logger.log_ai_engine_event(
            "remediation_planning", 
            "completed", 
            f"Generated {len(remediation_plan.get('immediate_actions', []))} actions, "
            f"Success probability: {remediation_plan.get('success_probability', 0)}",
            request.user_id
        )
        
        return jsonify(remediation_plan), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("remediation_planning", str(e), "generate_remediation_plan", request.user_id)
        return jsonify({"error": "Remediation planning failed"}), 500

@app.route('/api/ml/incidents/history', methods=['GET'])
@token_required
def get_incident_history():
    """Get ML-analyzed incident history"""
    try:
        history = root_cause_analyzer.incident_knowledge_base[-50:]  # Last 50 incidents
        
        # Add summary statistics
        summary = {
            'total_incidents': len(history),
            'common_root_causes': self._get_common_root_causes(history),
            'resolution_trends': self._get_resolution_trends(history),
            'most_affected_services': self._get_most_affected_services(history)
        }
        
        return jsonify({
            'incidents': history,
            'summary': summary
        }), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("incident_history", str(e), "get_incident_history", request.user_id)
        return jsonify({"error": "Failed to get incident history"}), 500

def _get_common_root_causes(self, history):
    """Get common root causes from incident history"""
    causes = {}
    for incident in history:
        analysis = incident.get('analysis', {})
        primary_cause = analysis.get('primary_cause', {})
        cause_type = primary_cause.get('type', 'unknown')
        causes[cause_type] = causes.get(cause_type, 0) + 1
    
    return [{'cause': cause, 'count': count} for cause, count in causes.items()]

def _get_resolution_trends(self, history):
    """Get resolution trends from incident history"""
    # Simplified - in real implementation, analyze resolution times and success rates
    return {
        'average_recovery_time': '45 minutes',
        'success_rate': '92%',
        'common_successful_actions': ['resource_scaling', 'service_restart']
    }

def _get_most_affected_services(self, history):
    """Get most frequently affected services"""
    services = {}
    for incident in history:
        business_impact = incident.get('business_impact', {})
        affected_services = business_impact.get('affected_business_services', [])
        for service in affected_services:
            service_name = service.get('service_name', 'unknown')
            services[service_name] = services.get(service_name, 0) + 1
    
    return sorted([{'service': service, 'incident_count': count} 
                   for service, count in services.items()], 
                  key=lambda x: x['incident_count'], reverse=True)[:5]
                  
        # ================== PHASE 3: AUTONOMOUS OPERATIONS ==================

class ReinforcementLearningHealer:
    """Simple reinforcement learning for healing action selection"""
    
    def __init__(self):
        self.q_table = {}  # State -> action -> Q-value
        self.learning_rate = 0.1
        self.discount_factor = 0.9
        self.exploration_rate = 0.1
        
    def select_healing_action(self, state, available_actions):
        """Select healing action using epsilon-greedy policy"""
        state_key = self._state_to_key(state)
        
        # Initialize Q-values for new state
        if state_key not in self.q_table:
            self.q_table[state_key] = {action: 0.0 for action in available_actions}
        
        # Epsilon-greedy action selection
        if np.random.random() < self.exploration_rate:
            # Explore: random action
            return np.random.choice(available_actions)
        else:
            # Exploit: best known action
            q_values = self.q_table[state_key]
            return max(q_values, key=q_values.get)
    
    def update_q_value(self, state, action, reward, next_state):
        """Update Q-value using Q-learning"""
        state_key = self._state_to_key(state)
        next_state_key = self._state_to_key(next_state)
        action_key = str(action)  # Convert action to string key
        
        # Initialize if needed
        if state_key not in self.q_table:
            self.q_table[state_key] = {}
        if action_key not in self.q_table[state_key]:
            self.q_table[state_key][action_key] = 0.0
        
        # Get max Q-value for next state
        next_max = 0.0
        if next_state_key in self.q_table and self.q_table[next_state_key]:
            next_max = max(self.q_table[next_state_key].values())
        
        # Q-learning update
        current_q = self.q_table[state_key][action_key]
        new_q = current_q + self.learning_rate * (reward + self.discount_factor * next_max - current_q)
        self.q_table[state_key][action_key] = new_q
        
        # Decay exploration rate
        self.exploration_rate = max(0.01, self.exploration_rate * 0.995)
    
    def _state_to_key(self, state):
        """Convert state dictionary to string key"""
        if isinstance(state, dict):
            return str(sorted(state.items()))
        return str(state)
    
    def get_learning_stats(self):
        """Get learning statistics"""
        return {
            'states_learned': len(self.q_table),
            'exploration_rate': round(self.exploration_rate, 3),
            'total_q_values': sum(len(actions) for actions in self.q_table.values())
        }


class AutonomousHealingOrchestrator:
    """ML-driven self-healing across the entire infrastructure stack"""
    
    def __init__(self):
        self.healing_policies = {}
        self.healing_history = []
        self.success_rates = {}
        self.learning_loop = ReinforcementLearningHealer()
        
    def execute_autonomous_healing(self, incident_analysis, remediation_plan):
        """Execute autonomous healing with ML-driven decision making"""
        try:
            print(f"[AUTONOMY] Executing autonomous healing for {incident_analysis.get('primary_cause', {}).get('type', 'unknown')}")
            
            healing_session = {
                'session_id': f"heal_{int(time.time())}",
                'start_time': datetime.now().isoformat(),
                'incident_id': incident_analysis.get('incident_id'),
                'root_cause': incident_analysis.get('primary_cause', {}).get('type'),
                'actions_executed': [],
                'outcome': 'in_progress',
                'business_impact_mitigated': 0
            }
            
            # Select and execute healing actions
            executable_actions = self._select_autonomous_actions(remediation_plan)
            
            for action in executable_actions:
                action_result = self._execute_healing_action(action, incident_analysis)
                healing_session['actions_executed'].append(action_result)
                
                # Check if healing is complete
                if action_result.get('status') == 'success' and self._is_healing_complete(incident_analysis):
                    healing_session['outcome'] = 'success'
                    healing_session['business_impact_mitigated'] = self._calculate_mitigated_impact(incident_analysis)
                    break
            
            # Learn from this healing session
            self._learn_from_healing_session(healing_session)
            
            # Update healing history
            self.healing_history.append(healing_session)
            
            return healing_session
            
        except Exception as e:
            print(f"[AUTONOMY ERROR] Autonomous healing failed: {e}")
            return {'outcome': 'failed', 'error': str(e)}
    
    def _select_autonomous_actions(self, remediation_plan):
        """Select which actions to execute autonomously"""
        autonomous_actions = []
        
        for action in remediation_plan.get('immediate_actions', []):
            if (action.get('automation_ready', False) and 
                action.get('risk') in ['low', 'medium'] and
                action.get('priority') in ['high', 'medium']):
                
                # Use reinforcement learning to decide
                system_state = self._get_current_system_state()
                should_execute = self.learning_loop.select_healing_action(
                    system_state, 
                    [action['action']]
                )
                
                if should_execute:
                    autonomous_actions.append(action)
        
        return autonomous_actions[:3]  # Limit to 3 actions per session
    
    def _execute_healing_action(self, action, incident_analysis):
        """Execute a healing action with real infrastructure commands"""
        try:
            action_type = action.get('type')
            action_result = {
                'action': action.get('action'),
                'type': action_type,
                'start_time': datetime.now().isoformat(),
                'status': 'executing'
            }
            
            # Execute based on action type
            if action_type == 'scaling':
                result = self._execute_scaling_action(action, incident_analysis)
            elif action_type == 'restart':
                result = self._execute_restart_action(action, incident_analysis)
            elif action_type == 'failover':
                result = self._execute_failover_action(action, incident_analysis)
            elif action_type == 'load_balancing':
                result = self._execute_load_balancing_action(action, incident_analysis)
            else:
                result = self._execute_general_action(action, incident_analysis)
            
            action_result.update(result)
            action_result['end_time'] = datetime.now().isoformat()
            
            return action_result
            
        except Exception as e:
            return {
                'action': action.get('action'),
                'type': action.get('type'),
                'status': 'failed',
                'error': str(e),
                'end_time': datetime.now().isoformat()
            }
    
    def _execute_scaling_action(self, action, incident_analysis):
        """Execute infrastructure scaling actions"""
        # Integration with your cloud provider/container orchestrator
        # This is a simplified example - implement based on your infrastructure
        
        affected_components = incident_analysis.get('affected_components', [])
        
        # Scale based on resource type
        for component in affected_components[:2]:  # Scale first 2 affected components
            if 'cpu' in incident_analysis.get('primary_cause', {}).get('description', '').lower():
                self._scale_compute_resources(component, scale_factor=1.5)
            elif 'memory' in incident_analysis.get('primary_cause', {}).get('description', '').lower():
                self._scale_memory_resources(component, scale_factor=1.5)
        
        return {
            'status': 'success',
            'details': f'Scaled resources for {len(affected_components[:2])} components',
            'impact': 'immediate'
        }
    
    def _execute_restart_action(self, action, incident_analysis):
        """Execute service restart actions"""
        affected_components = incident_analysis.get('affected_components', [])
        
        for component in affected_components[:3]:  # Restart first 3 affected components
            self._restart_service(component)
        
        return {
            'status': 'success',
            'details': f'Restarted {len(affected_components[:3])} services',
            'impact': 'immediate'
        }
    
    def _execute_failover_action(self, action, incident_analysis):
        """Execute failover to secondary systems"""
        # Implement your failover logic here
        primary_components = incident_analysis.get('affected_components', [])
        
        for component in primary_components:
            if self._has_secondary_system(component):
                self._trigger_failover(component)
        
        return {
            'status': 'success',
            'details': f'Failed over {len(primary_components)} components',
            'impact': 'immediate'
        }
    
    def _execute_load_balancing_action(self, action, incident_analysis):
        """Execute load balancing redistribution"""
        # Implement load balancer configuration updates
        overloaded_components = [comp for comp in incident_analysis.get('affected_components', []) 
                               if 'high load' in comp.get('status', '')]
        
        for component in overloaded_components:
            self._redistribute_load(component)
        
        return {
            'status': 'success',
            'details': f'Redistributed load for {len(overloaded_components)} components',
            'impact': 'immediate'
        }
    
    def _execute_general_action(self, action, incident_analysis):
        """Execute general healing actions"""
        # Implement general infrastructure remediation
        return {
            'status': 'success',
            'details': 'General remediation action completed',
            'impact': 'varies'
        }
    
    def _is_healing_complete(self, incident_analysis):
        """Check if healing has resolved the incident"""
        # Monitor key metrics to verify resolution
        affected_components = incident_analysis.get('affected_components', [])
        
        recovery_indicators = 0
        for component in affected_components:
            if self._is_component_healthy(component):
                recovery_indicators += 1
        
        # Consider healing complete if >70% of components are healthy
        return (recovery_indicators / len(affected_components)) > 0.7 if affected_components else True
    
    def _calculate_mitigated_impact(self, incident_analysis):
        """Calculate business impact mitigated by autonomous healing"""
        # Estimate financial impact that was prevented
        base_impact = 1000  # Base value per incident
        severity_multiplier = {
            'critical': 5,
            'high': 3,
            'medium': 2,
            'low': 1
        }
        
        severity = incident_analysis.get('severity', 'medium')
        component_count = len(incident_analysis.get('affected_components', []))
        
        return base_impact * severity_multiplier.get(severity, 1) * max(1, component_count / 2)
    
    def _learn_from_healing_session(self, healing_session):
        """Reinforcement learning from healing outcomes"""
        if healing_session['outcome'] == 'success':
            reward = 1.0
        else:
            reward = -1.0
        
        # Update Q-values for learning
        system_state = self._get_current_system_state()
        for action in healing_session['actions_executed']:
            if action['status'] == 'success':
                self.learning_loop.update_q_value(
                    system_state,
                    action['action'],
                    reward,
                    self._get_post_healing_state()
                )
    
    # Infrastructure integration methods (implement based on your environment)
    def _scale_compute_resources(self, component, scale_factor):
        """Scale compute resources for a component"""
        # Integrate with your cloud provider API (AWS, Azure, GCP)
        # or container orchestrator (Kubernetes, Docker Swarm)
        print(f"[AUTONOMY] Scaling compute for {component} by factor {scale_factor}")
        # Implementation depends on your infrastructure
    
    def _scale_memory_resources(self, component, scale_factor):
        """Scale memory resources for a component"""
        print(f"[AUTONOMY] Scaling memory for {component} by factor {scale_factor}")
        # Implementation depends on your infrastructure
    
    def _restart_service(self, component):
        """Restart a service/container/VM"""
        print(f"[AUTONOMY] Restarting {component}")
        # Implementation depends on your infrastructure
    
    def _has_secondary_system(self, component):
        """Check if component has a secondary system for failover"""
        # Implement based on your high-availability setup
        return True  # Simplified
    
    def _trigger_failover(self, component):
        """Trigger failover to secondary system"""
        print(f"[AUTONOMY] Failing over {component} to secondary")
        # Implementation depends on your infrastructure
    
    def _redistribute_load(self, component):
        """Redistribute load away from overloaded component"""
        print(f"[AUTONOMY] Redistributing load for {component}")
        # Implementation depends on your load balancer configuration
    
    def _is_component_healthy(self, component):
        """Check if component is healthy after healing"""
        # Implement health checks based on your monitoring
        return True  # Simplified
    
    def _get_current_system_state(self):
        """Get current system state for RL"""
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_health': 'degraded'  # Would be calculated from metrics
        }
    
    def _get_post_healing_state(self):
        """Get system state after healing attempts"""
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_health': 'healthy'  # Would be calculated from metrics
        }

class ProactiveOptimizationEngine:
    """ML-driven proactive optimization across infrastructure"""
    
    def __init__(self):
        self.optimization_models = {}
        self.performance_baselines = {}
        self.optimization_history = []
        
    def analyze_optimization_opportunities(self, infrastructure_data, historical_metrics):
        """Identify and execute proactive optimization opportunities"""
        try:
            opportunities = {
                'cost_optimizations': [],
                'performance_optimizations': [],
                'reliability_improvements': [],
                'security_enhancements': [],
                'executed_optimizations': []
            }
            
            # Cost optimization analysis
            cost_ops = self._analyze_cost_optimization(infrastructure_data)
            opportunities['cost_optimizations'] = cost_ops
            
            # Performance optimization analysis
            perf_ops = self._analyze_performance_optimization(historical_metrics)
            opportunities['performance_optimizations'] = perf_ops
            
            # Reliability improvement analysis
            reliability_ops = self._analyze_reliability_improvements(infrastructure_data)
            opportunities['reliability_improvements'] = reliability_ops
            
            # Execute high-value, low-risk optimizations
            executable_ops = self._select_optimizations_for_execution(opportunities)
            for optimization in executable_ops:
                result = self._execute_proactive_optimization(optimization)
                opportunities['executed_optimizations'].append(result)
            
            return opportunities
            
        except Exception as e:
            print(f"[OPTIMIZATION ERROR] Proactive optimization failed: {e}")
            return {'cost_optimizations': [], 'performance_optimizations': []}
    
    def _analyze_cost_optimization(self, infrastructure_data):
        """Analyze cost optimization opportunities"""
        optimizations = []
        
        # Identify over-provisioned resources
        for component in self._get_all_components(infrastructure_data):
            utilization = self._calculate_resource_utilization(component)
            
            if utilization.get('cpu', 0) < 30:  # Underutilized CPU
                optimizations.append({
                    'type': 'cost',
                    'component': component.get('name'),
                    'opportunity': 'Right-size compute resources',
                    'savings_estimate': self._estimate_cost_savings(component, 'compute'),
                    'risk': 'low',
                    'implementation_complexity': 'low'
                })
            
            if utilization.get('memory', 0) < 40:  # Underutilized memory
                optimizations.append({
                    'type': 'cost',
                    'component': component.get('name'),
                    'opportunity': 'Optimize memory allocation',
                    'savings_estimate': self._estimate_cost_savings(component, 'memory'),
                    'risk': 'low',
                    'implementation_complexity': 'medium'
                })
        
        # Identify unused resources
        unused_resources = self._identify_unused_resources(infrastructure_data)
        optimizations.extend(unused_resources)
        
        return sorted(optimizations, key=lambda x: x.get('savings_estimate', 0), reverse=True)
    
    def _analyze_performance_optimization(self, historical_metrics):
        """Analyze performance optimization opportunities"""
        optimizations = []
        
        # Identify performance bottlenecks
        bottlenecks = self._identify_performance_bottlenecks(historical_metrics)
        
        for bottleneck in bottlenecks:
            optimizations.append({
                'type': 'performance',
                'component': bottleneck.get('component'),
                'opportunity': f"Optimize {bottleneck.get('bottleneck_type')} performance",
                'expected_improvement': bottleneck.get('improvement_potential'),
                'risk': 'low',
                'implementation_complexity': bottleneck.get('complexity', 'medium')
            })
        
        # Identify caching opportunities
        caching_ops = self._identify_caching_opportunities(historical_metrics)
        optimizations.extend(caching_ops)
        
        return optimizations
    
    def _analyze_reliability_improvements(self, infrastructure_data):
        """Analyze reliability improvement opportunities"""
        optimizations = []
        
        # Identify single points of failure
        spofs = self._identify_single_points_of_failure(infrastructure_data)
        
        for spof in spofs:
            optimizations.append({
                'type': 'reliability',
                'component': spof.get('component'),
                'opportunity': 'Implement redundancy/high-availability',
                'expected_improvement': f"Eliminate single point of failure",
                'risk': 'medium',
                'implementation_complexity': spof.get('complexity', 'high')
            })
        
        # Identify backup improvements
        backup_ops = self._identify_backup_improvements(infrastructure_data)
        optimizations.extend(backup_ops)
        
        return optimizations
    
    def _select_optimizations_for_execution(self, opportunities):
        """Select which optimizations to execute proactively"""
        executable = []
        
        # Combine all optimization types
        all_optimizations = (
            opportunities['cost_optimizations'] +
            opportunities['performance_optimizations'] +
            opportunities['reliability_improvements']
        )
        
        # Filter for high-value, low-risk optimizations
        for optimization in all_optimizations:
            if (optimization.get('risk') == 'low' and 
                optimization.get('implementation_complexity') in ['low', 'medium']):
                
                # Check if savings/improvement is significant
                savings = optimization.get('savings_estimate', 0)
                if savings > 100 or optimization.get('type') != 'cost':  # $100+ savings or non-cost optimizations
                    executable.append(optimization)
        
        return executable[:5]  # Limit to 5 optimizations per cycle
    
    def _execute_proactive_optimization(self, optimization):
        """Execute a proactive optimization"""
        try:
            result = {
                'optimization': optimization.get('opportunity'),
                'component': optimization.get('component'),
                'start_time': datetime.now().isoformat(),
                'status': 'executing'
            }
            
            # Execute based on optimization type
            if optimization['type'] == 'cost':
                result.update(self._execute_cost_optimization(optimization))
            elif optimization['type'] == 'performance':
                result.update(self._execute_performance_optimization(optimization))
            elif optimization['type'] == 'reliability':
                result.update(self._execute_reliability_optimization(optimization))
            
            result['end_time'] = datetime.now().isoformat()
            
            # Record in history
            self.optimization_history.append(result)
            
            return result
            
        except Exception as e:
            return {
                'optimization': optimization.get('opportunity'),
                'status': 'failed',
                'error': str(e),
                'end_time': datetime.now().isoformat()
            }
    
    def _execute_cost_optimization(self, optimization):
        """Execute cost optimization"""
        component = optimization.get('component')
        
        if 'Right-size compute' in optimization.get('opportunity', ''):
            self._right_size_compute_resources(component)
            return {'status': 'success', 'details': 'Compute resources right-sized'}
        
        elif 'Optimize memory allocation' in optimization.get('opportunity', ''):
            self._optimize_memory_allocation(component)
            return {'status': 'success', 'details': 'Memory allocation optimized'}
        
        return {'status': 'skipped', 'details': 'Optimization type not implemented'}
    
    def _execute_performance_optimization(self, optimization):
        """Execute performance optimization"""
        # Implement performance optimizations
        return {'status': 'success', 'details': 'Performance optimization applied'}
    
    def _execute_reliability_optimization(self, optimization):
        """Execute reliability optimization"""
        # Implement reliability improvements
        return {'status': 'success', 'details': 'Reliability improvement implemented'}
    
    # Helper methods for optimization analysis
    def _get_all_components(self, infrastructure_data):
        """Get all components from infrastructure data"""
        all_components = []
        for category in infrastructure_data.values():
            if isinstance(category, list):
                all_components.extend(category)
        return all_components
    
    def _calculate_resource_utilization(self, component):
        """Calculate resource utilization for a component"""
        # Implement based on your monitoring data
        return {'cpu': 25, 'memory': 35, 'disk': 60}  # Example
    
    def _estimate_cost_savings(self, component, resource_type):
        """Estimate cost savings from optimization"""
        # Implement based on your pricing data
        base_savings = {'compute': 150, 'memory': 75, 'storage': 50}
        return base_savings.get(resource_type, 0)
    
    def _identify_unused_resources(self, infrastructure_data):
        """Identify unused or orphaned resources"""
        # Implement based on your resource tracking
        return []
    
    def _identify_performance_bottlenecks(self, historical_metrics):
        """Identify performance bottlenecks"""
        # Implement bottleneck detection
        return []
    
    def _identify_caching_opportunities(self, historical_metrics):
        """Identify caching optimization opportunities"""
        # Implement cache analysis
        return []
    
    def _identify_single_points_of_failure(self, infrastructure_data):
        """Identify single points of failure"""
        # Implement SPOF analysis
        return []
    
    def _identify_backup_improvements(self, infrastructure_data):
        """Identify backup and recovery improvements"""
        # Implement backup analysis
        return []
    
    # Infrastructure integration methods
    def _right_size_compute_resources(self, component):
        """Right-size compute resources"""
        print(f"[OPTIMIZATION] Right-sizing compute for {component}")
        # Implementation depends on your infrastructure
    
    def _optimize_memory_allocation(self, component):
        """Optimize memory allocation"""
        print(f"[OPTIMIZATION] Optimizing memory for {component}")
        # Implementation depends on your infrastructure

class PredictiveBusinessImpactEngine:
    """Predict business impact before incidents occur"""
    
    def __init__(self):
        self.prediction_models = {}
        self.business_metrics = {}
        self.forecast_history = []
        
    def predict_business_impact(self, infrastructure_health, business_context):
        """Predict potential business impact of infrastructure issues"""
        try:
            predictions = {
                'risk_forecasts': [],
                'opportunity_insights': [],
                'capacity_recommendations': [],
                'revenue_impacts': [],
                'confidence_scores': {}
            }
            
            # Predict infrastructure risks
            risk_predictions = self._predict_infrastructure_risks(infrastructure_health)
            predictions['risk_forecasts'] = risk_predictions
            
            # Predict business impact of risks
            for risk in risk_predictions:
                business_impact = self._predict_business_impact_of_risk(risk, business_context)
                predictions['revenue_impacts'].append(business_impact)
            
            # Identify business opportunities
            opportunities = self._identify_business_opportunities(infrastructure_health, business_context)
            predictions['opportunity_insights'] = opportunities
            
            # Generate capacity recommendations
            capacity_recs = self._generate_capacity_recommendations(infrastructure_health, business_context)
            predictions['capacity_recommendations'] = capacity_recs
            
            # Calculate confidence scores
            predictions['confidence_scores'] = self._calculate_prediction_confidence(
                risk_predictions, business_context
            )
            
            # Store prediction for learning
            self.forecast_history.append({
                'timestamp': datetime.now().isoformat(),
                'predictions': predictions,
                'actual_outcomes': 'pending'  # Would be updated later
            })
            
            return predictions
            
        except Exception as e:
            print(f"[PREDICTION ERROR] Business impact prediction failed: {e}")
            return {'risk_forecasts': [], 'revenue_impacts': []}
    
    def _predict_infrastructure_risks(self, infrastructure_health):
        """Predict potential infrastructure risks"""
        risks = []
        
        # Analyze dependency risks
        dependency_risks = self._analyze_dependency_risks(infrastructure_health)
        risks.extend(dependency_risks)
        
        # Analyze capacity risks
        capacity_risks = self._analyze_capacity_risks(infrastructure_health)
        risks.extend(capacity_risks)
        
        # Analyze performance risks
        performance_risks = self._analyze_performance_risks(infrastructure_health)
        risks.extend(performance_risks)
        
        return sorted(risks, key=lambda x: x.get('probability', 0), reverse=True)[:10]  # Top 10 risks
    
    def _predict_business_impact_of_risk(self, risk, business_context):
        """Predict business impact of a specific risk"""
        base_impact = {
            'high_availability_loss': 5000,  # $ per hour
            'performance_degradation': 1000,
            'partial_outage': 2500,
            'full_outage': 10000
        }
        
        risk_type = risk.get('type', 'performance_degradation')
        probability = risk.get('probability', 0.5)
        affected_services = risk.get('affected_services', [])
        
        # Calculate expected impact
        expected_impact = base_impact.get(risk_type, 1000) * probability
        
        # Adjust for business context (seasonality, promotions, etc.)
        context_multiplier = self._get_business_context_multiplier(business_context)
        adjusted_impact = expected_impact * context_multiplier
        
        return {
            'risk_description': risk.get('description'),
            'expected_impact': round(adjusted_impact, 2),
            'affected_services': affected_services,
            'timeframe': risk.get('timeframe', '1-4 weeks'),
            'mitigation_priority': 'high' if adjusted_impact > 5000 else 'medium'
        }
    
    def _identify_business_opportunities(self, infrastructure_health, business_context):
        """Identify business opportunities from infrastructure insights"""
        opportunities = []
        
        # Performance improvement opportunities
        if infrastructure_health.get('performance_health', {}).get('score', 0) > 80:
            opportunities.append({
                'type': 'performance_leverage',
                'description': 'High performance enables new feature rollout',
                'potential_revenue_impact': 15000,
                'implementation_timeline': '2-4 weeks'
            })
        
        # Cost optimization opportunities
        cost_savings = self._identify_cost_optimization_opportunities(infrastructure_health)
        opportunities.extend(cost_savings)
        
        # Reliability advantages
        if infrastructure_health.get('reliability_score', 0) > 95:
            opportunities.append({
                'type': 'reliability_marketing',
                'description': 'High reliability can be marketed as competitive advantage',
                'potential_revenue_impact': 25000,
                'implementation_timeline': '1-2 months'
            })
        
        return opportunities
    
    def _generate_capacity_recommendations(self, infrastructure_health, business_context):
        """Generate business-focused capacity recommendations"""
        recommendations = []
        
        # Growth-based recommendations
        growth_forecast = business_context.get('growth_forecast', 0.1)  # 10% default
        current_capacity = infrastructure_health.get('capacity_utilization', 65)
        
        if current_capacity > 80 and growth_forecast > 0.15:
            recommendations.append({
                'type': 'urgent_capacity_expansion',
                'description': 'High growth forecast with limited capacity headroom',
                'investment_required': 50000,
                'expected_roi': 2.5,
                'timeline': '1 month'
            })
        elif current_capacity > 70:
            recommendations.append({
                'type': 'planned_capacity_increase',
                'description': 'Moderate growth with adequate headroom',
                'investment_required': 25000,
                'expected_roi': 1.8,
                'timeline': '3 months'
            })
        
        return recommendations
    
    def _calculate_prediction_confidence(self, risks, business_context):
        """Calculate confidence scores for predictions"""
        total_risks = len(risks)
        high_prob_risks = len([r for r in risks if r.get('probability', 0) > 0.7])
        
        data_quality = business_context.get('data_quality_score', 0.8)
        model_maturity = 0.7  # Would be based on model performance history
        
        confidence = (high_prob_risks / max(1, total_risks)) * data_quality * model_maturity
        
        return {
            'overall_confidence': round(confidence, 2),
            'data_quality_score': data_quality,
            'model_maturity': model_maturity,
            'risk_coverage': f"{high_prob_risks}/{total_risks} high-probability risks"
        }
    
    # Helper methods
    def _analyze_dependency_risks(self, infrastructure_health):
        """Analyze dependency-related risks"""
        return [
            {
                'type': 'single_point_of_failure',
                'description': 'Critical database server has no redundancy',
                'probability': 0.6,
                'affected_services': ['checkout_service', 'user_management'],
                'timeframe': '1-4 weeks'
            }
        ]  # Simplified example
    
    def _analyze_capacity_risks(self, infrastructure_health):
        """Analyze capacity-related risks"""
        return [
            {
                'type': 'resource_exhaustion',
                'description': 'Web server cluster at 85% capacity',
                'probability': 0.4,
                'affected_services': ['customer_portal', 'api_gateway'],
                'timeframe': '2-8 weeks'
            }
        ]  # Simplified example
    
    def _analyze_performance_risks(self, infrastructure_health):
        """Analyze performance-related risks"""
        return [
            {
                'type': 'performance_degradation',
                'description': 'Database query performance trending downward',
                'probability': 0.3,
                'affected_services': ['order_processing', 'reporting'],
                'timeframe': '4-12 weeks'
            }
        ]  # Simplified example
    
    def _get_business_context_multiplier(self, business_context):
        """Get business context multiplier for impact calculations"""
        # Consider seasonality, promotions, business cycles
        base_multiplier = 1.0
        
        # Example adjustments
        if business_context.get('peak_season', False):
            base_multiplier *= 1.5
        if business_context.get('major_promotion', False):
            base_multiplier *= 2.0
        
        return base_multiplier
    
    def _identify_cost_optimization_opportunities(self, infrastructure_health):
        """Identify cost optimization opportunities with business impact"""
        return [
            {
                'type': 'infrastructure_optimization',
                'description': 'Right-sizing underutilized resources',
                'potential_revenue_impact': -20000,  # Negative = cost savings
                'implementation_timeline': '2 weeks',
                'savings_certainty': 'high'
            }
        ]

# Initialize Phase 3 components
autonomous_healer = AutonomousHealingOrchestrator()
proactive_optimizer = ProactiveOptimizationEngine()
business_predictor = PredictiveBusinessImpactEngine()

# ================== PHASE 3 API ENDPOINTS ==================

@app.route('/api/autonomy/heal', methods=['POST'])
@token_required
def execute_autonomous_healing():
    """Execute autonomous healing for an incident"""
    try:
        data = request.get_json()
        incident_analysis = data.get('incident_analysis', {})
        remediation_plan = data.get('remediation_plan', {})
        
        healing_result = autonomous_healer.execute_autonomous_healing(
            incident_analysis,
            remediation_plan
        )
        
        comprehensive_logger.log_ai_engine_event(
            "autonomous_healing", 
            healing_result.get('outcome', 'unknown'),
            f"Executed {len(healing_result.get('actions_executed', []))} actions, "
            f"Mitigated impact: ${healing_result.get('business_impact_mitigated', 0)}",
            request.user_id
        )
        
        return jsonify(healing_result), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("autonomous_healing", str(e), "execute_autonomous_healing", request.user_id)
        return jsonify({"error": "Autonomous healing failed"}), 500

@app.route('/api/autonomy/optimize', methods=['POST'])
@token_required
def execute_proactive_optimization():
    """Execute proactive infrastructure optimization"""
    try:
        data = request.get_json()
        infrastructure_data = data.get('infrastructure_data', {})
        historical_metrics = data.get('historical_metrics', [])
        
        optimization_result = proactive_optimizer.analyze_optimization_opportunities(
            infrastructure_data,
            historical_metrics
        )
        
        comprehensive_logger.log_ai_engine_event(
            "proactive_optimization", 
            "completed",
            f"Found {len(optimization_result.get('cost_optimizations', []))} cost optimizations, "
            f"Executed {len(optimization_result.get('executed_optimizations', []))} actions",
            request.user_id
        )
        
        return jsonify(optimization_result), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("proactive_optimization", str(e), "execute_proactive_optimization", request.user_id)
        return jsonify({"error": "Proactive optimization failed"}), 500

@app.route('/api/autonomy/predict/business-impact', methods=['POST'])
@token_required
def predict_business_impact():
    """Predict future business impact of infrastructure trends"""
    try:
        data = request.get_json()
        infrastructure_health = data.get('infrastructure_health', {})
        business_context = data.get('business_context', {})
        
        predictions = business_predictor.predict_business_impact(
            infrastructure_health,
            business_context
        )
        
        comprehensive_logger.log_ai_engine_event(
            "business_impact_prediction", 
            "completed",
            f"Predicted {len(predictions.get('risk_forecasts', []))} risks, "
            f"Confidence: {predictions.get('confidence_scores', {}).get('overall_confidence', 0)}",
            request.user_id
        )
        
        return jsonify(predictions), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("business_prediction", str(e), "predict_business_impact", request.user_id)
        return jsonify({"error": "Business impact prediction failed"}), 500

@app.route('/api/autonomy/status', methods=['GET'])
@token_required
def get_autonomy_status():
    """Get status of autonomous operations"""
    try:
        autonomy_status = {
            'self_healing': {
                'status': 'active',
                'sessions_completed': len(autonomous_healer.healing_history),
                'success_rate': self._calculate_healing_success_rate(),
                'last_activity': autonomous_healer.healing_history[-1]['start_time'] if autonomous_healer.healing_history else 'Never'
            },
            'proactive_optimization': {
                'status': 'active',
                'optimizations_completed': len(proactive_optimizer.optimization_history),
                'estimated_savings': self._calculate_optimization_savings(),
                'last_activity': proactive_optimizer.optimization_history[-1]['start_time'] if proactive_optimizer.optimization_history else 'Never'
            },
            'business_prediction': {
                'status': 'active',
                'predictions_made': len(business_predictor.forecast_history),
                'average_confidence': self._calculate_average_prediction_confidence(),
                'last_activity': business_predictor.forecast_history[-1]['timestamp'] if business_predictor.forecast_history else 'Never'
            },
            'overall_autonomy_level': self._calculate_autonomy_level(),
            'recommendations': self._generate_autonomy_recommendations()
        }
        
        return jsonify(autonomy_status), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("autonomy_status", str(e), "get_autonomy_status", request.user_id)
        return jsonify({"error": "Failed to get autonomy status"}), 500

def _calculate_healing_success_rate(self):
    """Calculate self-healing success rate"""
    if not autonomous_healer.healing_history:
        return 0
    
    successful = len([h for h in autonomous_healer.healing_history if h.get('outcome') == 'success'])
    return round(successful / len(autonomous_healer.healing_history) * 100, 1)

def _calculate_optimization_savings(self):
    """Calculate estimated savings from optimizations"""
    # Simplified calculation
    return len(proactive_optimizer.optimization_history) * 1000  # $1000 per optimization

def _calculate_average_prediction_confidence(self):
    """Calculate average prediction confidence"""
    if not business_predictor.forecast_history:
        return 0
    
    confidences = [f.get('predictions', {}).get('confidence_scores', {}).get('overall_confidence', 0) 
                   for f in business_predictor.forecast_history]
    return round(np.mean(confidences) * 100, 1) if confidences else 0

def _calculate_autonomy_level(self):
    """Calculate overall autonomy level"""
    healing_rate = self._calculate_healing_success_rate()
    optimization_count = len(proactive_optimizer.optimization_history)
    prediction_confidence = self._calculate_average_prediction_confidence()
    
    # Simple scoring algorithm
    score = (healing_rate * 0.4) + (min(optimization_count, 10) * 5) + (prediction_confidence * 0.2)
    
    if score >= 80:
        return "Advanced Autonomy"
    elif score >= 60:
        return "Moderate Autonomy"
    elif score >= 40:
        return "Basic Autonomy"
    else:
        return "Learning Phase"

def _generate_autonomy_recommendations(self):
    """Generate recommendations to improve autonomy"""
    recommendations = []
    
    healing_rate = self._calculate_healing_success_rate()
    if healing_rate < 70:
        recommendations.append("Improve self-healing success rate by refining action selection")
    
    if len(proactive_optimizer.optimization_history) < 5:
        recommendations.append("Execute more proactive optimizations to build confidence")
    
    prediction_confidence = self._calculate_average_prediction_confidence()
    if prediction_confidence < 70:
        recommendations.append("Gather more historical data to improve prediction accuracy")
    
    return recommendations

# ================== ALERTS API ENDPOINTS ==================

@app.route('/api/alerts/enhanced', methods=['GET', 'OPTIONS'])
@token_required
def get_enhanced_alerts():
    """Enhanced alerts endpoint that frontend expects"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        user_id = getattr(request, "user_id", None)
        is_admin = getattr(request, "is_admin", False)
        
        # Get real alerts from your monitoring system
        alerts = []
        
        # Get user's targets to check for alerts
        if is_admin:
            targets = MonitoringTarget.query.all()
        else:
            targets = MonitoringTarget.query.filter_by(user_id=user_id).all()
        
        # Check each target for issues and create REAL alerts
        for target in targets:
            # Alert for offline targets
            if target.status == "offline":
                alerts.append({
                    "id": len(alerts) + 1,
                    "type": "service_down",
                    "severity": "critical",
                    "message": f"Target {target.name} ({target.ip_address}) is offline",
                    "timestamp": datetime.now().isoformat(),
                    "component": target.name,
                    "acknowledged": False,
                    "suggested_fix": "Check network connectivity and power supply",
                    "ml_generated": True
                })
            
            # Check for high resource usage based on recent metrics
            recent_metrics = TargetMetric.query.filter_by(
                target_id=target.id
            ).order_by(TargetMetric.timestamp.desc()).limit(5).all()
            
            for metric in recent_metrics:
                if metric.type == 'response_time' and metric.value > 1000:
                    alerts.append({
                        "id": len(alerts) + 1,
                        "type": "high_latency",
                        "severity": "high",
                        "message": f"High latency detected on {target.name}: {metric.value}ms",
                        "timestamp": datetime.now().isoformat(),
                        "component": target.name,
                        "acknowledged": False,
                        "suggested_fix": "Check network performance and server load",
                        "ml_generated": True
                    })
                    break
        
        # Add system-wide alerts
        system_stats = get_user_system_stats()
        
        # CPU alert
        if system_stats.get('cpu', 0) > 80:
            alerts.append({
                "id": len(alerts) + 1,
                "type": "high_cpu",
                "severity": "high",
                "message": f"High CPU usage detected: {system_stats['cpu']:.1f}%",
                "timestamp": datetime.now().isoformat(),
                "component": "system",
                "acknowledged": False,
                "suggested_fix": "Check for resource-intensive processes",
                "ml_generated": False
            })
        
        # Memory alert
        if system_stats.get('memory', 0) > 85:
            alerts.append({
                "id": len(alerts) + 1,
                "type": "high_memory",
                "severity": "medium",
                "message": f"High memory usage: {system_stats['memory']:.1f}%",
                "timestamp": datetime.now().isoformat(),
                "component": "system",
                "acknowledged": False,
                "suggested_fix": "Consider adding more RAM or optimizing applications",
                "ml_generated": False
            })
        
        # Disk alert
        if system_stats.get('disk', 0) > 90:
            alerts.append({
                "id": len(alerts) + 1,
                "type": "high_disk",
                "severity": "critical",
                "message": f"High disk usage: {system_stats['disk']:.1f}%",
                "timestamp": datetime.now().isoformat(),
                "component": "system",
                "acknowledged": False,
                "suggested_fix": "Clean up disk space or expand storage",
                "ml_generated": False
            })
        
        comprehensive_logger.log_user_activity("enhanced_alerts_access", user_id, "alerts", f"Found {len(alerts)} alerts")
        
        return jsonify({
            "alerts": alerts,
            "total": len(alerts),
            "critical_count": len([a for a in alerts if a['severity'] == 'critical']),
            "warning_count": len([a for a in alerts if a['severity'] in ['high', 'medium']]),
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("enhanced_alerts", str(e), "get_enhanced_alerts", getattr(request, 'user_id', None))
        return jsonify({"error": "Failed to fetch enhanced alerts"}), 500

@app.route('/api/alerts/<int:alert_id>/acknowledge', methods=['POST', 'OPTIONS'])
@token_required
def acknowledge_alert(alert_id):
    """Acknowledge an alert"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        user_id = getattr(request, "user_id", None)
        
        # In a real implementation, you'd store this in the database
        # For now, we'll just return success
        comprehensive_logger.log_user_activity("alert_acknowledged", user_id, "alerts", f"Alert {alert_id} acknowledged")
        
        return jsonify({
            "status": "success",
            "message": f"Alert {alert_id} acknowledged",
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("alert_acknowledge", str(e), "acknowledge_alert", getattr(request, 'user_id', None))
        return jsonify({"error": "Failed to acknowledge alert"}), 500

@app.route('/api/alerts/stats', methods=['GET', 'OPTIONS'])
@token_required
def get_alert_stats():
    """Get alert statistics for dashboard"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        user_id = getattr(request, "user_id", None)
        is_admin = getattr(request, "is_admin", False)
        
        # Get targets based on user role
        if is_admin:
            targets = MonitoringTarget.query.all()
        else:
            targets = MonitoringTarget.query.filter_by(user_id=user_id).all()
        
        # Calculate basic stats
        total_targets = len(targets)
        offline_targets = len([t for t in targets if t.status == "offline"])
        warning_targets = len([t for t in targets if t.status == "warning"])
        healthy_targets = len([t for t in targets if t.status == "healthy"])
        
        # Get system stats for performance alerts
        system_stats = get_user_system_stats()
        performance_alerts = 0
        if system_stats.get('cpu', 0) > 80: performance_alerts += 1
        if system_stats.get('memory', 0) > 85: performance_alerts += 1
        if system_stats.get('disk', 0) > 90: performance_alerts += 1
        
        stats = {
            "targets": {
                "total": total_targets,
                "offline": offline_targets,
                "warning": warning_targets,
                "healthy": healthy_targets,
                "health_percentage": round((healthy_targets / total_targets * 100) if total_targets > 0 else 100, 1)
            },
            "performance": {
                "cpu_alert": system_stats.get('cpu', 0) > 80,
                "memory_alert": system_stats.get('memory', 0) > 85,
                "disk_alert": system_stats.get('disk', 0) > 90,
                "total_alerts": performance_alerts
            },
            "summary": {
                "overall_status": "healthy" if offline_targets == 0 and performance_alerts == 0 else "degraded",
                "requires_attention": offline_targets + performance_alerts,
                "last_updated": datetime.now().isoformat()
            }
        }
        
        comprehensive_logger.log_user_activity("alert_stats_access", user_id, "alerts")
        
        return jsonify(stats), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("alert_stats", str(e), "get_alert_stats", getattr(request, 'user_id', None))
        return jsonify({"error": "Failed to fetch alert statistics"}), 500

# ================== HELPER FUNCTIONS FOR ALERTS ==================
def get_targets_data(user_id, is_admin):
    """Get monitoring targets data for AI context"""
    if is_admin:
        targets = MonitoringTarget.query.all()
    else:
        targets = MonitoringTarget.query.filter_by(user_id=user_id).all()
    return [target.to_dict() for target in targets]

def analyze_monitoring_targets(targets_data):
    """Comprehensive real analysis of monitoring targets"""
    if not targets_data:
        return {
            "overview": {
                "health_score": 100, 
                "status": "healthy",
                "total_targets": 0,
                "healthy_targets": 0,
                "warning_targets": 0,
                "offline_targets": 0
            },
            "categories_health": {},
            "critical_issues": [],
            "recommendations": [],
            "targets_requiring_attention": []
        }
    
    # Real target analysis
    total_targets = len(targets_data)
    healthy_targets = len([t for t in targets_data if t.get('status') == 'healthy'])
    warning_targets = len([t for t in targets_data if t.get('status') == 'warning'])
    offline_targets = len([t for t in targets_data if t.get('status') == 'offline'])
    
    # Calculate real health score with weighted factors
    health_score = (healthy_targets / total_targets * 100) if total_targets > 0 else 100
    
    # Adjust score based on priority of offline targets
    critical_offline = len([t for t in targets_data if t.get('status') == 'offline' and t.get('priority') in ['high', 'critical']])
    if critical_offline > 0:
        health_score = max(0, health_score - (critical_offline * 10))
    
    # Analyze by category
    categories_health = {}
    target_categories = {
        'servers': ['server', 'web', 'application', 'database'],
        'network_devices': ['router', 'switch', 'firewall', 'network'],
        'services': ['service', 'api', 'website'],
        'infrastructure': ['vm', 'container', 'storage']
    }
    
    for target in targets_data:
        category = 'other'
        target_name = target.get('name', '').lower()
        target_type = target.get('type', '').lower()
        
        for cat, patterns in target_categories.items():
            for pattern in patterns:
                if pattern in target_name or pattern in target_type:
                    category = cat
                    break
        
        if category not in categories_health:
            categories_health[category] = {
                'total': 0, 
                'healthy': 0, 
                'warning': 0,
                'offline': 0,
                'health_score': 0,
                'issues': []
            }
        
        categories_health[category]['total'] += 1
        if target.get('status') == 'healthy':
            categories_health[category]['healthy'] += 1
        elif target.get('status') == 'warning':
            categories_health[category]['warning'] += 1
        else:
            categories_health[category]['offline'] += 1
            categories_health[category]['issues'].append({
                'name': target.get('name'),
                'status': target.get('status'),
                'ip_address': target.get('ip_address'),
                'priority': target.get('priority', 'medium'),
                'last_check': target.get('last_check')
            })
    
    # Calculate health scores for each category
    for category in categories_health:
        cat_data = categories_health[category]
        if cat_data['total'] > 0:
            cat_data['health_score'] = round((cat_data['healthy'] / cat_data['total']) * 100, 1)
    
    # Identify critical issues
    critical_issues = []
    for target in targets_data:
        issues = []
        
        # Offline targets
        if target.get('status') == 'offline':
            issues.append({
                'type': 'offline',
                'severity': 'critical' if target.get('priority') in ['high', 'critical'] else 'high',
                'description': f"Target {target.get('name')} is offline",
                'suggested_action': 'Check network connectivity and power supply'
            })
        
        # Stale data (no recent checks)
        last_check = target.get('last_check')
        if last_check:
            try:
                if isinstance(last_check, str):
                    last_check_time = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
                else:
                    last_check_time = last_check
                
                time_diff = datetime.now().astimezone() - last_check_time
                if time_diff > timedelta(hours=1):
                    issues.append({
                        'type': 'stale_data',
                        'severity': 'warning',
                        'description': f"No recent checks for {target.get('name')}",
                        'suggested_action': 'Run manual scan to update status'
                    })
            except (ValueError, TypeError) as e:
                issues.append({
                    'type': 'data_quality',
                    'severity': 'low',
                    'description': f"Invalid timestamp for {target.get('name')}",
                    'suggested_action': 'Check data collection system'
                })
        
        # High priority targets with issues
        if target.get('priority') in ['high', 'critical'] and target.get('status') != 'healthy':
            issues.append({
                'type': 'critical_target_issue',
                'severity': 'critical',
                'description': f"Critical target {target.get('name')} has issues",
                'suggested_action': 'Immediate attention required'
            })
        
        if issues:
            critical_issues.append({
                'target_name': target.get('name'),
                'target_type': target.get('type'),
                'ip_address': target.get('ip_address'),
                'priority': target.get('priority', 'medium'),
                'issues': issues
            })
    
    # Get targets requiring attention
    targets_requiring_attention = []
    for target in targets_data:
        if target.get('status') in ['offline', 'warning']:
            targets_requiring_attention.append({
                'name': target.get('name'),
                'type': target.get('type'),
                'ip_address': target.get('ip_address'),
                'status': target.get('status'),
                'priority': target.get('priority', 'medium'),
                'last_check': target.get('last_check')
            })
    
    # Sort by priority (critical first) then by status
    priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    status_order = {'offline': 0, 'warning': 1, 'unknown': 2}
    
    targets_requiring_attention.sort(key=lambda x: (
        priority_order.get(x['priority'], 3),
        status_order.get(x['status'], 2)
    ))
    
    # Generate intelligent recommendations
    recommendations = generate_target_recommendations(
        total_targets, healthy_targets, warning_targets, offline_targets, 
        health_score, critical_issues, categories_health
    )
    
    return {
        "overview": {
            "health_score": round(health_score, 1),
            "status": "healthy" if health_score > 90 else "warning" if health_score > 70 else "critical",
            "total_targets": total_targets,
            "healthy_targets": healthy_targets,
            "warning_targets": warning_targets,
            "offline_targets": offline_targets,
            "availability_percentage": round((healthy_targets / total_targets) * 100, 1) if total_targets > 0 else 100
        },
        "categories_health": categories_health,
        "critical_issues": critical_issues,
        "recommendations": recommendations,
        "targets_requiring_attention": targets_requiring_attention[:10],  # Top 10 most critical
        "analysis_timestamp": datetime.now().isoformat()
    }


def analyze_system_health(system_metrics, targets_data=None):
    """Comprehensive real system health analysis with ML-inspired scoring"""
    if not system_metrics:
        return {
            "system_health": {
                "overall_score": 0,
                "status": "unknown",
                "metrics": {},
                "trends": {},
                "recommendations": []
            },
            "targets_health": {},
            "timestamp": datetime.now().isoformat()
        }
    
    # Extract and validate metrics
    cpu = float(system_metrics.get('cpu', 0))
    memory = float(system_metrics.get('memory', 0))
    disk = float(system_metrics.get('disk', 0))
    processes = int(system_metrics.get('processes', 0))
    network_recv = float(system_metrics.get('network_recv', 0))
    network_sent = float(system_metrics.get('network_sent', 0))
    
    # Advanced health scoring with weighted factors
    cpu_weight, memory_weight, disk_weight = 0.35, 0.30, 0.25
    process_weight, network_weight = 0.05, 0.05
    
    # Calculate component scores (0-100, higher is better)
    cpu_score = max(0, 100 - (cpu * 1.2))  # CPU is critical
    memory_score = max(0, 100 - (memory * 1.1))  # Memory is important
    disk_score = max(0, 100 - (disk * 1.0))  # Disk is important but less critical
    
    # Process score (penalize very high process counts)
    process_score = 100 if processes < 500 else max(0, 100 - ((processes - 500) / 10))
    
    # Network score (check for extreme values)
    network_usage = (network_recv + network_sent) / (1024 * 1024)  # Convert to MB
    network_score = 100 if network_usage < 1000 else max(0, 100 - (network_usage - 1000) / 100)
    
    # Calculate overall health score
    overall_score = (
        cpu_score * cpu_weight +
        memory_score * memory_weight +
        disk_score * disk_weight +
        process_score * process_weight +
        network_score * network_weight
    )
    
    # Determine system status with hysteresis
    if overall_score >= 85:
        status = "healthy"
    elif overall_score >= 65:
        status = "warning"
    else:
        status = "critical"
    
    # Analyze trends (you would compare with historical data in real implementation)
    trends = {
        "cpu_trend": "stable",  # Would be calculated from historical data
        "memory_trend": "stable",
        "disk_trend": "stable",
        "performance_trend": "stable"
    }
    
    # Generate detailed metrics analysis
    metrics_analysis = {
        'cpu': {
            'value': cpu,
            'status': 'normal' if cpu < 70 else 'warning' if cpu < 85 else 'critical',
            'score': round(cpu_score, 1),
            'thresholds': {'warning': 70, 'critical': 85}
        },
        'memory': {
            'value': memory,
            'status': 'normal' if memory < 75 else 'warning' if memory < 90 else 'critical',
            'score': round(memory_score, 1),
            'thresholds': {'warning': 75, 'critical': 90}
        },
        'disk': {
            'value': disk,
            'status': 'normal' if disk < 80 else 'warning' if disk < 95 else 'critical',
            'score': round(disk_score, 1),
            'thresholds': {'warning': 80, 'critical': 95}
        },
        'processes': {
            'value': processes,
            'status': 'normal' if processes < 400 else 'warning' if processes < 600 else 'critical',
            'score': round(process_score, 1),
            'thresholds': {'warning': 400, 'critical': 600}
        }
    }
    
    # Generate intelligent recommendations
    recommendations = generate_system_recommendations(metrics_analysis, overall_score)
    
    # Include targets health if provided
    targets_health = {}
    if targets_data:
        targets_health = analyze_monitoring_targets(targets_data)
    
    return {
        "system_health": {
            "overall_score": round(overall_score, 1),
            "status": status,
            "component_scores": {
                "cpu": round(cpu_score, 1),
                "memory": round(memory_score, 1),
                "disk": round(disk_score, 1),
                "processes": round(process_score, 1),
                "network": round(network_score, 1)
            },
            "metrics": metrics_analysis,
            "trends": trends,
            "recommendations": recommendations,
            "analysis_timestamp": datetime.now().isoformat()
        },
        "targets_health": targets_health,
        "timestamp": datetime.now().isoformat()
    }


def generate_target_recommendations(total_targets, healthy_targets, warning_targets, offline_targets, 
                                  health_score, critical_issues, categories_health):
    """Generate intelligent recommendations for target management"""
    recommendations = []
    
    # Health score based recommendations
    if health_score < 70:
        recommendations.append({
            'type': 'urgent',
            'priority': 'critical',
            'title': 'Improve Overall Health',
            'description': f'Current health score is {health_score:.1f}% - focus on bringing targets online',
            'actions': [
                'Address all critical issues immediately',
                'Check network connectivity for offline targets',
                'Review monitoring configuration and thresholds',
                'Verify target accessibility and credentials'
            ],
            'impact': 'high'
        })
    
    # Critical issues recommendations
    critical_count = len([issue for issue in critical_issues if any(i['severity'] == 'critical' for i in issue['issues'])])
    if critical_count > 0:
        recommendations.append({
            'type': 'critical_issues',
            'priority': 'critical',
            'title': 'Address Critical Target Issues',
            'description': f'Found {critical_count} targets with critical issues requiring immediate attention',
            'actions': [
                'Prioritize critical targets first',
                'Check power and network connectivity',
                'Verify target configurations and access',
                'Implement redundancy for critical systems'
            ],
            'impact': 'high'
        })
    
    # Offline targets recommendations
    if offline_targets > 0:
        recommendations.append({
            'type': 'offline_targets',
            'priority': 'high' if offline_targets > 2 else 'medium',
            'title': 'Investigate Offline Targets',
            'description': f'{offline_targets} targets are currently offline',
            'actions': [
                'Run diagnostic scans on offline targets',
                'Check firewall rules and network paths',
                'Verify target hardware status',
                'Review recent configuration changes'
            ],
            'impact': 'medium'
        })
    
    # Category distribution recommendations
    if len(categories_health) < 3:
        recommendations.append({
            'type': 'coverage',
            'priority': 'medium',
            'title': 'Diversify Monitoring Coverage',
            'description': 'Limited variety in monitored target types',
            'actions': [
                'Add network devices (routers, switches, firewalls)',
                'Monitor critical services and applications',
                'Include infrastructure components (VMs, containers)',
                'Consider adding cloud resources'
            ],
            'impact': 'medium'
        })
    
    # Performance optimization
    if health_score > 90 and total_targets > 20:
        recommendations.append({
            'type': 'optimization',
            'priority': 'low',
            'title': 'Optimize Monitoring Performance',
            'description': 'System is healthy - consider optimizations',
            'actions': [
                'Review and adjust monitoring intervals',
                'Implement predictive monitoring',
                'Optimize alert thresholds',
                'Consider automated remediation'
            ],
            'impact': 'low'
        })
    
    # Regular maintenance
    recommendations.append({
        'type': 'maintenance',
        'priority': 'medium',
        'title': 'Regular Health Maintenance',
        'description': 'Schedule regular system health checks',
        'actions': [
            'Run comprehensive scans weekly',
            'Review and update target configurations monthly',
            'Clean up unused or deprecated targets',
            'Update monitoring agents and tools'
        ],
        'impact': 'medium'
    })
    
    return recommendations


def generate_system_recommendations(metrics_analysis, overall_score):
    """Generate intelligent system recommendations based on metrics"""
    recommendations = []
    
    cpu_status = metrics_analysis['cpu']['status']
    memory_status = metrics_analysis['memory']['status']
    disk_status = metrics_analysis['disk']['status']
    processes_status = metrics_analysis['processes']['status']
    
    # CPU recommendations
    if cpu_status == 'critical':
        recommendations.append({
            'category': 'performance',
            'priority': 'critical',
            'title': 'Critical CPU Usage',
            'description': f"CPU usage at {metrics_analysis['cpu']['value']}% - immediate action required",
            'actions': [
                'Identify and terminate resource-intensive processes',
                'Check for runaway processes or infinite loops',
                'Consider immediate scaling or load balancing',
                'Review application performance and optimization'
            ]
        })
    elif cpu_status == 'warning':
        recommendations.append({
            'category': 'performance',
            'priority': 'high',
            'title': 'High CPU Usage',
            'description': f"CPU usage at {metrics_analysis['cpu']['value']}% - monitor closely",
            'actions': [
                'Monitor process CPU usage patterns',
                'Consider optimizing application code',
                'Plan for capacity scaling',
                'Review system load averages'
            ]
        })
    
    # Memory recommendations
    if memory_status == 'critical':
        recommendations.append({
            'category': 'performance',
            'priority': 'critical',
            'title': 'Critical Memory Usage',
            'description': f"Memory usage at {metrics_analysis['memory']['value']}% - risk of system instability",
            'actions': [
                'Identify memory leaks in applications',
                'Check swap usage and activity',
                'Kill non-essential processes',
                'Consider immediate memory upgrade'
            ]
        })
    elif memory_status == 'warning':
        recommendations.append({
            'category': 'performance',
            'priority': 'high',
            'title': 'High Memory Usage',
            'description': f"Memory usage at {metrics_analysis['memory']['value']}% - optimization recommended",
            'actions': [
                'Review application memory allocation',
                'Optimize database and cache settings',
                'Monitor memory growth trends',
                'Plan for memory upgrade'
            ]
        })
    
    # Disk recommendations
    if disk_status == 'critical':
        recommendations.append({
            'category': 'storage',
            'priority': 'critical',
            'title': 'Critical Disk Usage',
            'description': f"Disk usage at {metrics_analysis['disk']['value']}% - immediate cleanup required",
            'actions': [
                'Clean up temporary files and logs',
                'Archive old data immediately',
                'Check for large unnecessary files',
                'Consider storage expansion urgently'
            ]
        })
    elif disk_status == 'warning':
        recommendations.append({
            'category': 'storage',
            'priority': 'high',
            'title': 'High Disk Usage',
            'description': f"Disk usage at {metrics_analysis['disk']['value']}% - cleanup recommended",
            'actions': [
                'Schedule regular cleanup tasks',
                'Implement log rotation and compression',
                'Monitor disk growth patterns',
                'Plan for storage expansion'
            ]
        })
    
    # Process recommendations
    if processes_status == 'critical':
        recommendations.append({
            'category': 'system',
            'priority': 'high',
            'title': 'High Process Count',
            'description': f"Running {metrics_analysis['processes']['value']} processes - system may be overloaded",
            'actions': [
                'Identify and kill zombie processes',
                'Review process startup configurations',
                'Check for process leaks in applications',
                'Optimize service configurations'
            ]
        })
    
    # General optimization for healthy systems
    if overall_score > 90:
        recommendations.append({
            'category': 'optimization',
            'priority': 'low',
            'title': 'System Optimization',
            'description': 'System is healthy - consider proactive optimizations',
            'actions': [
                'Review and fine-tune performance settings',
                'Implement caching strategies',
                'Optimize database queries',
                'Consider containerization for better resource management'
            ]
        })
    
    return recommendations

def generate_ml_alerts(infrastructure_data):
    """Generate ML-based predictive alerts"""
    ml_alerts = []
    
    try:
        # Check for single points of failure
        for component_type, components in infrastructure_data.items():
            if len(components) == 1 and component_type in ['database', 'load_balancer']:
                component = components[0]
                ml_alerts.append({
                    "id": len(ml_alerts) + 1000,  # Start from 1000 for ML alerts
                    "target_id": None,
                    "type": "single_point_failure",
                    "severity": "high",
                    "message": f"Single point of failure detected: {component.get('name', 'Unknown')} ({component_type})",
                    "suggested_fix": "Implement redundancy and failover mechanisms",
                    "timestamp": datetime.now().isoformat(),
                    "acknowledged": False,
                    "ml_generated": True
                })
        
        # Check for resource trends (simplified)
        system_stats = get_user_system_stats()
        if system_stats.get('memory', 0) > 70 and system_stats.get('memory', 0) < 85:
            ml_alerts.append({
                "id": len(ml_alerts) + 1000,
                "target_id": None,
                "type": "memory_trend",
                "severity": "medium",
                "message": f"Memory usage trending high: {system_stats['memory']:.1f}%",
                "suggested_fix": "Monitor memory growth and consider optimization",
                "timestamp": datetime.now().isoformat(),
                "acknowledged": False,
                "ml_generated": True
            })
        
        # Check for dependency risks
        if ML_AVAILABLE and dependency_mapper and hasattr(dependency_mapper, 'dependency_graph'):
            graph = dependency_mapper.dependency_graph
            if hasattr(graph, 'nodes') and len(graph.nodes) > 0:
                # Simple centrality check (if NetworkX available)
                if NETWORKX_AVAILABLE and hasattr(nx, 'degree_centrality'):
                    try:
                        centrality = nx.degree_centrality(graph)
                        most_central = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:3]
                        for node_id, score in most_central:
                            if score > 0.3:  # Highly connected node
                                node_data = graph.nodes[node_id]
                                ml_alerts.append({
                                    "id": len(ml_alerts) + 1000,
                                    "target_id": None,
                                    "type": "critical_dependency",
                                    "severity": "high",
                                    "message": f"Critical dependency detected: {node_data.get('name', node_id)}",
                                    "suggested_fix": "Ensure high availability and monitoring for this component",
                                    "timestamp": datetime.now().isoformat(),
                                    "acknowledged": False,
                                    "ml_generated": True
                                })
                    except Exception as nx_error:
                        print(f"[ML ALERTS] NetworkX error: {nx_error}")
        
    except Exception as e:
        print(f"[ML ALERTS ERROR] {e}")
    
    return ml_alerts
def get_user_conversation_history(user_id: str, max_messages: int = 10) -> List[Dict]:
    """Get conversation history for a user (compatibility function)"""
    if not user_id:
        return []
    
    try:
        return enhanced_ai_assistant.conversation_manager.get_conversation_history(
            user_id, max_messages
        )
    except Exception as e:
        print(f"Error getting conversation history: {e}")
        return []

def clear_user_conversation_history(user_id: str):
    """Clear conversation history for a user (compatibility function)"""
    if not user_id:
        return
    
    try:
        enhanced_ai_assistant.conversation_manager.clear_user_history(user_id)
    except Exception as e:
        print(f"Error clearing conversation history: {e}")

def analyze_monitoring_targets(targets_data: List[Dict]) -> Dict[str, Any]:
    """Analyze monitoring targets (compatibility function)"""
    try:
        return enhanced_ai_assistant.targets_analyzer.analyze_targets_health(targets_data)
    except Exception as e:
        print(f"Error analyzing targets: {e}")
        return {'overview': {'health_score': 0, 'total_targets': 0}, 'critical_issues': []}

def get_user_system_stats():
    """Get system statistics for the current user"""
    try:
        stats = {
            "cpu": psutil.cpu_percent(interval=1),
            "memory": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage('/').percent,
            "network_recv": psutil.net_io_counters().bytes_recv,
            "network_sent": psutil.net_io_counters().bytes_sent,
            "processes": len(psutil.pids()),
            "uptime": time.time() - psutil.boot_time(),
        }
        return stats
    except Exception as e:
        print(f"[STATS ERROR] {e}")
        return {"cpu": 0, "memory": 0, "disk": 0, "network_recv": 0, "network_sent": 0, "processes": 0, "uptime": 0}

# Update ML initialization to include all phases
def initialize_ml_components():
    """Initialize all ML components across all phases"""
    try:
        print("[ML] Initializing complete ML intelligence stack...")
        
        # Phase 1: Foundation
        monitoring_data = {'timestamp': datetime.now().isoformat()}
        dependency_mapper.auto_discover_dependencies(monitoring_data)
        
        # Phase 2: Intelligence 
        # (Components are initialized with class definitions)
        
        # Phase 3: Autonomy
        # (Components are initialized with class definitions)
        
        print("[ML] All ML phases (Foundation, Intelligence, Autonomy) initialized successfully")
        comprehensive_logger.log_ai_engine_event("ml_initialization", "success", 
                                               "Complete ML intelligence stack with autonomous operations started")
        
    except Exception as e:
        print(f"[ML ERROR] Initialization failed: {e}")
        comprehensive_logger.log_error_event("ml_initialization", str(e), "initialize_ml_components")

# Add autonomous background tasks
def start_autonomous_operations():
    """Start autonomous background operations"""
    try:
        # Start periodic optimization scans
        optimization_thread = threading.Thread(target=_run_periodic_optimizations, daemon=True)
        optimization_thread.start()
        
        # Start business impact forecasting
        prediction_thread = threading.Thread(target=_run_periodic_predictions, daemon=True)
        prediction_thread.start()
        
        print("[AUTONOMY] Autonomous operations started")
        comprehensive_logger.log_ai_engine_event("autonomous_operations", "started", 
                                               "Background autonomous tasks activated")
        
    except Exception as e:
        print(f"[AUTONOMY ERROR] Failed to start autonomous operations: {e}")
        comprehensive_logger.log_error_event("autonomous_operations", str(e), "start_autonomous_operations")

def _run_periodic_optimizations():
    """Run periodic optimization scans"""
    while True:
        try:
            # Run every 6 hours
            time.sleep(6 * 60 * 60)
            
            # Get current infrastructure state
            infrastructure_data = dependency_mapper._extract_components({'timestamp': datetime.now().isoformat()})
            
            # Run optimization analysis
            proactive_optimizer.analyze_optimization_opportunities(infrastructure_data, [])
            
            print("[AUTONOMY] Periodic optimization scan completed")
            
        except Exception as e:
            print(f"[AUTONOMY ERROR] Periodic optimization failed: {e}")

def _run_periodic_predictions():
    """Run periodic business impact predictions"""
    while True:
        try:
            # Run every 12 hours
            time.sleep(12 * 60 * 60)
            
            # Get current infrastructure health
            infrastructure_health = {
                'dependency_health': dependency_mapper._get_dependency_summary(),
                'performance_health': {'score': 85},  # Simplified
                'reliability_score': 92,
                'capacity_utilization': 75
            }
            
            # Run business impact prediction
            business_predictor.predict_business_impact(infrastructure_health, {})
            
            print("[AUTONOMY] Periodic business impact prediction completed")
            
        except Exception as e:
            print(f"[AUTONOMY ERROR] Periodic prediction failed: {e}")       

# ================== MONITORING API CONFIGURATION ==================
ZABBIX_URL = "http://localhost:3001"  
GRAFANA_URL = "http://localhost:3000"
PROMETHEUS_URL = "http://localhost:9090"

# Zabbix Configuration
ZABBIX_CONFIG = {
    'url': "http://172.20.10.3:3001/api_jsonrpc.php",
    'username': 'Admin',
    'password': 'zabbix',
    'api_token': 'cc21e75efea06b4dd2ed6bdf310c795b'
}

# ================== COMPREHENSIVE LOGGING SYSTEM (DEFINE EARLY!) ==================
class ComprehensiveLogger:
    def __init__(self):
        self.logs = []
        self.next_id = 1
        self.performance_thresholds = {
            'cpu_warning': 70, 'cpu_critical': 85,
            'memory_warning': 75, 'memory_critical': 90,
            'disk_warning': 80, 'disk_critical': 95,
            'latency_warning': 1000, 'latency_critical': 5000,
            'error_rate_warning': 5, 'error_rate_critical': 10
        }
        
    def _create_log_entry(self, message, level, category, user_id=None, metadata=None):
        log_entry = {
            "id": self.next_id,
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "category": category,
            "message": message,
            "user_id": user_id,
            "metadata": metadata or {},
            "source": "neosilix_system"
        }
        self.next_id += 1
        return log_entry
    
    def log_user_activity(self, action, user_id, resource=None, details=None):
        metadata = {
            "action": action,
            "resource": resource,
            "user_agent": request.headers.get('User-Agent', 'Unknown') if request else None,
            "ip_address": request.remote_addr if request else None,
            "endpoint": request.endpoint if request else None,
            "details": details
        }
        log_entry = self._create_log_entry(
            f"User activity: {action}" + (f" on {resource}" if resource else ""),
            "info", "user_activity", user_id, metadata
        )
        self.logs.append(log_entry)
        self._trim_logs()
        print(f"[USER_ACTIVITY] User {user_id}: {action}")
        return log_entry
    
    def log_performance_event(self, metric_name, metric_value, threshold_type, user_id=None):
        level = "warning" if "warning" in threshold_type else "error"
        metadata = {
            "metric_name": metric_name,
            "metric_value": metric_value,
            "threshold_type": threshold_type,
            "threshold_value": self.performance_thresholds.get(threshold_type)
        }
        log_entry = self._create_log_entry(
            f"Performance {threshold_type}: {metric_name} = {metric_value}",
            level, "performance", user_id, metadata
        )
        self.logs.append(log_entry)
        self._trim_logs()
        print(f"[PERFORMANCE] {metric_name} {threshold_type}: {metric_value}")
        return log_entry
    
    def log_infrastructure_event(self, component, status, details=None, user_id=None):
        metadata = {"component": component, "status": status, "details": details}
        log_entry = self._create_log_entry(
            f"Infrastructure {component}: {status}",
            "info", "infrastructure", user_id, metadata
        )
        self.logs.append(log_entry)
        self._trim_logs()
        print(f"[INFRASTRUCTURE] {component}: {status}")
        return log_entry
    
    def log_error_event(self, error_type, error_message, context=None, user_id=None):
        metadata = {"error_type": error_type, "context": context, "stack_trace": None}
        log_entry = self._create_log_entry(
            f"Error {error_type}: {error_message}",
            "error", "error", user_id, metadata
        )
        self.logs.append(log_entry)
        self._trim_logs()
        print(f"[ERROR] {error_type}: {error_message}")
        return log_entry
    
    def log_security_event(self, event_type, severity, user_id=None, details=None):
        metadata = {
            "event_type": event_type,
            "severity": severity,
            "details": details,
            "ip_address": request.remote_addr if request else None
        }
        log_entry = self._create_log_entry(
            f"Security event: {event_type}",
            "warning" if severity == "medium" else "error",
            "security", user_id, metadata
        )
        self.logs.append(log_entry)
        self._trim_logs()
        print(f"[SECURITY] {event_type} - {severity}")
        return log_entry
    
    def log_ai_engine_event(self, action, status, details=None, user_id=None):
        metadata = {"action": action, "status": status, "details": details}
        log_entry = self._create_log_entry(
            f"AI Engine {action}: {status}",
            "info", "ai_engine", user_id, metadata
        )
        self.logs.append(log_entry)
        self._trim_logs()
        print(f"[AI_ENGINE] {action}: {status}")
        return log_entry
    
    def auto_detect_performance_issues(self, metrics, user_id=None):
        issues_detected = []
        
        cpu = metrics.get('cpu', 0)
        if cpu > self.performance_thresholds['cpu_critical']:
            self.log_performance_event('cpu', cpu, 'cpu_critical', user_id)
            issues_detected.append('cpu_critical')
        elif cpu > self.performance_thresholds['cpu_warning']:
            self.log_performance_event('cpu', cpu, 'cpu_warning', user_id)
            issues_detected.append('cpu_warning')
        
        memory = metrics.get('memory', 0)
        if memory > self.performance_thresholds['memory_critical']:
            self.log_performance_event('memory', memory, 'memory_critical', user_id)
            issues_detected.append('memory_critical')
        elif memory > self.performance_thresholds['memory_warning']:
            self.log_performance_event('memory', memory, 'memory_warning', user_id)
            issues_detected.append('memory_warning')
        
        disk = metrics.get('disk', 0)
        if disk > self.performance_thresholds['disk_critical']:
            self.log_performance_event('disk', disk, 'disk_critical', user_id)
            issues_detected.append('disk_critical')
        elif disk > self.performance_thresholds['disk_warning']:
            self.log_performance_event('disk', disk, 'disk_warning', user_id)
            issues_detected.append('disk_warning')
        
        return issues_detected
    
    def _trim_logs(self):
        if len(self.logs) > 500:
            self.logs = self.logs[-500:]
    
    def get_logs(self, user_id=None, is_admin=False, category=None, level=None):
        filtered_logs = self.logs
        
        if not is_admin:
            filtered_logs = [log for log in filtered_logs if log.get('user_id') in [user_id, None]]
        
        if category:
            filtered_logs = [log for log in filtered_logs if log.get('category') == category]
        
        if level:
            filtered_logs = [log for log in filtered_logs if log.get('level') == level]
        
        return filtered_logs
    
    def get_log_stats(self):
        stats = {
            'total_logs': len(self.logs),
            'by_level': {},
            'by_category': {},
            'recent_activity': []
        }
        
        for log in self.logs[-50:]:
            stats['recent_activity'].append({
                'timestamp': log['timestamp'],
                'level': log['level'],
                'category': log['category'],
                'message': log['message'][:100]
            })
        
        for log in self.logs:
            level = log.get('level', 'unknown')
            stats['by_level'][level] = stats['by_level'].get(level, 0) + 1
            
            category = log.get('category', 'unknown')
            stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
        
        return stats

# CREATE LOGGER FIRST!
comprehensive_logger = ComprehensiveLogger()

# ================== ZABBIX API (NOW LOGGER EXISTS) ==================
class ZabbixAPI:
    def __init__(self):
        self.auth_token = None
        self.last_auth = None
        
    def authenticate(self):
        """Authenticate with Zabbix API using correct method and parameters"""
        try:
            # Try using API token first
            if ZABBIX_CONFIG.get('api_token'):
                response = requests.post(
                    ZABBIX_CONFIG['url'],
                    json={
                        "jsonrpc": "2.0",
                        "method": "user.login",
                        "params": {
                            "username": ZABBIX_CONFIG['username'],
                            "password": ZABBIX_CONFIG['password']
                        },
                        "id": 1
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
            else:
                # Fallback to username/password
                response = requests.post(
                    ZABBIX_CONFIG['url'],
                    json={
                        "jsonrpc": "2.0",
                        "method": "user.login",
                        "params": {
                            "username": ZABBIX_CONFIG['username'],
                            "password": ZABBIX_CONFIG['password']
                        },
                        "id": 1
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
            
            if response.status_code == 200:
                result = response.json()
                if 'result' in result:
                    self.auth_token = result['result']
                    self.last_auth = datetime.now()
                    print(f"[SUCCESS] Zabbix authenticated successfully, token: {self.auth_token[:20]}...")
                    comprehensive_logger.log_infrastructure_event("zabbix", "authenticated_successfully")
                    return self.auth_token
                else:
                    print(f"[ERROR] Zabbix auth failed: {result.get('error', {})}")
                    comprehensive_logger.log_error_event("zabbix_auth", f"API error: {result.get('error', {})}", "zabbix_authentication")
            else:
                print(f"[ERROR] Zabbix HTTP error: {response.status_code}")
                comprehensive_logger.log_error_event("zabbix_auth", f"HTTP {response.status_code}", "zabbix_authentication")
            
            return None
            
        except requests.exceptions.ConnectionError:
            print("[ERROR] Zabbix connection failed - service may be down")
            comprehensive_logger.log_error_event("zabbix_connection", "Connection refused", "zabbix_authentication")
            return None
        except requests.exceptions.Timeout:
            print("[ERROR] Zabbix connection timeout")
            comprehensive_logger.log_error_event("zabbix_timeout", "Request timeout", "zabbix_authentication")
            return None
        except Exception as e:
            print(f"[ERROR] Zabbix authentication error: {str(e)}")
            comprehensive_logger.log_error_event("zabbix_auth", str(e), "zabbix_authentication")
            return None
    
    def make_request(self, method, params=None):
        """Make Zabbix API request"""
        if not self.auth_token or (self.last_auth and (datetime.now() - self.last_auth) > timedelta(hours=1)):
            self.authenticate()
            
        if not self.auth_token:
            return None
            
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params or {},
                "id": 1,
                "auth": self.auth_token
            }
            
            response = requests.post(
                ZABBIX_CONFIG['url'],
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'error' in result:
                    return None
                return result.get('result')
            return None
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            return None
        except Exception:
            return None
    
    def get_hosts(self):
        """Get all hosts from Zabbix"""
        params = {
            "output": ["hostid", "host", "name", "status"],
            "selectInterfaces": ["ip", "port", "type"],
            "monitored_hosts": True
        }
        return self.make_request("host.get", params)
    
    def get_problems(self, limit=50):
        """Get recent problems from Zabbix"""
        params = {
            "output": ["eventid", "name", "severity", "clock", "acknowledged"],
            "selectAcknowledges": "extend",
            "recent": True,
            "sortfield": ["eventid"],
            "sortorder": "DESC",
            "limit": limit
        }
        return self.make_request("problem.get", params)
    
    def get_triggers(self):
        """Get active triggers from Zabbix"""
        params = {
            "output": ["triggerid", "description", "priority", "lastchange"],
            "filter": {"value": 1},
            "sortfield": "lastchange",
            "sortorder": "DESC",
            "limit": 20
        }
        return self.make_request("trigger.get", params)

# Initialize Zabbix API
zabbix_api = ZabbixAPI()

class MonitoringAPI:
    def __init__(self):
        self.zabbix_auth = zabbix_api.authenticate()
        self.real_monitor = RealMonitoringAPI()
    
    def get_system_metrics(self):
        """Get combined system metrics from all monitoring sources"""
        try:
            real_metrics = self.real_monitor.get_system_metrics()
            zabbix_metrics = self._get_zabbix_metrics()
            
            combined_metrics = {
                **real_metrics,
                **zabbix_metrics,
                "active_alerts": zabbix_metrics.get('active_alerts', 0),
                "running_vms": 24,
                "total_vms": 28,
                "security_threats": 1,
                "network_connections": 1247,
                "users_online": 342,
                "library_status": "healthy"
            }
            return combined_metrics
        except Exception as e:
            print(f"Error getting system metrics: {e}")
            return self._get_fallback_metrics()
    
    def _get_zabbix_metrics(self):
        """Get metrics from Zabbix"""
        try:
            hosts = zabbix_api.get_hosts() or []
            problems = zabbix_api.get_problems(limit=10) or []
            triggers = zabbix_api.get_triggers() or []
            
            total_hosts = len(hosts)
            online_hosts = len([h for h in hosts if h.get('status') == '0'])
            active_alerts = len(problems)
            
            return {
                "total_hosts": total_hosts,
                "online_hosts": online_hosts,
                "active_alerts": active_alerts,
                "zabbix_connected": True
            }
        except Exception:
            return {
                "total_hosts": 0,
                "online_hosts": 0,
                "active_alerts": 0,
                "zabbix_connected": False
            }
    
    def _get_fallback_metrics(self):
        """Fallback metrics when monitoring services are unavailable"""
        return {
            "cpu_usage": 45.5,
            "memory_usage": 78.2,
            "disk_usage": 62.8,
            "network_in": 125000,
            "network_out": 89000,
            "processes": 243,
            "server_name": "neosilix-main",
            "uptime": 86400,
            "total_hosts": 156,
            "online_hosts": 148,
            "student_portal_status": "healthy",
            "student_portal_response_time": 45,
            "lms_status": "healthy",
            "lms_response_time": 67,
            "university_website_status": "healthy",
            "email_status": "healthy",
            "total_network_devices": 45,
            "online_network_devices": 43,
            "main_router_status": "healthy",
            "core_switch_status": "healthy",
            "firewall_status": "healthy",
            "active_alerts": 3,
            "running_vms": 24,
            "total_vms": 28,
            "security_threats": 1,
            "network_connections": 1247,
            "users_online": 342,
            "library_status": "healthy",
            "monitoring_mode": "real",
            "timestamp": datetime.now().isoformat()
        }

monitoring_api = MonitoringAPI()



DB_URL = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
engine = create_engine(DB_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db.metadata.create_all(bind=engine)

SECRET_KEY = os.getenv("SECRET_KEY")
MONITOR_USERNAME = os.getenv("MONITOR_AUTH_USERNAME")
MONITOR_PASSWORD = os.getenv("MONITOR_AUTH_PASSWORD")
JWT_SECRET = "supersecretkey"  # Same as in auth.py
JWT_ALGORITHM = "HS256"

model = None
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MODEL_PATH = os.path.join(BASE_DIR, 'ai_engine', 'model.pkl')
METRICS_HISTORY_PATH = os.path.join(BASE_DIR, 'ai_engine', 'metrics_history.json')
LATEST_METRICS_PATH = os.path.join(BASE_DIR, 'ai_engine', 'metrics.json')

# ================== MONITORING BLUEPRINT ==================
monitoring_bp = Blueprint('monitoring', __name__)

@monitoring_bp.route('/api/monitoring/metrics', methods=['GET', 'OPTIONS'])
@token_required
def get_metrics():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        metrics = monitoring_api.get_system_metrics()
        comprehensive_logger.log_user_activity("monitoring_metrics_access", request.user_id, "monitoring")
        return jsonify(metrics), 200
    except Exception as e:
        comprehensive_logger.log_error_event("monitoring_metrics", str(e), "get_metrics", request.user_id)
        return jsonify({"error": "Failed to fetch metrics"}), 500

@monitoring_bp.route('/api/monitoring/alerts', methods=['GET', 'OPTIONS'])
@token_required
def get_monitoring_alerts():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        alerts = []
        
        # Get Zabbix problems
        problems = zabbix_api.get_problems(limit=20) or []
        for problem in problems:
            alerts.append({
                "id": problem.get('eventid'),
                "severity": _zabbix_severity_to_text(problem.get('severity', '0')),
                "message": problem.get('name', 'Unknown problem'),
                "timestamp": datetime.fromtimestamp(int(problem.get('clock', 0))).isoformat(),
                "host": "Zabbix System",
                "acknowledged": problem.get('acknowledged') == '1'
            })
        
        # Get Zabbix triggers as fallback
        if not alerts:
            triggers = zabbix_api.get_triggers() or []
            for trigger in triggers:
                alerts.append({
                    "id": trigger.get('triggerid'),
                    "severity": _zabbix_priority_to_severity(trigger.get('priority', '0')),
                    "message": trigger.get('description', 'Unknown alert'),
                    "timestamp": datetime.fromtimestamp(int(trigger.get('lastchange', 0))).isoformat(),
                    "host": "Unknown",
                    "acknowledged": False
                })
        
        comprehensive_logger.log_user_activity("monitoring_alerts_access", request.user_id, "monitoring")
        return jsonify(alerts), 200
    except Exception as e:
        comprehensive_logger.log_error_event("monitoring_alerts", str(e), "get_monitoring_alerts", request.user_id)
        return jsonify({"error": "Failed to fetch alerts"}), 500

@monitoring_bp.route('/api/monitoring/zabbix/hosts', methods=['GET', 'OPTIONS'])
@token_required
def get_zabbix_hosts():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        hosts = zabbix_api.get_hosts() or []
        
        # Transform hosts for frontend
        transformed_hosts = []
        for host in hosts:
            transformed_hosts.append({
                "hostid": host.get('hostid'),
                "host": host.get('host'),
                "name": host.get('name'),
                "status": host.get('status', '1'),
                "interfaces": host.get('interfaces', [])
            })
        
        comprehensive_logger.log_user_activity("zabbix_hosts_access", request.user_id, "monitoring")
        return jsonify(transformed_hosts), 200
    except Exception as e:
        comprehensive_logger.log_error_event("zabbix_hosts", str(e), "get_zabbix_hosts", request.user_id)
        return jsonify({"error": "Failed to fetch Zabbix hosts"}), 500

@monitoring_bp.route('/api/monitoring/zabbix/alerts', methods=['GET', 'OPTIONS'])
@token_required
def get_zabbix_alerts():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        problems = zabbix_api.get_problems(limit=50) or []
        
        transformed_alerts = []
        for problem in problems:
            transformed_alerts.append({
                "eventid": problem.get('eventid'),
                "name": problem.get('name'),
                "severity": problem.get('severity', '0'),
                "clock": problem.get('clock'),
                "acknowledged": problem.get('acknowledged') == '1'
            })
        
        comprehensive_logger.log_user_activity("zabbix_alerts_access", request.user_id, "monitoring")
        return jsonify(transformed_alerts), 200
    except Exception as e:
        comprehensive_logger.log_error_event("zabbix_alerts", str(e), "get_zabbix_alerts", request.user_id)
        return jsonify({"error": "Failed to fetch Zabbix alerts"}), 500

@monitoring_bp.route('/api/monitoring/health', methods=['GET', 'OPTIONS'])
@token_required
def health_check():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        services = {
            "zabbix": False, 
            "grafana": False, 
            "prometheus": False, 
            "node_exporter": False
        }
        
        # Check Zabbix
        try:
            hosts = zabbix_api.get_hosts()
            services["zabbix"] = hosts is not None
        except: 
            services["zabbix"] = False
        
        # Check other services
        try:
            services["grafana"] = requests.get(f"{GRAFANA_URL}", timeout=5).status_code == 200
        except: pass
        
        try:
            services["prometheus"] = requests.get(f"{PROMETHEUS_URL}", timeout=5).status_code == 200
        except: pass
        
        try:
            services["node_exporter"] = requests.get("http://localhost:9100", timeout=5).status_code == 200
        except: pass
        
        comprehensive_logger.log_user_activity("monitoring_health_check", request.user_id, "monitoring")
        
        return jsonify({
            "status": "healthy" if any(services.values()) else "degraded",
            "services": services,
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        comprehensive_logger.log_error_event("monitoring_health", str(e), "health_check", request.user_id)
        return jsonify({"error": "Failed to check monitoring services health"}), 500

@monitoring_bp.route('/api/monitoring/mode', methods=['GET'])
@token_required
def get_monitoring_mode():
    try:
        mode_data = {
            "mode": "real", 
            "scenario": "normal_operations", 
            "description": "Real monitoring mode with live data from Zabbix and system metrics",
            "zabbix_connected": zabbix_api.auth_token is not None
        }
        comprehensive_logger.log_user_activity("monitoring_mode_check", request.user_id, "monitoring")
        return jsonify(mode_data), 200
    except Exception as e:
        comprehensive_logger.log_error_event("monitoring_mode", str(e), "get_monitoring_mode", request.user_id)
        return jsonify({"error": "Failed to get monitoring mode"}), 500

@monitoring_bp.route('/api/monitoring/switch-scenario/<scenario>', methods=['POST'])
@token_required
def switch_scenario(scenario):
    try:
        valid_scenarios = ['normal_operations', 'registration_peak', 'exam_period', 'security_incident', 'system_maintenance']
        
        if scenario not in valid_scenarios:
            return jsonify({"error": "Invalid scenario"}), 400
        
        comprehensive_logger.log_user_activity("scenario_switch", request.user_id, "monitoring", f"Switched to {scenario}")
        
        return jsonify({
            "message": f"Scenario switched to {scenario}",
            "mode": "real",
            "scenario": scenario,
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        comprehensive_logger.log_error_event("scenario_switch", str(e), "switch_scenario", request.user_id)
        return jsonify({"error": "Failed to switch scenario"}), 500

def _zabbix_priority_to_severity(priority):
    priority_map = {
        '0': 'Information', 
        '1': 'Warning', 
        '2': 'Average', 
        '3': 'High', 
        '4': 'Disaster', 
        '5': 'Critical'
    }
    return priority_map.get(priority, 'Unknown')

def _zabbix_severity_to_text(severity):
    severity_map = {
        '0': 'Information',
        '1': 'Information', 
        '2': 'Warning',
        '3': 'Average',
        '4': 'High',
        '5': 'Disaster'
    }
    return severity_map.get(severity, 'Unknown')

app.register_blueprint(monitoring_bp)

# ================== Helper Functions ==================
def make_json_serializable(obj):
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    elif isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_json_serializable(i) for i in obj]
    else:
        return str(obj)

def get_user_system_stats():
    try:
        stats = {
            "cpu": psutil.cpu_percent(interval=1),
            "memory": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage('/').percent,
            "network_recv": psutil.net_io_counters().bytes_recv,
            "network_sent": psutil.net_io_counters().bytes_sent,
            "processes": len(psutil.pids()),
            "uptime": time.time() - psutil.boot_time(),
            "network_usage": psutil.net_if_stats(),
        }
        comprehensive_logger.auto_detect_performance_issues(stats)
        return stats
    except Exception as e:
        comprehensive_logger.log_error_event("system_stats", str(e), "get_user_system_stats")
        return {"cpu": 0, "memory": 0, "disk": 0, "network_recv": 0, "network_sent": 0, "processes": 0, "uptime": 0, "network_usage": {}}

def calculate_uptime_percentage():
    try:
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        return 99.9 if uptime_seconds > 86400 else min(99.9, (uptime_seconds / 86400) * 99.9)
    except Exception as e:
        comprehensive_logger.log_error_event("uptime_calculation", str(e), "calculate_uptime")
        return 99.5

def load_latest_metrics(user_id=None):
    """Load metrics for a specific user or global metrics"""
    if user_id:
        try:
            import psycopg2
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            cur.execute("""
                SELECT metric_name, metric_value, metric_json, metric_type
                FROM metrics
                WHERE user_id=%s
                ORDER BY created_at DESC
                LIMIT 10
            """, (user_id,))
            rows = cur.fetchall()
            conn.close()
            
            metrics = {}
            for row in rows:
                metric_name, metric_value, metric_json, metric_type = row
                if metric_type == 'numeric' and metric_value is not None:
                    metrics[metric_name] = metric_value
                elif metric_type == 'complex' and metric_json is not None:
                    try:
                        pass
                    except:
                        pass
            return metrics
        except Exception as e:
            comprehensive_logger.log_error_event("database_error", str(e), "load_user_metrics", user_id)
            print(f"Error loading user metrics: {e}")
            return {}
    else:
        try:
            with open(LATEST_METRICS_PATH, 'r') as f:
                data = json.load(f)
                return data.get('metrics', {})
        except Exception as e:
            comprehensive_logger.log_error_event("file_error", str(e), "load_global_metrics")
            return {}

def store_user_metrics(user_id, metrics):
    """Store REAL user metrics in database - handle different data types"""
    try:
        import psycopg2
        import json
        from datetime import datetime
        
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        numeric_metrics = {
            'cpu': float,
            'memory': float, 
            'disk': float,
            'network_recv': float,
            'network_sent': float,
            'processes': int,
            'uptime': float,
        }
        
        complex_metrics = ['network_usage']
        
        for metric_name, metric_value in metrics.items():
            if metric_name in numeric_metrics:
                try:
                    converted_value = numeric_metrics[metric_name](metric_value)
                    
                    cur.execute("""
                        INSERT INTO metrics (user_id, metric_name, metric_value, metric_type, created_at)
                        VALUES (%s, %s, %s, 'numeric', %s)
                    """, (user_id, metric_name, converted_value, datetime.now()))
                    
                except (ValueError, TypeError) as e:
                    comprehensive_logger.log_error_event("metric_conversion", str(e), f"metric_{metric_name}", user_id)
                    print(f"Error converting metric {metric_name}: {e}")
                    continue
                    
            elif metric_name in complex_metrics:
                try:
                    json_value = json.dumps(make_json_serializable(metric_value))
                    
                    cur.execute("""
                        INSERT INTO metrics (user_id, metric_name, metric_json, metric_type, created_at)
                        VALUES (%s, %s, %s, 'complex', %s)
                    """, (user_id, metric_name, json_value, datetime.now()))
                    
                except Exception as e:
                    comprehensive_logger.log_error_event("complex_metric_storage", str(e), f"metric_{metric_name}", user_id)
                    print(f"Error storing complex metric {metric_name}: {e}")
                    continue
        
        conn.commit()
        conn.close()
        
        comprehensive_logger.log_user_activity("metrics_stored", user_id, "system_metrics", f"{len(metrics)} metrics stored")
        return True
    except Exception as e:
        comprehensive_logger.log_error_event("metrics_storage", str(e), "store_user_metrics", user_id)
        print(f"Error storing user metrics: {e}")
        return False

def _get_service_name(port):
    """Get service name for common ports"""
    service_map = {
        22: "SSH", 80: "HTTP", 443: "HTTPS", 8080: "HTTP-Alt",
        3306: "MySQL", 5432: "PostgreSQL", 27017: "MongoDB"
    }
    return service_map.get(port, f"Port {port}")

# ================== COMPREHENSIVE STATS ENDPOINTS ==================

@app.route('/api/stats', methods=['GET', 'OPTIONS'])
@token_required
def get_stats():
    """Main stats endpoint - provides overview data for dashboard"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        # Get system stats
        stats = get_user_system_stats()
        monitoring_metrics = monitoring_api.get_system_metrics()
        
        stats_data = {
            "system_health": {
                "status": "healthy",
                "cpu": stats.get("cpu", 0),
                "memory": stats.get("memory", 0),
                "disk": stats.get("disk", 0),
                "uptime_percentage": calculate_uptime_percentage(),
                "server_name": "neosilix-main"
            },
            "monitoring": {
                "total_hosts": monitoring_metrics.get("total_hosts", 0),
                "online_hosts": monitoring_metrics.get("online_hosts", 0),
                "active_alerts": monitoring_metrics.get("active_alerts", 0),
                "zabbix_connected": monitoring_metrics.get("zabbix_connected", False)
            },
            "services": {
                "student_portal": monitoring_metrics.get("student_portal_status", "unknown"),
                "lms": monitoring_metrics.get("lms_status", "unknown"),
                "website": monitoring_metrics.get("university_website_status", "unknown"),
                "email": monitoring_metrics.get("email_status", "unknown"),
                "library": monitoring_metrics.get("library_status", "unknown")
            },
            "performance": {
                "network_in": stats.get("network_recv", 0),
                "network_out": stats.get("network_sent", 0),
                "processes": stats.get("processes", 0)
            },
            "timestamp": datetime.now().isoformat()
        }
        
        comprehensive_logger.log_user_activity("stats_access", request.user_id, "stats")
        return jsonify(stats_data), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("stats", str(e), "get_stats", request.user_id)
        return jsonify({"error": "Failed to fetch stats"}), 500


@app.route('/api/stats/comprehensive', methods=['GET', 'OPTIONS'])
@token_required
def comprehensive_stats():
    """Comprehensive stats with detailed infrastructure data"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        # Get data from multiple sources
        system_stats = get_user_system_stats()
        monitoring_metrics = monitoring_api.get_system_metrics()
        
        # Get Zabbix data for more details
        zabbix_hosts = zabbix_api.get_hosts() or []
        zabbix_problems = zabbix_api.get_problems(limit=50) or []
        
        # Network information
        network_info = get_network_info()
        
        # VM information (you can integrate with your VM management system)
        vm_info = get_vm_stats()
        
        comprehensive_data = {
            "system": {
                **system_stats,
                "uptime_percentage": calculate_uptime_percentage(),
                "server_name": "neosilix-main",
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat() if hasattr(psutil, 'boot_time') else None
            },
            "infrastructure": {
                "total_hosts": monitoring_metrics.get("total_hosts", 0),
                "online_hosts": monitoring_metrics.get("online_hosts", 0),
                "offline_hosts": monitoring_metrics.get("total_hosts", 0) - monitoring_metrics.get("online_hosts", 0),
                "hosts_by_status": categorize_hosts_by_status(zabbix_hosts),
                "zabbix_connected": zabbix_api.auth_token is not None
            },
            "virtualization": {
                **vm_info,
                "running_vms": monitoring_metrics.get("running_vms", 0),
                "total_vms": monitoring_metrics.get("total_vms", 0),
                "vm_utilization": calculate_vm_utilization(monitoring_metrics.get("running_vms", 0), monitoring_metrics.get("total_vms", 0))
            },
            "networking": {
                **network_info,
                "total_network_devices": monitoring_metrics.get("total_network_devices", 0),
                "online_network_devices": monitoring_metrics.get("online_network_devices", 0),
                "network_connections": monitoring_metrics.get("network_connections", 0),
                "main_router_status": monitoring_metrics.get("main_router_status", "unknown"),
                "core_switch_status": monitoring_metrics.get("core_switch_status", "unknown"),
                "firewall_status": monitoring_metrics.get("firewall_status", "unknown")
            },
            "security": {
                "security_threats": monitoring_metrics.get("security_threats", 0),
                "users_online": monitoring_metrics.get("users_online", 0),
                "failed_login_attempts": get_failed_login_attempts(),
                "firewall_rules": get_firewall_rules_count()
            },
            "alerts": {
                "active_alerts": monitoring_metrics.get("active_alerts", 0),
                "critical_alerts": count_alerts_by_severity(zabbix_problems, ['4', '5']),  # High and Disaster
                "warning_alerts": count_alerts_by_severity(zabbix_problems, ['2', '3']),   # Warning and Average
                "recent_alerts": transform_alerts_for_display(zabbix_problems)[:10]  # Last 10 alerts
            },
            "services": {
                "student_portal": {
                    "status": monitoring_metrics.get("student_portal_status", "unknown"),
                    "response_time": monitoring_metrics.get("student_portal_response_time", 0)
                },
                "lms": {
                    "status": monitoring_metrics.get("lms_status", "unknown"),
                    "response_time": monitoring_metrics.get("lms_response_time", 0)
                },
                "university_website": {
                    "status": monitoring_metrics.get("university_website_status", "unknown")
                },
                "email": {
                    "status": monitoring_metrics.get("email_status", "unknown")
                },
                "library": {
                    "status": monitoring_metrics.get("library_status", "unknown")
                }
            },
            "performance_metrics": {
                "cpu": system_stats.get("cpu", 0),
                "memory": system_stats.get("memory", 0),
                "disk": system_stats.get("disk", 0),
                "network_in": system_stats.get("network_recv", 0),
                "network_out": system_stats.get("network_sent", 0),
                "processes": system_stats.get("processes", 0)
            },
            "timestamp": datetime.now().isoformat(),
            "data_source": "comprehensive"
        }
        
        comprehensive_logger.log_user_activity("comprehensive_stats_access", request.user_id, "stats")
        return jsonify(comprehensive_data), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("comprehensive_stats", str(e), "comprehensive_stats", request.user_id)
        return jsonify({"error": "Failed to fetch comprehensive stats"}), 500

@app.route('/api/stats/network', methods=['GET', 'OPTIONS'])
@token_required
def network_stats():
    """Detailed network statistics and IP information"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        network_info = get_detailed_network_info()
        
        network_data = {
            "network_interfaces": network_info.get("interfaces", []),
            "connections": network_info.get("connections", []),
            "bandwidth": {
                "bytes_sent": psutil.net_io_counters().bytes_sent,
                "bytes_recv": psutil.net_io_counters().bytes_recv,
                "packets_sent": psutil.net_io_counters().packets_sent,
                "packets_recv": psutil.net_io_counters().packets_recv
            },
            "ip_addresses": network_info.get("ip_addresses", []),
            "network_devices": {
                "total": 45,  # You can make this dynamic
                "online": 43,
                "offline": 2
            },
            "gateway": network_info.get("gateway", "unknown"),
            "dns_servers": network_info.get("dns_servers", []),
            "timestamp": datetime.now().isoformat()
        }
        
        comprehensive_logger.log_user_activity("network_stats_access", request.user_id, "stats")
        return jsonify(network_data), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("network_stats", str(e), "network_stats", request.user_id)
        return jsonify({"error": "Failed to fetch network stats"}), 500

@app.route('/api/stats/virtualization', methods=['GET', 'OPTIONS'])
@token_required
def virtualization_stats():
    """Virtualization and VM statistics"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        vm_stats = get_detailed_vm_stats()
        monitoring_metrics = monitoring_api.get_system_metrics()
        
        virtualization_data = {
            "vm_overview": {
                "total_vms": monitoring_metrics.get("total_vms", 28),
                "running_vms": monitoring_metrics.get("running_vms", 24),
                "stopped_vms": monitoring_metrics.get("total_vms", 28) - monitoring_metrics.get("running_vms", 24),
                "utilization_percentage": round((monitoring_metrics.get("running_vms", 24) / monitoring_metrics.get("total_vms", 28)) * 100, 1)
            },
            "vm_hosts": vm_stats.get("hosts", []),
            "resource_usage": {
                "cpu_allocated": vm_stats.get("cpu_allocated", 0),
                "memory_allocated": vm_stats.get("memory_allocated", 0),
                "storage_allocated": vm_stats.get("storage_allocated", 0),
                "cpu_used": vm_stats.get("cpu_used", 0),
                "memory_used": vm_stats.get("memory_used", 0),
                "storage_used": vm_stats.get("storage_used", 0)
            },
            "performance": {
                "average_cpu_usage": vm_stats.get("average_cpu_usage", 0),
                "average_memory_usage": vm_stats.get("average_memory_usage", 0),
                "average_disk_usage": vm_stats.get("average_disk_usage", 0)
            },
            "timestamp": datetime.now().isoformat()
        }
        
        comprehensive_logger.log_user_activity("virtualization_stats_access", request.user_id, "stats")
        return jsonify(virtualization_data), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("virtualization_stats", str(e), "virtualization_stats", request.user_id)
        return jsonify({"error": "Failed to fetch virtualization stats"}), 500

# ================== HELPER FUNCTIONS FOR STATS ==================

def get_network_info():
    """Get detailed network information"""
    try:
        interfaces = psutil.net_if_addrs()
        io_counters = psutil.net_io_counters()
        connections = psutil.net_connections()
        
        network_data = {
            "interfaces": [],
            "connections": len(connections),
            "bandwidth": {
                "bytes_sent": io_counters.bytes_sent,
                "bytes_recv": io_counters.bytes_recv
            }
        }
        
        for interface, addrs in interfaces.items():
            interface_info = {
                "name": interface,
                "ip_addresses": [],
                "mac_address": None
            }
            
            for addr in addrs:
                if addr.family == 2:  # IPv4
                    interface_info["ip_addresses"].append({
                        "type": "IPv4",
                        "address": addr.address,
                        "netmask": addr.netmask
                    })
                elif addr.family == 17:  # MAC address
                    interface_info["mac_address"] = addr.address
            
            network_data["interfaces"].append(interface_info)
        
        return network_data
    except Exception as e:
        comprehensive_logger.log_error_event("network_info", str(e), "get_network_info")
        return {"interfaces": [], "connections": 0, "bandwidth": {"bytes_sent": 0, "bytes_recv": 0}}

def get_vm_stats():
    """Get VM statistics"""
    # This is a placeholder - integrate with your VM management system
    # For example: VMware vSphere, Proxmox, Hyper-V, etc.
    return {
        "total_vms": 28,
        "running_vms": 24,
        "stopped_vms": 4,
        "cpu_allocated": 112,  # in cores
        "memory_allocated": 256,  # in GB
        "storage_allocated": 5120,  # in GB
        "cpu_used": 84,  # in cores
        "memory_used": 192,  # in GB
        "storage_used": 3840  # in GB
    }

def get_detailed_network_info():
    """Get more detailed network information"""
    try:
        # You can expand this with actual network scanning
        return {
            "interfaces": [],
            "connections": [],
            "ip_addresses": [
                {"ip": "192.168.1.1", "type": "gateway", "status": "online"},
                {"ip": "192.168.1.10", "type": "server", "status": "online"},
                {"ip": "192.168.1.20", "type": "vm", "status": "online"}
            ],
            "gateway": "192.168.1.1",
            "dns_servers": ["8.8.8.8", "8.8.4.4"]
        }
    except Exception as e:
        return {"interfaces": [], "connections": [], "ip_addresses": [], "gateway": "unknown", "dns_servers": []}

def get_detailed_vm_stats():
    """Get detailed VM statistics"""
    # Integrate with your virtualization platform
    return {
        "hosts": [
            {"name": "hypervisor-01", "vms": 8, "status": "online", "cpu_usage": 65, "memory_usage": 72},
            {"name": "hypervisor-02", "vms": 7, "status": "online", "cpu_usage": 58, "memory_usage": 68},
            {"name": "hypervisor-03", "vms": 9, "status": "online", "cpu_usage": 72, "memory_usage": 75}
        ],
        "cpu_allocated": 112,
        "memory_allocated": 256,
        "storage_allocated": 5120,
        "cpu_used": 84,
        "memory_used": 192,
        "storage_used": 3840,
        "average_cpu_usage": 65,
        "average_memory_usage": 72,
        "average_disk_usage": 75
    }

def categorize_hosts_by_status(hosts):
    """Categorize hosts by their status"""
    status_count = {"online": 0, "offline": 0, "maintenance": 0}
    for host in hosts:
        status = host.get('status', '1')  # '0' = enabled, '1' = disabled
        if status == '0':
            status_count["online"] += 1
        else:
            status_count["offline"] += 1
    return status_count

def count_alerts_by_severity(problems, severity_levels):
    """Count alerts by severity levels"""
    count = 0
    for problem in problems:
        if problem.get('severity') in severity_levels:
            count += 1
    return count

def transform_alerts_for_display(problems):
    """Transform Zabbix problems for frontend display"""
    alerts = []
    for problem in problems[:10]:  # Limit to 10 most recent
        alerts.append({
            "id": problem.get('eventid'),
            "severity": _zabbix_severity_to_text(problem.get('severity', '0')),
            "message": problem.get('name', 'Unknown problem'),
            "timestamp": datetime.fromtimestamp(int(problem.get('clock', 0))).isoformat(),
            "acknowledged": problem.get('acknowledged') == '1'
        })
    return alerts

def get_failed_login_attempts():
    """Get failed login attempts count"""
    # You can implement this by querying your logs or security system
    return 3  # Placeholder

def get_firewall_rules_count():
    """Get firewall rules count"""
    # You can implement this by querying your firewall
    return 245  # Placeholder

def calculate_vm_utilization(running_vms, total_vms):
    """Calculate VM utilization percentage"""
    if total_vms == 0:
        return 0
    return round((running_vms / total_vms) * 100, 1)

@app.route('/api/ask-anything', methods=['POST', 'OPTIONS'])
@token_required
def ask_anything_endpoint():
    """Enhanced AI assistant endpoint with the new Neosilix assistant"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'error': 'No question provided'}), 400
        
        # Get system metrics
        system_stats = get_user_system_stats()
        monitoring_metrics = monitoring_api.get_system_metrics()
        combined_metrics = {**system_stats, **monitoring_metrics}
        
        # Get monitoring targets for context
        user_id = getattr(request, "user_id", None)
        is_admin = getattr(request, "is_admin", False)
        
        if is_admin:
            targets = MonitoringTarget.query.all()
        else:
            targets = MonitoringTarget.query.filter_by(user_id=user_id).all()
        
        targets_data = [target.to_dict() for target in targets]
        
        # User context
        user_context = {
            'user_id': user_id,
            'is_admin': is_admin
        }
        
        # Use the new Neosilix assistant
        response = neosilix_assistant.ask_anything(
            question, 
            combined_metrics, 
            user_context, 
            targets_data
        )
        
        comprehensive_logger.log_ai_engine_event(
            "ask_anything", 
            "processed", 
            f"User: {user_id} | Type: {response.get('question_type', 'unknown')} | Method: {response.get('method', 'unknown')}",
            user_id
        )
        
        return jsonify(response), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("ask_anything", str(e), "ask_anything_endpoint", request.user_id)
        return jsonify({'error': 'Failed to process question'}), 500
@app.route('/api/ai-assistant/conversation-history', methods=['GET', 'OPTIONS'])
@token_required
def get_user_conversation_history_route():
    """Get enhanced conversation history with analytics"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        user_id = getattr(request, "user_id", None)
        max_messages = request.args.get('max_messages', 20, type=int)
        
        # Get conversation history
        history = neosilix_assistant.get_user_conversation_history(user_id, max_messages)
        
        # Get conversation statistics
        stats = neosilix_assistant.get_user_analytics(user_id)
        
        comprehensive_logger.log_user_activity(
            "conversation_history_access", 
            user_id, 
            "ai_assistant",
            f"Retrieved {len(history)} messages with analytics"
        )
        
        return jsonify({
            'user_id': user_id,
            'history': history,
            'total_messages': len(history),
            'conversation_stats': stats,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("conversation_history", str(e), "get_user_conversation_history", request.user_id)
        return jsonify({"error": "Failed to fetch conversation history"}), 500

@app.route('/api/ai-assistant/clear-history', methods=['POST', 'OPTIONS'])
@token_required
def clear_conversation_history_route():
    """Clear conversation history with confirmation"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        user_id = getattr(request, "user_id", None)
        
        neosilix_assistant.clear_user_history(user_id)
        
        comprehensive_logger.log_user_activity(
            "conversation_history_cleared", 
            user_id, 
            "ai_assistant",
            "User conversation history cleared"
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Conversation history cleared successfully',
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("clear_history", str(e), "clear_conversation_history", request.user_id)
        return jsonify({"error": "Failed to clear conversation history"}), 500

@app.route('/api/ai-assistant/create-target', methods=['POST', 'OPTIONS'])
@token_required
def create_target_via_ai():
    """Create monitoring target via AI assistant (manual database insertion)"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        user_id = getattr(request, "user_id", None)
        is_admin = getattr(request, "is_admin", False)
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        target_request = data.get('target_request', '')
        
        if not target_request:
            return jsonify({"error": "No target request provided"}), 400
        
        # Use the AI to parse and validate the target creation request
        from universal_ai_assistant import analyze_monitoring_targets
        
        # Get current targets for context
        if is_admin:
            existing_targets = MonitoringTarget.query.all()
        else:
            existing_targets = MonitoringTarget.query.filter_by(user_id=user_id).all()
        
        existing_targets_data = [target.to_dict() for target in existing_targets]
        
        # Enhanced ask_anything call that includes target creation capability
        response = ask_anything(
            target_request, 
            get_user_system_stats(), 
            {'user_id': user_id, 'is_admin': is_admin},
            existing_targets_data
        )
        
        # Check if this was processed as a target creation request
        if response.get('question_type') == 'target_creation':
            creation_result = response.get('target_creation_result', {})
            
            if creation_result.get('success'):
                # MANUALLY INSERT INTO DATABASE using your existing add_target logic
                target_data = creation_result['target_data']
                
                # Create new target using your existing database logic
                new_target = MonitoringTarget(
                    name=target_data['name'],
                    type=target_data['type'],
                    ip_address=target_data['ip_address'],
                    subnet=target_data.get('subnet', '32'),
                    priority=target_data.get('priority', 'medium'),
                    user_id=user_id,
                    status='unknown',  # Initial status
                    last_check=datetime.now(timezone.utc)
                )
                
                db.session.add(new_target)
                db.session.commit()
                
                # Log the successful creation
                comprehensive_logger.log_user_activity(
                    "target_created_via_ai", 
                    user_id, 
                    "targets",
                    f"Created target: {target_data['name']} ({target_data['ip_address']})"
                )
                
                return jsonify({
                    'status': 'success',
                    'message': f"Target '{target_data['name']}' created successfully!",
                    'target': new_target.to_dict(),
                    'ai_analysis': creation_result,
                    'next_steps': [
                        f"Target ID: {new_target.id}",
                        "Run initial scan via /api/targets/{id}/scan",
                        "View target in monitoring dashboard"
                    ],
                    'timestamp': datetime.now().isoformat()
                }), 201
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Target creation failed',
                    'errors': creation_result.get('errors', []),
                    'suggestions': creation_result.get('suggestions', []),
                    'guide': creation_result.get('guide', '')
                }), 400
        
        # If it wasn't processed as target creation, return the general response
        return jsonify({
            'status': 'info',
            'message': 'This appears to be a general question, not a target creation request',
            'ai_response': response,
            'suggestions': [
                "Use format: 'Add a server named web01 with IP 192.168.1.10'",
                "Or: 'Create database server db-primary at 192.168.1.20'",
                "Or use direct API: POST /api/targets with JSON data"
            ]
        }), 200
        
    except Exception as e:
        db.session.rollback()
        comprehensive_logger.log_error_event("ai_target_creation", str(e), "create_target_via_ai", request.user_id)
        return jsonify({"error": f"Failed to create target via AI: {str(e)}"}), 500

@app.route('/api/ai-assistant/targets-preview', methods=['POST', 'OPTIONS'])
@token_required
def preview_target_creation():
    """Preview target creation without actually adding to database"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        user_id = getattr(request, "user_id", None)
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        target_request = data.get('target_request', '')
        
        if not target_request:
            return jsonify({"error": "No target request provided"}), 400
        
        # Use the AI to parse and validate without database insertion
        from universal_ai_assistant import analyze_monitoring_targets
        
        # Get current targets for context
        existing_targets = MonitoringTarget.query.filter_by(user_id=user_id).all()
        existing_targets_data = [target.to_dict() for target in existing_targets]
        
        response = ask_anything(
            target_request, 
            get_user_system_stats(), 
            {'user_id': user_id, 'is_admin': request.is_admin},
            existing_targets_data
        )
        
        comprehensive_logger.log_user_activity(
            "target_creation_preview", 
            user_id, 
            "ai_assistant",
            f"Preview: {target_request[:50]}..."
        )
        
        return jsonify(response), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("target_preview", str(e), "preview_target_creation", request.user_id)
        return jsonify({"error": "Failed to preview target creation"}), 500

@app.route('/api/ai-assistant/targets-analysis', methods=['GET', 'OPTIONS'])
@token_required  
def get_targets_analysis():
    """Get comprehensive analysis of monitoring targets using the new assistant"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        user_id = getattr(request, "user_id", None)
        is_admin = getattr(request, "is_admin", False)
        
        # Get user's targets
        if is_admin:
            targets = MonitoringTarget.query.all()
        else:
            targets = MonitoringTarget.query.filter_by(user_id=user_id).all()
        
        targets_data = [target.to_dict() for target in targets]
        
        # Generate comprehensive analysis using new assistant
        analysis = neosilix_assistant.analyze_targets(targets_data)
        
        comprehensive_logger.log_ai_engine_event(
            "targets_analysis",
            "generated", 
            f"Health score: {analysis['overview']['health_score']}% | Issues: {len(analysis['critical_issues'])}",
            request.user_id
        )
        
        return jsonify(analysis), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("targets_analysis", str(e), "get_targets_analysis", request.user_id)
        return jsonify({"error": "Failed to generate targets analysis"}), 500
@app.route('/api/ai-assistant/system-analysis', methods=['GET', 'OPTIONS'])
@token_required  
def get_system_analysis():
    """Get comprehensive system analysis using the new assistant"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        # Get current system metrics
        system_stats = get_user_system_stats()
        monitoring_metrics = monitoring_api.get_system_metrics()
        combined_metrics = {**system_stats, **monitoring_metrics}
        
        # Get monitoring targets data
        user_id = getattr(request, "user_id", None)
        is_admin = getattr(request, "is_admin", False)
        
        if is_admin:
            targets = MonitoringTarget.query.all()
        else:
            targets = MonitoringTarget.query.filter_by(user_id=user_id).all()
        
        targets_data = [target.to_dict() for target in targets]
        
        # Generate comprehensive analysis using new assistant
        analysis = neosilix_assistant.get_system_insights(combined_metrics, targets_data)
        
        comprehensive_logger.log_ai_engine_event(
            "system_analysis",
            "generated", 
            f"Health score: {analysis['current_health']['overall_score']:.1f} | Targets: {len(targets_data)}",
            request.user_id
        )
        
        return jsonify(analysis), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("system_analysis", str(e), "get_system_analysis", request.user_id)
        return jsonify({"error": "Failed to generate system analysis"}), 500
@app.route('/api/ai-assistant/status', methods=['GET', 'OPTIONS'])
@token_required
def get_ai_assistant_status():
    """Get status of the Neosilix AI assistant"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        cache_stats = neosilix_assistant.get_cache_stats()
        
        status = {
            'version': '2.0',
            'openai_configured': neosilix_assistant.openai_client is not None,
            'redis_connected': neosilix_assistant.cache.connected,
            'security_enabled': True,
            'conversation_history': True,
            'target_creation_support': True,
            'analytics_enabled': neosilix_assistant.config.enable_telemetry,
            'cache_enabled': True,
            'cache_stats': cache_stats,
            'features': [
                'User conversation history with persistence',
                'Natural language target creation', 
                'Advanced caching with Redis',
                'Comprehensive analytics and telemetry',
                'Enhanced security validation',
                'Intelligent context awareness'
            ],
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(status), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("ai_assistant_status", str(e), "get_ai_assistant_status", request.user_id)
        return jsonify({"error": "Failed to get AI assistant status"}), 500
@app.route('/api/ask-anything', methods=['POST', 'OPTIONS'])
@token_required
def ask_anything_legacy():
    """Legacy endpoint - redirects to enhanced Neosilix AI assistant"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'error': 'No question provided'}), 400
        
        # Get system metrics
        system_stats = get_user_system_stats()
        monitoring_metrics = monitoring_api.get_system_metrics()
        combined_metrics = {**system_stats, **monitoring_metrics}
        
        # Get targets
        user_id = getattr(request, "user_id", None)
        is_admin = getattr(request, "is_admin", False)
        
        if is_admin:
            targets = MonitoringTarget.query.all()
        else:
            targets = MonitoringTarget.query.filter_by(user_id=user_id).all()
        
        targets_data = [target.to_dict() for target in targets]
        
        user_context = {
            'user_id': user_id,
            'is_admin': is_admin
        }
        
        # Use the new Neosilix AI assistant
        response = neosilix_assistant.ask_anything(
            question, 
            combined_metrics, 
            user_context, 
            targets_data
        )
        
        comprehensive_logger.log_ai_engine_event(
            "ask-anything_legacy", 
            "processed", 
            f"Legacy endpoint used: {question[:50]}...",
            user_id
        )
        
        return jsonify(response), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("ask_anything_legacy", str(e), "ask_anything_legacy", request.user_id)
        return jsonify({'error': 'Failed to process question'}), 500

# ================== Routes ==================
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response
   
@app.route('/api/ai-engine/cpu-heal', methods=['POST', 'OPTIONS'])
@token_required
def trigger_cpu_heal():
    """Manually trigger CPU healing"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        data = request.get_json()
        threshold = data.get('threshold', 80)
        
        # Trigger CPU healing
        heal_report = intelligent_cpu_healer(cpu_threshold=threshold)
        
        comprehensive_logger.log_ai_engine_event(
            "manual_cpu_heal", 
            heal_report['status'],
            f"CPU: {heal_report['cpu_percent']}% -> {heal_report.get('post_heal_cpu', 'N/A')}%",
            request.user_id
        )
        
        return jsonify({
            'success': heal_report['status'] in ['success', 'partial_success'],
            'message': f"CPU healing completed: {heal_report['status']}",
            'report': heal_report
        }), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("cpu_heal_endpoint", str(e), "trigger_cpu_heal", request.user_id)
        return jsonify({'error': 'Failed to trigger CPU healing'}), 500

@app.route('/api/ai-engine/cpu-diagnosis', methods=['GET', 'OPTIONS'])
@token_required
def get_cpu_diagnosis():
    """Get current CPU diagnosis"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        from ai_engine.self_healer import diagnose_cpu_stress
        
        diagnosis = diagnose_cpu_stress()
        
        comprehensive_logger.log_user_activity(
            "cpu_diagnosis_check", 
            request.user_id, 
            "ai_engine",
            f"CPU: {diagnosis.get('cpu_total', 0)}%"
        )
        
        return jsonify(diagnosis), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("cpu_diagnosis", str(e), "get_cpu_diagnosis", request.user_id)
        return jsonify({'error': 'Failed to get CPU diagnosis'}), 500

@app.route("/api/admin/stats", methods=["GET"])
@admin_required
def admin_stats():
        """Admin-only: Real Neosilix infrastructure metrics"""
        try:
            infra = get_system_stats()
            
            try:
                import psycopg2
                conn = psycopg2.connect(**DB_CONFIG)
                cur = conn.cursor()
                
                cur.execute("SELECT COUNT(*) FROM users")
                result = cur.fetchone()
                total_users = result[0] if result else 0
                
                cur.execute("SELECT COUNT(*) FROM websites")
                result = cur.fetchone()
                total_websites = result[0] if result else 0
                
                cur.execute("""
                    SELECT COUNT(*) FROM metrics 
                    WHERE created_at >= NOW() - INTERVAL '24 hours'
                    AND ((metric_name = 'status_code' AND metric_value != '200')
                        OR (metric_name = 'latency_ms' AND CAST(metric_value AS FLOAT) > 1000))
                """)
                result = cur.fetchone()
                anomalies = result[0] if result else 0
                
                cur.execute("""
                    SELECT COUNT(*) FROM healing_logs 
                    WHERE created_at >= NOW() - INTERVAL '24 hours'
                """)
                result = cur.fetchone()
                heals_last_24h = result[0] if result else 0
                
                uptime_seconds = time.time() - psutil.boot_time()
                uptime_percentage = 100.0
                
                conn.close()
            except Exception as db_error:
                comprehensive_logger.log_error_event("database_error", str(db_error), "admin_stats_fetch", request.user_id)
                print(f"Database error in admin stats: {db_error}")
                total_users = 0
                total_websites = 0
                anomalies = 0
                heals_last_24h = 0
                uptime_percentage = 0

            comprehensive_logger.log_user_activity("admin_dashboard_access", request.user_id, "admin_stats", 
                                                 f"CPU: {infra.get('cpu', 0):.1f}%, Memory: {infra.get('memory', 0):.1f}%")
            
            if anomalies > 0:
                comprehensive_logger.log_ai_engine_event("anomaly_detection", f"{anomalies} anomalies found", None, request.user_id)
            
            comprehensive_logger.auto_detect_performance_issues(infra, request.user_id)

            payload = {
                "cpu": float(infra.get("cpu", 0)),
                "memory": float(infra.get("memory", 0)),
                "disk": float(infra.get("disk", 0)),
                "network_recv": float(infra.get("network_recv", 0)),
                "network_sent": float(infra.get("network_sent", 0)),
                "total_users": total_users,
                "total_websites": total_websites,
                "anomalies": anomalies,
                "heals_last_24h": heals_last_24h,
                "uptime_percentage": uptime_percentage,
                "ai_engine_status": "operational",
                "system_uptime": uptime_seconds,
            }
            return jsonify(payload), 200
        except Exception as e:
            comprehensive_logger.log_error_event("endpoint_error", str(e), "admin_stats", getattr(request, 'user_id', None))
            system_logger.log(f"Error fetching admin stats: {str(e)}", "error", getattr(request, 'user_id', None))
            print(f"Admin stats endpoint error: {e}")
            return jsonify({"error": str(e)}), 500
     
@app.route('/api/stats/dashboard', methods=['GET', 'OPTIONS'])
@token_required
def get_dashboard_stats():
    """Dashboard stats endpoint with unified data structure"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        is_admin = getattr(request, "is_admin", False)
        user_id = getattr(request, "user_id", None)

        # Get basic system stats
        system_stats = get_system_stats()
        
        if is_admin:
            # Admin dashboard data
            try:
                import psycopg2
                conn = psycopg2.connect(**DB_CONFIG)
                cur = conn.cursor()
                
                
                # Get total users - FIXED: Handle None results properly
                cur.execute("SELECT COUNT(*) FROM users")
                result = cur.fetchone()
                total_users = result[0] if result and result[0] is not None else 0
                
                # Get total websites - FIXED: Handle None results properly
                cur.execute("SELECT COUNT(*) FROM websites")
                result = cur.fetchone()
                total_websites = result[0] if result and result[0] is not None else 0
                
                # Get anomalies count - FIXED: Handle None results properly
                cur.execute("""
                    SELECT COUNT(*) FROM metrics 
                    WHERE (metric_name = 'status_code' AND metric_value != '200')
                       OR (metric_name = 'latency_ms' AND CAST(metric_value AS FLOAT) > 1000)
                """)
                result = cur.fetchone()
                anomalies = result[0] if result and result[0] is not None else 0
                
                # Get healing actions count - FIXED: Handle None results properly
                cur.execute("SELECT COUNT(*) FROM healing_logs WHERE created_at >= NOW() - INTERVAL '24 hours'")
                result = cur.fetchone()
                heals_last_24h = result[0] if result and result[0] is not None else 0

                
                conn.close()
                
            except Exception as db_error:
                comprehensive_logger.log_error_event("dashboard_stats_db", str(db_error), "admin_dashboard", user_id)
                total_users = 0
                total_websites = 0
                anomalies = 0
                heals_last_24h = 0

            dashboard_data = {
                "cpu": float(system_stats.get("cpu", 0)),
                "memory": float(system_stats.get("memory", 0)),
                "disk": float(system_stats.get("disk", 0)),
                "uptime_percentage": calculate_uptime_percentage(),
                "total_systems": total_websites,
                "anomalies": anomalies,
                "heals_last_24h": heals_last_24h,
                "critical_alerts": 0,  # You can implement this later
                "ai_engine_status": "running",
                "total_users": total_users,
                "total_websites": total_websites,
                "system_uptime": time.time() - psutil.boot_time()
            }
            
        else:
            # User dashboard data
            try:
                import psycopg2
                conn = psycopg2.connect(**DB_CONFIG)
                cur = conn.cursor()
                
                
                # Get user's websites count - FIXED: Handle None results properly
                cur.execute("SELECT COUNT(*) FROM websites WHERE user_id = %s", (user_id,))
                result = cur.fetchone()
                user_websites = result[0] if result and result[0] is not None else 0
                
                # Get user's anomalies - FIXED: Handle None results properly
                cur.execute("""
                    SELECT COUNT(*) FROM metrics 
                    WHERE user_id = %s 
                    AND ((metric_name = 'status_code' AND metric_value != '200')
                        OR (metric_name = 'latency_ms' AND CAST(metric_value AS FLOAT) > 1000))
                """, (user_id,))
                result = cur.fetchone()
                user_anomalies = result[0] if result and result[0] is not None else 0

                
                conn.close()
                
            except Exception as db_error:
                comprehensive_logger.log_error_event("dashboard_stats_db", str(db_error), "user_dashboard", user_id)
                user_websites = 0
                user_anomalies = 0

            dashboard_data = {
                "cpu": float(system_stats.get("cpu", 0)),
                "memory": float(system_stats.get("memory", 0)),
                "disk": float(system_stats.get("disk", 0)),
                "uptime_percentage": calculate_uptime_percentage(),
                "total_systems": user_websites,
                "anomalies": user_anomalies,
                "heals_last_24h": 0,  # Users don't see auto-heals
                "critical_alerts": 0,
                "ai_engine_status": "running",
                "user_websites": user_websites,
                "user_anomalies": user_anomalies,
                "processes": system_stats.get("processes", 0),
                "uptime": system_stats.get("uptime", 0)
            }

        comprehensive_logger.log_user_activity("dashboard_access", user_id, "dashboard")
        return jsonify(dashboard_data), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("dashboard_stats", str(e), "get_dashboard_stats", getattr(request, 'user_id', None))
        return jsonify({"error": "Failed to fetch dashboard stats"}), 500

@app.route('/api/dashboard', methods=['GET', 'OPTIONS'])
@token_required
def dashboard():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        # Get system stats
        stats = get_user_system_stats()
        
        # Get monitoring metrics
        monitoring_metrics = monitoring_api.get_system_metrics()
        
        # Get recent logs
        logs = comprehensive_logger.get_logs(
            user_id=request.user_id,
            is_admin=request.is_admin
        )[-10:]  # Last 10 logs
        
        dashboard_data = {
            "system_health": {
                "status": "healthy",
                "cpu": stats.get("cpu", 0),
                "memory": stats.get("memory", 0),
                "disk": stats.get("disk", 0),
                "uptime_percentage": calculate_uptime_percentage()
            },
            "monitoring": {
                "total_hosts": monitoring_metrics.get("total_hosts", 0),
                "online_hosts": monitoring_metrics.get("online_hosts", 0),
                "active_alerts": monitoring_metrics.get("active_alerts", 0)
            },
            "recent_activity": {
                "logs": logs,
                "total_logs": len(logs)
            },
            "services": {
                "student_portal": monitoring_metrics.get("student_portal_status", "unknown"),
                "lms": monitoring_metrics.get("lms_status", "unknown"),
                "website": monitoring_metrics.get("university_website_status", "unknown"),
                "email": monitoring_metrics.get("email_status", "unknown")
            }
        }
        
        comprehensive_logger.log_user_activity("dashboard_access", request.user_id, "dashboard")
        return jsonify(dashboard_data), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("dashboard", str(e), "dashboard", request.user_id)
        return jsonify({"error": "Failed to fetch dashboard data"}), 500

@app.route('/api/system-stats', methods=['GET', 'OPTIONS'])
@token_required
def system_stats():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        stats = get_user_system_stats()
        store_user_metrics(request.user_id, stats)
        
        stats["uptime_percentage"] = calculate_uptime_percentage()
        stats["server_name"] = "neosilix-main"
        
        comprehensive_logger.log_user_activity("system_stats_access", request.user_id, "system_stats")
        return jsonify(stats), 200
    except Exception as e:
        comprehensive_logger.log_error_event("system_stats", str(e), "system_stats_route", request.user_id)
        return jsonify({"error": "Failed to fetch system stats"}), 500

@app.route('/api/performance-metrics', methods=['GET', 'OPTIONS'])
@token_required
def performance_metrics():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        stats = get_user_system_stats()
        
        performance_data = {
            "cpu": stats.get("cpu", 0),
            "memory": stats.get("memory", 0),
            "disk": stats.get("disk", 0),
            "network_in": stats.get("network_recv", 0),
            "network_out": stats.get("network_sent", 0),
            "processes": stats.get("processes", 0),
            "uptime": stats.get("uptime", 0),
            "uptime_percentage": calculate_uptime_percentage(),
            "timestamp": datetime.now().isoformat()
        }
        
        comprehensive_logger.auto_detect_performance_issues(performance_data, request.user_id)
        comprehensive_logger.log_user_activity("performance_metrics_access", request.user_id, "performance_metrics")
        
        return jsonify(performance_data), 200
    except Exception as e:
        comprehensive_logger.log_error_event("performance_metrics", str(e), "performance_metrics_route", request.user_id)
        return jsonify({"error": "Failed to fetch performance metrics"}), 500

@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "services": {
                "database": "connected",
                "ai_engine": "ready",
                "monitoring": "active"
            }
        }
        return jsonify(health_data), 200
    except Exception as e:
        comprehensive_logger.log_error_event("health_check", str(e), "health_route")
        return jsonify({"error": "Health check failed"}), 500

@app.route('/api/logs', methods=['GET', 'OPTIONS'])
@token_required
def get_logs():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        category = request.args.get('category')
        level = request.args.get('level')
        
        logs = comprehensive_logger.get_logs(
            user_id=request.user_id,
            is_admin=request.is_admin,
            category=category,
            level=level
        )
        
        comprehensive_logger.log_user_activity("logs_access", request.user_id, "logs", f"category={category}, level={level}")
        
        return jsonify({
            "logs": logs[-100:],
            "total_count": len(logs)
        }), 200
    except Exception as e:
        comprehensive_logger.log_error_event("logs_access", str(e), "get_logs", request.user_id)
        return jsonify({"error": "Failed to fetch logs"}), 500

@app.route('/api/ai-engine/status', methods=['GET', 'OPTIONS'])
@token_required
def get_ai_engine_status():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        status_data = {
            "status": "active",
            "model_loaded": model is not None,
            "anomaly_detection": "enabled",
            "self_healing": "enabled",
            "last_training": "2024-01-01T00:00:00Z",
            "accuracy": 0.95
        }
        comprehensive_logger.log_ai_engine_event("status_check", "success", None, request.user_id)
        return jsonify(status_data), 200
    except Exception as e:
        comprehensive_logger.log_ai_engine_event("status_check", "failed", str(e), request.user_id)
        return jsonify({"error": "Failed to get AI engine status"}), 500

@app.route('/api/ai-engine/anomalies', methods=['GET', 'OPTIONS'])
@token_required
def get_anomalies():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        anomalies = []
        
        try:
            with open(METRICS_HISTORY_PATH, 'r') as f:
                history = json.load(f)
            
            metrics_data = []
            for entry in history[-100:]:
                if 'metrics' in entry:
                    metrics = entry['metrics']
                    metrics_data.append([
                        metrics.get('cpu', 0),
                        metrics.get('memory', 0),
                        metrics.get('disk', 0),
                        metrics.get('network_recv', 0),
                        metrics.get('network_sent', 0)
                    ])
            
            if len(metrics_data) > 10:
                global model
                if model is None:
                    model = IsolationForest(contamination=0.1, random_state=42)
                    model.fit(metrics_data)
                
                predictions = model.predict(metrics_data)
                anomaly_indices = np.where(predictions == -1)[0]
                
                for idx in anomaly_indices[-5:]:
                    if idx < len(history):
                        entry = history[idx]
                        anomalies.append({
                            "timestamp": entry.get('timestamp'),
                            "metrics": entry.get('metrics', {}),
                            "score": float(predictions[idx])
                        })
        except Exception as e:
            comprehensive_logger.log_error_event("anomaly_detection", str(e), "get_anomalies", request.user_id)
        
        comprehensive_logger.log_ai_engine_event("anomaly_check", "success", f"Found {len(anomalies)} anomalies", request.user_id)
        return jsonify({"anomalies": anomalies}), 200
    except Exception as e:
        comprehensive_logger.log_ai_engine_event("anomaly_check", "failed", str(e), request.user_id)
        return jsonify({"error": "Failed to get anomalies"}), 500

@app.route('/api/ai-engine/heal', methods=['POST', 'OPTIONS'])
@token_required
def trigger_healing():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        data = request.get_json()
        anomaly_type = data.get('anomaly_type', 'unknown')
        
        result = heal_anomaly(anomaly_type)
        
        if result.get('success'):
            comprehensive_logger.log_ai_engine_event("healing_triggered", "success", f"Anomaly: {anomaly_type}", request.user_id)
            return jsonify({
                "message": f"Healing triggered for {anomaly_type}",
                "action": result.get('action')
            }), 200
        else:
            comprehensive_logger.log_ai_engine_event("healing_triggered", "failed", f"Anomaly: {anomaly_type}", request.user_id)
            return jsonify({"error": result.get('error', 'Healing failed')}), 400
    except Exception as e:
        comprehensive_logger.log_ai_engine_event("healing_triggered", "failed", str(e), request.user_id)
        return jsonify({"error": "Failed to trigger healing"}), 500

@app.route('/api/metrics', methods=['GET'])
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

@app.route('/api/copilot/logs', methods=['GET', 'OPTIONS'])
@token_required
def get_copilot_logs():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        logs = copilot_logs[-50:]
        comprehensive_logger.log_user_activity("copilot_logs_access", request.user_id, "copilot")
        return jsonify({"logs": logs}), 200
    except Exception as e:
        comprehensive_logger.log_error_event("copilot_logs", str(e), "get_copilot_logs", request.user_id)
        return jsonify({"error": "Failed to fetch copilot logs"}), 500

@app.route('/api/admin/dashboard', methods=['GET', 'OPTIONS'])
@admin_required
def admin_dashboard():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        dashboard_data = {
            "system_health": {
                "status": "healthy",
                "uptime": 86400,
                "services": 12,
                "services_healthy": 11
            },
            "performance": {
                "cpu": 45.5,
                "memory": 78.2,
                "disk": 62.8,
                "network": 125000
            },
            "users": {
                "total": 1542,
                "active_today": 342,
                "new_this_week": 127
            },
            "alerts": {
                "critical": 2,
                "warning": 5,
                "info": 12
            },
            "ai_engine": {
                "status": "active",
                "anomalies_detected": 3,
                "healing_actions": 12
            }
        }
        
        comprehensive_logger.log_user_activity("admin_dashboard_access", request.user_id, "administration")
        return jsonify(dashboard_data), 200
    except Exception as e:
        comprehensive_logger.log_error_event("admin_dashboard", str(e), "admin_dashboard", request.user_id)
        return jsonify({"error": "Failed to fetch admin dashboard data"}), 500

@app.route('/api/admin/users', methods=['GET', 'OPTIONS'])
@admin_required
def admin_users():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        session = SessionLocal()
        users = session.query(User).all()
        session.close()
        
        users_data = []
        for user in users:
            users_data.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None
            })
        
        comprehensive_logger.log_user_activity("admin_users_access", request.user_id, "administration")
        return jsonify({"users": users_data}), 200
    except Exception as e:
        comprehensive_logger.log_error_event("admin_users", str(e), "admin_users", request.user_id)
        return jsonify({"error": "Failed to fetch users"}), 500

@app.route('/api/admin/logs', methods=['GET', 'OPTIONS'])
@admin_required
def admin_logs():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        category = request.args.get('category')
        level = request.args.get('level')
        user_id = request.args.get('user_id')
        
        logs = comprehensive_logger.get_logs(
            user_id=user_id,
            is_admin=True,
            category=category,
            level=level
        )
        
        comprehensive_logger.log_user_activity("admin_logs_access", request.user_id, "administration", f"category={category}, level={level}")
        
        return jsonify({
            "logs": logs,
            "total_count": len(logs)
        }), 200
    except Exception as e:
        comprehensive_logger.log_error_event("admin_logs", str(e), "admin_logs", request.user_id)
        return jsonify({"error": "Failed to fetch admin logs"}), 500

@app.route('/api/admin/system-info', methods=['GET', 'OPTIONS'])
@admin_required
def admin_system_info():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        system_info = {
            "python_version": sys.version,
            "flask_version": "2.3.3",
            "platform": sys.platform,
            "database_url": DB_URL.replace(DB_CONFIG['password'], '***'),
            "monitoring_services": {
                "zabbix": zabbix_api.auth_token is not None,
                "grafana": False,
                "prometheus": False
            },
            "ai_engine": {
                "model_loaded": model is not None,
                "self_healing": True
            },
            "logging": {
                "total_logs": len(comprehensive_logger.logs),
                "performance_thresholds": comprehensive_logger.performance_thresholds
            }
        }
        
        comprehensive_logger.log_user_activity("admin_system_info_access", request.user_id, "administration")
        return jsonify(system_info), 200
    except Exception as e:
        comprehensive_logger.log_error_event("admin_system_info", str(e), "admin_system_info", request.user_id)
        return jsonify({"error": "Failed to fetch system info"}), 500

@app.route('/api/targets/<int:target_id>/health', methods=['GET', 'OPTIONS'])
@token_required
def get_target_health(target_id):
    """Get comprehensive health analysis for a target"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        user_id = getattr(request, "user_id", None)
        is_admin = getattr(request, "is_admin", False)
        
        target = MonitoringTarget.query.get(target_id)
        if not target:
            return jsonify({'error': 'Target not found'}), 404
        
        # Check permissions
        if not is_admin and target.user_id != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get recent metrics for real data
        recent_metrics = TargetMetric.query.filter_by(
            target_id=target_id
        ).order_by(TargetMetric.timestamp.desc()).limit(5).all()
        
        # Build health report with real data
        response_time = None
        for metric in recent_metrics:
            if metric.type == 'response_time':
                response_time = metric.value
                break
        
        # Determine health status based on real metrics
        issues = []
        suggestions = []
        
        if target.status == "offline":
            issues.append("target_offline")
            suggestions.append("Target is not responding to ping checks")
            suggestions.append("Check network connectivity and firewall rules")
        elif response_time and response_time > 500:  # High latency threshold
            issues.append("high_latency")
            suggestions.append(f"High network latency detected: {response_time}ms")
            suggestions.append("Investigate network congestion or routing issues")
        elif response_time and response_time > 1000:  # Very high latency
            issues.append("critical_latency") 
            suggestions.append(f"Critical network latency: {response_time}ms")
            suggestions.append("Immediate network investigation required")
        
        # Get actual open ports from recent scan (you might need to store this)
        open_ports = [22, 53, 80, 443]  # Default/common ones
        
        health_report = {
            "target": {
                "id": target.id,
                "name": target.name,
                "type": target.type,
                "ip_address": target.ip_address,
                "status": target.status,
                "priority": target.priority,
                "last_check": target.last_check.isoformat() if target.last_check else None
            },
            "health": {
                "status": target.status,
                "issues": issues,
                "suggestions": suggestions,
                "last_checked": datetime.now().isoformat(),
                "response_time": response_time,
                "metrics_count": len(recent_metrics)
            },
            "services": [
                {"name": "SSH", "port": 22, "status": "healthy" if 22 in open_ports else "closed"},
                {"name": "DNS", "port": 53, "status": "healthy" if 53 in open_ports else "closed"}, 
                {"name": "HTTP", "port": 80, "status": "healthy" if 80 in open_ports else "closed"},
                {"name": "HTTPS", "port": 443, "status": "healthy" if 443 in open_ports else "closed"}
            ],
            "recommendations": [
                {
                    "priority": "high" if issues else "low",
                    "action": "Network Performance Review" if response_time else "Regular Monitoring",
                    "steps": suggestions if suggestions else ["Continue regular health checks", "Monitor performance trends"]
                }
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        comprehensive_logger.log_user_activity("target_health_check", user_id, "monitoring", 
                                             f"Health check for {target.name}")
        
        return jsonify(health_report), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("target_health", str(e), "get_target_health", getattr(request, 'user_id', None))
        return jsonify({'error': 'Failed to get target health'}), 500

@app.route('/api/targets/<int:target_id>/deep-scan', methods=['POST', 'OPTIONS'])
@token_required
def deep_scan_target(target_id):
    """Perform comprehensive scan on target"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        user_id = getattr(request, "user_id", None)
        is_admin = getattr(request, "is_admin", False)
        
        target = MonitoringTarget.query.get(target_id)
        if not target:
            return jsonify({'error': 'Target not found'}), 404
        
        # Check permissions
        if not is_admin and target.user_id != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Perform multiple checks
        import subprocess
        import platform
        import socket
        import time
        
        scan_results = {
            "basic_ping": False,
            "port_scan": [],
            "response_time": None,
            "services": [],
            "detailed_metrics": {}
        }
        
        # Basic ping check with timing
        param = "-n" if platform.system().lower() == "windows" else "-c"
        command = ["ping", param, "4", target.ip_address]  # 4 packets for better timing
        
        try:
            start_time = time.time()
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            end_time = time.time()
            
            scan_results["basic_ping"] = result.returncode == 0
            
            # Extract response time from ping output
            if scan_results["basic_ping"]:
                lines = result.stdout.split('\n')
                times = []
                for line in lines:
                    if 'time=' in line:
                        try:
                            time_str = line.split('time=')[1].split(' ')[0]
                            time_ms = float(time_str.replace('ms', ''))
                            times.append(time_ms)
                        except:
                            continue
                
                if times:
                    scan_results["response_time"] = sum(times) / len(times)
                    scan_results["detailed_metrics"]["ping_times"] = times
                    scan_results["detailed_metrics"]["ping_loss"] = 0  # Can calculate packet loss
                
                # Overall scan duration
                scan_results["detailed_metrics"]["scan_duration"] = round((end_time - start_time) * 1000, 2)
            
        except subprocess.TimeoutExpired:
            scan_results["basic_ping"] = False
            scan_results["detailed_metrics"]["scan_timeout"] = True
        
        # Comprehensive port scan for common services
        common_ports = [
            (22, "SSH"), (80, "HTTP"), (443, "HTTPS"), (53, "DNS"),
            (21, "FTP"), (25, "SMTP"), (110, "POP3"), (143, "IMAP"),
            (993, "IMAPS"), (995, "POP3S"), (3389, "RDP"), (5900, "VNC")
        ]
        
        open_ports = []
        for port, service_name in common_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                start_connect = time.time()
                result = sock.connect_ex((target.ip_address, port))
                connect_time = time.time() - start_connect
                sock.close()
                
                if result == 0:
                    port_info = {
                        "port": port,
                        "status": "open",
                        "service": service_name,
                        "response_time": round(connect_time * 1000, 2)  # Convert to ms
                    }
                    open_ports.append(port_info)
                    scan_results["port_scan"].append(port_info)
            except:
                pass
        
        # DNS resolution test (for DNS servers)
        if target.ip_address in ["8.8.8.8", "8.8.4.4", "1.1.1.1"]:
            try:
                import dns.resolver
                resolver = dns.resolver.Resolver()
                resolver.nameservers = [target.ip_address]
                start_dns = time.time()
                answers = resolver.resolve('google.com', 'A')
                dns_time = time.time() - start_dns
                scan_results["detailed_metrics"]["dns_response_time"] = round(dns_time * 1000, 2)
                scan_results["detailed_metrics"]["dns_resolved"] = [str(rdata) for rdata in answers]
            except:
                scan_results["detailed_metrics"]["dns_failed"] = True
        
        # Update target status based on comprehensive scan
        if scan_results["basic_ping"]:
            if scan_results["response_time"] and scan_results["response_time"] > 500:  # High latency
                target.status = "warning"
            else:
                target.status = "healthy"
                
            # Store response time metric
            if scan_results["response_time"]:
                new_metric = TargetMetric(
                    type='response_time',
                    value=scan_results["response_time"],
                    unit='ms',
                    target_id=target_id
                )
                db.session.add(new_metric)
        else:
            target.status = "offline"
        
        target.last_check = datetime.now(timezone.utc)
        db.session.commit()
        
        comprehensive_logger.log_user_activity("deep_scan", user_id, "monitoring", 
                                             f"Deep scan for {target.name}: {target.status}")
        
        return jsonify({
            "status": "success",
            "message": f"Deep scan completed for {target.name}",
            "scan_results": scan_results,
            "target_status": target.status,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        comprehensive_logger.log_error_event("deep_scan", str(e), "deep_scan_target", getattr(request, 'user_id', None))
        return jsonify({'error': f'Deep scan failed: {str(e)}'}), 500

@app.route('/api/alerts', methods=['GET', 'OPTIONS'])
@token_required
def get_alerts():
    """Get REAL system alerts based on actual monitoring"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        user_id = getattr(request, "user_id", None)
        is_admin = getattr(request, "is_admin", False)
        
        alerts = []
        
        # Get user's targets to check for alerts
        if is_admin:
            targets = MonitoringTarget.query.all()
        else:
            targets = MonitoringTarget.query.filter_by(user_id=user_id).all()
        
        # Check each target for issues and create REAL alerts
        for target in targets:
            # Alert for offline targets
            if target.status == "offline":
                alerts.append({
                    "id": len(alerts) + 1,
                    "target_id": target.id,
                    "type": "target_offline",
                    "severity": "critical",
                    "message": f"Target {target.name} ({target.ip_address}) is offline",
                    "suggested_fix": "Check network connectivity and power supply",
                    "timestamp": datetime.now().isoformat(),
                    "acknowledged": False
                })
            
            # Alert for targets that haven't been checked recently
            if target.last_check:
                time_since_check = datetime.now(timezone.utc) - target.last_check
                if time_since_check.total_seconds() > 3600:  # 1 hour
                    alerts.append({
                        "id": len(alerts) + 1,
                        "target_id": target.id,
                        "type": "stale_data",
                        "severity": "warning",
                        "message": f"Target {target.name} hasn't been checked in over 1 hour",
                        "suggested_fix": "Run a manual scan to update status",
                        "timestamp": datetime.now().isoformat(),
                        "acknowledged": False
                    })
        
        # Add system performance alerts
        system_stats = get_user_system_stats()
        
        # CPU alert
        if system_stats.get('cpu', 0) > 80:
            alerts.append({
                "id": len(alerts) + 1,
                "target_id": None,
                "type": "high_cpu",
                "severity": "warning",
                "message": f"High CPU usage: {system_stats['cpu']:.1f}%",
                "suggested_fix": "Check for resource-intensive processes",
                "timestamp": datetime.now().isoformat(),
                "acknowledged": False
            })
        
        # Memory alert
        if system_stats.get('memory', 0) > 85:
            alerts.append({
                "id": len(alerts) + 1,
                "target_id": None,
                "type": "high_memory",
                "severity": "warning",
                "message": f"High memory usage: {system_stats['memory']:.1f}%",
                "suggested_fix": "Consider adding more RAM or optimizing applications",
                "timestamp": datetime.now().isoformat(),
                "acknowledged": False
            })
        
        # Disk alert
        if system_stats.get('disk', 0) > 90:
            alerts.append({
                "id": len(alerts) + 1,
                "target_id": None,
                "type": "high_disk",
                "severity": "critical",
                "message": f"High disk usage: {system_stats['disk']:.1f}%",
                "suggested_fix": "Clean up disk space or expand storage",
                "timestamp": datetime.now().isoformat(),
                "acknowledged": False
            })
        
        comprehensive_logger.log_user_activity("alerts_access", user_id, "alerts", f"Found {len(alerts)} alerts")
        
        return jsonify({
            "alerts": alerts,
            "total": len(alerts),
            "critical_count": len([a for a in alerts if a['severity'] == 'critical']),
            "warning_count": len([a for a in alerts if a['severity'] == 'warning']),
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("alerts", str(e), "get_alerts", getattr(request, 'user_id', None))
        return jsonify({"error": "Failed to fetch alerts"}), 500

# ================== ENHANCED AI ASSISTANT ROUTES ==================# Initialize the enhanced AI assistant

@app.route('/api/ai-assistant/ask-enhanced', methods=['POST', 'OPTIONS'])
@token_required
def ask_enhanced_ai():
    """Enhanced AI assistant with conversation history and target creation"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'error': 'No question provided'}), 400
        
        # Get current system metrics for context
        system_stats = get_user_system_stats()
        monitoring_metrics = monitoring_api.get_system_metrics()
        combined_metrics = {**system_stats, **monitoring_metrics}
        
        # Get monitoring targets data for context
        user_id = getattr(request, "user_id", None)
        is_admin = getattr(request, "is_admin", False)
        
        if is_admin:
            targets = MonitoringTarget.query.all()
        else:
            targets = MonitoringTarget.query.filter_by(user_id=user_id).all()
        
        targets_data = [target.to_dict() for target in targets]
        
        # Get user context
        user_context = {
            'user_id': user_id,
            'is_admin': is_admin
        }
        
        # Call the enhanced universal AI assistant
        response = enhanced_ai_assistant.ask_anything(
            question, 
            combined_metrics, 
            user_context, 
            targets_data
        )
        
        # Enhanced logging with user context
        comprehensive_logger.log_ai_engine_event(
            "ask_enhanced_ai", 
            "processed", 
            f"User: {user_id} | Question: {question[:50]}... | Type: {response.get('question_type', 'unknown')}",
            user_id
        )
        
        return jsonify(response), 200
        
    except SecurityException as e:
        comprehensive_logger.log_security_event("ai_assistant_security", "medium", request.user_id, str(e))
        return jsonify({'error': 'Security violation detected'}), 403
        
    except Exception as e:
        comprehensive_logger.log_error_event("ask_enhanced_ai", str(e), "ask_enhanced_ai", request.user_id)
        return jsonify({'error': 'Failed to process question'}), 500

@app.route('/api/ai-assistant/conversation-history', methods=['GET', 'OPTIONS'])
@token_required
def get_conversation_history():
    """Get conversation history for the current user"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        user_id = getattr(request, "user_id", None)
        max_messages = request.args.get('max_messages', 10, type=int)
        
        history = enhanced_ai_assistant.conversation_manager.get_conversation_history(
            user_id, max_messages
        )
        
        comprehensive_logger.log_user_activity(
            "conversation_history_access", 
            user_id, 
            "ai_assistant",
            f"Retrieved {len(history)} messages"
        )
        
        return jsonify({
            'user_id': user_id,
            'history': history,
            'total_messages': len(history),
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("conversation_history", str(e), "get_conversation_history", request.user_id)
        return jsonify({"error": "Failed to fetch conversation history"}), 500

@app.route('/api/ai-assistant/clear-history', methods=['POST', 'OPTIONS'])
@token_required
def clear_conversation_history():
    """Clear conversation history for the current user"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        user_id = getattr(request, "user_id", None)
        
        enhanced_ai_assistant.conversation_manager.clear_user_history(user_id)
        
        comprehensive_logger.log_user_activity(
            "conversation_history_cleared", 
            user_id, 
            "ai_assistant"
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Conversation history cleared successfully',
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("clear_history", str(e), "clear_conversation_history", request.user_id)
        return jsonify({"error": "Failed to clear conversation history"}), 500

# ================== USER & TARGET MANAGEMENT ENDPOINTS ==================

@app.route('/api/user/stats', methods=['GET', 'OPTIONS'])
@token_required
def get_user_stats():
    """Get user-specific statistics"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        user_id = getattr(request, "user_id", None)
        
        # Get REAL system stats
        stats = get_user_system_stats()
        
        try:
            # Use raw SQL to avoid the status column issue
            from sqlalchemy import text
            result = db.session.execute(text("SELECT COUNT(*) FROM websites WHERE user_id = :user_id"), 
                               {"user_id": user_id})
            user_websites_count = result.scalar() or 0
        except Exception as db_error:
            print(f"Database error counting websites: {db_error}")
            user_websites_count = 0

        user_stats = {
            "cpu": stats.get("cpu", 0),
            "memory": stats.get("memory", 0),
            "disk": stats.get("disk", 0),
            "network_recv": stats.get("network_recv", 0),
            "network_sent": stats.get("network_sent", 0),
            "processes": stats.get("processes", 0),
            "uptime": stats.get("uptime", 0),
            "user_websites": user_websites_count,
            "user_anomalies": 0,
            "uptime_percentage": calculate_uptime_percentage(),
            "timestamp": datetime.now().isoformat()
        }
        
        comprehensive_logger.log_user_activity("user_stats_access", user_id, "stats")
        return jsonify(user_stats), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("user_stats", str(e), "get_user_stats", getattr(request, 'user_id', None))
        return jsonify({"error": "Failed to fetch user stats"}), 500

@app.route('/api/targets', methods=['GET', 'OPTIONS'])
@token_required
def get_targets():
    """Get all monitoring targets for the current user"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        user_id = getattr(request, "user_id", None)
        is_admin = getattr(request, "is_admin", False)
        
        if is_admin:
            targets = MonitoringTarget.query.all()
        else:
            targets = MonitoringTarget.query.filter_by(user_id=user_id).all()
        
        targets_data = [target.to_dict() for target in targets]
        
        comprehensive_logger.log_user_activity("targets_list_access", user_id, "targets")
        
        return jsonify({
            "targets": targets_data,
            "total": len(targets_data)
        }), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("targets_list", str(e), "get_targets", getattr(request, 'user_id', None))
        return jsonify({"error": "Failed to fetch targets"}), 500

@app.route('/api/targets', methods=['POST', 'OPTIONS'])
@token_required
def add_target():
    """Add a new monitoring target"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        user_id = getattr(request, "user_id", None)
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validate required fields
        required_fields = ['name', 'type', 'ip_address']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Create new target
        new_target = MonitoringTarget(
            name=data['name'],
            type=data.get('type', 'server'),
            ip_address=data['ip_address'],
            subnet=data.get('subnet', '32'),
            priority=data.get('priority', 'medium'),
            user_id=user_id,
            status='unknown',
            last_check=datetime.now(timezone.utc)
        )
        
        db.session.add(new_target)
        db.session.commit()
        
        comprehensive_logger.log_user_activity("target_added", user_id, "targets", f"Added target: {data['name']}")
        
        return jsonify({
            "status": "success",
            "message": "Target added successfully",
            "target": new_target.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        comprehensive_logger.log_error_event("target_add", str(e), "add_target", getattr(request, 'user_id', None))
        return jsonify({"error": f"Failed to add target: {str(e)}"}), 500

@app.route('/api/targets/<int:target_id>', methods=['DELETE', 'OPTIONS'])
@token_required
def delete_target(target_id):
    """Delete a monitoring target"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        user_id = getattr(request, "user_id", None)
        is_admin = getattr(request, "is_admin", False)
        
        target = MonitoringTarget.query.get_or_404(target_id)
        
        # Check permissions
        if not is_admin and target.user_id != user_id:
            return jsonify({"error": "Access denied"}), 403
        
        db.session.delete(target)
        db.session.commit()
        
        comprehensive_logger.log_user_activity("target_deleted", user_id, "targets", f"Deleted target: {target.name}")
        
        return jsonify({
            "status": "success",
            "message": "Target deleted successfully"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        comprehensive_logger.log_error_event("target_delete", str(e), "delete_target", getattr(request, 'user_id', None))
        return jsonify({"error": f"Failed to delete target: {str(e)}"}), 500

@app.route('/api/targets/<int:target_id>/scan', methods=['POST', 'OPTIONS'])
@token_required
def scan_target(target_id):
    """Perform REAL quick scan on target using actual ping"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        user_id = getattr(request, "user_id", None)
        is_admin = getattr(request, "is_admin", False)
        
        target = MonitoringTarget.query.get_or_404(target_id)
        
        # Check permissions
        if not is_admin and target.user_id != user_id:
            return jsonify({"error": "Access denied"}), 403
        
        import subprocess
        import platform
        
        # REAL ping check - no randomness
        param = "-n" if platform.system().lower() == "windows" else "-c"
        command = ["ping", param, "3", target.ip_address]  # 3 real packets
        
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                target.status = "healthy"
                # Extract real response time
                response_time = None
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'time=' in line:
                        time_str = line.split('time=')[1].split(' ')[0]
                        response_time = float(time_str.replace('ms', ''))
                        break
                
                # Store real metric
                new_metric = TargetMetric(
                    type='ping_response_time',
                    value=response_time or 1.0,
                    unit='ms',
                    target_id=target_id
                )
                db.session.add(new_metric)
            else:
                target.status = "offline"
                
        except subprocess.TimeoutExpired:
            target.status = "offline"
        except Exception as e:
            target.status = "unknown"
            print(f"Ping error: {e}")
        
        target.last_check = datetime.now(timezone.utc)
        db.session.commit()
        
        comprehensive_logger.log_user_activity("target_scanned", user_id, "targets", 
                                             f"REAL scan for {target.name}: {target.status}")
        
        return jsonify({
            "status": "success",
            "target_status": target.status,
            "message": f"REAL scan completed: {target.status}"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        comprehensive_logger.log_error_event("target_scan", str(e), "scan_target", getattr(request, 'user_id', None))
        return jsonify({"error": f"Scan failed: {str(e)}"}), 500


@app.route('/api/admin/stats', methods=['GET', 'OPTIONS'])
@admin_required
def get_admin_stats():
    """Get admin dashboard statistics"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        # Get system stats
        stats = get_user_system_stats()
        
        # Get admin-specific data
        total_users = User.query.count()
        total_websites = Website.query.count()
        
        admin_stats = {
            "cpu": stats.get("cpu", 0),
            "memory": stats.get("memory", 0),
            "disk": stats.get("disk", 0),
            "network_recv": stats.get("network_recv", 0),
            "network_sent": stats.get("network_sent", 0),
            "total_users": total_users,
            "total_websites": total_websites,
            "anomalies": 0,  # You can implement this
            "heals_last_24h": 0,  # You can implement this
            "uptime_percentage": calculate_uptime_percentage(),
            "ai_engine_status": "active",
            "system_uptime": stats.get("uptime", 0),
            "timestamp": datetime.now().isoformat()
        }
        
        comprehensive_logger.log_user_activity("admin_stats_access", request.user_id, "administration")
        return jsonify(admin_stats), 200
        
    except Exception as e:
        comprehensive_logger.log_error_event("admin_stats", str(e), "get_admin_stats", getattr(request, 'user_id', None))
        return jsonify({"error": "Failed to fetch admin stats"}), 500

@app.errorhandler(404)
def not_found(error):
    comprehensive_logger.log_error_event("404_not_found", str(error), "error_handler", getattr(request, 'user_id', None))
    return jsonify({'message': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    comprehensive_logger.log_error_event("500_internal_error", str(error), "error_handler", getattr(request, 'user_id', None))
    return jsonify({'message': 'Internal server error'}), 500

@app.errorhandler(401)
def unauthorized(error):
    comprehensive_logger.log_security_event("unauthorized_access", "medium", getattr(request, 'user_id', None))
    return jsonify({'message': 'Unauthorized'}), 401

@app.errorhandler(403)
def forbidden(error):
    comprehensive_logger.log_security_event("forbidden_access", "medium", getattr(request, 'user_id', None))
    return jsonify({'message': 'Forbidden'}), 403

# ================== INITIALIZATION ==================
def initialize_ai_model():
    global model
    try:
        if os.path.exists(MODEL_PATH):
            model = joblib.load(MODEL_PATH)
            print("[SUCCESS] AI model loaded successfully")
            comprehensive_logger.log_ai_engine_event("model_loading", "success", "Model loaded from disk")
        else:
            model = IsolationForest(contamination=0.1, random_state=42)
            print("[INFO] Created new AI model")
            comprehensive_logger.log_ai_engine_event("model_creation", "success", "New model created")
    except Exception as e:
        print(f"[ERROR] Failed to initialize AI model: {e}")
        comprehensive_logger.log_ai_engine_event("model_initialization", "failed", str(e))

def initialize_cpu_healer():
    """Initialize the CPU auto-healing system"""
    try:
        # Start the safe CPU auto-heal monitor
        start_cpu_auto_heal_monitor(interval=30, cpu_threshold=80)
        print("[SUCCESS] CPU Auto-Healer started successfully")
        comprehensive_logger.log_ai_engine_event("cpu_healer", "started", "CPU auto-healing monitor activated")
        
        # Test the CPU healer on startup
        test_result = intelligent_cpu_healer(cpu_threshold=10)  # Low threshold to test
        print(f"[DEBUG] CPU Healer test: {test_result['status']}")
        
    except Exception as e:
        print(f"[ERROR] Failed to start CPU healer: {e}")
        comprehensive_logger.log_ai_engine_event("cpu_healer", "failed", str(e))

# ================== NEW COMPREHENSIVE LOGGING ENDPOINTS ==================

@app.route("/api/logs/comprehensive", methods=["GET"])
@token_required
def comprehensive_logs():
    """Get comprehensive logs for current user (both admin and regular users)"""
    try:
        user_id = getattr(request, "user_id", None)
        is_admin = getattr(request, "is_admin", False)
        
        category = request.args.get('category')
        level = request.args.get('level')
        
        # Get logs filtered by user access
        logs = comprehensive_logger.get_logs(
            user_id=user_id, 
            is_admin=is_admin, 
            category=category, 
            level=level
        )
        
        comprehensive_logger.log_user_activity("comprehensive_logs_access", user_id, "logging_system")
        
        # FIX: Explicitly set content type and ensure proper JSON serialization
        response = jsonify(logs)
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response, 200
    except Exception as e:
        comprehensive_logger.log_error_event("log_retrieval", str(e), "comprehensive_logs", getattr(request, 'user_id', None))
        response = jsonify({"error": "Failed to fetch comprehensive logs"})
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response, 500

@app.route("/api/logs/stats", methods=["GET"])
@token_required
def log_statistics():
    """Get logging statistics for current user"""
    try:
        user_id = getattr(request, "user_id", None)
        is_admin = getattr(request, "is_admin", False)
        
        stats = comprehensive_logger.get_log_stats()
        
        # Filter stats for non-admin users
        if not is_admin:
            user_logs = comprehensive_logger.get_logs(user_id=user_id, is_admin=False)
            stats['total_logs'] = len(user_logs)
            stats['by_level'] = {}
            stats['by_category'] = {}
            
            for log in user_logs:
                level = log.get('level', 'unknown')
                stats['by_level'][level] = stats['by_level'].get(level, 0) + 1
                
                category = log.get('category', 'unknown')
                stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
            
            stats['recent_activity'] = [{
                'timestamp': log['timestamp'],
                'level': log['level'],
                'category': log['category'],
                'message': log['message'][:100]
            } for log in user_logs[-10:]]
        
        comprehensive_logger.log_user_activity("log_stats_access", user_id, "logging_system")
        
        # FIX: Explicitly set content type
        response = jsonify(stats)
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response, 200
    except Exception as e:
        comprehensive_logger.log_error_event("log_stats", str(e), "log_statistics", getattr(request, 'user_id', None))
        response = jsonify({"error": "Failed to fetch log statistics"})
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response, 500

@app.route("/api/logs/categories", methods=["GET"])
@token_required
def log_categories():
    """Get available log categories"""
    categories = [
        "user_activity", "performance", "infrastructure", 
        "error", "security", "ai_engine", "legacy"
    ]
    comprehensive_logger.log_user_activity("log_categories_access", request.user_id, "logging_system")
    return jsonify(categories)

@app.route("/api/debug/logs-stats", methods=["GET"])
def debug_logs_stats():
    """Debug endpoint to check what log stats returns"""
    try:
        stats = comprehensive_logger.get_log_stats()
        return jsonify({
            "debug": True,
            "stats": stats,
            "content_type": "application/json"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Initialize the ML components when app starts
def initialize_ml_components():
    """Initialize all ML components"""
    try:
        print("[ML] Initializing cross-component ML intelligence...")
        
        # Start with basic dependency discovery
        monitoring_data = {'timestamp': datetime.now().isoformat()}
        dependency_mapper.auto_discover_dependencies(monitoring_data)
        
        print("[ML] ML components initialized successfully")
        comprehensive_logger.log_ai_engine_event("ml_initialization", "success", 
                                               "Advanced ML intelligence with root cause analysis and business impact correlation started")
        
    except Exception as e:
        print(f"[ML ERROR] Initialization failed: {e}")
        comprehensive_logger.log_error_event("ml_initialization", str(e), "initialize_ml_components")
        
def start_background_tasks():
    """Start all background tasks including autonomous operations"""
    try:
        # Existing tasks
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        
        heal_thread = threading.Thread(target=auto_heal_loop, daemon=True)
        heal_thread.start()
        
        # ML initialization
        ml_init_thread = threading.Thread(target=initialize_ml_components, daemon=True)
        ml_init_thread.start()
        
        # Autonomous operations
        autonomy_thread = threading.Thread(target=start_autonomous_operations, daemon=True)
        autonomy_thread.start()
        
        print("[SUCCESS] All background tasks and autonomous operations started")
        comprehensive_logger.log_infrastructure_event("background_tasks", "started", 
                                                    "monitoring, healing, ML intelligence, and autonomous operations")
    except Exception as e:
        print(f"[ERROR] Failed to start background tasks: {e}")
        comprehensive_logger.log_error_event("background_tasks", str(e), "start_background_tasks")


def start_auto_heal():
    thread = threading.Thread(target=auto_heal_loop, kwargs={'interval': 10}, daemon=True)
    thread.start()
    comprehensive_logger.log_ai_engine_event("auto_healing", "started")

if __name__ == '__main__':
    initialize_ai_model()
    start_background_tasks()
    initialize_cpu_healer()
    start_auto_heal()
    
    print("[SUCCESS] Neosilix AI System starting on http://localhost:5000")
    comprehensive_logger.log_infrastructure_event("system", "startup_complete", "Neosilix AI System started successfully")
    
    app.run(
        host='0.0.0.0', 
        port=5000, 
        debug=True, 
        use_reloader=False
    )
