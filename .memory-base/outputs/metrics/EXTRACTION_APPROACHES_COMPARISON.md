# Сравнение подходов к автоматическому извлечению метрик

## Обзор

Создано **3 подхода** для автоматического извлечения метрик из DOCX-отчётов:

1. **Вариант 1: Гибридный OCR + Gemini** (`extract_hybrid_ocr.py`) ⭐ РЕКОМЕНДУЕТСЯ
2. **Вариант 2: Улучшенный промпт Gemini** (`extract_improved_prompt.py`)
3. **Baseline: Оригинальный подход с консенсусом** (`extract_batura_metrics.py`) ❌ НЕ РЕКОМЕНДУЕТСЯ

Дополнительно создан **CLI инструмент для валидации** (`validate_metrics.py`) для ручной проверки и исправления результатов.

---

## Вариант 1: Гибридный OCR + Gemini ⭐

### Стратегия
```
DOCX → Изображения → Tesseract OCR → Текст → Gemini → JSON → Пост-обработка
```

### Преимущества ✅
- **Детерминистичность**: OCR всегда выдаёт одинаковый текст для одного изображения
- **Скорость**: OCR быстрее Vision API
- **Надёжность**: Gemini только структурирует текст (проще задача → меньше ошибок)
- **Меньше API вызовов**: 1 запрос на изображение (вместо 3)
- **Лучше для кириллицы**: Tesseract хорошо распознаёт русский текст
- **Fallback**: Если Gemini не смог распарсить, есть regex-фоллбэк

### Недостатки ❌
- **Зависимость от Tesseract**: требует установки `tesseract-ocr` и `pytesseract`
- **Качество OCR**: зависит от качества изображения (размытие, низкое разрешение)
- **Дополнительная библиотека**: нужна установка Tesseract на сервере

### Установка зависимостей

```bash
# macOS
brew install tesseract tesseract-lang

# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-rus

# Python пакет
pip install pytesseract
```

### Использование

```bash
cd api-gateway

# Запуск извлечения
python -m app.cli.extract_hybrid_ocr

# Результаты:
# - .memory-base/outputs/metrics/batura_hybrid_metric_names.json
# - .memory-base/outputs/metrics/batura_hybrid_metric_names.csv
# - .memory-base/outputs/metrics/batura_hybrid_extraction_results.json
# - tmp_images/*_hybrid_processed.png (обработанные изображения)
# - tmp_images/*_ocr.txt (извлечённый OCR текст для отладки)
```

### Ожидаемое время
- ~2-3 минуты (3 DOCX, 18 изображений)
- OCR: ~0.5-1 сек на изображение
- Gemini: ~1-2 сек на изображение

### Пример вывода

```
=== Unique Metric Names (Hybrid OCR + Gemini) ===
  1. АНАЛИЗ И ПЛАНИРОВАНИЕ
  2. ВЕРБАЛЬНАЯ ЛОГИКА
  3. ВНИМАНИЕ К ДЕТАЛЯМ
  ...
 56. ЭРУДИЦИЯ
```

---

## Вариант 2: Улучшенный промпт Gemini

### Стратегия
```
DOCX → Изображения → Gemini Vision (улучшенный промпт) → JSON → Пост-обработка
```

### Преимущества ✅
- **Нет внешних зависимостей**: только Gemini API
- **Простота развёртывания**: не нужен Tesseract
- **Улучшенный промпт**:
  - Явные примеры ожидаемого вывода
  - Детальное описание формата данных
  - Правила фильтрации служебных слов
- **Retry logic**: exponential backoff при 503 ошибках
- **Автосравнение**: сравнивает результат с ручным извлечением

### Недостатки ❌
- **Недетерминистичность**: Gemini Vision может выдавать разные результаты
- **API нестабильность**: 503 ошибки при высокой нагрузке
- **Стоимость**: больше токенов на Vision (изображение + длинный промпт)

### Использование

```bash
cd api-gateway

# Запуск извлечения
python -m app.cli.extract_improved_prompt

# Результаты:
# - .memory-base/outputs/metrics/batura_improved_metric_names.json
# - .memory-base/outputs/metrics/batura_improved_metric_names.csv
# - .memory-base/outputs/metrics/batura_improved_metrics_with_values.csv
# - .memory-base/outputs/metrics/batura_improved_extraction_results.json
# - tmp_images/*_improved_processed.png (обработанные изображения)
```

### Ожидаемое время
- ~3-5 минут (3 DOCX, 18 изображений)
- Gemini Vision: ~2-10 сек на изображение (зависит от API)

### Пример вывода с автосравнением

```
=== Unique Metric Names (Improved Prompt) ===
  1. АНАЛИЗ И ПЛАНИРОВАНИЕ
  ...
 52. ЭРУДИЦИЯ

=== Comparison with Manual Extraction ===
Manual: 58 labels
Auto:   52 labels
Match:  48 labels

Missing from auto extraction (10):
  - ВКЛЮЧЕННОСТЬ В КОМАНДУ
  - ВЫЧИСЛЕНИЯ
  ...

Extra in auto extraction (4):
  + АКТИВНОСТЬ (дубликат с другим регистром)
  ...
```

---

## Вариант 3: Baseline (Консенсус) ❌

### Стратегия (НЕ РЕКОМЕНДУЕТСЯ)
```
DOCX → Изображения → 3x Gemini Vision → Консенсус → JSON
```

### Проблемы ❌
- **Неэффективность**: 3x запросы на одно изображение
- **Низкая точность**: строгие правила консенсуса → много false negatives
- **Долгое выполнение**: ~10-15 минут
- **Высокая стоимость API**: 3x токенов
- **503 ошибки**: 40% запросов падают из-за rate limits

### Результаты тестирования
- Извлечено: 1 метрика из 58 (2% покрытие)
- Время: ~11 минут
- API ошибки: 40% запросов

**Вывод:** Подход неэффективен, не рекомендуется к использованию.

---

## CLI Инструмент для валидации

### Назначение
Интерактивная валидация и исправление автоматически извлечённых метрик.

### Возможности
- ✅ Просмотр каждой метрики с контекстом (изображение, source)
- ✅ Принятие (ENTER) или исправление (ввод нового значения)
- ✅ Пропуск метрик (skip)
- ✅ Сохранение прогресса (quit в любой момент)
- ✅ Экспорт валидированных данных в JSON/CSV
- ✅ Лог исправлений для анализа

### Использование

```bash
cd api-gateway

# Валидация гибридных результатов
python -m app.cli.validate_metrics --input batura_hybrid_extraction_results.json

# Валидация улучшенного промпта
python -m app.cli.validate_metrics --input batura_improved_extraction_results.json

# Валидация оригинальных результатов
python -m app.cli.validate_metrics --input batura_extraction_results.json
```

### Пример сессии

```
================================================================================
METRIC VALIDATION TOOL
================================================================================

Instructions:
  - Review each extracted metric
  - Press ENTER to accept
  - Type new value to correct
  - Type 'skip' to skip this metric
  - Type 'quit' to exit and save

================================================================================
Document: Batura_A.A._Biznes-Profil_Biznes-otchyot_1718107.docx
================================================================================

[1/44] Metric from image3.png
Label:      РАБОТА С ДОКУМЕНТАМИ
Value:      6.4
Confidence: 1.00
Image:      Batura_A.A._Biznes-Profil_Biznes-otchyot_1718107_image3_hybrid_processed.png
            800x600 px, PNG

Action [ENTER=accept, VALUE=correct, skip, quit]:
  ✓ Accepted

[2/44] Metric from image3.png
Label:      ПРОДВИЖЕНИЕ
Value:      7.6
Confidence: 1.00
Image:      Batura_A.A._Biznes-Profil_Biznes-otchyot_1718107_image3_hybrid_processed.png
            800x600 px, PNG

Action [ENTER=accept, VALUE=correct, skip, quit]: 7.5
  ✓ Corrected: 7.6 → 7.5

...

================================================================================
VALIDATION COMPLETE
================================================================================

Validation summary:
  Total metrics validated: 44
  Accepted as-is:          42
  Corrected:               2

Saved validated metrics to .../batura_validated_metrics.json
Saved corrections log to .../batura_corrections_log.json
Saved validated metrics to .../batura_validated_metrics.csv
```

### Выходные файлы

- `batura_validated_metrics.json` - валидированные метрики
- `batura_corrections_log.json` - лог всех исправлений
- `batura_validated_metrics.csv` - CSV для удобного просмотра

---

## Сравнительная таблица

| Критерий | Гибридный OCR ⭐ | Улучшенный промпт | Baseline консенсус |
|----------|------------------|-------------------|--------------------|
| **Точность (ожидаемая)** | 85-95% | 70-85% | 2% (тест) |
| **Скорость** | ~2-3 мин | ~3-5 мин | ~10-15 мин |
| **API запросов** | 18 (1 на изображение) | 18 (1 на изображение) | 54 (3 на изображение) |
| **Детерминистичность** | ✅ Высокая (OCR) | ❌ Низкая (Vision) | ❌ Низкая (Vision) |
| **Внешние зависимости** | Tesseract | Нет | Нет |
| **Стоимость API** | Средняя | Средняя | Высокая (3x) |
| **Обработка ошибок** | ✅ Fallback regex | ✅ Exponential backoff | ⚠️ Retry (недостаточно) |
| **Отладка** | ✅ OCR txt файлы | ⚠️ Только логи | ⚠️ Только логи |
| **Рекомендация** | ⭐ **РЕКОМЕНДУЕТСЯ** | ✅ Альтернатива | ❌ НЕ ИСПОЛЬЗОВАТЬ |

---

## Рекомендации по использованию

### Для Production

**1. Основной подход: Гибридный OCR + Gemini**
```bash
python -m app.cli.extract_hybrid_ocr
```

**2. Валидация результатов:**
```bash
python -m app.cli.validate_metrics --input batura_hybrid_extraction_results.json
```

**3. Экспорт валидированных данных:**
- Используйте `batura_validated_metrics.csv` как источник истины
- Анализируйте `batura_corrections_log.json` для улучшения промптов/OCR

### Для тестирования/сравнения

**Запустите оба подхода:**
```bash
# Гибридный
python -m app.cli.extract_hybrid_ocr

# Улучшенный промпт
python -m app.cli.extract_improved_prompt
```

**Сравните результаты:**
- Improved prompt автоматически показывает сравнение с `batura_manual_metrics.csv`
- Сравните `batura_hybrid_metric_names.csv` и `batura_improved_metric_names.csv`

### Для CI/CD

**Скрипт для автотестов:**
```bash
#!/bin/bash
set -e

# Извлечение метрик
python -m app.cli.extract_hybrid_ocr

# Сравнение с gold standard
EXPECTED=58
ACTUAL=$(wc -l < .memory-base/outputs/metrics/batura_hybrid_metric_names.csv)
ACTUAL=$((ACTUAL - 1))  # Subtract header

if [ $ACTUAL -lt 50 ]; then
  echo "ERROR: Expected ~$EXPECTED metrics, got $ACTUAL"
  exit 1
fi

echo "SUCCESS: Extracted $ACTUAL/$EXPECTED metrics"
```

---

## Улучшения в будущем

### Для гибридного подхода
1. **Улучшить OCR предобработку:**
   - Adaptive thresholding для различных типов изображений
   - Deskewing (выравнивание наклона)
   - Удаление шумов (denoise)

2. **Fine-tune Gemini промпт:**
   - Добавить больше примеров специфичных метрик
   - Указать явные правила для edge cases

3. **Кэширование OCR результатов:**
   - Сохранять OCR текст в БД
   - Переиспользовать при повторных запусках

### Для улучшенного промпта
1. **Few-shot learning:**
   - Передавать реальные примеры метрик в промпте
   - Использовать контекстное обучение

2. **Vision API оптимизация:**
   - Экспериментировать с разными моделями (Flash vs Pro)
   - A/B тестирование разных промптов

3. **Автоматическая валидация:**
   - Использовать confidence scores для фильтрации
   - Автофлаг метрик с низким confidence для ручной проверки

---

## FAQ

### Q: Какой подход использовать для новых отчётов?
**A:** Используйте **Гибридный OCR + Gemini** (`extract_hybrid_ocr.py`). Он даёт лучшее соотношение точность/скорость/стоимость.

### Q: Нужно ли валидировать каждый раз?
**A:** Рекомендуется валидировать первые 10-20 отчётов для каждого нового формата/источника. После этого можно полагаться на автоматическое извлечение с выборочной проверкой.

### Q: Что делать, если Tesseract выдаёт плохие результаты?
**A:**
1. Проверьте качество изображения (разрешение, контраст)
2. Попробуйте улучшить предобработку (контраст, размер)
3. Используйте fallback на **Улучшенный промпт** (`extract_improved_prompt.py`)

### Q: Можно ли комбинировать оба подхода?
**A:** Да! Можно запустить оба и использовать консенсус между ними:
```python
# Pseudo-code
hybrid_results = extract_hybrid_ocr()
improved_results = extract_improved_prompt()

# Если оба подхода согласны - высокая уверенность
# Если расходятся - отправить на ручную валидацию
```

### Q: Как измерить качество извлечения?
**A:** Сравните с gold standard (`batura_manual_metrics.csv`):
```bash
# Скрипт сравнения
python -m app.cli.compare_extractions \
  --gold .memory-base/outputs/metrics/batura_manual_metrics.csv \
  --test .memory-base/outputs/metrics/batura_hybrid_metric_names.csv
```

---

## Контакты и поддержка

- **Документация**: `.memory-base/outputs/metrics/`
- **Логи**: `tmp_images/*_ocr.txt`, `tmp_images/*_processed.png`
- **Issues**: создайте тикет с примерами неправильного извлечения

---

## Changelog

- **2025-11-10**: Создание документа, реализация 3 подходов + CLI валидатор
