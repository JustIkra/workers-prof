Ссылки на базу знаний в папке `.memory-base`:

## Пользовательская история (основа функциональных требований)

- `.memory-base/Product Overview/User story/user_flow.md` — детально описывает шаги пользователя: регистрация, управление участниками, загрузку трёх DOCX-отчётов, извлечение метрик из таблиц-изображений, выбор профдеятельности и расчёт коэффициента пригодности.
- `.memory-base/Product Overview/User story/*.docx` — контрольные отчёты кейса Батуры (используются как эталон потока и данных для извлечения).

Ниже перечислены остальные разделы памяти проекта:

- Продукт
  - `.memory-base/Product Overview/Features/README.md`
  - `.memory-base/Product Overview/Personas.md`
  - `.memory-base/Product Overview/Success metrics.md`
  - `.memory-base/Product Overview/User story/user_flow.md`

- Конвенции
  - `.memory-base/Conventions/Development/development_guidelines.md`
  - `.memory-base/Conventions/Documentation/documentation_workflow.md`
  - `.memory-base/Conventions/Git/git_conventions.md`
  - `.memory-base/Conventions/Testing/testing_guidelines.md`
  - `.memory-base/Conventions/Testing/backend.md`
  - `.memory-base/Conventions/Testing/frontend.md`
  - `.memory-base/Conventions/Testing/fixtures.md`
  - `.memory-base/Conventions/Testing/e2e-matrix.md`
  - `.memory-base/Conventions/Testing/ci.md`
  - `.memory-base/Conventions/Frontend/ui_style.md`
  - `.memory-base/Conventions/Frontend/frontend-requirements.md` ⭐ **Указатель требований к фронтенду**
  - `frontend/public/assets/theme-tokens.css` — CSS токены темы (в продакшене доступны как `/assets/theme-tokens.css`)

- Тех детали
  - `.memory-base/Tech details/Tech stack/TECH_STACK.md`
  - `.memory-base/Tech details/infrastructure/architecture.md`
  - `.memory-base/Tech details/infrastructure/data-model.md`
  - `.memory-base/Tech details/infrastructure/extraction-pipeline.md`
  - `.memory-base/Tech details/infrastructure/service-boundaries.md`
  - `.memory-base/Tech details/infrastructure/operations.md`
  - `.memory-base/Tech details/infrastructure/storage.md`
  - `.memory-base/Tech details/infrastructure/metric-mapping.md`
  - `.memory-base/Tech details/infrastructure/prompt-gemini-recommendations.md`

- Итоговый отчёт
  - `.memory-base/Product Overview/Final report/README.md`

- Тесты / E2E статус
  - `e2e/docs/EXECUTIVE_SUMMARY_FINAL_REPORTS.md` — сводка по сценариям финального отчёта (текущее состояние)
  - `e2e/docs/FINAL_REPORT_DATA_FLOW.md` — поток данных (ожидание vs факт)
  - `e2e/docs/FINAL_REPORT_FUNCTIONALITY_ANALYSIS.md` — разбор функциональности и гэпов
  - `e2e/docs/QUICK_FIX_CHECKLIST.md` — быстрые правки для разблокировки сценариев 9–10

- Задачи
  - `.memory-base/task/backlog.md`
  - `.memory-base/task/plan.md`
  - `.memory-base/task/tickets/` (каталог детализированных задач)
    - Ключевые ближайшие тикеты: `S2-04_final_report_json_html.md`, `S2-06_scoring_history_endpoint.md`
    - OCR/LLM: `AI-01_gemini_client.md`, `AI-02_keys_pool_rate_limit.md`, `AI-04_vision_fallback.md`
    - VPN: `VPN-01_wireguard_entrypoint.md`, `VPN-02_split_tunnel.md`, `VPN-03_vpn_health_endpoint.md`
