"""Scheduler — APScheduler для автоматизации и расписаний."""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from models import db, User, Schedule, Backup
from backup_manager import BackupManager
from config import config

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Управление автоматизированными задачами."""
    
    def __init__(self, app=None):
        self.app = app
        self.scheduler = BackgroundScheduler()
        self.backup_mgr = BackupManager()
        
    def init_app(self, app):
        """Инициализация со своим Flask приложением."""
        self.app = app
        
    def start(self):
        """Запуск планировщика."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Планировщик задач запущен")
            self._schedule_system_tasks()
    
    def stop(self):
        """Остановка планировщика."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Планировщик задач остановлен")
    
    def _schedule_system_tasks(self):
        """Планирование системных задач."""
        # Периодическая очистка старых бэкапов
        self.scheduler.add_job(
            func=self._cleanup_backups,
            trigger=IntervalTrigger(hours=1),
            id='cleanup_backups',
            name='Очистка старых бэкапов',
            replace_existing=True
        )
        
        # Периодическое обновление статистики
        self.scheduler.add_job(
            func=self._update_statistics,
            trigger=IntervalTrigger(hours=1),
            id='update_statistics',
            name='Обновление статистики',
            replace_existing=True
        )
        
        logger.info("Системные задачи спланированы")
    
    def schedule_user_tasks(self, app_context=None):
        """Планирование пользовательских задач из БД."""
        try:
            ctx = app_context or self.app.app_context()
            with ctx:
                schedules = Schedule.query.filter_by(is_active=True).all()
                
                for schedule in schedules:
                    job_id = f"user_{schedule.user_id}_job_{schedule.id}"
                    
                    # Пропускаем если уже спланирована
                    if self.scheduler.get_job(job_id):
                        continue
                    
                    # Создаём триггер в зависимости от типа
                    if schedule.schedule_type == 'interval':
                        trigger = IntervalTrigger(minutes=schedule.interval_minutes)
                    elif schedule.schedule_type == 'cron':
                        trigger = CronTrigger.from_crontab(schedule.cron_expression)
                    else:
                        continue
                    
                    # Добавляем работу
                    self.scheduler.add_job(
                        func=self._execute_user_task,
                        trigger=trigger,
                        args=[schedule.user_id, schedule.action, schedule.config],
                        id=job_id,
                        name=f"User {schedule.user_id}: {schedule.name}",
                        replace_existing=True
                    )
                    
                    logger.info(f"Задача спланирована: {job_id}")
        except Exception as e:
            logger.error(f"Ошибка планирования пользовательских задач: {e}")
    
    def _execute_user_task(self, user_id: int, action: str, config: dict):
        """Выполнение пользовательской задачи."""
        try:
            logger.info(f"Выполнение задачи для пользователя {user_id}: {action}")
            
            with self.app.app_context():
                if action == 'backup':
                    backup_info = self.backup_mgr.create_backup(user_id, "auto")
                    if backup_info.get('status') == 'completed':
                        backup = Backup(
                            user_id=user_id,
                            filename=backup_info['filename'],
                            size_bytes=backup_info['size_bytes'],
                            checksum=backup_info['checksum'],
                            backup_type='auto',
                            status='completed'
                        )
                        db.session.add(backup)
                        db.session.commit()
                        logger.info(f"Автоматический бэкап создан для {user_id}")
                
                elif action == 'check_orders':
                    logger.info(f"Проверка заказов для {user_id}")
                    # Здесь будет логика проверки заказов через API FunPay
                
                elif action == 'check_notifications':
                    logger.info(f"Проверка уведомлений для {user_id}")
                    # Здесь будет логика проверки уведомлений через API FunPay
        
        except Exception as e:
            logger.error(f"Ошибка выполнения задачи для {user_id}: {e}")
    
    def _cleanup_backups(self):
        """Очистка старых резервных копий."""
        try:
            retention_days = int(config.BACKUP_RETENTION_DAYS or 30)
            self.backup_mgr.cleanup_old_backups(retention_days)
            logger.info("Очистка старых бэкапов завершена")
        except Exception as e:
            logger.error(f"Ошибка очистки бэкапов: {e}")
    
    def _update_statistics(self):
        """Обновление статистики."""
        try:
            from models import Statistics, Order
            from datetime import date
            
            with self.app.app_context():
                users = User.query.filter_by(is_active=True).all()
                today = date.today()
                
                for user in users:
                    # Проверяем наличие записи за сегодня
                    stat = Statistics.query.filter_by(user_id=user.id, date=today).first()
                    if stat:
                        continue
                    
                    # Вычисляем статистику
                    orders = Order.query.filter_by(user_id=user.id, status='completed').all()
                    total_revenue = sum(o.amount for o in orders)
                    avg_order_value = total_revenue / len(orders) if orders else 0
                    
                    stat = Statistics(
                        user_id=user.id,
                        date=today,
                        total_orders=len(orders),
                        completed_orders=len([o for o in orders if o.status == 'completed']),
                        total_revenue=total_revenue,
                        avg_order_value=avg_order_value
                    )
                    db.session.add(stat)
                
                db.session.commit()
                logger.info("Статистика обновлена")
        except Exception as e:
            logger.error(f"Ошибка обновления статистики: {e}")


# Глобальный экземпляр
scheduler = TaskScheduler()
