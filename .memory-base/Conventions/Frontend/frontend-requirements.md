# Указатель требований к фронтенду

## Цель документа
Справочник требований для разработки фронтенда системы оценки профессиональной пригодности.

---

## 1. Стилистика и дизайн

### 1.1 Общий стиль
- **Тип**: Офисный, строгий, функциональный
- **Целевая аудитория**: Госсектор (Windows, невысокие DPI)
- **Принципы**: Сдержанность, консервативность, предсказуемость, доступность

### 1.2 Цветовая палитра
```css
/* Primary Colors */
--color-primary: #00798D;
--color-primary-dark: #025E6D;
--color-primary-light: #E0F3F6;

/* Semantic Colors */
--color-info: #0B5CAD;
--color-success: #2E7D32;
--color-warning: #B26A00;
--color-danger: #C62828;

/* Grayscale */
--color-gray-900: #1F2937;
--color-gray-700: #374151;
--color-gray-500: #6B7280;
--color-gray-200: #E5E7EB;
--color-gray-50: #F9FAFB;

/* Focus */
--color-focus: #0B5CAD;
```

### 1.3 Типографика
```css
/* Font Stack */
font-family: 'Segoe UI', Tahoma, Arial, -apple-system, system-ui, sans-serif;

/* Font Sizes */
--font-size-base: 14px;
--font-size-h1: 20px;
--font-size-h2: 18px;
--font-size-h3: 16px;

/* Line Height */
--line-height-base: 1.5;
```

Источник токенов темы
- Хранить CSS‑токены темы в `frontend/public/assets/theme-tokens.css` и подключать через `/assets/theme-tokens.css`.

### 1.4 Компоновка
- **Header**: 64px высота, логотип + название
- **Sidebar**: 240px ширина, вертикальное меню слева
- **Content**: max-width 1280px, поля 24px, сетка 12 колонок
- **Сетка**: Bootstrap-like, 12 колонок

---

## 2. UI Компоненты

### 2.1 Кнопки
- **Primary**: сплошная заливка `--color-primary`, hover затемнение 8%
- **Secondary**: заливка `--color-gray-50`, border `--color-gray-200`
- **Link**: цвет `--color-info`, подчёркивание только при hover/focus
- **Disabled**: 40% opacity

### 2.2 Формы
- **Лейблы**: слева от полей
- **Обязательные поля**: звёздочка `*`
- **Валидация**: подсказки/ошибки под полем (малый серый/красный текст)
- **Маски**:
  - Дата: `dd.mm.yyyy`
  - Числа: десятичная запятая
  - Проценты: символ `%` справа

### 2.3 Таблицы
- **Высота строки**: 44px
- **Шрифт**: 14px
- **Зебра**: чередование строк (`--color-gray-50`)
- **Заголовок**: фиксированный, сортировка по столбцам
- **Действия**: явные текстовые кнопки («Открыть», «Загрузить», «Удалить»)
- **Пагинация**: внизу справа, размеры 10/20/50

### 2.4 Модальные окна
- **Ширина**: 560–720px
- **Заголовок**: H2
- **Кнопки**: «Сохранить»/«Отмена» внизу справа
- **Закрытие**: Esc + крестик

### 2.5 Загрузка файлов
- **Dropzone**: border `--color-gray-200`
- **Подсказка**: «Поддерживаются .docx»
- **Прогресс-бар**: явный индикатор
- **Ошибки**: в явном алерте

### 2.6 Уведомления
- **Toast**: ненавязчивые, вверху справа
- **Alert**: важные ошибки в контенте

### 2.7 Иконки
- **Стиль**: лаконичные, монохромные
- **Набор**: Element Plus Icons или Material Outlined
- **Размеры**: 16px / 20px

---

## 3. Библиотека UI

### 3.1 Рекомендуемая библиотека
- **Первый выбор**: [Element Plus](https://element-plus.org/)
- **Альтернатива**: [Naive UI](https://www.naiveui.com/)
- **Причина**: офисный стиль, доступность, совместимость токенов темы

### 3.2 Интеграция Element Plus
```javascript
// Сопоставление токенов
--el-color-primary: var(--color-primary);
--el-font-size-base: 14px;
--el-border-radius-base: 4px;
--el-color-success: var(--color-success);
--el-color-warning: var(--color-warning);
--el-color-danger: var(--color-danger);
--el-color-info: var(--color-info);
```

---

## 4. Доступность (WCAG AA)

### 4.1 Требования
- ✅ Контраст цветов: минимум AA
- ✅ Навигация табом: все интерактивные элементы
- ✅ Видимый фокус: outline 2px `--color-focus`
- ✅ ARIA: для форм/алертов
- ✅ `aria-describedby`: для ошибок ввода

### 4.2 Проверка
- Инструменты: stylelint-a11y (опционально в CI)
- Ручное тестирование: навигация клавиатурой

---

## 5. Локализация (ru-RU)

### 5.1 Форматы данных
- **Дата**: `01.02.2025` (dd.mm.yyyy)
- **Время**: `14:05` (24-часовой формат)
- **Числа**: разделитель тысяч — пробел, десятичный — запятая
  - Пример: `1 234,56`

### 5.2 Микрокопирайтинг
- **Тон**: деловой, нейтральный
- **Примеры**: «Загрузить», «Сохранить», «Отменить», «Рассчитать», «Сгенерировать рекомендации»
- **Ошибки**: конкретные формулировки
  - Пример: «Файл должен быть .docx и не больше 20 МБ»

---

## 6. Ключевые экраны и функции

### 6.1 Управление участниками
- **CRUD**: Создание, чтение, обновление, удаление участников
- **Поля**: ФИО, дата рождения, внешний ID
- **Поиск/фильтр**: по ФИО/ID
- **Таблица**: с пагинацией, сортировкой

### 6.2 Загрузка отчётов
- **Привязка**: к участнику
- **Типы**: Отчёт 1, 2, 3
- **Формат**: .docx
- **Действия**: загрузка, скачивание, просмотр статуса

### 6.3 Извлечение метрик
- **Процесс**: OCR → нормализация → валидация
- **UI**: отображение извлечённых значений с изображением
- **Ручная валидация**: редактирование значений

### 6.4 Весовые таблицы (ADMIN)
- **Список версий**: слева
- **Активная версия**: справа, строки весов
- **Валидация**: сумма весов = 1.0
- **Действия**: загрузка, активация

### 6.5 Расчёт пригодности
- **Выбор профдеятельности**: dropdown
- **Кнопка**: «Рассчитать»
- **Результат**: процент, сильные стороны, зоны развития, рекомендации

### 6.6 Роли и доступ
- **ADMIN**: управление весами, подтверждение регистраций, полный доступ
- **USER**: работа с участниками, загрузка отчётов, расчёт
- **Регистрация**: → PENDING → ADMIN одобряет → ACTIVE

---

## 7. Технологический стек

### 7.1 Фреймворк
- **Vue 3**: Composition API
- **Pinia**: управление состоянием
- **Vue Router**: клиентская маршрутизация

### 7.2 Сборка
- **Vite**: dev server + production build
- **TypeScript**: опционально (рекомендуется)

### 7.3 Тестирование
- **Vitest**: unit тесты
- **Playwright**: E2E тесты

### 7.4 Структура проекта
```
frontend/
├── src/
│   ├── components/     # Переиспользуемые компоненты
│   ├── views/          # Страницы (роуты)
│   ├── stores/         # Pinia stores
│   ├── services/       # API клиенты
│   ├── composables/    # Композиции (логика)
│   ├── assets/         # Статика (CSS, изображения)
│   └── router/         # Маршрутизация
├── tests/
│   ├── unit/
│   └── e2e/
└── dist/               # Production build
```

---

## 8. Интеграция с Backend

### 8.1 API Endpoints
- Базовый URL: `/api`
- Аутентификация: JWT в заголовке `Authorization: Bearer <token>`
- Документация: `/api/docs` (Swagger)

### 8.2 Основные эндпоинты
```
POST   /api/auth/register
POST   /api/auth/login
GET    /api/participants
POST   /api/participants
GET    /api/participants/{id}
PUT    /api/participants/{id}
DELETE /api/participants/{id}
POST   /api/participants/{id}/reports
GET    /api/reports/{id}/download
POST   /api/reports/{id}/extract
GET    /api/reports/{id}/metrics
GET    /api/admin/weights
POST   /api/admin/weights
POST   /api/admin/weights/{id}/activate
POST   /api/participants/{id}/score?activity=CODE
```

### 8.3 Обработка ошибок
- 401: перенаправление на логин
- 403: сообщение «Недостаточно прав»
- 422: валидация, отображение ошибок полей
- 500: общее сообщение об ошибке

---

## 9. Производительность

### 9.1 Оптимизация
- **Lazy loading**: роутов и компонентов
- **Виртуализация**: для длинных списков (Element Plus Table)
- **Дебаунс**: для поиска/фильтров (300ms)

### 9.2 Build
- **Минификация**: CSS/JS
- **Tree-shaking**: удаление неиспользуемого кода
- **Code splitting**: по роутам

---

## 10. Готовность к продакшену

### 10.1 Чеклист
- ✅ UI соответствует стилю документации
- ✅ Все основные экраны реализованы
- ✅ Роли и доступ работают корректно
- ✅ Валидация форм на клиенте
- ✅ Обработка ошибок API
- ✅ Доступность WCAG AA
- ✅ Локализация ru-RU
- ✅ Unit тесты (покрытие ≥60%)
- ✅ E2E тесты (критические сценарии)
- ✅ Production build оптимизирован

### 10.2 Деплой
- **Сборка**: `npm run build`
- **Выход**: `dist/`
- **Раздача**: FastAPI StaticFiles + SPA fallback
- **Nginx**: TLS на `prof.labs-edu.ru`

---

## 11. Ссылки на документацию

### 11.1 Продуктовая документация
- [Ключевые фичи](.memory-base/Product Overview/Features/README.md)
- [Персонажи](.memory-base/Product Overview/Personas.md)
- [User flow](.memory-base/Product Overview/User story/user_flow.md)
- [Финальный отчёт](.memory-base/Product Overview/Final report/README.md)

### 11.2 Технические требования
- [UI стиль](.memory-base/Conventions/Frontend/ui_style.md)
- [Тестирование фронтенда](.memory-base/Conventions/Testing/frontend.md)
- [Руководство по разработке](.memory-base/Conventions/Development/development_guidelines.md)
- [Tech stack](.memory-base/Tech details/Tech stack/TECH_STACK.md)

### 11.3 Архитектура
- [Service boundaries](.memory-base/Tech details/infrastructure/service-boundaries.md)
- [Data model](.memory-base/Tech details/infrastructure/data-model.md)

### 11.4 Задачи
- [S2-05: Frontend metrics calc](.memory-base/task/tickets/S2-05_frontend_metrics_calc.md)
- [E2E matrix](.memory-base/Conventions/Testing/e2e-matrix.md)

---

## 12. Быстрый старт для разработчика

### 12.1 Установка зависимостей
```bash
cd frontend
npm install
```

### 12.2 Разработка
```bash
npm run dev  # Запуск dev server на http://localhost:5173
```

### 12.3 Сборка
```bash
npm run build  # Сборка для production в dist/
```

### 12.4 Тестирование
```bash
npm run test:unit  # Vitest unit тесты
npm run test:e2e   # Playwright E2E тесты
```

---

**Версия документа**: 1.0
**Дата создания**: 2025-01-06
**Ответственный**: Claude Code (S1-10)
