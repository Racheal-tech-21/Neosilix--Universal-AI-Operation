# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

Base = db.Model

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    websites = db.relationship('Website', backref='owner', lazy=True)
    metrics = db.relationship('Metric', backref='user', lazy=True)
    monitoring_targets = db.relationship('MonitoringTarget', backref='owner', lazy=True)

class Website(db.Model):
    __tablename__ = 'websites'
    
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    name = db.Column(db.String(100))
    status = db.Column(db.String(20), default='unknown')
    last_check = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign key
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    metrics = db.relationship('Metric', backref='website', lazy=True)

class Metric(db.Model):
    __tablename__ = 'metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    metric_name = db.Column(db.String(100), nullable=False)
    metric_value = db.Column(db.Float)
    metric_json = db.Column(db.Text)
    metric_type = db.Column(db.String(20), default='numeric')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    website_id = db.Column(db.Integer, db.ForeignKey('websites.id'))

class HealingLogs(db.Model):
    __tablename__ = 'healing_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    anomaly_type = db.Column(db.String(100), nullable=False)
    action_taken = db.Column(db.String(500))
    status = db.Column(db.String(20), default='completed')
    details = db.Column(db.Text)
    improvement_percent = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    target_id = db.Column(db.Integer, db.ForeignKey('monitoring_targets.id'))

# ================== TARGET MANAGEMENT MODELS ==================

class MonitoringTarget(db.Model):
    __tablename__ = 'monitoring_targets'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    ip_address = db.Column(db.String(15), nullable=False)
    subnet = db.Column(db.String(18), default='32')
    status = db.Column(db.String(20), default='unknown')
    priority = db.Column(db.String(20), default='medium')
    last_check = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships - UPDATED to use target_services
    services = db.relationship('TargetService', backref='host', lazy=True, cascade='all, delete-orphan')
    target_metrics = db.relationship('TargetMetric', backref='target', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'ip_address': self.ip_address,
            'subnet': self.subnet,
            'status': self.status,
            'priority': self.priority,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'user_id': self.user_id,
            'services_count': len(self.services),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class TargetService(db.Model):
    __tablename__ = 'target_services'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    port = db.Column(db.Integer)
    protocol = db.Column(db.String(10), default='TCP')
    status = db.Column(db.String(20), default='unknown')
    last_check = db.Column(db.DateTime)
    host_id = db.Column(db.Integer, db.ForeignKey('monitoring_targets.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'port': self.port,
            'protocol': self.protocol,
            'status': self.status,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'host_id': self.host_id
        }

class TargetMetric(db.Model):
    __tablename__ = 'target_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)
    value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(10), default='%')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    target_id = db.Column(db.Integer, db.ForeignKey('monitoring_targets.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'value': self.value,
            'unit': self.unit,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'target_id': self.target_id
        }

# Initialize the database
def init_db():
    db.create_all()
