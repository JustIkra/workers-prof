# S2-05 — Frontend: Метрики и расчёт — COMPLETED ✅

**Дата завершения:** 2025-11-07

## Реализованная функциональность

### 1. Утилиты форматирования чисел (ru-RU)
**Файл**: `frontend/src/utils/numberFormat.js`

Созданы утилиты для работы с числами в формате ru-RU (запятая как десятичный разделитель):

**Функции**:
- `formatNumber(value, decimals)` — форматирует число для отображения с запятой (7.5 → "7,5")
- `parseNumber(value)` — парсит строку с запятой в число ("7,5" → 7.5)
- `isValidNumber(value)` — валидирует строку как число
- `normalizeInput(value)` — нормализует ввод (заменяет точку на запятую)
- `formatForApi(value)` — конвертирует для отправки на API
- `formatFromApi(value, decimals)` — конвертирует из API для отображения

**Особенности**:
- Поддержка как точки, так и запятой при вводе
- Корректная обработка отрицательных чисел
- Настраиваемое количество знаков после запятой

### 2. Локализация Element Plus
**Файл**: `frontend/src/main.js` (уже был настроен)

Element Plus уже использовал русскую локализацию:
```javascript
import ru from 'element-plus/es/locale/lang/ru'
app.use(ElementPlus, { locale: ru })
```

### 3. Обновлённый MetricsEditor
**Файл**: `frontend/src/components/MetricsEditor.vue`

**Обновления**:
- Импорт и использование утилит форматирования `numberFormat.js`
- `parseNumber()` при загрузке метрик из API
- `formatForApi()` при сохранении метрик на сервер
- Улучшенная обработка ошибок с подробными сообщениями
- Счётчик сохранённых метрик в success message

**Функциональность**:
- Ручной ввод/редактирование метрик
- Валидация значений по диапазону (min_value, max_value)
- Массовое сохранение метрик через bulk API
- Отображение источника данных (OCR, LLM, MANUAL)
- Element Plus InputNumber с поддержкой ru-RU локали

### 4. Исправленный Scoring API
**Файл**: `frontend/src/api/scoring.js`

**Обновления**:
- ✅ Исправлен endpoint: `/scoring/participants/{id}/calculate` (был `/participants/{id}/score`)
- ✅ Исправлен query parameter: `activity_code` (был `activity`)
- ✅ Обновлён метод `getFinalReport()`:
  - Добавлен обязательный параметр `activityCode`
  - Исправлен endpoint: `/api/participants/{id}/final-report`
  - Правильная обработка параметров `activity_code` и `format`

### 5. Улучшенный ParticipantDetailView
**Файл**: `frontend/src/views/ParticipantDetailView.vue`

**Обновления отображения результатов**:

**Сильные стороны и зоны развития**:
- Отображение как объектов `MetricItem` (metric_name, value, weight)
- Форматирование значений с запятой через `formatFromApi()`
- Структура: `<strong>Название метрики</strong> — значение (вес)`
- Empty state если нет данных

**Диалог расчёта**:
- Валидация наличия отчётов перед расчётом
- Предупреждение если нет загруженных отчётов
- Блокировка кнопки "Рассчитать" если нет отчётов
- Улучшенное информационное сообщение

**Обработка результата расчёта**:
- Сохранение полного результата из API
- Добавление нового результата в историю (unshift)
- Парсинг score_pct как числа для прогресс-бара
- Вывод подробных ошибок из API

### 6. Валидация и обработка ошибок

**MetricsEditor**:
- Проверка наличия значений перед сохранением
- Валидация диапазона значений
- Подробные сообщения об ошибках от API
- Обработка разных форматов ошибок (string, array)

**ParticipantDetailView**:
- Проверка наличия отчётов перед расчётом
- Visual feedback (alert) если нет отчётов
- Консольный лог ошибок для отладки
- User-friendly сообщения об ошибках

## Проверка критериев приемки (AC)

- [x] **ru-RU локаль**: Числа отображаются с запятой (7,5 вместо 7.5)
- [x] **Валидация ввода**: Проверка диапазонов значений метрик
- [x] **Корректное преобразование запятая↔точка**: Утилиты `formatForApi()` / `formatFromApi()`
- [x] **Обработка ошибок API**: Подробные сообщения пользователю
- [x] **Ввод/редактирование метрик**: MetricsEditor с полной функциональностью
- [x] **Выбор профдеятельности**: Dropdown в диалоге расчёта
- [x] **Кнопка "Рассчитать"**: С валидацией наличия отчётов
- [x] **Отображение результатов**: strengths/dev_areas как объекты MetricItem
- [x] **Форматирование чисел**: Использование ru-RU формата повсюду

## Тестирование

### Backend тесты
**Результат**: ✅ **28 passed, 21 warnings in 22.49s**

Все тесты для метрик и scoring прошли успешно:
- `tests/test_metrics.py` — 18 tests ✅
- `tests/test_scoring.py` — 10 tests ✅

### Frontend build
**Результат**: ✅ **Built in 8.69s**

```
../api-gateway/static/assets/index-CQR9KiYx.js      1,037.48 kB │ gzip: 343.96 kB
✓ built in 8.69s
```

Frontend успешно собирается без ошибок.

## Архитектура изменений

```
frontend/
├── src/
│   ├── utils/
│   │   └── numberFormat.js               # NEW: Утилиты форматирования ru-RU
│   ├── components/
│   │   └── MetricsEditor.vue             # UPDATED: Использование numberFormat
│   ├── views/
│   │   └── ParticipantDetailView.vue     # UPDATED: Улучшенное отображение результатов
│   ├── api/
│   │   └── scoring.js                    # UPDATED: Исправлен endpoint
│   └── main.js                           # OK: Локализация уже настроена
```

## User Flow

### Сценарий: Ввод метрик → Расчёт → Результаты

1. **Открыть участника**: `/participants/{id}`
2. **Загрузить отчёт**: Кнопка "Загрузить отчёт" → выбрать DOCX
3. **Просмотреть метрики**: Кнопка "Метрики" на отчёте
4. **Ввести метрики вручную**:
   - Кнопка "Редактировать"
   - Ввод значений с запятой (например: 7,5)
   - Валидация по диапазону [1, 10]
   - Кнопка "Сохранить"
5. **Рассчитать пригодность**:
   - Кнопка "Рассчитать пригодность" (в header)
   - Выбрать профессиональную область
   - Кнопка "Рассчитать"
6. **Просмотреть результаты**:
   - Итоговый score в процентах
   - Прогресс-бар
   - Сильные стороны (top 5 метрик)
   - Зоны развития (bottom 5 метрик)
   - Рекомендации (если есть)

## Примеры

### Отображение метрики с запятой

**Input (ввод пользователя)**:
```
Коммуникабельность (балл): 7,5
```

**Отправка на API**:
```json
{
  "metric_def_id": "uuid...",
  "value": 7.5,
  "source": "MANUAL"
}
```

**Отображение в результатах**:
```
Сильные стороны:
• Коммуникабельность — 7,5 (вес 0,18)
```

### Пример результата расчёта

```json
{
  "scoring_result_id": "uuid...",
  "participant_id": "uuid...",
  "score_pct": "71.25",
  "strengths": [
    {
      "metric_code": "low_conflict",
      "metric_name": "Конфликтность (низкая)",
      "value": "9.5",
      "weight": "0.07"
    }
  ],
  "dev_areas": [
    {
      "metric_code": "leadership",
      "metric_name": "Лидерство",
      "value": "3.0",
      "weight": "0.12"
    }
  ]
}
```

## Зависимости

- ✅ S2-04 (Final report) — API endpoints используются
- ✅ S2-03 (Strengths/dev_areas) — Правильное отображение
- ✅ S2-02 (Scoring calculation) — Расчёт работает
- ✅ S2-01 (Metrics) — CRUD метрик реализован

## Следующие шаги

Задача S2-05 завершена и готова к использованию:
- **S3-01**: Парсинг DOCX и извлечение изображений
- **AI-01**: Gemini Vision для OCR fallback
- **S3-03**: Логирование и трейсинг для отладки

## Файлы созданы/изменены

**Новые файлы**:
- `frontend/src/utils/numberFormat.js` — утилиты форматирования

**Изменённые файлы**:
- `frontend/src/components/MetricsEditor.vue` — интеграция numberFormat
- `frontend/src/views/ParticipantDetailView.vue` — улучшенное отображение
- `frontend/src/api/scoring.js` — исправлен endpoint

## Технические детали

### Локализация чисел

**JavaScript Intl API** (используется в `numberFormat.js`):
```javascript
const num = 7.5
num.toLocaleString('ru-RU', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1
})
// Результат: "7,5"
```

**Element Plus InputNumber**:
- Автоматически использует locale из `app.use(ElementPlus, { locale: ru })`
- Поддерживает ввод с запятой
- Отображает значения с запятой

### API интеграция

**Scoring endpoint**:
```
POST /scoring/participants/{participant_id}/calculate?activity_code=meeting_facilitation
```

**Metrics bulk save**:
```
POST /api/reports/{report_id}/metrics/bulk
{
  "metrics": [
    { "metric_def_id": "...", "value": 7.5, "source": "MANUAL" }
  ]
}
```

## Примечания

- ru-RU локализация работает автоматически благодаря Element Plus
- Утилиты `numberFormat.js` обеспечивают единообразие форматирования
- Валидация происходит как на клиенте, так и на сервере
- Backend тесты подтверждают корректность API
- Frontend build проходит без ошибок

## Визуальный стиль

Соответствует требованиям `.memory-base/Conventions/Frontend/frontend-requirements.md`:
- ✅ Офисный стиль (Element Plus)
- ✅ Primary цвет: #00798D
- ✅ Системные шрифты: Segoe UI, Tahoma, Arial
- ✅ ru-RU локаль (запятая в числах)
- ✅ Доступность WCAG AA
- ✅ Responsive layout
