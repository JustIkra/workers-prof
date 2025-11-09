# Critical Path E2E UI Test Plan (S3-05)
## Цифровая модель управления компетенциями

## Application Overview

The Цифровая модель управления компетенциями (Digital Competency Management Model) is a comprehensive web application for professional competency assessment and personnel development. The system provides:

- **User Management**: Registration with admin approval workflow
- **Participant Management**: Centralized registry of assessment participants with full history
- **Report Processing**: Automated DOCX report upload with OCR and AI-powered metric extraction
- **Professional Suitability Scoring**: Calculation of professional fitness scores based on weighted metric tables
- **Final Reports**: Generation of comprehensive assessment reports in JSON and HTML formats

The application features role-based access control with:
- **Regular Users**: Can manage participants, upload reports, enter metrics, and calculate scores
- **Administrators**: Can approve new users and manage weight tables

## Test Environment

- **Application URL**: http://localhost:9187
- **Test Browser**: Chromium
- **Seed File**: `e2e/seed.spec.ts`
- **Test Data Location**: `/Users/maksim/git_projects/workers-prof/e2e/fixtures/test-report.docx`
- **Admin Credentials**:
  - Email: `admin@test.com`
  - Password: `admin123`

## Critical Path Test Scenarios

### Scenario 1: User Registration

**Seed:** `e2e/seed.spec.ts`

**Objective**: Verify that new users can register and their account is created in PENDING status awaiting admin approval.

**Steps:**
1. Navigate to application home page at `http://localhost:9187`
2. Verify landing page displays with heading "Цифровая модель управления компетенциями"
3. Click on "Зарегистрироваться" button (ref: top right button or bottom CTA button)
4. Verify navigation to registration page at `http://localhost:9187/register`
5. Verify registration form displays with heading "Регистрация"
6. In the "*Email" textbox, enter a unique test email address:
   - Format: `e2e-test-user-{timestamp}@test.com`
   - Example: `e2e-test-user-1699876543210@test.com`
7. In the "*Пароль" textbox, enter a valid password:
   - Must contain at least 8 characters, including letters and numbers
   - Example: `TestPass123`
8. In the "*Подтверждение пароля" textbox, enter the same password: `TestPass123`
9. Click the "Зарегистрироваться" button to submit the form

**Expected Results:**
- Form submission is successful
- User receives confirmation that registration is pending admin approval
- User cannot log in until approved
- New user appears in the admin pending users list with status PENDING

**Data to Save for Later Scenarios:**
- `testUserEmail`: The email address used for registration
- `testUserPassword`: The password used for registration

---

### Scenario 2: Admin Login

**Seed:** `e2e/seed.spec.ts`

**Objective**: Verify that admin can successfully authenticate and access admin-specific features.

**Assumptions**:
- Admin account exists with email `admin@test.com` and password `admin123`
- This should be performed in a separate browser context/tab to maintain both sessions

**Steps:**
1. Open a new browser context (separate session)
2. Navigate to `http://localhost:9187`
3. Click "Войти в систему" button on the landing page
4. Verify navigation to login page at `http://localhost:9187/login`
5. Verify login form displays with heading "Вход в систему"
6. In the "*Email" textbox, enter: `admin@test.com`
7. In the "*Пароль" textbox, enter: `admin123`
8. Click the "Войти" button to submit the form

**Expected Results:**
- Login is successful
- Success message displays: "Вход выполнен успешно"
- Redirect to participants page at `http://localhost:9187/participants`
- Top navigation bar displays:
  - "Участники" menu item (with icon)
  - "Админ" dropdown menu (with icon)
  - User profile button showing "admin@test.com"
- Admin dropdown menu contains:
  - "Пользователи" (Users management)
  - "Весовые таблицы" (Weight tables)

---

### Scenario 3: Admin User Approval

**Seed:** `e2e/seed.spec.ts`

**Objective**: Verify that admin can view pending users and approve new registrations, granting them access to the system.

**Assumptions**:
- Admin is logged in (from Scenario 2)
- At least one user is in PENDING status (from Scenario 1)

**Steps:**
1. From the participants page, click on the "Админ" dropdown menu
2. Verify dropdown displays menu items: "Пользователи" and "Весовые таблицы"
3. Click on "Пользователи" menu item
4. Verify navigation to admin users page at `http://localhost:9187/admin/users`
5. Verify page displays heading "Управление пользователями"
6. Verify subheading "Ожидают одобрения (N)" where N is the count of pending users
7. Locate the newly registered user in the pending users table:
   - Email matches the test email from Scenario 1
   - Status column shows "PENDING" badge
   - Date column shows current date (08.11.2025)
8. Click the "Одобрить" button for the test user

**Expected Results:**
- Success message appears confirming user approval
- User row is removed from the pending users table
- Counter "Ожидают одобрения (N)" decreases by 1
- The approved user can now log in to the system

**Verification Points:**
- The email of the approved user matches the one from Scenario 1
- Status changes from PENDING to ACTIVE (if there's an approved users section)

---

### Scenario 4: User Login (After Approval)

**Seed:** `e2e/seed.spec.ts`

**Objective**: Verify that newly approved users can successfully log in and access the application.

**Assumptions**:
- User was registered in Scenario 1
- User was approved by admin in Scenario 3
- Use the original browser context from Scenario 1 (or open a new one)

**Steps:**
1. If not already on login page, navigate to `http://localhost:9187/login`
2. In the "*Email" textbox, enter the test user email from Scenario 1
3. In the "*Пароль" textbox, enter the test user password from Scenario 1
4. Click the "Войти" button

**Expected Results:**
- Login is successful
- Success message displays: "Вход выполнен успешно"
- Redirect to participants page at `http://localhost:9187/participants`
- Top navigation bar displays:
  - "Участники" menu item
  - User profile button showing the test user's email
- Note: Regular users do NOT see the "Админ" dropdown menu
- Participants list page displays with heading "Участники"
- "Добавить участника" button is visible

---

### Scenario 5: Create Participant

**Seed:** `e2e/seed.spec.ts`

**Objective**: Verify that authenticated users can create new participants in the system.

**Assumptions**:
- User is logged in (from Scenario 4)
- User is on the participants list page

**Steps:**
1. From the participants page, click the "Добавить участника" button
2. Verify "Добавить участника" dialog opens with heading "Добавить участника"
3. Verify the dialog contains:
   - "*ФИО" textbox (required, placeholder: "Введите полное имя")
   - "Дата рождения" date picker
   - "Внешний ID" textbox (optional, placeholder: "Внешний идентификатор (необязательно)")
   - "Отмена" button
   - "Создать" button
4. In the "*ФИО" textbox, enter: `Тестов Тест Тестович`
5. Click on the "Дата рождения" date picker
6. Select birth date: `1990-01-15`
7. In the "Внешний ID" textbox, enter: `E2E-TEST-{timestamp}`
   - Example: `E2E-TEST-001`
8. Click the "Создать" button to submit the form

**Expected Results:**
- Dialog closes
- Success message appears confirming participant creation
- Participants table refreshes and displays the new participant
- New participant row shows:
  - ФИО: "Тестов Тест Тестович"
  - Дата рождения: "1990-01-15" (or formatted as "15.01.1990")
  - Внешний ID: "E2E-TEST-001"
  - Действия: "Открыть" and "Удалить" buttons
- Total count updates (e.g., "Всего 3" if there were 2 before)

**Data to Save for Later Scenarios:**
- `participantId`: The ID of the created participant (can be extracted from URL when opened)
- `participantName`: "Тестов Тест Тестович"
- `participantExternalId`: "E2E-TEST-001"

---

### Scenario 6: Upload Report

**Seed:** `e2e/seed.spec.ts`

**Objective**: Verify that users can upload DOCX reports for participants, triggering the automated extraction pipeline.

**Assumptions**:
- User is logged in
- Participant was created in Scenario 5
- Test DOCX file exists at `/Users/maksim/git_projects/workers-prof/e2e/fixtures/test-report.docx`

**Steps:**
1. From the participants list, locate the test participant "Тестов Тест Тестович"
2. Click the "Открыть" button for the test participant
3. Verify navigation to participant detail page at `http://localhost:9187/participants/{participantId}`
4. Verify page displays:
   - Heading with participant name: "Тестов Тест Тестович"
   - "Назад" button
   - "Рассчитать пригодность" button
   - Participant details table showing ФИО, Дата рождения, Внешний ID, Дата создания
   - "Отчёты" section with heading "Отчёты"
   - "Загрузить отчёт" button
5. Click the "Загрузить отчёт" button
6. Verify "Загрузить отчёт" dialog opens with heading "Загрузить отчёт"
7. Verify dialog contains:
   - "*Тип отчёта" dropdown (required, placeholder: "Выберите тип")
   - "*Файл (DOCX)" file upload section
   - "Выбрать файл" button
   - Helper text: "Только файлы DOCX, максимум 20 МБ"
   - "Отмена" button
   - "Загрузить" button (initially disabled)
8. Click on "*Тип отчёта" dropdown
9. Select report type from available options (check what types are available in the dropdown)
10. Click "Выбрать файл" button
11. When file chooser dialog appears, select the test DOCX file:
    - Path: `/Users/maksim/git_projects/workers-prof/e2e/fixtures/test-report.docx`
12. Verify selected filename appears in the upload section
13. Verify "Загрузить" button becomes enabled
14. Click the "Загрузить" button to submit the upload

**Expected Results:**
- Dialog closes
- Success message appears: "Отчёт загружен успешно" or similar
- Reports table refreshes and shows the uploaded report with:
  - Тип: Selected report type
  - Статус: "PROCESSING" or "PENDING" initially
  - Дата загрузки: Current date and time
  - Действия: Available action buttons (e.g., "Просмотреть", "Удалить")
- Empty state message "Нет загруженных отчётов" is no longer visible
- Background processing begins:
  - Celery task extracts images from DOCX
  - OCR processing on extracted tables/charts
  - Metrics are extracted and stored in database

**Note on Async Processing:**
- The extraction pipeline runs asynchronously via Celery
- Report status should eventually change to "COMPLETED" or "READY"
- For E2E testing, may need to poll/wait for status change
- Metrics should appear in the extracted_metric table

**Data to Save for Later Scenarios:**
- `reportId`: The ID of the uploaded report
- `reportType`: The type selected during upload

---

### Scenario 7: Enter Metrics Manually

**Seed:** `e2e/seed.spec.ts`

**Objective**: Verify that users can manually enter or verify metric values extracted from reports.

**Assumptions**:
- User is logged in
- Participant has at least one uploaded report (from Scenario 6)
- Metrics have been extracted (either via OCR or need manual entry)

**Note**: Based on the exploration, the UI for manual metric entry was not directly visible. This scenario assumes there is a metrics management interface accessible from the participant detail page or report detail view. If metrics are automatically extracted and no manual entry UI exists, this scenario should focus on viewing/verifying extracted metrics.

**Steps (Assuming Metrics View/Edit Interface Exists):**

1. From the participant detail page, locate the uploaded report in the reports table
2. Click on the report row or "Просмотреть" action button to view report details
3. Navigate to the metrics section of the report detail view
4. Verify that extracted metrics are displayed (if OCR processing completed)
5. If manual entry/editing is available:
   - Locate metric input fields or edit buttons
   - For each required metric (scale 1-10), enter or verify values:
     - Коммуникабельность (communicability): `7.5`
     - Командность (teamwork): `8.0`
     - Конфликтность низкая (low_conflict): `6.5`
     - Роль «Душа команды» (team_soul): `7.0`
     - Организованность (organization): `8.5`
     - Ответственность (responsibility): `9.0`
     - Невербальная логика (nonverbal_logic): `6.0`
     - Обработка информации (info_processing): `7.5`
     - Комплексное решение проблем (complex_problem_solving): `7.0`
     - Эмоциональная стабильность (emotional_stability): `8.0`
     - Стрессоустойчивость (stress_resistance): `7.5`
     - Вербальная логика (verbal_logic): `6.5`
     - Вербальный интеллект (verbal_intelligence): `7.0`
6. Click "Сохранить" or "Подтвердить" button to save metric values
7. Verify success message appears

**Alternative Steps (If No Manual Entry UI):**

1. Verify that OCR extraction completed successfully
2. Check that metrics appear in the participant detail view or scoring interface
3. Ensure minimum required metrics are present for scoring calculation

**Expected Results:**
- All 13 metrics required for "meeting_facilitation" professional activity are available
- Metric values are within valid range (1.0 to 10.0)
- Metrics are stored in the `extracted_metric` table with proper participant and report associations
- Confidence scores are recorded for each metric
- Source is marked as either "OCR" or "MANUAL" (if manually entered)

**Metrics Required for Meeting Facilitation:**
Based on the seed data, these 13 metrics are required:
1. communicability (вес: 0.18)
2. teamwork (вес: 0.10)
3. low_conflict (вес: 0.05)
4. team_soul (вес: 0.05)
5. organization (вес: 0.12)
6. responsibility (вес: 0.10)
7. nonverbal_logic (вес: 0.08)
8. info_processing (вес: 0.08)
9. complex_problem_solving (вес: 0.06)
10. emotional_stability (вес: 0.07)
11. stress_resistance (вес: 0.05)
12. verbal_logic (вес: 0.03)
13. verbal_intelligence (вес: 0.03)

---

### Scenario 8: Calculate Professional Suitability Score

**Seed:** `e2e/seed.spec.ts`

**Objective**: Verify that users can calculate professional suitability scores for participants based on extracted metrics and weight tables.

**Assumptions**:
- User is logged in
- Participant has uploaded reports with extracted metrics (from Scenarios 6 & 7)
- All required metrics for at least one professional activity are available
- Weight table exists for the professional activity "Организация и проведение совещаний" (code: `meeting_facilitation`)

**Steps:**
1. Navigate to the participant detail page for "Тестов Тест Тестович"
2. Verify participant details are displayed
3. Click the "Рассчитать пригодность" button
4. Verify "Рассчитать профессиональную пригодность" dialog opens
5. Verify dialog contains:
   - Heading: "Рассчитать профессиональную пригодность"
   - "*Профессиональная область" dropdown (required)
   - Info alert: "Убедитесь, что у участника загружены и обработаны отчёты с метриками"
   - "Отмена" button
   - "Рассчитать" button (initially disabled)
6. If warning appears "У участника нет загруженных отчётов":
   - Verify this is accurate (check reports table)
   - If reports exist but metrics aren't extracted yet, wait for processing to complete
7. Click on "*Профессиональная область" dropdown to view available activities
8. Select "Организация и проведение совещаний" from the dropdown
9. Verify "Рассчитать" button becomes enabled
10. Click the "Рассчитать" button to trigger score calculation

**Expected Results:**
- Dialog closes
- Success message appears: "Расчёт выполнен успешно" or similar
- Participant detail page refreshes
- Scoring results section appears on the page showing:
  - **Профессиональная область**: "Организация и проведение совещаний"
  - **Процент пригодности**: Calculated percentage (e.g., "72.5%")
  - **Дата расчёта**: Current date and time
  - **Сильные стороны**: List of top-performing metrics (highest values)
  - **Зоны развития**: List of metrics needing improvement (lowest values)
- Action buttons available:
  - "Просмотреть JSON" - View detailed results in JSON format
  - "Скачать HTML" or "Просмотреть отчёт" - View/download HTML report

**Calculation Details:**
- Score is calculated as: `score_pct = Σ(metric_value × weight) × 10`
- Example with sample values:
  ```
  communicability (7.5) × 0.18 = 1.35
  teamwork (8.0) × 0.10 = 0.80
  ... (all 13 metrics)
  Total weighted sum × 10 = 72.5%
  ```
- Result is stored in `scoring_result` table with:
  - participant_id
  - prof_activity_id
  - weight_table_id
  - score_pct (Decimal with 2 decimal places)
  - strengths (JSONB array)
  - development_areas (JSONB array)
  - recommendations (JSONB, if AI-generated)

**Verification Points:**
- Score percentage is between 0.00 and 100.00
- Strengths list contains 3-5 top metrics
- Development areas list contains 3-5 bottom metrics
- Timestamp is accurate

**Data to Save for Later Scenarios:**
- `scoringResultId`: The ID of the created scoring result
- `calculatedScore`: The percentage score calculated

---

### Scenario 9: View Final Report (JSON Format)

**Seed:** `e2e/seed.spec.ts`

**Objective**: Verify that users can view comprehensive assessment results in JSON format with all scoring details.

**Assumptions**:
- User is logged in
- Scoring calculation was completed in Scenario 8
- Scoring results exist for the test participant

**Steps:**
1. From the participant detail page with scoring results visible
2. Locate the scoring results section
3. Click the "Просмотреть JSON" button or link

**Expected Results:**
- JSON report modal/page opens or new tab opens
- JSON content is displayed in a formatted/readable way (with syntax highlighting if available)
- JSON structure contains:
  ```json
  {
    "participant": {
      "id": "uuid",
      "full_name": "Тестов Тест Тестович",
      "birth_date": "1990-01-15",
      "external_id": "E2E-TEST-001"
    },
    "professional_activity": {
      "code": "meeting_facilitation",
      "name": "Организация и проведение совещаний",
      "description": "..."
    },
    "scoring": {
      "score_pct": "72.50",
      "calculated_at": "2025-11-08T...",
      "weight_table_version": "v1.0"
    },
    "metrics": [
      {
        "code": "communicability",
        "name": "Коммуникабельность",
        "value": "7.50",
        "weight": "0.18",
        "contribution": "1.35"
      },
      // ... all 13 metrics
    ],
    "strengths": [
      {
        "metric_code": "responsibility",
        "metric_name": "Ответственность",
        "value": "9.00"
      },
      // ... top 3-5 metrics
    ],
    "development_areas": [
      {
        "metric_code": "verbal_logic",
        "metric_name": "Вербальная логика",
        "value": "6.50"
      },
      // ... bottom 3-5 metrics
    ],
    "recommendations": [
      // AI-generated recommendations if available
    ]
  }
  ```
- User can copy/download the JSON content
- Close button or back navigation returns to participant detail page

**Verification Points:**
- All participant data is accurate and matches Scenario 5 inputs
- Professional activity is "meeting_facilitation"
- Score percentage matches Scenario 8 calculation
- All 13 metrics are listed with correct values and weights
- Strengths highlight top performers (e.g., responsibility: 9.0, organization: 8.5)
- Development areas highlight areas for growth (e.g., verbal_logic: 6.5)
- No PII data leakage in unexpected fields
- Timestamps are in ISO format

---

### Scenario 10: View Final Report (HTML Format)

**Seed:** `e2e/seed.spec.ts`

**Objective**: Verify that users can view or download professionally formatted HTML reports suitable for sharing with stakeholders.

**Assumptions**:
- User is logged in
- Scoring calculation was completed in Scenario 8
- Scoring results exist for the test participant

**Steps:**
1. From the participant detail page with scoring results visible
2. Locate the scoring results section
3. Click the "Скачать HTML" or "Просмотреть отчёт" button

**Expected Results:**
- HTML report opens in a new tab/window or download dialog appears
- If opened in browser, HTML report displays with:

  **Header Section:**
  - Report title: "Отчёт о профессиональной пригодности"
  - Participant name: "Тестов Тест Тестович"
  - Date of birth: "15.01.1990"
  - External ID: "E2E-TEST-001"
  - Report generation date: Current date

  **Professional Activity Section:**
  - Activity name: "Организация и проведение совещаний"
  - Activity description: Full description text

  **Score Summary:**
  - Overall suitability percentage displayed prominently (e.g., "72.5%")
  - Visual indicator (color coding: green for high, yellow for medium, red for low)
  - Calculation date and time

  **Metrics Breakdown Table:**
  | Метрика | Значение | Вес | Вклад в оценку |
  |---------|----------|-----|----------------|
  | Коммуникабельность | 7.50 | 0.18 | 1.35 |
  | Командность | 8.00 | 0.10 | 0.80 |
  | ... | ... | ... | ... |

  **Strengths Section:**
  - Heading: "Сильные стороны"
  - List of top 3-5 metrics with high scores
  - Each item shows metric name and value
  - Formatted as bullet points or cards

  **Development Areas Section:**
  - Heading: "Зоны развития"
  - List of 3-5 metrics with lower scores
  - Each item shows metric name and value
  - Formatted as bullet points or cards

  **Recommendations Section (if available):**
  - AI-generated personalized recommendations
  - Development action items
  - Training suggestions

  **Footer:**
  - Report generation metadata
  - System version/branding
  - Disclaimer text (if applicable)

- HTML is properly formatted with CSS styling
- Report is printable (good print layout)
- If downloaded, file is saved with meaningful name:
  - Pattern: `report_{participant_external_id}_{date}.html`
  - Example: `report_E2E-TEST-001_2025-11-08.html`

**Verification Points:**
- All data matches the JSON report from Scenario 9
- No broken styling or layout issues
- All sections are present and readable
- Numbers are formatted correctly (decimal precision)
- Russian language text displays correctly (no encoding issues)
- Report can be printed or saved as PDF from browser

---

## Test Data Summary

### Pre-existing Data (Seeded)
- **Admin User**:
  - Email: `admin@test.com`
  - Password: `admin123`

- **Existing Participants**:
  - Батура Александр Александрович (BATURA_AA_001)
  - Иванов Иван Иванович (E2E-TEST-001)

- **Professional Activity**:
  - Code: `meeting_facilitation`
  - Name: "Организация и проведение совещаний"
  - ID: `22fdacda-0f53-44d2-aba5-49f9239fd383`

- **Metrics**: 13 metrics required for meeting_facilitation (see Scenario 7)

- **Weight Table**: Active weight table for meeting_facilitation with sum of weights = 1.0

### Test Data to Create
- **New User**:
  - Email: `e2e-test-user-{timestamp}@test.com`
  - Password: `TestPass123`

- **New Participant**:
  - Full Name: `Тестов Тест Тестович`
  - Birth Date: `1990-01-15`
  - External ID: `E2E-TEST-{timestamp}`

- **Test Report**:
  - File: `/Users/maksim/git_projects/workers-prof/e2e/fixtures/test-report.docx`
  - Type: To be determined from available dropdown options

## Key UI Elements Reference

### Navigation
- **Landing Page Buttons**: "Войти в систему", "Зарегистрироваться"
- **Main Menu**: "Участники", "Админ" (admin only)
- **Admin Submenu**: "Пользователи", "Весовые таблицы"
- **User Profile Button**: Displays logged-in user email

### Forms and Dialogs

#### Registration Form (`/register`)
- Fields: Email*, Пароль*, Подтверждение пароля*
- Buttons: "Зарегистрироваться", Link to "Войти"

#### Login Form (`/login`)
- Fields: Email*, Пароль*
- Buttons: "Войти", Link to "Зарегистрироваться"

#### Add Participant Dialog
- Fields: ФИО*, Дата рождения, Внешний ID
- Buttons: "Отмена", "Создать"

#### Upload Report Dialog
- Fields: Тип отчёта* (dropdown), Файл (DOCX)*
- Buttons: "Отмена", "Загрузить"

#### Calculate Score Dialog
- Fields: Профессиональная область* (dropdown)
- Buttons: "Отмена", "Рассчитать"

### Tables

#### Participants Table
- Columns: ФИО, Дата рождения, Внешний ID, Действия
- Actions: "Открыть", "Удалить"
- Pagination: Items per page selector, Previous/Next buttons

#### Pending Users Table (`/admin/users`)
- Columns: Email, Статус, Дата регистрации, Действия
- Actions: "Одобрить"

#### Reports Table (on participant detail page)
- Columns: Тип, Статус, Дата загрузки, Действия
- Empty State: "Нет загруженных отчётов" with icon

## Success Criteria

The E2E critical path test passes if:

1. **User Registration & Approval Flow**:
   - New users can register successfully
   - Admins can view and approve pending users
   - Approved users can log in and access the system

2. **Participant Management**:
   - Users can create new participants with required data
   - Participants appear in the list with correct information
   - Participant detail pages are accessible

3. **Report Processing**:
   - DOCX reports can be uploaded successfully
   - File validation works (type, size limits)
   - Upload triggers background processing

4. **Metric Extraction**:
   - Metrics are extracted from reports (via OCR or manual entry)
   - All required metrics for scoring are available
   - Metric values are within valid ranges (1.0 - 10.0)

5. **Scoring Calculation**:
   - Professional suitability scores can be calculated
   - Score is mathematically correct based on weights
   - Results include strengths and development areas

6. **Final Reports**:
   - JSON reports contain complete and accurate data
   - HTML reports are well-formatted and printable
   - Reports can be viewed/downloaded successfully

7. **Data Integrity**:
   - All data persists correctly in the database
   - Relationships between entities are maintained
   - No data loss or corruption occurs

8. **User Experience**:
   - Navigation flows are intuitive
   - Success/error messages are clear
   - Forms validate input appropriately
   - Loading states are handled gracefully

## Edge Cases and Error Handling

### To Consider for Extended Testing:

1. **Registration Errors**:
   - Duplicate email addresses
   - Weak passwords (< 8 chars, no numbers)
   - Password mismatch
   - Invalid email format

2. **Login Errors**:
   - Incorrect credentials
   - Pending user attempts to log in
   - Disabled/deleted user account

3. **File Upload Errors**:
   - Non-DOCX file types
   - Files exceeding 20 MB size limit
   - Corrupted DOCX files
   - Empty files

4. **Metric Extraction Failures**:
   - OCR confidence below threshold
   - Missing required tables in report
   - Gemini API failures (fallback to manual entry)

5. **Scoring Errors**:
   - Missing required metrics
   - Invalid weight table (sum ≠ 1.0)
   - Metric values out of range

6. **Concurrent Operations**:
   - Multiple users accessing same participant
   - Simultaneous report uploads
   - Weight table updates during scoring

## Notes for Test Implementation

1. **Browser Contexts**: Maintain separate contexts for admin and regular user sessions to test concurrent workflows.

2. **Async Operations**: Report processing and metric extraction are asynchronous. Implement polling or wait strategies to verify completion.

3. **Test Data Cleanup**: Consider implementing cleanup after test execution to maintain test environment state.

4. **Timestamps**: Use dynamic timestamp generation for unique test data (emails, external IDs).

5. **Report Type Selection**: During upload dialog testing, document available report types for future test updates.

6. **Metric Entry UI**: If manual metric entry UI is not implemented, adjust Scenario 7 to focus on verifying OCR extraction results.

7. **Screenshots**: Capture screenshots at key points for debugging and documentation.

8. **Performance**: Monitor response times for file upload and score calculation operations.

## File Paths

- **Test Plan**: `/Users/maksim/git_projects/workers-prof/e2e/TEST_PLAN_S3-05_CRITICAL_PATH.md`
- **Test Data**: `/Users/maksim/git_projects/workers-prof/e2e/fixtures/test-report.docx`
- **Seed File**: `/Users/maksim/git_projects/workers-prof/e2e/seed.spec.ts`
- **Playwright Config**: `/Users/maksim/git_projects/workers-prof/playwright.config.js`

---

**Document Version**: 1.0
**Last Updated**: 2025-11-08
**Prepared By**: Test Planning Agent
**Application Version**: 0.0.1 (beta)
