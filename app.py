"""Flask API — REST endpoints для управления FunPay."""

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
import logging
from datetime import datetime, timedelta
from config import config, logger
from models import db, User, Order, Notification, Schedule, Backup, Statistics
from backup_manager import BackupManager

# Инициализация Flask
app = Flask(__name__)
app.config.from_object(config)
db.init_app(app)
CORS(app)

# Rate limiting
limiter = Limiter(app=app, key_func=get_remote_address)

# Backup manager
backup_mgr = BackupManager()

logger_api = logging.getLogger("api")


def token_required(f):
    """Декоратор для проверки API токена."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Отсутствует токен"}), 401
        
        try:
            token = token.replace('Bearer ', '')
            user = User.query.filter_by(api_token=token, is_active=True).first()
            if not user:
                return jsonify({"error": "Неверный токен"}), 401
            return f(user, *args, **kwargs)
        except Exception as e:
            logger_api.error(f"Ошибка при проверке токена: {e}")
            return jsonify({"error": "Ошибка аутентификации"}), 500
    
    return decorated


# === Authentication endpoints ===
@app.route('/api/auth/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    """Регистрация нового пользователя."""
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        api_token = data.get('api_token')
        
        if not all([username, email, api_token]):
            return jsonify({"error": "Требуются username, email, api_token"}), 400
        
        if User.query.filter_by(username=username).first():
            return jsonify({"error": "Пользователь уже существует"}), 400
        
        user = User(username=username, email=email, api_token=api_token)
        db.session.add(user)
        db.session.commit()
        
        logger_api.info(f"Новый пользователь зарегистрирован: {username}")
        return jsonify({"id": user.id, "username": user.username}), 201
    except Exception as e:
        logger_api.error(f"Ошибка регистрации: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/auth/verify', methods=['POST'])
@token_required
def verify_token(user):
    """Проверка токена."""
    return jsonify(user.to_dict()), 200


# === Orders endpoints ===
@app.route('/api/orders', methods=['GET'])
@token_required
@limiter.limit("30 per minute")
def get_orders(user):
    """Получить заказы пользователя."""
    try:
        status = request.args.get('status')
        limit = request.args.get('limit', 50, type=int)
        
        query = Order.query.filter_by(user_id=user.id)
        if status:
            query = query.filter_by(status=status)
        
        orders = query.order_by(Order.created_at.desc()).limit(limit).all()
        return jsonify([order.to_dict() for order in orders]), 200
    except Exception as e:
        logger_api.error(f"Ошибка получения заказов: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/orders', methods=['POST'])
@token_required
def create_order(user):
    """Добавить заказ вручную."""
    try:
        data = request.get_json()
        order = Order(
            user_id=user.id,
            order_id=data.get('order_id'),
            buyer_id=data.get('buyer_id'),
            amount=data.get('amount'),
            status=data.get('status', 'pending'),
            description=data.get('description')
        )
        db.session.add(order)
        db.session.commit()
        
        logger_api.info(f"Заказ создан: {order.order_id}")
        return jsonify(order.to_dict()), 201
    except Exception as e:
        logger_api.error(f"Ошибка создания заказа: {e}")
        return jsonify({"error": str(e)}), 500


# === Notifications endpoints ===
@app.route('/api/notifications', methods=['GET'])
@token_required
@limiter.limit("30 per minute")
def get_notifications(user):
    """Получить уведомления."""
    try:
        is_read = request.args.get('is_read', type=bool)
        limit = request.args.get('limit', 50, type=int)
        
        query = Notification.query.filter_by(user_id=user.id)
        if is_read is not None:
            query = query.filter_by(is_read=is_read)
        
        notifs = query.order_by(Notification.created_at.desc()).limit(limit).all()
        return jsonify([n.to_dict() for n in notifs]), 200
    except Exception as e:
        logger_api.error(f"Ошибка получения уведомлений: {e}")
        return jsonify({"error": str(e)}), 500


# === Statistics endpoints ===
@app.route('/api/statistics', methods=['GET'])
@token_required
@limiter.limit("30 per minute")
def get_statistics(user):
    """Получить статистику."""
    try:
        days = request.args.get('days', 7, type=int)
        start_date = datetime.utcnow().date() - timedelta(days=days)
        
        stats = Statistics.query.filter(
            Statistics.user_id == user.id,
            Statistics.date >= start_date
        ).order_by(Statistics.date.desc()).all()
        
        return jsonify([s.to_dict() for s in stats]), 200
    except Exception as e:
        logger_api.error(f"Ошибка получения статистики: {e}")
        return jsonify({"error": str(e)}), 500


# === Backup endpoints ===
@app.route('/api/backup/create', methods=['POST'])
@token_required
@limiter.limit("5 per hour")
def create_backup(user):
    """Создать резервную копию вручную."""
    try:
        backup_info = backup_mgr.create_backup(user.id, "manual")
        
        if backup_info.get('status') == 'completed':
            backup = Backup(
                user_id=user.id,
                filename=backup_info['filename'],
                size_bytes=backup_info['size_bytes'],
                checksum=backup_info['checksum'],
                backup_type='manual',
                status='completed'
            )
            db.session.add(backup)
            db.session.commit()
            
            logger_api.info(f"Бэкап создан вручную для пользователя {user.id}")
            return jsonify(backup.to_dict()), 201
        else:
            return jsonify({"error": backup_info.get('error')}), 500
    except Exception as e:
        logger_api.error(f"Ошибка создания бэкапа: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/backup/list', methods=['GET'])
@token_required
def list_backups(user):
    """Список резервных копий."""
    try:
        backups = Backup.query.filter_by(user_id=user.id).order_by(Backup.created_at.desc()).all()
        return jsonify([b.to_dict() for b in backups]), 200
    except Exception as e:
        logger_api.error(f"Ошибка получения списка бэкапов: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/backup/restore/<int:backup_id>', methods=['POST'])
@token_required
@limiter.limit("3 per day")
def restore_backup(user, backup_id):
    """Восстановление из резервной копии."""
    try:
        backup = Backup.query.filter_by(id=backup_id, user_id=user.id).first()
        if not backup:
            return jsonify({"error": "Бэкап не найден"}), 404
        
        success = backup_mgr.restore_backup(backup.filename)
        if success:
            logger_api.info(f"Бэкап восстановлен для пользователя {user.id}")
            return jsonify({"message": "Восстановление успешно"}), 200
        else:
            return jsonify({"error": "Ошибка восстановления"}), 500
    except Exception as e:
        logger_api.error(f"Ошибка восстановления бэкапа: {e}")
        return jsonify({"error": str(e)}), 500


# === Schedules endpoints ===
@app.route('/api/schedules', methods=['GET'])
@token_required
def get_schedules(user):
    """Получить расписания."""
    try:
        schedules = Schedule.query.filter_by(user_id=user.id).all()
        return jsonify([s.to_dict() for s in schedules]), 200
    except Exception as e:
        logger_api.error(f"Ошибка получения расписаний: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/schedules', methods=['POST'])
@token_required
def create_schedule(user):
    """Создать расписание."""
    try:
        data = request.get_json()
        schedule = Schedule(
            user_id=user.id,
            name=data.get('name'),
            action=data.get('action'),
            schedule_type=data.get('schedule_type', 'interval'),
            interval_minutes=data.get('interval_minutes', 30),
            is_active=data.get('is_active', True)
        )
        db.session.add(schedule)
        db.session.commit()
        
        logger_api.info(f"Расписание создано: {schedule.name}")
        return jsonify(schedule.to_dict()), 201
    except Exception as e:
        logger_api.error(f"Ошибка создания расписания: {e}")
        return jsonify({"error": str(e)}), 500


# === Health check ===
@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()}), 200


# === Error handlers ===
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint не найден"}), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Ошибка сервера"}), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
