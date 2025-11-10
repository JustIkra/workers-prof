# AI-03 — Генерация рекомендаций (COMPLETED)

## Цель
Промпт по схеме, self-heal JSON при невалидной отдаче.

## Описание
Сборка промпта и системных инструкций для получения структурированных рекомендаций на русском языке по жёсткой JSON-схеме. Повторный запрос/исправление при невалидном JSON (self-heal) с ограничением длины списков.

## Реализация

### Созданные компоненты

1. **Pydantic схемы** (`app/schemas/recommendations.py`):
   - `StrengthItem` - элемент списка сильных сторон
   - `DevelopmentAreaItem` - элемент области развития
   - `RecommendationItem` - элемент рекомендации (ресурс обучения)
   - `RecommendationsResponse` - полный ответ от Gemini API
   - `RecommendationsInput` - входные данные для генерации
   - Валидация: ≤5 элементов на секцию, max длины строк (80/200/500 символов)

2. **Сервис генерации** (`app/services/recommendations.py`):
   - `RecommendationsGenerator` - класс для генерации рекомендаций
   - Промпт по схеме из `.memory-base/Tech details/infrastructure/prompt-gemini-recommendations.md`
   - Self-heal логика: до 2 попыток при невалидном JSON
   - Автоматическая обрезка списков если Gemini вернул >5 элементов
   - Функция `generate_recommendations()` для convenience использования

3. **Интеграция в ScoringService** (`app/services/scoring.py`):
   - Добавлен опциональный параметр `gemini_client` в `__init__`
   - После вычисления score и strengths/dev_areas вызывается генерация рекомендаций
   - Рекомендации сохраняются в `scoring_result.recommendations` (JSONB)
   - Graceful degradation: если генерация рекомендаций fails, scoring продолжает работать

4. **Роутер** (`app/routers/scoring.py`):
   - Добавлена зависимость `gemini_client` через DI
   - Обновлена схема `ScoringResponse` для включения recommendations
   - Recommendations передаются в ответе API

5. **Тесты** (`tests/test_recommendations.py`):
   - Unit тесты для Pydantic схем (валидация, max_length, field_validator)
   - Тесты для RecommendationsGenerator:
     - Базовая генерация с mock transport
     - Обрезка списков >5 элементов
     - Self-heal при невалидном JSON (retry с исправленным промптом)
     - Failure после max_attempts
     - Convenience функция `generate_recommendations()`
   - Все тесты используют MockTransport для изоляции от сети
   - 12/12 тестов прошли успешно ✅

## Acceptance Criteria

✅ Валидный JSON ≤5 элементов/секцию
✅ Self-heal при невалидном JSON (до 2 попыток)
✅ Корректная локаль RU (все тексты на русском)
✅ Строгая валидация схемы (Pydantic)
✅ Обрезка длины списков и строк
✅ Graceful degradation (scoring работает даже если recommendations failed)
✅ Unit тесты покрывают все основные сценарии
✅ Интеграция с ScoringService через DI
✅ Существующие тесты не сломаны (test_scoring.py: 15/15 ✅)

## Зависимости

- ✅ AI-02 (пул ключей/rate limiting) - используется через `get_gemini_client()`
- ✅ S2-02 (scoring) - интегрировано в `ScoringService.calculate_score()`

## Конфигурация

```bash
# .env
AI_RECOMMENDATIONS_ENABLED=1          # Включить генерацию рекомендаций
GEMINI_API_KEYS="key1,key2"          # CSV список ключей
GEMINI_MODEL_TEXT="gemini-2.5-flash" # Модель для text generation
```

## Использование

### Автоматическая генерация при расчёте score

```python
# POST /api/scoring/participants/{id}/calculate?activity_code=SALES
# Response includes:
{
  "score_pct": 78.4,
  "strengths": [...],
  "dev_areas": [...],
  "recommendations": [  # <-- AI-generated
    {
      "title": "Курс по коммуникации",
      "link_url": "https://example.com/course",
      "priority": 1
    }
  ]
}
```

### Программное использование

```python
from app.core.gemini_factory import create_gemini_client
from app.services.recommendations import generate_recommendations

client = create_gemini_client()

recommendations = await generate_recommendations(
    gemini_client=client,
    metrics=[
        {"code": "COMMUNICATION_CLARITY", "name": "Ясность речи",
         "unit": "балл", "value": 8.5, "weight": 0.15}
    ],
    score_pct=78.4,
    prof_activity_code="SALES",
    prof_activity_name="Продажи",
    weight_table_version=1,
)

# Returns: {"strengths": [...], "dev_areas": [...], "recommendations": [...]}
```

## Архитектура

```
┌─────────────────────────────────────────────┐
│         FastAPI Route                       │
│    POST /scoring/participants/{id}/calc     │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│          ScoringService                     │
│  - calculate_score()                        │
│  - Generate strengths/dev_areas             │
│  - Call generate_recommendations()          │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│      RecommendationsGenerator               │
│  - _build_prompt() (structured)             │
│  - generate() with self-heal                │
│  - _truncate_response() (≤5 items)          │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│     GeminiPoolClient (AI-02)                │
│  - generate_text()                          │
│  - Key rotation, rate limiting              │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│          Gemini API                         │
│  gemini-2.5-flash (text model)              │
└─────────────────────────────────────────────┘
```

## Промпт-инжиниринг

Промпт строится по схеме из `.memory-base/Tech details/infrastructure/prompt-gemini-recommendations.md`:

1. **System instructions**: эксперт по компетенциям, русский язык, краткость
2. **User prompt**: контекст (activity, version), metrics с весами, score_pct
3. **JSON schema**: жёсткая структура с constraints (≤5 items, max_length)
4. **Self-heal prompt**: при невалидном JSON - повторный запрос с объяснением ошибки

## Offline режим (test/ci)

В test/ci окружениях (`ENV=test|ci`):
- Gemini API calls автоматически блокируются через `OfflineTransport`
- `generate_recommendations()` проверяет `settings.ai_recommendations_enabled`
- Тесты используют `MockTransport` для изоляции

## Следующие шаги

AI-03 полностью завершён. Рекомендации генерируются и сохраняются в БД.

Оставшиеся задачи из backlog:
- FR-UI-01/02: Отображение рекомендаций в UI финального отчёта
- FR-BE-01: История оценок участника (уже реализовано в S2-06)
- AI-REC-01: Дополнительная обработка рекомендаций (optional)

## Результат

✅ **AI-03 завершён**
✅ **Все тесты прошли** (12/12 recommendations + 15/15 scoring)
✅ **Интеграция работает** (recommendations появляются в scoring API response)
✅ **Self-heal реализован** (до 2 попыток при невалидном JSON)
✅ **Graceful degradation** (scoring работает даже если AI fails)

Готово к использованию в production при наличии валидных `GEMINI_API_KEYS`.
