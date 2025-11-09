# E2E Test Plan - Workers-Prof Critical Path

## Overview
Comprehensive test plan for the critical user journey covering registration, approval, participant management, report upload, metrics entry, scoring, and final report generation.

**Base URL**: `http://localhost:9187`
**Test Framework**: Playwright
**Browser**: Chromium (Desktop Chrome)

---

## Test Scenario 1: User Registration

### Steps
1. Navigate to home page `/`
2. Click "Зарегистрироваться" button
3. Fill registration form:
   - Email: `test-e2e-{timestamp}@test.com`
   - Password: `TestPass123!`
   - Confirm Password: `TestPass123!`
4. Click "Зарегистрироваться" submit button

### Expected Results
- Redirect to `/login?message=pending`
- Success alert: "Регистрация успешна! Ожидайте одобрения администратора."
- Info message: "Ваш аккаунт ожидает одобрения администратором."

### Selectors
- Register button: `button[name="Зарегистрироваться"]` or `getByRole('button', { name: 'Зарегистрироваться' })`
- Email field: `textbox[name="*Email"]`
- Password field: `textbox[name="*Пароль"]`
- Confirm password field: `textbox[name="*Подтверждение пароля"]`

### Edge Cases
- Duplicate email registration
- Weak password validation
- Password mismatch

---

## Test Scenario 2: Admin Approval

### Prerequisites
- Admin user exists: `admin@test.com` / `admin123`
- Test user from Scenario 1 is in PENDING status

### Steps
1. Navigate to `/login`
2. Login as admin:
   - Email: `admin@test.com`
   - Password: `admin123`
3. Click "Админ" menu
4. Click "Пользователи" menu item
5. Verify pending user appears in table
6. Click "Одобрить" button for test user
7. Verify user disappears from pending list

### Expected Results
- Navigate to `/admin/users`
- Pending users table shows 1 user
- Success alert: "Пользователь {email} одобрен"
- Pending count becomes 0
- Empty state message: "Нет пользователей, ожидающих одобрения"

### Selectors
- Admin menu: `menuitem[name="Админ"]`
- Users submenu: `menuitem[name="Пользователи"]`
- Approve button: `button[name="Одобрить"]`
- User email cell: table row containing email

### Edge Cases
- Multiple pending users
- Already approved user
- Network failure during approval

---

## Test Scenario 3: User Login

### Prerequisites
- User from Scenario 1 has been approved

### Steps
1. Logout admin user (if logged in)
2. Navigate to `/login`
3. Fill login form:
   - Email: test user email
   - Password: `TestPass123!`
4. Click "Войти" button

### Expected Results
- Redirect to `/participants`
- Success alert: "Вход выполнен успешно"
- User email shown in header: `test-e2e-{timestamp}@test.com`
- Main navigation visible

### Selectors
- Email field: `textbox[name="*Email"]`
- Password field: `textbox[name="*Пароль"]`
- Login button: `button[name="Войти"]`
- User menu: `button[name="{email}"]`

### Edge Cases
- Invalid credentials
- PENDING user attempting login (should get 403)
- Empty credentials

---

## Test Scenario 4: Create Participant

### Prerequisites
- User is logged in
- On `/participants` page

### Steps
1. Click "Добавить участника" button
2. Fill participant form:
   - ФИО: `Иванов Иван Иванович`
   - Дата рождения: Select `1990-06-15` via date picker
     - Click year → select 1990
     - Click month → select Июнь
     - Click day → select 15
   - Внешний ID: `E2E-TEST-001`
3. Click "Создать" button

### Expected Results
- Modal dialog appears
- Form validation passes
- Success alert: "Участник создан"
- Modal closes
- New participant appears in table
- Total count updates: "Всего 2"

### Selectors
- Add button: `button[name="Добавить участника"]`
- Full name field: `textbox[name="*ФИО"]`
- Birth date picker: `combobox[name="Дата рождения"]`
- External ID field: `textbox[name="Внешний ID"]`
- Create button: `button[name="Создать"]`
- Cancel button: `button[name="Отмена"]`

### Date Picker Navigation
- Year selector: `button[name="{year}"]`
- Month grid: `gridcell[name="{month}"]`
- Day grid: `gridcell[name="{day}"]`
- Previous/Next controls: `button[name="Предыдущий год"]`, etc.

### Edge Cases
- Empty required fields (ФИО, дата рождения)
- Future birth date
- Duplicate external ID

---

## Test Scenario 5: Upload Report

### Prerequisites
- Participant created in Scenario 4
- Test DOCX file available: `e2e/fixtures/test-report.docx`

### Steps
1. Find participant in table
2. Click "Открыть" button
3. Navigate to reports section
4. Click "Загрузить отчёт" button
5. Select report type: `REPORT_1`
6. Upload file: `test-report.docx`
7. Verify upload success

### Expected Results
- Navigate to participant detail page
- File upload form visible
- Success message after upload
- Report appears in reports list
- Status: `UPLOADED`

### Selectors
- Open button: `button[name="Открыть"]` in participant row
- Upload button: `button[name="Загрузить отчёт"]`
- Report type select: `combobox` or `select`
- File input: `input[type="file"]`

### Edge Cases
- Invalid file type (not DOCX)
- File too large (> 15MB)
- Missing report type
- Network interruption

---

## Test Scenario 6: Manual Metrics Entry

### Prerequisites
- Report uploaded in Scenario 5
- Metric definitions seeded in database

### Steps
1. Open report detail page
2. View metrics table/form
3. For each metric definition:
   - Enter value between 1.0 - 10.0
   - Source: `MANUAL`
   - Confidence: `1.0`
4. Save metrics

### Expected Results
- Metrics form displays all metric definitions
- Values validated (range 1-10)
- Success message on save
- Metrics appear in table with source `MANUAL`

### Selectors
- Metric value inputs: `input[type="number"]` or textbox
- Save button: `button[name="Сохранить"]` or similar
- Metric name labels: text labels

### Edge Cases
- Values outside range (< 1 or > 10)
- Non-numeric input
- Missing required metrics
- Decimal precision (1 decimal place)

---

## Test Scenario 7: Calculate Score

### Prerequisites
- Metrics entered in Scenario 6
- Professional activity exists: `meeting_facilitation`
- Weight table activated

### Steps
1. Navigate to scoring section
2. Select professional activity: `MEETING_FACILITATION`
3. Click "Рассчитать" button
4. Wait for calculation to complete
5. Verify score result

### Expected Results
- Score calculation succeeds
- `score_pct` between 0-100
- Strengths list (3-5 items)
- Development areas list (3-5 items)
- Calculation timestamp

### Selectors
- Activity selector: `select` or `combobox`
- Calculate button: `button[name="Рассчитать"]` or similar
- Score display: element containing score percentage
- Strengths list: list of strength items
- Dev areas list: list of development areas

### Edge Cases
- Missing metrics
- Invalid activity code
- No active weight table
- Weight sum ≠ 1.0

---

## Test Scenario 8: View Final Report

### Prerequisites
- Score calculated in Scenario 7

### Steps
1. Navigate to final report section
2. Select format: `json` or `html`
3. Click "Получить отчёт" or navigate to endpoint
4. Verify report content

### Expected JSON Structure
```json
{
  "participant_id": "uuid",
  "score_pct": 72.5,
  "strengths": ["strength1", "strength2", "strength3"],
  "dev_areas": ["area1", "area2", "area3"],
  "metrics_table": [...],
  "template_version": "1.0"
}
```

### Expected HTML Content
- DOCTYPE html
- Participant name
- Score percentage
- Strengths section
- Development areas section
- Recommendations (if AI enabled)

### Selectors
- Format selector: radio buttons or select
- View report button: `button` or link
- Download button: `button[name="Скачать"]`

### API Endpoints
- JSON: `GET /api/participants/{id}/final-report?activity_code={code}&format=json`
- HTML: `GET /api/participants/{id}/final-report?activity_code={code}&format=html`

### Edge Cases
- Missing score calculation
- Invalid activity code
- Network timeout
- Large report size

---

## Error Handling Tests

### Network Failures
- Simulate offline mode
- API timeout
- 500 server errors

### Validation Errors
- 422 Unprocessable Entity
- Missing required fields
- Invalid data types

### Authorization Errors
- 401 Unauthorized (expired token)
- 403 Forbidden (insufficient permissions)
- PENDING user accessing protected routes

---

## Performance Considerations

### Wait Strategies
- Use `waitForURL` after navigation
- Use `waitForSelector` for dynamic content
- Use `waitForLoadState('networkidle')` after API calls
- Use `waitForResponse` for specific API calls

### Timeouts
- Default action timeout: 10000ms
- Navigation timeout: 30000ms
- API call timeout: 30000ms

---

## Test Data Cleanup

### After Each Test
- Delete created participants
- Delete uploaded reports
- Delete test users (except admin)

### Database State
- Reset to known state before test suite
- Seed required data (metrics, activities, weights)
- Clean up test artifacts

---

## CI/CD Configuration

### Environment Variables
- `BASE_URL`: Application URL (default: http://localhost:9187)
- `CI`: Set to true in CI environment
- Test retries: 2 on CI, 0 locally
- Parallel workers: 1 on CI

### Artifacts
- Screenshots on failure: `screenshot: 'only-on-failure'`
- Video on failure: `video: 'retain-on-failure'`
- Trace on retry: `trace: 'on-first-retry'`
- HTML report: Always generated

### Pre-requisites
- PostgreSQL running
- Redis running
- RabbitMQ running
- Database migrations applied
- Admin user seeded
- Metric definitions seeded
- Weight tables seeded

---

## Test Stability

### Anti-Patterns to Avoid
- Hard-coded waits (`page.waitForTimeout`)
- Fragile selectors (CSS classes, IDs that may change)
- Test interdependencies
- Shared mutable state

### Best Practices
- Use semantic selectors (`getByRole`, `getByText`, `getByLabel`)
- Wait for specific conditions, not arbitrary time
- Isolate tests (each test should be independent)
- Use test fixtures for common setup
- Clean up after tests
- Use data-testid attributes for critical elements

---

## Success Criteria

### Test Pass Rate
- All critical path tests pass: 100%
- Edge case tests pass: ≥ 95%
- Performance tests pass: ≥ 90%

### Coverage
- All API endpoints in critical path tested
- All user-facing forms validated
- All navigation flows covered
- Error states handled

### Artifacts
- Video recordings on test failures
- Screenshots on assertion failures
- Detailed error logs
- Network request logs

---

## Maintenance

### When to Update Tests
- UI changes (new selectors)
- API contract changes
- New features added
- Bug fixes that affect test assertions

### Test Review Cadence
- Weekly: Review failed tests
- Monthly: Review test execution time
- Quarterly: Full test suite audit
