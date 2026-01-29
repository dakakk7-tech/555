# FunPay Manager — Professional Solution

Профессиональное приложение для управления FunPay с web API, резервными копиями, автоматизацией и аналитикой.

## Основные возможности

✅ **REST API** — полнофункциональный Flask API с rate limiting и аутентификацией  
✅ **База данных** — SQLAlchemy ORM с миграциями (SQLite/PostgreSQL)  
✅ **Автоматические резервные копии** — zip архивы с проверкой целостности (SHA256)  
✅ **Планировщик задач** — APScheduler для автоматизации (interval, cron)  
✅ **Аналитика** — статистика, графики, отчёты  
✅ **Система уведомлений** — логирование всех операций  
✅ **Rate limiting** — защита от abuse  
✅ **Docker** — готовые контейнеры для deployment  

## Архитектура

```
FunPay_Manager/
├── app.py                    # Flask REST API (endpoints)
├── models.py                 # SQLAlchemy ORM (User, Order, Backup, Stats и т.д.)
├── config.py                 # Конфигурация (development, production, testing)
├── scheduler.py              # APScheduler — автоматизация и расписания
├── backup_manager.py         # Система резервного копирования с checksum
├── requirements.txt          # Зависимости
├── pyproject.toml            # Конфигурация пакета
├── .env.example              # Пример переменных окружения
├── .gitignore                # Git ignore
├── README.md                 # Этот файл
├── Dockerfile                # Docker контейнеризация
├── docker-compose.yml        # Docker Compose для local dev
├── data/                     # БД и данные
├── backups/                  # Резервные копии
└── logs/                     # Логи приложения
```

## Быстрый старт

### 1. Установка зависимостей
```bash
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate    # Linux/Mac

pip install -r requirements.txt
```

### 2. Настройка .env
```bash
cp .env.example .env
# Отредактируйте .env: SECRET_KEY, DATABASE_URL и т.д.
```

### 3. Инициализация БД
```bash
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### 4. Запуск сервера
```bash
python app.py
# или через Gunicorn для production:
gunicorn app:app --bind 0.0.0.0:5000
```

Сервер доступен на `http://localhost:5000`

## API Endpoints

### Аутентификация
- `POST /api/auth/register` — регистрация нового пользователя
- `POST /api/auth/verify` — проверка токена (требует `Authorization: Bearer <token>`)

### Заказы
- `GET /api/orders?status=pending&limit=50` — список заказов
- `POST /api/orders` — добавить новый заказ

### Уведомления
- `GET /api/notifications?is_read=false` — список уведомлений
- `GET /api/notifications/<id>/mark-read` — отметить как прочитанное

### Статистика
- `GET /api/statistics?days=7` — аналитика за период

### Резервные копии
- `POST /api/backup/create` — создать бэкап вручную
- `GET /api/backup/list` — список всех бэкапов
- `POST /api/backup/restore/<id>` — восстановить из бэкапа

### Расписания
- `GET /api/schedules` — список расписаний
- `POST /api/schedules` — создать новое расписание
- `PUT /api/schedules/<id>` — изменить расписание
- `DELETE /api/schedules/<id>` — удалить расписание

### Здоровье
- `GET /api/health` — проверка статуса приложения

## Пример использования (cURL)

```bash
# Регистрация
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "myuser",
    "email": "user@example.com",
    "api_token": "my-funpay-api-token"
  }'

# Получить заказы (требуется token)
curl -X GET http://localhost:5000/api/orders \
  -H "Authorization: Bearer my-funpay-api-token"

# Создать бэкап
curl -X POST http://localhost:5000/api/backup/create \
  -H "Authorization: Bearer my-funpay-api-token"
```

## Docker

### Запуск через Docker Compose
```bash
docker-compose up -d
```

### Запуск отдельного контейнера
```bash
docker build -t funpay-manager .
docker run -p 5000:5000 -v $(pwd)/data:/app/data funpay-manager
```

## Автоматизация и расписания

Система поддерживает два типа планирования:

### Interval (каждые N минут)
```json
{
  "name": "Check orders every 30 minutes",
  "action": "check_orders",
  "schedule_type": "interval",
  "interval_minutes": 30
}
```

### Cron (по расписанию)
```json
{
  "name": "Daily backup at midnight",
  "action": "backup",
  "schedule_type": "cron",
  "cron_expression": "0 0 * * *"
}
```

## Резервные копии

### Автоматические бэкапы
- Создаются автоматически каждые 6 часов (настраивается)
- Хранятся с метаданными и checksum
- Старые бэкапы удаляются после 30 дней (настраивается)

### Восстановление
```bash
curl -X POST http://localhost:5000/api/backup/restore/1 \
  -H "Authorization: Bearer token"
```

## Логирование

Логи сохраняются в `logs/app.log` и выводятся в консоль.

Уровень логирования настраивается через `LOG_LEVEL` в `.env`:
- DEBUG
- INFO
- WARNING
- ERROR
- CRITICAL

## Статистика и аналитика

Система автоматически собирает статистику:
- Количество заказов в день
- Количество выполненных заказов
- Общую выручку
- Среднюю стоимость заказа

Данные доступны через `GET /api/statistics`

## Безопасность

- ✅ API токен-based аутентификация
- ✅ Rate limiting (5 req/min для регистрации, 30 req/min для остального)
- ✅ CORS поддержка
- ✅ Валидация входных данных
- ✅ SQL injection protection (через SQLAlchemy ORM)
- ✅ Checksum для бэкапов

## Production deployment

1. Установите переменные окружения:
   ```bash
   APP_ENV=production
   SECRET_KEY=<длинный-безопасный-ключ>
   ```

2. Используйте PostgreSQL вместо SQLite:
   ```
   DATABASE_URL=postgresql://user:pass@localhost/funpay_db
   ```

3. Запустите через Gunicorn с Nginx reverse proxy

4. Включите HTTPS через Let's Encrypt

## Тестирование

```bash
pytest tests/
```

## Поддерживаемые форматы

- JSON для API
- SQLite/PostgreSQL для БД
- ZIP для резервных копий
- CSV для экспорта статистики

## Рекомендации

- Регулярно проверяйте резервные копии
- Мониторьте логи для ошибок
- Обновляйте SECRET_KEY в production
- Используйте PostgreSQL для масштабирования
- Включите HTTPS

## Лицензия

MIT

## Автор

FunPay Manager Team — 2026

---

**Готово к production!** 🚀
