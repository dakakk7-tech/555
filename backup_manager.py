"""Backup система — автоматическое резервное копирование и восстановление."""

import os
import shutil
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from zipfile import ZipFile
from config import BACKUP_DIR, DATA_DIR, config

logger = logging.getLogger(__name__)


class BackupManager:
    """Управление резервными копиями."""
    
    def __init__(self):
        self.backup_dir = BACKUP_DIR
        self.data_dir = DATA_DIR
        self.backup_dir.mkdir(exist_ok=True)

    def create_backup(self, user_id: int, backup_type: str = "auto") -> dict:
        """Создание резервной копии."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{user_id}_{timestamp}.zip"
            backup_path = self.backup_dir / backup_name
            
            logger.info(f"Начало создания бэкапа: {backup_name}")
            
            # Создаём архив
            with ZipFile(backup_path, 'w') as zipf:
                # Добавляем файлы БД
                db_file = self.data_dir / "funpay.db"
                if db_file.exists():
                    zipf.write(db_file, arcname="funpay.db")
            
            # Вычисляем checksum
            checksum = self._calculate_checksum(backup_path)
            size_bytes = backup_path.stat().st_size
            
            logger.info(f"Бэкап создан: {backup_name} ({size_bytes} bytes)")
            
            return {
                "filename": backup_name,
                "path": str(backup_path),
                "size_bytes": size_bytes,
                "checksum": checksum,
                "status": "completed"
            }
        except Exception as e:
            logger.error(f"Ошибка создания бэкапа: {e}")
            return {"status": "failed", "error": str(e)}

    def restore_backup(self, backup_path: str) -> bool:
        """Восстановление из резервной копии."""
        try:
            backup_path = Path(backup_path)
            if not backup_path.exists():
                raise FileNotFoundError(f"Бэкап не найден: {backup_path}")
            
            # Создаём временную директорию
            temp_dir = self.backup_dir / f"temp_{datetime.now().timestamp()}"
            temp_dir.mkdir(exist_ok=True)
            
            logger.info(f"Начало восстановления из: {backup_path.name}")
            
            # Распаковываем архив
            with ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(temp_dir)
            
            # Восстанавливаем БД (с созданием backup текущей)
            db_file = self.data_dir / "funpay.db"
            if db_file.exists():
                backup_old = db_file.with_suffix('.db.old')
                shutil.copy(db_file, backup_old)
                logger.info(f"Текущая БД сохранена: {backup_old.name}")
            
            # Копируем восстановленные файлы
            for file_path in temp_dir.glob("*"):
                if file_path.is_file():
                    dest = self.data_dir / file_path.name
                    shutil.copy(file_path, dest)
            
            # Очищаем temp
            shutil.rmtree(temp_dir)
            
            logger.info(f"Восстановление успешно завершено")
            return True
        except Exception as e:
            logger.error(f"Ошибка восстановления: {e}")
            return False

    def cleanup_old_backups(self, retention_days: int = 30):
        """Удаление старых резервных копий."""
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            deleted_count = 0
            
            for backup_file in self.backup_dir.glob("backup_*.zip"):
                if backup_file.stat().st_mtime < cutoff_date.timestamp():
                    backup_file.unlink()
                    deleted_count += 1
                    logger.info(f"Удалён старый бэкап: {backup_file.name}")
            
            logger.info(f"Удалено {deleted_count} старых бэкапов")
        except Exception as e:
            logger.error(f"Ошибка очистки бэкапов: {e}")

    def list_backups(self, user_id: int = None) -> list:
        """Список всех резервных копий."""
        backups = []
        for backup_file in self.backup_dir.glob("backup_*.zip"):
            stat = backup_file.stat()
            backups.append({
                "filename": backup_file.name,
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "path": str(backup_file)
            })
        
        # Сортируем по времени (новые первыми)
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        return backups

    @staticmethod
    def _calculate_checksum(file_path: Path) -> str:
        """Вычисление SHA256 checksum файла."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
