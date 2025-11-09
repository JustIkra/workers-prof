Код: S2-04 — Итоговый отчёт (JSON + HTML) + интеграция UI

Статус: ✅ COMPLETED
- Backend готов: эндпоинт `GET /api/participants/{id}/final-report?activity_code=...&format=json|html` реализован; HTML шаблон рендерится; JSON соответствует схеме.
- Frontend интеграция выполнена: кнопки для просмотра JSON и скачивания HTML работают.
- Полное покрытие pytest-тестами: 11 тестов (7 базовых + 4 edge-case), все проходят успешно.
- Покрытие кода: 100% для report_template.py, 91.67% для scoring.py

Цель
- Дать пользователю возможность просматривать JSON и скачивать HTML из UI.

Шаги (Frontend)
1) Список отчётов: заменить заглушку на вызов `GET /api/participants/{id}/reports`
2) Добавить кнопки в таймлайн результатов: «Просмотреть JSON», «Скачать HTML»
3) Методы:
   - `viewFinalReportJSON(result)`: вызывает `scoringApi.getFinalReport(..., 'json')`, открывает JSON (в новой вкладке/диалоге)
   - `downloadFinalReportHTML(result)`: вызывает `scoringApi.getFinalReport(..., 'html')`, скачивает файл
4) Починить клиент: убрать двойной `/api` в `frontend/src/api/scoring.js` для `getFinalReport`
5) Сохранять `prof_activity_code` в элементе истории расчёта (UI использует для запроса отчёта)

Тестирование (обязательно)
- Ручная проверка в браузере (DevTools): кнопки видны, JSON открывается, HTML скачивается
- E2E сценарии 9–10 в Playwright (артефакты на падениях)

AC
- Кнопки отображаются для элементов истории с известным `prof_activity_code`
- JSON открывается в новой вкладке, HTML скачивается и корректно рендерится
- Без ошибок в консоли; корректные запросы к `/api/participants/{id}/final-report`
