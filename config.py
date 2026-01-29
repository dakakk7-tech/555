"""FunPay Manager — основной конфиг и инициализация приложения."""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

# Пути
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = BASE_DIR / "backups"
LOGS_DIR = BASE_DIR / "logs"

# Создаём директории
for dir_path in [DATA_DIR, BACKUP_DIR, LOGS_DIR]:
    dir_path.mkdir(exist_ok=True)

# Конфигурация логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Flask конфиг
class Config:
    """Базовая конфигурация."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATA_DIR / 'funpay.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    
    # API лимиты
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = "memory://"
    
    # Backup
    BACKUP_ENABLED = True
    BACKUP_INTERVAL_HOURS = 6
    BACKUP_RETENTION_DAYS = 30


class DevelopmentConfig(Config):
    """Конфиг для разработки."""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Конфиг для production."""
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    """Конфиг для тестирования."""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


# Выбор конфига
ENV = os.getenv('APP_ENV', 'development')
if ENV == 'production':
    config = ProductionConfig
elif ENV == 'testing':
    config = TestingConfig
else:
    config = DevelopmentConfig

logger.info(f"App started with config: {config.__name__}")
