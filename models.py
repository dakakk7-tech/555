"""Database models — SQLAlchemy ORM модели."""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()


class User(db.Model):
    """Пользователь."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    api_token = db.Column(db.String(500), nullable=False)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    orders = db.relationship('Order', backref='user', lazy=True, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan')
    schedules = db.relationship('Schedule', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }


class Order(db.Model):
    """Заказ."""
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    order_id = db.Column(db.String(120), unique=True, nullable=False, index=True)
    buyer_id = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='pending', index=True)  # pending, completed, cancelled
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'buyer_id': self.buyer_id,
            'amount': self.amount,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }


class Notification(db.Model):
    """Уведомление."""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    notif_id = db.Column(db.String(120), unique=True, nullable=False, index=True)
    from_user = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, index=True)
    replied = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'notif_id': self.notif_id,
            'from_user': self.from_user,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat()
        }


class Schedule(db.Model):
    """Расписание для автоматизации."""
    __tablename__ = 'schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # check_orders, check_notifications, backup
    schedule_type = db.Column(db.String(50), default='interval')  # interval, cron
    interval_minutes = db.Column(db.Integer, default=30)
    cron_expression = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True, index=True)
    config = db.Column(db.JSON, default=dict)
    last_run = db.Column(db.DateTime)
    next_run = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'action': self.action,
            'schedule_type': self.schedule_type,
            'is_active': self.is_active,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None
        }


class Backup(db.Model):
    """Резервные копии."""
    __tablename__ = 'backups'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    filename = db.Column(db.String(300), nullable=False)
    size_bytes = db.Column(db.Integer)
    status = db.Column(db.String(50), default='completed')  # pending, completed, failed
    backup_type = db.Column(db.String(50), default='auto')  # auto, manual
    checksum = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'size_bytes': self.size_bytes,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }


class Statistics(db.Model):
    """Статистика и аналитика."""
    __tablename__ = 'statistics'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    date = db.Column(db.Date, default=datetime.utcnow, index=True)
    total_orders = db.Column(db.Integer, default=0)
    completed_orders = db.Column(db.Integer, default=0)
    total_revenue = db.Column(db.Float, default=0.0)
    avg_order_value = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'date': self.date.isoformat(),
            'total_orders': self.total_orders,
            'completed_orders': self.completed_orders,
            'total_revenue': self.total_revenue,
            'avg_order_value': self.avg_order_value
        }
