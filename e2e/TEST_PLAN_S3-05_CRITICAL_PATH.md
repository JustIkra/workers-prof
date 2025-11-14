# Workers-Prof Application - Critical Path Test Plan (S3-05)

## Application Overview

The **Workers-Prof** application is a comprehensive competency management system that automates professional suitability assessment. The platform features:

- **User Management**: Role-based access control with admin approval workflow for new registrations
- **Participant Management**: Complete registry of participants with personal data and assessment history
- **Report Processing**: Upload and automated processing of DOCX reports with AI Vision-powered metric extraction
- **Manual Metric Entry**: Interface for reviewing and correcting automatically extracted metrics
- **Scoring Engine**: Calculation of professional suitability scores using weighted metric formulas
- **Final Reports**: Generation of comprehensive assessment reports in JSON and HTML formats with personalized recommendations

The system supports three types of reports per participant: Business Report (REPORT_1), Respondent Report (REPORT_2), and Competencies Report (REPORT_3).

---

## Test Execution Environment

- **Application URL**: http://localhost:9187
- **Test Fixtures Location**: `/Users/maksim/git_projects/workers-prof/e2e/fixtures/`
- **Admin Credentials**: admin@test.com / admin123
- **Test Data Files**:
  - REPORT_1: `Batura_A.A._Biznes-Profil_Biznes-otchyot_1718107.docx`
  - REPORT_2: `Batura_A.A._Biznes-Profil_Otchyot_dlya_respondenta_1718107.docx`
  - REPORT_3: `Batura_A.A._Biznes-Profil_Otchyot_po_kompetentsiyam_1718107.docx`

---

## Test Scenarios

### 1. User Registration

**Seed**: `e2e/seed.spec.ts` (fresh database state)

**Preconditions**:
- Application is running on http://localhost:9187
- Database is in fresh state (no pending users)
- Browser is opened to the home page

#### 1.1 Successful User Registration

**Steps**:
1. Navigate to http://localhost:9187
2. Verify page displays heading "Цифровая модель управления компетенциями"
3. Click button with text "Зарегистрироваться" (either top or bottom button)
4. Verify redirect to `/register` page
5. Verify heading "Регистрация" is displayed
6. Locate textbox with placeholder "Введите email"
7. Type email: `testuser@example.com`
8. Locate textbox with placeholder "Введите пароль (минимум 8 символов, буквы и цифры)"
9. Type password: `Test1234`
10. Locate textbox with placeholder "Повторите пароль"
11. Type password confirmation: `Test1234`
12. Click button "Зарегистрироваться"
13. Wait for success message (toast notification)

**Expected Results**:
- Toast/alert appears with text: "Регистрация успешна! Ожидайте одобрения администратора."
- Form is cleared or user is redirected to login page
- New user record is created in database with `approved=false`

**Verification Points**:
- Email validation works (prevents invalid formats)
- Password requirements are enforced (minimum 8 characters, letters and digits)
- Password confirmation must match password
- Success message is clearly visible

#### 1.2 Registration with Invalid Email

**Steps**:
1. Navigate to http://localhost:9187/register
2. Enter email: `invalid-email`
3. Enter password: `Test1234`
4. Enter password confirmation: `Test1234`
5. Attempt to submit form

**Expected Results**:
- Form validation prevents submission
- Error message indicates invalid email format

#### 1.3 Registration with Weak Password

**Steps**:
1. Navigate to http://localhost:9187/register
2. Enter email: `testuser2@example.com`
3. Enter password: `weak`
4. Enter password confirmation: `weak`
5. Attempt to submit form

**Expected Results**:
- Form validation prevents submission
- Error message indicates password requirements (minimum 8 characters, letters and digits)

#### 1.4 Registration with Mismatched Passwords

**Steps**:
1. Navigate to http://localhost:9187/register
2. Enter email: `testuser3@example.com`
3. Enter password: `Test1234`
4. Enter password confirmation: `Different1234`
5. Attempt to submit form

**Expected Results**:
- Form validation prevents submission
- Error message indicates passwords do not match

#### 1.5 Registration with Duplicate Email

**Steps**:
1. Complete successful registration with `duplicate@example.com`
2. Navigate back to http://localhost:9187/register
3. Attempt to register again with same email `duplicate@example.com`
4. Submit form

**Expected Results**:
- Server returns error response
- Error message indicates email already exists

---

### 2. Admin Approval

**Seed**: `e2e/seed.spec.ts` (requires at least one pending user)

**Preconditions**:
- At least one user with `approved=false` exists in database
- Admin user exists (admin@test.com)
- Browser is not logged in

#### 2.1 Admin Login

**Steps**:
1. Navigate to http://localhost:9187/login
2. Verify heading "Вход в систему" is displayed
3. Locate textbox with placeholder "Введите email"
4. Type email: `admin@test.com`
5. Locate textbox with placeholder "Введите пароль"
6. Type password: `admin123`
7. Click button "Войти"
8. Wait for redirect

**Expected Results**:
- Redirect to `/participants` page
- Toast notification appears with text: "Вход выполнен успешно"
- Top navigation shows user email "admin@test.com" in dropdown
- "Админ" menu item is visible (admin-only feature)

**Verification Points**:
- Login fails with incorrect credentials
- Session is established (token stored)
- Navigation bar shows authenticated state

#### 2.2 Navigate to User Management

**Steps**:
1. Ensure logged in as admin
2. Locate menuitem "Админ" in top navigation
3. Click on "Админ" menuitem to expand dropdown
4. Verify dropdown contains options: "Пользователи" and "Весовые таблицы"
5. Click menuitem "Пользователи"
6. Wait for page load

**Expected Results**:
- URL changes to `/admin/users`
- Heading "Управление пользователями" is displayed
- Section heading "Ожидают одобрения (N)" shows count of pending users
- If pending users exist, they are listed with email and approval button
- If no pending users, message "Нет пользователей, ожидающих одобрения" is shown

#### 2.3 Approve Pending User

**Preconditions**:
- At least one pending user exists (from scenario 1.1)

**Steps**:
1. Navigate to `/admin/users` (as admin)
2. Verify pending user `testuser@example.com` is listed in "Ожидают одобрения" section
3. Locate button "Одобрить" next to the user email
4. Click "Одобрить" button
5. Wait for confirmation

**Expected Results**:
- Toast notification appears: "Пользователь одобрен"
- User is removed from "Ожидают одобрения" section
- User count in heading decrements
- User record in database is updated with `approved=true`

**Verification Points**:
- Approved user can now log in
- Pending list updates in real-time
- Admin action is logged (audit trail)

#### 2.4 Reject Pending User (Optional Edge Case)

**Steps**:
1. Navigate to `/admin/users` (as admin)
2. Locate pending user with "Отклонить" button (if available)
3. Click "Отклонить" button
4. Confirm rejection dialog (if present)

**Expected Results**:
- User is removed from pending list
- User record is either deleted or marked as rejected
- User cannot log in

---

### 3. User Login

**Seed**: `e2e/seed.spec.ts` (requires approved user)

**Preconditions**:
- User `testuser@example.com` exists with `approved=true` (from scenario 2.3)
- Browser is logged out

#### 3.1 Successful Login with Approved User

**Steps**:
1. Navigate to http://localhost:9187/login
2. Enter email: `testuser@example.com`
3. Enter password: `Test1234`
4. Click button "Войти"
5. Wait for redirect

**Expected Results**:
- Redirect to `/participants` page
- Toast notification: "Вход выполнен успешно"
- Top navigation shows user email "testuser@example.com"
- Participants list is visible (may be empty initially)
- "Админ" menu is NOT visible (non-admin user)

**Verification Points**:
- Session token is stored in localStorage or cookies
- Authenticated routes are accessible
- Role-based UI elements are correct

#### 3.2 Login with Unapproved User

**Preconditions**:
- User exists with `approved=false`

**Steps**:
1. Navigate to http://localhost:9187/login
2. Enter email of unapproved user
3. Enter correct password
4. Click "Войти"

**Expected Results**:
- Login fails with error message
- Error indicates user is not approved or account is pending
- No redirect occurs

#### 3.3 Login with Invalid Credentials

**Steps**:
1. Navigate to http://localhost:9187/login
2. Enter email: `testuser@example.com`
3. Enter password: `WrongPassword123`
4. Click "Войти"

**Expected Results**:
- Error message appears: "Неверный email или пароль" (or similar)
- No redirect occurs
- Form remains on login page

#### 3.4 Verify Session Persistence

**Steps**:
1. Login successfully as `testuser@example.com`
2. Navigate to `/participants`
3. Refresh browser page (F5)
4. Wait for page load

**Expected Results**:
- User remains logged in (session persists)
- Page loads without redirect to login
- User email still visible in navigation

---

### 4. Create Participant

**Seed**: `e2e/seed.spec.ts`

**Preconditions**:
- User is logged in (from scenario 3.1)
- Currently on `/participants` page

#### 4.1 Successful Participant Creation

**Steps**:
1. Verify on `/participants` page with heading "Участники"
2. Click button "Добавить участника"
3. Verify dialog opens with heading "Добавить участника"
4. Locate textbox with placeholder "Введите полное имя"
5. Type full name: `Батура Александр Александрович`
6. Locate combobox labeled "Дата рождения"
7. Click on date picker to open calendar
8. Select date: June 15, 1985 (1985-06-15)
   - Navigate to year 1985
   - Navigate to month June (Июнь)
   - Click day 15
9. Locate textbox with placeholder "Внешний идентификатор (необязательно)"
10. Type external ID: `BATURA_AA_TEST`
11. Click button "Создать"
12. Wait for dialog to close

**Expected Results**:
- Dialog closes
- Toast notification: "Участник создан успешно" (or similar)
- New participant appears in the table with:
  - Full name: "Батура Александр Александрович"
  - Birth date: "1985-06-15"
  - External ID: "BATURA_AA_TEST"
- Table shows action buttons: "Открыть" and "Удалить"
- Participant count updates ("Всего 1" or increments)

**Verification Points**:
- Form validation requires full name
- Date picker accepts valid dates
- External ID is optional
- Participant is persisted in database

#### 4.2 Create Participant Without External ID

**Steps**:
1. Click "Добавить участника"
2. Enter full name: `Иванов Иван Иванович`
3. Select birth date: 1990-01-01
4. Leave external ID empty
5. Click "Создать"

**Expected Results**:
- Participant is created successfully
- External ID cell is empty or shows placeholder value
- No validation error for missing external ID

#### 4.3 Create Participant with Missing Required Fields

**Steps**:
1. Click "Добавить участника"
2. Leave full name empty
3. Select birth date
4. Click "Создать"

**Expected Results**:
- Form validation prevents submission
- Error message indicates required field "ФИО"

#### 4.4 Create Participant with Invalid Date

**Steps**:
1. Click "Добавить участника"
2. Enter full name
3. Attempt to select future date (e.g., tomorrow)
4. Try to submit

**Expected Results**:
- Date picker prevents selection of future dates
- Or validation error appears if future date is entered

---

### 5. Upload Reports

**Seed**: `e2e/seed.spec.ts`

**Preconditions**:
- User is logged in
- Participant "Батура Александр Александрович" exists (from scenario 4.1)
- Test fixture files are available at `/Users/maksim/git_projects/workers-prof/e2e/fixtures/`

#### 5.1 Navigate to Participant Detail Page

**Steps**:
1. On `/participants` page, locate participant "Батура Александр Александрович"
2. Click button "Открыть" for this participant
3. Wait for page load

**Expected Results**:
- URL changes to `/participants/{participant_id}` (UUID)
- Heading displays participant name: "Батура Александр Александрович"
- Participant info table shows:
  - ФИО: "Батура Александр Александрович"
  - Дата рождения: "1985-06-15"
  - Внешний ID: "BATURA_AA_TEST"
  - Дата создания: current timestamp
- Section "Отчёты" is visible with heading
- Button "Загрузить отчёт" is present
- Button "Рассчитать пригодность" is present but may be disabled
- Reports table is empty with message: "Нет загруженных отчётов"

#### 5.2 Upload REPORT_1 (Business Report)

**Steps**:
1. On participant detail page, click button "Загрузить отчёт"
2. Verify dialog opens with heading "Загрузить отчёт"
3. Click combobox labeled "Тип отчёта"
4. Verify dropdown shows options: "Отчёт 1", "Отчёт 2", "Отчёт 3"
5. Select option "Отчёт 1"
6. Click button "Выбрать файл"
7. In file picker dialog, select file: `Batura_A.A._Biznes-Profil_Biznes-otchyot_1718107.docx`
8. Verify filename appears in upload area
9. Click button "Загрузить"
10. Wait for upload to complete

**Expected Results**:
- Dialog closes
- Toast notification: "Отчёт загружен успешно" (or similar)
- Reports table now shows one row:
  - Тип: "Отчёт 1" or "REPORT_1"
  - Статус: "Обработка" or "Обработан" (depending on Celery task completion)
  - Дата загрузки: current date/time
  - Действия: buttons for "Открыть" / "Скачать" / "Удалить"
- File is stored on server in `/app/storage/` directory
- Database records created: `file_ref`, `report` (with `file_ref_id`)
- Celery task `extract_images_from_report` is triggered (runs async or eager in test mode)

**Verification Points**:
- Only DOCX files are accepted
- File size limit is enforced (max 20 MB)
- Upload progress indicator appears for large files
- Status updates when processing completes

#### 5.3 Upload REPORT_2 (Respondent Report)

**Steps**:
1. Click "Загрузить отчёт" again
2. Select report type "Отчёт 2"
3. Choose file: `Batura_A.A._Biznes-Profil_Otchyot_dlya_respondenta_1718107.docx`
4. Click "Загрузить"
5. Wait for completion

**Expected Results**:
- Second report appears in table
- Type: "Отчёт 2" or "REPORT_2"
- Status updates to "Обработан" when Celery task completes
- Reports table shows 2 rows

#### 5.4 Upload REPORT_3 (Competencies Report)

**Steps**:
1. Click "Загрузить отчёт" again
2. Select report type "Отчёт 3"
3. Choose file: `Batura_A.A._Biznes-Profil_Otchyot_po_kompetentsiyam_1718107.docx`
4. Click "Загрузить"
5. Wait for completion

**Expected Results**:
- Third report appears in table
- Type: "Отчёт 3" or "REPORT_3"
- Reports table shows 3 rows (all reports uploaded)
- Each report has independent status tracking

**Verification Points**:
- System prevents uploading duplicate report types for same participant
- Or allows overwriting with confirmation dialog
- Status transitions: "Загружается" → "Обработка" → "Обработан" or "Ошибка"

#### 5.5 Attempt to Upload Invalid File Type

**Steps**:
1. Click "Загрузить отчёт"
2. Select report type "Отчёт 1"
3. Attempt to select a .pdf or .txt file

**Expected Results**:
- File picker restricts to .docx only
- Or validation error appears: "Только файлы DOCX"

#### 5.6 Attempt to Upload Oversized File

**Preconditions**:
- Test file larger than 20 MB is available

**Steps**:
1. Click "Загрузить отчёт"
2. Select report type
3. Choose file larger than 20 MB
4. Attempt to upload

**Expected Results**:
- Validation error: "Максимум 20 МБ"
- Upload is prevented

#### 5.7 Verify Processing Status Updates

**Steps**:
1. After uploading a report, observe status column
2. Wait for Celery task to complete (may take 10-60 seconds depending on Vision processing)
3. Refresh page if needed

**Expected Results**:
- Status changes from "Обработка" to "Обработан"
- Or status shows "Ошибка" if extraction failed
- Status updates automatically via polling or WebSocket (if implemented)
- Or manual refresh shows updated status

---

### 6. Manual Metrics Entry

**Seed**: `e2e/seed.spec.ts`

**Preconditions**:
- User is logged in
- Participant "Батура Александр Александрович" exists
- At least one report is uploaded and processed (status: "Обработан")
- On participant detail page

#### 6.1 Navigate to Report Metrics Page

**Steps**:
1. On participant detail page, locate the uploaded report (e.g., REPORT_1)
2. Verify status is "Обработан"
3. Click button "Открыть" in the report's action column
4. Wait for navigation

**Expected Results**:
- URL changes to `/reports/{report_id}` or `/participants/{participant_id}/reports/{report_id}`
- Page displays report details:
  - Report type (REPORT_1, REPORT_2, or REPORT_3)
  - Upload date
  - Processing status
- Section "Извлечённые метрики" or "Метрики" is visible
- If Vision extraction succeeded, metrics are pre-filled with values and confidence scores
- If extraction failed or no metrics found, form is empty
- Edit/input controls are available for each metric

**Verification Points**:
- Source indicator displays: "LLM" (Vision) or "MANUAL"
- Confidence scores are shown (e.g., 0.85, 0.92)
- Low confidence metrics (< 0.8) are highlighted or flagged for review

#### 6.2 Review Auto-Extracted Metrics

**Steps**:
1. On report metrics page, review the list of metrics
2. Verify expected metrics are present based on report type:
   - Communicability (коммуникабельность)
   - Teamwork (работа в команде)
   - Responsibility (ответственность)
   - Leadership (лидерство)
   - Stress resistance (стрессоустойчивость)
   - Time management (тайм-менеджмент)
   - And others as defined in metric definitions

**Expected Results**:
- Each metric has a label (name)
- Each metric shows a numeric value (range 1.0 to 10.0)
- Confidence score is displayed (if available)
- Source indicator shows "LLM" or "MANUAL"

#### 6.3 Manually Enter/Correct Metric Values

**Assumption**: Metrics can be edited even if auto-extracted

**Steps**:
1. Locate metric input field for "Communicability" (коммуникабельность)
2. Clear existing value (if any)
3. Enter value: `7.5`
4. Locate metric input for "Teamwork" (работа в команде)
5. Enter value: `6.5`
6. Locate metric input for "Responsibility" (ответственность)
7. Enter value: `8.0`
8. Locate metric input for "Leadership" (лидерство)
9. Enter value: `7.0`
10. Locate metric input for "Stress resistance" (стрессоустойчивость)
11. Enter value: `7.5`
12. Locate metric input for "Time management" (тайм-менеджмент)
13. Enter value: `6.0`
14. Continue entering values for remaining metrics as needed
15. Click button "Сохранить" or "Сохранить метрики"
16. Wait for save confirmation

**Expected Results**:
- Toast notification: "Метрики сохранены успешно"
- Values are persisted to database (`extracted_metric` table)
- Source changes to "MANUAL" or remains as is with updated values
- Confidence score may be set to 1.0 for manual entries
- Page remains on report detail or redirects back to participant page

**Verification Points**:
- Input validation enforces range 1.0-10.0
- Decimal values are accepted (e.g., 7.5)
- Values outside range show error (e.g., 11.0 or 0.5)
- Save button is disabled until valid changes are made

#### 6.4 Enter Invalid Metric Values

**Steps**:
1. On metrics entry page, locate a metric input
2. Enter value: `15.0` (above max)
3. Attempt to save

**Expected Results**:
- Validation error: "Значение должно быть от 1 до 10"
- Save is prevented

**Steps**:
1. Clear field and enter value: `0.5` (below min)
2. Attempt to save

**Expected Results**:
- Validation error: "Значение должно быть от 1 до 10"
- Save is prevented

#### 6.5 Save Partial Metrics

**Steps**:
1. Enter values for only some metrics (e.g., 3 out of 10)
2. Leave other fields empty
3. Click "Сохранить"

**Expected Results**:
- Either:
  - A) System allows partial save (saves entered values)
  - B) Validation requires all metrics to be filled
- If partial save allowed, warning may appear about incomplete data
- Scoring calculation later may require all metrics

#### 6.6 Navigate Back to Participant Page

**Steps**:
1. After saving metrics, click "Назад" button or navigate via breadcrumbs
2. Verify return to participant detail page

**Expected Results**:
- URL returns to `/participants/{participant_id}`
- Reports list still shows all uploaded reports
- Metrics are saved and available for scoring

---

### 7. Calculate Score

**Seed**: `e2e/seed.spec.ts`

**Preconditions**:
- User is logged in
- Participant "Батура Александр Александрович" exists
- All three reports uploaded and metrics entered (from scenarios 5 and 6)
- On participant detail page

#### 7.1 Open Calculate Score Dialog

**Steps**:
1. On participant detail page, verify reports are present
2. Click button "Рассчитать пригодность"
3. Verify dialog opens

**Expected Results**:
- Dialog appears with heading "Рассчитать профессиональную пригодность"
- Combobox labeled "Профессиональная область" is present
- Info alert may appear: "Убедитесь, что у участника загружены и обработаны отчёты с метриками"
- If no reports uploaded, warning alert: "У участника нет загруженных отчётов"
- Button "Рассчитать" is initially disabled until activity selected

#### 7.2 Select Professional Activity

**Steps**:
1. In the dialog, click combobox "Профессиональная область"
2. Verify dropdown shows available professional activities
3. Verify option "Организация и проведение совещаний" is present
4. Verify code "meeting_facilitation" is shown as subtitle
5. Click option "Организация и проведение совещаний"
6. Verify button "Рассчитать" becomes enabled

**Expected Results**:
- Selected activity appears in combobox
- Professional activity options are loaded from database (`prof_activity` table)
- Each option shows name and code
- Button "Рассчитать" is now clickable

**Verification Points**:
- Dropdown loads all active professional activities
- Activities with no active weight tables may be disabled or show warning

#### 7.3 Calculate Suitability Score

**Steps**:
1. With "Организация и проведение совещаний" selected
2. Click button "Рассчитать"
3. Wait for calculation to complete

**Expected Results**:
- Dialog closes or shows loading indicator
- Calculation is performed (may call API endpoint: `POST /api/scoring/calculate`)
- API uses `ScoringService.calculate_score()` with:
  - Participant ID
  - Professional activity code: `meeting_facilitation`
  - Fetches extracted metrics from database
  - Loads active weight table for `meeting_facilitation`
  - Computes: `score_pct = Σ(metric_value × weight) × 10`
  - Expected score ≈ 72% based on sample metrics:
    - Communicability 7.5 × weight
    - Teamwork 6.5 × weight
    - Responsibility 8.0 × weight
    - etc.
- Toast notification: "Расчёт выполнен успешно"
- Scoring result is saved to database (`scoring_result` table)
- Page may show new "Результаты" section or update UI with score

**Verification Points**:
- Calculation requires all necessary metrics to be present
- If metrics are missing, error appears: "Недостаточно данных для расчёта"
- Score is quantized to 0.01 precision (e.g., 72.34%)
- Recommendations are generated (strengths and development areas)

#### 7.4 Verify Calculation Error Handling

**Preconditions**:
- Participant has no metrics entered

**Steps**:
1. On participant with no reports or metrics, click "Рассчитать пригодность"
2. Select professional activity
3. Click "Рассчитать"

**Expected Results**:
- Error message: "У участника нет метрик для расчёта"
- Or dialog prevents calculation with disabled button and warning

**Steps** (Missing metrics):
1. Participant has some metrics but not all required for selected activity
2. Attempt calculation

**Expected Results**:
- Error: "Не все метрики доступны для расчёта"
- Missing metrics are listed

#### 7.5 View Calculation Results

**Steps**:
1. After successful calculation, verify results are displayed on participant page
2. Look for "Результаты профпригодности" section or similar

**Expected Results**:
- Section shows:
  - Professional activity: "Организация и проведение совещаний"
  - Score percentage: ~72% (or calculated value)
  - Calculation date/time
  - Action buttons: "Просмотреть JSON", "Скачать HTML"
- Results table may show multiple scoring results if calculated for different activities

---

### 8. View Final Report JSON

**Seed**: `e2e/seed.spec.ts`

**Preconditions**:
- User is logged in
- Participant "Батура Александр Александрович" exists
- Scoring calculation completed for "Организация и проведение совещаний" (from scenario 7.3)

#### 8.1 Open JSON Report Dialog/Page

**Steps**:
1. On participant detail page, locate scoring results section
2. Find result for "Организация и проведение совещаний" (meeting_facilitation)
3. Click button "Просмотреть JSON"
4. Wait for dialog or new page to load

**Expected Results**:
- Dialog or modal appears with heading "Финальный отчёт (JSON)"
- Or new page/tab opens showing JSON content
- JSON structure is displayed (may be formatted with syntax highlighting)

#### 8.2 Verify JSON Report Structure

**Steps**:
1. In the JSON view, verify presence of required fields:
   - `participant_id` (UUID string)
   - `participant_name` (string: "Батура Александр Александрович")
   - `activity_code` (string: "meeting_facilitation")
   - `activity_name` (string: "Организация и проведение совещаний")
   - `score_pct` (number: approximately 72.0)
   - `calculated_at` (ISO timestamp)
   - `strengths` (array of objects)
   - `dev_areas` (array of objects, development areas)
   - `metrics_table` (array of metric objects)

**Expected Results - Field Details**:
- `participant_id`: matches participant UUID
- `score_pct`: decimal value, expected ≈ 72.0 or similar
- `strengths`: array with 3-5 elements
  - Each element has: `metric_code`, `metric_name`, `value`, `description`
  - Example: `{"metric_code": "responsibility", "metric_name": "Ответственность", "value": 8.0, "description": "..."}`
- `dev_areas`: array with 3-5 elements (areas for development)
  - Similar structure to strengths
  - Contains metrics with lower values or high improvement potential
- `metrics_table`: array of all metrics used in calculation
  - Each element: `metric_code`, `metric_name`, `value`, `weight`, `weighted_score`
  - Example: `{"metric_code": "communicability", "metric_name": "Коммуникабельность", "value": 7.5, "weight": 0.15, "weighted_score": 1.125}`

**Verification Points**:
- JSON is valid (can be parsed)
- `strengths.length >= 3 && strengths.length <= 5`
- `dev_areas.length >= 3 && dev_areas.length <= 5`
- `metrics_table` includes all metrics from weight table
- Sum of weights in `metrics_table` equals 1.0
- Calculated `score_pct` matches: `Σ(value × weight) × 10`

#### 8.3 Verify Strengths Content

**Steps**:
1. Locate `strengths` array in JSON
2. Verify each strength has:
   - High metric value (typically >= 7.0)
   - Descriptive text explaining why it's a strength
   - Metric is relevant to selected professional activity

**Expected Results**:
- Strengths are top-performing metrics for the participant
- Descriptions are meaningful (not generic placeholders)
- Example strength:
  ```json
  {
    "metric_code": "responsibility",
    "metric_name": "Ответственность",
    "value": 8.0,
    "description": "Высокий уровень ответственности способствует эффективному выполнению задач и соблюдению обязательств."
  }
  ```

#### 8.4 Verify Development Areas Content

**Steps**:
1. Locate `dev_areas` array in JSON
2. Verify each development area has:
   - Lower metric value or improvement opportunity
   - Constructive recommendation for improvement
   - Relevance to professional activity

**Expected Results**:
- Development areas identify opportunities for growth
- Recommendations are actionable
- Example:
  ```json
  {
    "metric_code": "time_management",
    "metric_name": "Тайм-менеджмент",
    "value": 6.0,
    "description": "Развитие навыков планирования и приоритизации поможет повысить эффективность работы."
  }
  ```

#### 8.5 Copy or Download JSON

**Steps**:
1. If "Копировать" button is present, click it
2. Or if "Скачать JSON" button is present, click it

**Expected Results**:
- If copy: JSON is copied to clipboard, toast: "JSON скопирован в буфер обмена"
- If download: file downloads with name like `final_report_{participant_id}_{activity_code}.json`
- File contents match displayed JSON

---

### 9. Download Final Report HTML

**Seed**: `e2e/seed.spec.ts`

**Preconditions**:
- User is logged in
- Scoring calculation completed for participant (from scenario 7.3)
- On participant detail page

#### 9.1 Download HTML Report

**Steps**:
1. On participant detail page, locate scoring results section
2. Find result for "Организация и проведение совещаний"
3. Click button "Скачать HTML"
4. Wait for download to start

**Expected Results**:
- File download initiates
- Filename format: `final_report_{participant_name}_{activity_code}.html` or similar
- Example: `final_report_Batura_A.A._meeting_facilitation.html`
- File is saved to browser's download folder

**Verification Points**:
- HTTP request is sent: `GET /api/participants/{participant_id}/final-report?activity_code=meeting_facilitation&format=html`
- Response `Content-Type`: `text/html; charset=utf-8`
- Response status: 200 OK
- File size is reasonable (typically 20-100 KB depending on template)

#### 9.2 Verify HTML Report Content

**Steps**:
1. Open downloaded HTML file in browser
2. Verify document structure:
   - Page title: "Финальный отчёт - Батура Александр Александрович"
   - Header section with participant info
   - Scoring summary section
   - Strengths section (3-5 items)
   - Development areas section (3-5 items)
   - Metrics table with all metric values and weights
   - Footer with generation date/time

**Expected Results - HTML Structure**:
- Professional HTML layout (not raw JSON)
- CSS styles applied (template may include Bootstrap or custom CSS)
- Sections:
  - **Header**: Participant name, birth date, external ID
  - **Overview**: Professional activity, score percentage (e.g., "72%"), calculation date
  - **Strengths**: Bulleted or numbered list with descriptions
  - **Development Areas**: Bulleted or numbered list with recommendations
  - **Metrics Table**: Columns: Metric Name, Value, Weight, Weighted Score
  - **Footer**: "Сгенерировано: {timestamp}", system version

**Verification Points**:
- HTML is well-formed (valid syntax)
- Text is readable and properly encoded (UTF-8, no mojibake)
- Score is displayed prominently (e.g., in large font or colored badge)
- Strengths and dev areas match JSON content
- Metrics table includes all metrics from calculation
- Visual design is professional (suitable for business reports)

#### 9.3 Verify HTML Report Rendering

**Steps**:
1. Open HTML file in different browsers (Chrome, Firefox, Safari if possible)
2. Check for rendering consistency
3. Verify no missing images or broken styles

**Expected Results**:
- Report renders correctly across browsers
- No JavaScript errors in console
- Print preview shows good layout (report is printable)
- Colors and fonts are consistent

#### 9.4 Download Report for Different Activity (Edge Case)

**Preconditions**:
- Participant has scoring results for multiple professional activities

**Steps**:
1. Calculate score for a second activity (if available)
2. Click "Скачать HTML" for the second activity

**Expected Results**:
- Different HTML file downloads
- Filename includes second activity code
- Content reflects second activity's scoring results

---

## Test Execution Notes

### Asynchronous Processing Considerations

**Celery Task Handling**:
- In `test` or `ci` environment, Celery tasks run synchronously (eager mode) due to `CELERY_TASK_ALWAYS_EAGER=1`
- In `dev` environment with Redis/RabbitMQ, tasks are async:
  - Report extraction may take 10-60 seconds
  - Status updates require polling or page refresh
  - Tests should implement retry logic or wait strategies

**Wait Strategies**:
- Use `await page.waitForSelector()` for dynamic content
- Use `await page.waitForResponse()` to wait for API calls
- For status updates, implement polling with timeout:
  ```javascript
  // Poll status until "Обработан" or timeout (60s)
  await page.waitForFunction(
    () => document.querySelector('.status-cell')?.textContent === 'Обработан',
    { timeout: 60000 }
  );
  ```

### Test Data Management

**Database State**:
- Each test scenario should use `e2e/seed.spec.ts` to ensure fresh state
- Use transactions or database cleanup hooks between tests
- For isolation, consider creating unique test users per scenario (e.g., `testuser_${timestamp}@example.com`)

**File Fixtures**:
- Test DOCX files are located at `/Users/maksim/git_projects/workers-prof/e2e/fixtures/`
- Verify files exist before test run
- Files contain real business report data with embedded tables/images

### UI Element Selectors

**Recommended Selector Strategy**:
1. Prefer `role` selectors: `page.getByRole('button', { name: 'Загрузить' })`
2. Use `placeholder` for textboxes: `page.getByPlaceholder('Введите email')`
3. Use `text` for exact matches: `page.getByText('Регистрация успешна!')`
4. Avoid CSS selectors or XPath unless necessary (brittle)

**Dynamic Content**:
- Some elements may render after API calls
- Use `waitForSelector` or `waitForLoadState('networkidle')`
- Toast notifications may auto-dismiss after 3-5 seconds (capture quickly)

### Expected Score Calculation

**Example Calculation for "meeting_facilitation"**:
- Assume weight table for `meeting_facilitation` has:
  - `communicability`: weight 0.20
  - `teamwork`: weight 0.15
  - `responsibility`: weight 0.15
  - `leadership`: weight 0.20
  - `stress_resistance`: weight 0.15
  - `time_management`: weight 0.15
  - Sum of weights = 1.0

- With sample metrics:
  - Communicability: 7.5
  - Teamwork: 6.5
  - Responsibility: 8.0
  - Leadership: 7.0
  - Stress resistance: 7.5
  - Time management: 6.0

- Calculation:
  ```
  score_pct = (7.5×0.20 + 6.5×0.15 + 8.0×0.15 + 7.0×0.20 + 7.5×0.15 + 6.0×0.15) × 10
            = (1.5 + 0.975 + 1.2 + 1.4 + 1.125 + 0.9) × 10
            = 7.1 × 10
            = 71.0%
  ```

- Expected `score_pct` ≈ 71.0% (may vary based on actual weight table)

**Verification**:
- Test should assert `score_pct` is within expected range (e.g., 70-75%)
- If exact weights are known, calculate expected value and assert with tolerance (±0.5%)

---

## Edge Cases and Error Scenarios

### User Registration Edge Cases

1. **Email Already Exists**: Attempt registration with existing email
2. **SQL Injection**: Enter `'; DROP TABLE users; --` in email field (should be sanitized)
3. **XSS Attack**: Enter `<script>alert('XSS')</script>` in name field (should be escaped)
4. **Unicode Characters**: Enter Cyrillic email like `тест@тест.рф` (may or may not be supported)
5. **Very Long Password**: Enter 1000-character password (should be limited)

### Report Upload Edge Cases

1. **Corrupted DOCX**: Upload a DOCX file with invalid ZIP structure
2. **Empty DOCX**: Upload a DOCX with no content
3. **DOCX Without Images**: Upload report without embedded tables/images (no numeric data to extract)
4. **Duplicate Upload**: Upload same report type twice for same participant
5. **Concurrent Uploads**: Upload multiple reports simultaneously (race condition test)

### Metric Entry Edge Cases

1. **Negative Values**: Enter `-5.0` (should be rejected)
2. **Very Large Decimals**: Enter `7.123456789` (should round to precision limit)
3. **Non-Numeric Input**: Enter `abc` or `seven` (should show validation error)
4. **Empty Fields**: Leave all fields empty and attempt save
5. **Scientific Notation**: Enter `1e1` (equal to 10.0) - should be handled or rejected

### Scoring Edge Cases

1. **Missing Metrics**: Calculate score with only partial metrics available
2. **No Weight Table**: Select activity with no active weight table
3. **Weight Sum ≠ 1.0**: Backend error if weight table is misconfigured
4. **Extreme Metric Values**: All metrics at 1.0 or all at 10.0 (boundary testing)
5. **Concurrent Calculations**: Calculate score multiple times rapidly (idempotency test)

### Final Report Edge Cases

1. **Large Report**: Participant with 100+ metrics (stress test HTML generation)
2. **Special Characters in Name**: Participant name with `<>&"'` characters (HTML escaping)
3. **Missing Recommendations**: If AI recommendation generation fails
4. **Very Long Descriptions**: Strengths/dev areas with 1000+ character descriptions

---

## Success Criteria

### Test Pass Conditions

A test scenario passes if:
1. All steps execute without errors
2. All expected results are observed
3. All verification points are confirmed
4. No unexpected errors appear in browser console or backend logs
5. Database state is consistent after scenario completion

### Coverage Goals

- **Functional Coverage**: All critical path scenarios (1-9) pass
- **Happy Path**: 100% of scenarios 1.1, 2.1, 3.1, 4.1, 5.2-5.4, 6.3, 7.3, 8.2, 9.1 pass
- **Error Handling**: At least 70% of edge case scenarios pass
- **Cross-Browser**: Tests pass in Chrome (primary) and Firefox (secondary)

### Performance Benchmarks

- **Page Load**: Any page loads within 3 seconds
- **Report Upload**: File upload completes within 10 seconds (excluding processing)
- **Vision Processing**: Report extraction completes within 60 seconds (in dev mode)
- **Scoring Calculation**: Score calculation completes within 5 seconds
- **HTML Report Download**: Download initiates within 2 seconds

---

## Appendix

### Test Environment Setup

**Prerequisites**:
```bash
# Start application stack
docker-compose up -d

# Or run locally
cd api-gateway
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 9187

# Start Celery worker (separate terminal)
celery -A app.core.celery_app.celery_app worker -l info
```

**Seed Test Data**:
```bash
# Run seed script to create admin user and test data
cd api-gateway
python setup_test_data.py
```

**Run Playwright Tests**:
```bash
# From project root
npm run test:e2e

# Or run specific test
npx playwright test e2e/critical-path.spec.ts
```

### Troubleshooting

**Issue**: "У участника нет загруженных отчётов" warning persists after upload
- **Cause**: Celery task not running or failed silently
- **Fix**: Check Celery worker logs, ensure Redis/RabbitMQ is running, verify `CELERY_TASK_ALWAYS_EAGER=1` in test env

**Issue**: "Недостаточно данных для расчёта" error when calculating score
- **Cause**: Missing required metrics or metrics not saved
- **Fix**: Verify all metrics from weight table are present in `extracted_metric` for participant

**Issue**: JSON report shows empty `strengths` or `dev_areas`
- **Cause**: Recommendation generation failed or disabled
- **Fix**: Check `AI_RECOMMENDATIONS_ENABLED=1` in env, verify Gemini API keys, check backend logs

**Issue**: HTML download returns 404
- **Cause**: Scoring result not found or activity code mismatch
- **Fix**: Verify `scoring_result` exists in database for participant + activity, check query params

### Test Data Reference

**Admin User**:
- Email: `admin@test.com`
- Password: `admin123`
- Role: ADMIN
- Approved: true

**Test Participant**:
- Full Name: `Батура Александр Александрович`
- Birth Date: `1985-06-15`
- External ID: `BATURA_AA_TEST`

**Professional Activity**:
- Code: `meeting_facilitation`
- Name: `Организация и проведение совещаний`

**Report Files**:
- REPORT_1: `Batura_A.A._Biznes-Profil_Biznes-otchyot_1718107.docx`
- REPORT_2: `Batura_A.A._Biznes-Profil_Otchyot_dlya_respondenta_1718107.docx`
- REPORT_3: `Batura_A.A._Biznes-Profil_Otchyot_po_kompetentsiyam_1718107.docx`

---

**Document Version**: 1.0
**Date**: 2025-11-09
**Author**: Test Planning Team
**Status**: Ready for Implementation
