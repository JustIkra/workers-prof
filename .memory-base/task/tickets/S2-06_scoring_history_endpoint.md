Код: S2-06 — История оценок участника (API)

Цель
- Реализовать `GET /api/participants/{participant_id}/scores` для загрузки истории расчётов пригодности на UI.

Описание
- Возвращать список результатов в порядке `created_at DESC`.
- Поля элемента: `id`, `participant_id`, `prof_activity_code`, `prof_activity_name`, `score_pct`, `strengths`, `dev_areas`, `recommendations`, `created_at`.

Шаги
1) Router `api-gateway/app/routers/scoring.py`: новый эндпоинт с авторизацией
2) Репозиторий `ScoringResultRepository`: метод выборки по `participant_id`
3) Схема ответа (pydantic) для списка результатов
4) Подключить на UI: `scoringApi.getHistory()` → `ParticipantDetailView.vue`

Тестирование (обязательно)
- Unit/integration: выборка результатов и сортировка DESC
- UI: список истории отображается, без 404

AC
- Эндпоинт возвращает историю с полными данными для UI
- Ошибки авторизации/доступа корректно обрабатываются
