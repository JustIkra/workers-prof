# Код: AI-06 — DOCX: извлечение метрик (Batura A.A., 3 файла)

## Цель
- Извлечь ВСЕ числовые метрики (1..10) из трёх DOCX и собрать набор наименований метрик (заголовков строк/подписей), следуя пайплайну `.memory-base/Tech details/infrastructure/extraction-pipeline.md`.
- Подготовить входные данные для шаблона проф. областей (следующая задача AI-07).

## Входные файлы (.docx)
- `/Users/maksim/git_projects/workers-prof/.memory-base/Product Overview/User story/Batura_A.A._Biznes-Profil_Biznes-otchyot_1718107.docx`
- `/Users/maksim/git_projects/workers-prof/.memory-base/Product Overview/User story/Batura_A.A._Biznes-Profil_Otchyot_dlya_respondenta_1718107.docx`
- `/Users/maksim/git_projects/workers-prof/.memory-base/Product Overview/User story/Batura_A.A._Biznes-Profil_Otchyot_po_kompetentsiyam_1718107.docx`

## Описание
- Использовать существующий экстрактор изображений из DOCX (`app/services/docx_extraction.py`) для получения `word/media/*`.
- Для изображений с таблицами/барчартами:
  - Обрезать до ROI строк (отбросить нижние ~15% с осью Х), минимизировать PII.
  - Отправлять в Gemini Vision с обновлённым строгим JSON‑промптом (см. AI-08) и принимать ТОЛЬКО значения, соответствующие `^(?:10|[1-9])([,.][0-9])?$` и диапазону 1..10.
  - Идентифицировать наименования метрик (левые заголовки строк у барчартов/первая колонка у таблиц). Если OCR/LLM даёт неоднозначность — пометить на ручную валидацию (без молчаливых подстановок).
- Сформировать консолидированный список уникальных наименований метрик (RU), пригодный для последующего маппинга в `MetricDef.code`.

## Выходные артефакты
- `/.memory-base/outputs/metrics/batura_metric_names.json` — список уникальных наименований метрик (RU), отсортированный по алфавиту.
- `/.memory-base/outputs/metrics/batura_metric_names.csv` — тот же список в CSV (удобно для ручной валидации).
- Логи без ПДн; изображения/ROI — в `tmp_images/` (локально, не коммитить).

## Acceptance Criteria
- Из каждого из 3 DOCX извлечены все доступные числовые метрики; значения вне диапазона/с несоответствием шаблону отклонены.
- Сформирован и сохранён консолидированный список уникальных наименований метрик (RU) в JSON/CSV.
- Осевые подписи «1…10», «НИЗКАЯ/ВЫСОКАЯ», «ЗОНЫ ИНТЕРПРЕТАЦИИ», символы `++/+/−/--/%/±` не попадают в результат (строгая фильтрация).
- Любые неоднозначности вынесены в отдельный список для UI‑валидации (например, `batura_metric_names_ambiguous.json`).

## Подзадачи
1) Экстракция изображений: `DocxImageExtractor.extract_images()` → PNG в `tmp_images/`.
2) Предобработка: обрезка до ROI строк (отброс нижних 15%), нормализация ширины.
3) Вызов Vision: `VisionMetricExtractor.extract_metrics_from_image()` c обновлённым промптом (AI-08) и `responseMimeType=application/json`.
4) Извлечение наименований метрик (заголовков строк):
   - Левый ROI (рядом с баром) через OCR/LLM; удалить служебные надписи.
   - Нормализовать регистр/пробелы; аккуратно с кириллицей.
5) Консолидация и дедупликация списков из 3 документов; сортировка; экспорт JSON/CSV.
6) Список неоднозначностей для ручной валидации (если названия конфликтуют/не читаются).

## Очереди Celery (маршрутизация)
- `vision` — основной поток Gemini (извлечение чисел/наименований из ROI)
- `normalize` — нормализация/валидация/дедупликация списков, подготовка JSON/CSV

## Ссылки
- Пайплайн: `.memory-base/Tech details/infrastructure/extraction-pipeline.md`
- Маппинг: `.memory-base/Tech details/infrastructure/metric-mapping.md`
- Клиент Gemini: `api-gateway/app/clients/gemini.py`
- Vision сервис: `api-gateway/app/services/vision_extraction.py`
