# S1-08: Prof activities seed — COMPLETED ✅

**Дата завершения:** 2025-11-05

## Реализованная функциональность

### 1. Идемпотентный сидер профобластей
- ✅ Добавлен общий модуль `app/db/seeds/prof_activity.py` с детерминированным UUID и кодом `meeting_facilitation`
- ✅ Репозиторий `ProfActivityRepository.seed_defaults()` использует `INSERT ... ON CONFLICT` для обновления данных без дублей
- ✅ Сервис `ProfActivityService.seed_defaults()` переиспользуем в миграциях и тестовых фикстурах

### 2. Миграция Alembic
- ✅ Ревизия `3a015d9b6e41_seed_prof_activities.py` вставляет/обновляет стартовую запись в `prof_activity`
- ✅ Повторный запуск миграции не меняет состояние данных (идемпотентность)
- ✅ Downgrade удаляет только добавленные коды

### 3. Публичный API для профобластей
- ✅ Добавлен роутер `GET /api/prof-activities`
  - Требует аутентифицированного пользователя (ACTIVE)
  - Возвращает список справочника в детерминированном порядке
- ✅ Протянуты DTO `ProfActivityResponse` и подключение роутера в `main.py`

## Архитектура

```
api-gateway/
├── app/
│   ├── db/seeds/prof_activity.py         # Данные сидера
│   ├── repositories/prof_activity.py     # Идемпотентный upsert + list
│   ├── services/prof_activity.py         # Сервисный слой
│   ├── schemas/prof_activity.py          # Pydantic DTO
│   └── routers/prof_activities.py        # REST endpoint (GET /api/prof-activities)
├── alembic/versions/3a015d9b6e41_*.py    # Миграция с сидером
└── tests/test_prof_activities.py         # Покрытие сидера и эндпоинта
```

## Тестирование

Запуск: `cd api-gateway && pytest tests/test_prof_activities.py`

**Покрытые сценарии:**
- Двойной вызов сидера не создаёт дублей и сохраняет данные (`seed_defaults`)
- `GET /api/prof-activities` возвращает ожидаемый перечень
- Неавторизованный запрос получает `401`

Все 3 теста прошли (`3 passed`).

## Проверка AC
- [x] Список профобластей доступен через API
- [x] Инициализация идемпотентна и повторный сид не создаёт дублей
- [x] Миграция S1-04 — зависимость — используется (таблица `prof_activity` присутствует)

## Следующие шаги
- Подготовить сидеры весовых таблиц в рамках S1-09
- Документировать использование справочника в UI (в отдельной задаче фронтенда)
