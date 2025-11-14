# Workers-Prof Application - Detailed Test Plan for Scenarios 6-9

## Document Overview

**Purpose**: This document provides comprehensive test scenarios for the final four critical path steps (6-9) of the Workers-Prof application, focusing on manual metrics entry, score calculation, and final report viewing/download features.

**Scope**: Scenarios 6 (Manual Metrics Entry), 7 (Calculate Score), 8 (View Final Report JSON), and 9 (Download Final Report HTML)

**Target Audience**: QA Engineers, Test Automation Developers, Manual Testers

**Date**: 2025-11-09

**Version**: 1.0

---

## Application Context

The **Workers-Prof** application is a competency management system that automates professional suitability assessment. The application provides:

- Automated extraction of metrics from DOCX reports using AI Vision
- Manual entry and correction of metrics through an intuitive interface
- Weighted score calculation based on professional activity requirements
- Generation of comprehensive final reports in JSON and HTML formats

### Test Environment

- **Application URL**: http://localhost:9187
- **Admin Credentials**: admin@test.com / admin123
- **Test Fixtures Location**: `/Users/maksim/git_projects/workers-prof/e2e/fixtures/`
- **Test File**: `Batura_A.A._Biznes-Profil_Biznes-otchyot_1718107.docx` (REPORT_1)
- **Professional Activity**: "Организация и проведение совещаний" (meeting_facilitation)

### Prerequisites for Scenarios 6-9

Before executing these scenarios, ensure:

1. User is logged in as admin (admin@test.com / admin123)
2. Participant "Батура Александр Александрович" exists (External ID: BATURA_AA_TEST, DOB: 1985-06-15)
3. At least one report (REPORT_1) has been uploaded and is in "Загружен" (Uploaded) status
4. You are on the participant detail page at `/participants/{participant_id}`

---

## Scenario 6: Manual Metrics Entry

### Overview

This scenario validates the manual metrics entry interface, which allows users to view automatically extracted metrics and manually enter or correct metric values when automatic extraction fails or produces low-confidence results.

### Preconditions

- User is logged in as admin@test.com
- Participant exists with at least one uploaded report (status: "Загружен")
- Currently on participant detail page showing reports table
- Report row shows action buttons: "Скачать", "Извлечь метрики", "Метрики", "Удалить"

### Test Data

**13 Metrics to be Entered** (all values must be between 1.0 and 10.0):

1. **Коммуникабельность** (Communicability): 7.5
2. **Комплексное решение проблем** (Complex Problem Solving): 7.0
3. **Обработка информации** (Information Processing): 8.0
4. **Лидерство** (Leadership): 7.0
5. **Конфликтность (низкая)** (Low Conflict): 6.5
6. **Моральность / Нормативность** (Morality/Normativity): 8.0
7. **Невербальная логика** (Non-verbal Logic): 6.0
8. **Организованность** (Organization): 7.5
9. **Ответственность** (Responsibility): 8.0
10. **Стрессоустойчивость** (Stress Resistance): 7.5
11. **Роль «Душа команды» (Белбин)** (Team Soul Role - Belbin): 6.5
12. **Командность** (Teamwork): 7.0
13. **Лексика** (Vocabulary): 6.5

---

### 6.1 Open Metrics Dialog (View-Only Mode)

**Objective**: Navigate to the metrics dialog and verify initial state before editing.

**Steps**:

1. On participant detail page, locate the reports table
2. Find the row for "Отчёт 1" (REPORT_1)
3. Verify the report status shows "Загружен" (Uploaded)
4. In the "Действия" (Actions) column, click button **"Метрики"**
5. Wait for dialog to open

**Expected Results**:

- Dialog opens with heading **"Метрики отчёта"** (Report Metrics)
- Close button (X) is visible in top-right corner
- Section header shows **"Ручной ввод метрик"** (Manual Metrics Entry)
- Button **"Редактировать"** (Edit) is displayed and enabled
- Blue alert box appears with message: **"Метрики для этого отчёта ещё не извлечены. Вы можете ввести их вручную."** (Metrics for this report have not been extracted yet. You can enter them manually.)
- All 13 metric fields are listed in a grid layout (4 columns on desktop):
  - Row 1: Коммуникабельность, Комплексное решение проблем, Обработка информации, Лидерство
  - Row 2: Конфликтность (низкая), Моральность / Нормативность, Невербальная логика, Организованность
  - Row 3: Ответственность, Стрессоустойчивость, Роль «Душа команды» (Белбин), Командность
  - Row 4: Лексика
- All metric fields are currently empty or disabled (view-only mode)
- No "Сохранить" (Save) or "Отмена" (Cancel) buttons are visible yet

**UI Element Locators**:

- Dialog: `dialog[role="dialog"]` with heading "Метрики отчёта"
- Close button: `button` with aria-label "Close this dialog" containing icon
- Edit button: `button` with text "Редактировать"
- Alert message: `alert` element with info icon
- Metric fields: `group` elements with labels containing metric names

**Verification Points**:

- Dialog is modal and overlays the participant detail page
- All 13 metrics are visible without scrolling (on typical desktop resolution)
- Alert message clearly indicates metrics need to be entered manually
- Edit button is the primary action available

---

### 6.2 Enable Edit Mode

**Objective**: Activate the editing interface to allow metric value entry.

**Steps**:

1. In the metrics dialog (from step 6.1), verify "Редактировать" button is visible
2. Click button **"Редактировать"**
3. Observe UI changes

**Expected Results**:

- The "Редактировать" button disappears
- Two new buttons appear in the top-right section of the dialog:
  - **"Отмена"** (Cancel) - secondary/gray button
  - **"Сохранить"** (Save) - primary/blue button
- The alert message remains visible: "Метрики для этого отчёта ещё не извлечены. Вы можете ввести их вручную."
- Metric fields remain displayed in the same grid layout

**Note**: Based on current implementation, input fields may not be visually rendered in edit mode. The UI may display metric labels only. This is a known UI issue that should be documented as a defect. For testing purposes:

- If input fields appear: Proceed with metric entry as described in section 6.3
- If input fields do NOT appear: Document as **BUG-001** (see section 6.8 below) and mark scenario as blocked

**UI Element Locators**:

- Cancel button: `button` with text "Отмена"
- Save button: `button` with text "Сохранить"

**Verification Points**:

- Edit mode is clearly indicated by presence of Save/Cancel buttons
- The transition from view mode to edit mode is smooth (no page refresh)

---

### 6.3 Enter Valid Metric Values (IDEAL SCENARIO - requires input fields)

**Objective**: Manually enter all 13 metric values with valid data.

**Precondition**: Input fields are rendered and accessible (this may not be the case in current implementation - see 6.2 Note).

**Steps**:

1. In edit mode, locate the first metric field **"Коммуникабельность (балл)"**
2. If input field is present, click on it to focus
3. Type value: **7.5**
4. Press Tab key to move to next field
5. Repeat for all 13 metrics using the test data values listed above:
   - Коммуникабельность: 7.5
   - Комплексное решение проблем: 7.0
   - Обработка информации: 8.0
   - Лидерство: 7.0
   - Конфликтность (низкая): 6.5
   - Моральность / Нормативность: 8.0
   - Невербальная логика: 6.0
   - Организованность: 7.5
   - Ответственность: 8.0
   - Стрессоустойчивость: 7.5
   - Роль «Душа команды» (Белбин): 6.5
   - Командность: 7.0
   - Лексика: 6.5
6. After all values are entered, verify all fields show correct values
7. Click button **"Сохранить"**
8. Wait for save operation to complete

**Expected Results**:

- Each input field accepts the numeric value
- Values are displayed with proper decimal formatting (e.g., "7.5" not "7,5")
- No validation errors appear during entry (all values are within range 1.0-10.0)
- After clicking "Сохранить":
  - Toast/alert notification appears: **"Метрики сохранены успешно"** (Metrics saved successfully) or similar
  - Dialog either closes automatically or returns to view-only mode
  - If dialog closes, participant detail page is visible again
  - If dialog remains open, "Сохранить" and "Отмена" buttons are replaced with "Редактировать" button

**UI Element Locators**:

- Input fields: `input[type="number"]` or `input[inputmode="decimal"]` within each metric group
- Save button: `button` with text "Сохранить"
- Success toast: `alert` or toast notification with success message

**Verification Points**:

- All 13 metrics are persisted to database (`extracted_metric` table)
- Each metric record has:
  - `metric_code`: corresponding metric code (e.g., "communicability")
  - `value`: entered decimal value (e.g., 7.5)
  - `source`: "MANUAL" (indicating manual entry)
  - `confidence`: 1.0 (manual entries have 100% confidence)
- Database query to verify:
  ```sql
  SELECT metric_code, value, source, confidence
  FROM extracted_metric
  WHERE report_id = '{report_id}'
  ORDER BY metric_code;
  ```
- Expected 13 rows with matching values

---

### 6.4 Validate Metric Value Range (Boundary Testing)

**Objective**: Verify input validation enforces the 1.0-10.0 range requirement.

**Steps**:

1. Open metrics dialog and enable edit mode (repeat 6.1-6.2)
2. Locate the "Коммуникабельность" input field
3. Attempt to enter value: **11.0** (above maximum)
4. Try to move to next field or click "Сохранить"
5. Observe validation behavior
6. Clear the field
7. Attempt to enter value: **0.5** (below minimum)
8. Try to move to next field or click "Сохранить"
9. Observe validation behavior
10. Clear the field
11. Attempt to enter value: **-3.0** (negative value)
12. Observe validation behavior

**Expected Results**:

For each invalid value:

- Input validation prevents the value from being accepted, OR
- Field shows error state (red border, error icon), AND
- Error message appears: **"Значение должно быть от 1 до 10"** (Value must be between 1 and 10) or similar
- "Сохранить" button is either:
  - Disabled (grayed out) when invalid values are present, OR
  - Enabled but clicking it triggers validation error toast
- Invalid values are not persisted to database

**Verification Points**:

- Validation is applied on blur (when leaving field)
- Validation is applied on submit (when clicking "Сохранить")
- Clear, user-friendly error messages are displayed
- Decimal precision is supported (e.g., 7.5, 8.25 are valid)
- Integer values are valid (e.g., 7 is treated as 7.0)

---

### 6.5 Test Empty Field Handling

**Objective**: Verify behavior when some metrics are left empty.

**Steps**:

1. Open metrics dialog and enable edit mode
2. Enter values for only 5 metrics (e.g., first 5 in the list):
   - Коммуникабельность: 7.5
   - Комплексное решение проблем: 7.0
   - Обработка информации: 8.0
   - Лидерство: 7.0
   - Конфликтность (низкая): 6.5
3. Leave the remaining 8 metrics empty (no value entered)
4. Click button **"Сохранить"**
5. Observe system response

**Expected Results** (One of two behaviors):

**Option A - Partial Save Allowed**:
- Save operation succeeds
- Toast notification: "Метрики сохранены успешно"
- Warning message may appear: "Некоторые метрики не заполнены" (Some metrics are not filled)
- Only the 5 entered metrics are saved to database
- Missing metrics have no records in `extracted_metric` table

**Option B - Complete Data Required**:
- Save operation fails
- Validation error appears: "Заполните все обязательные метрики" (Fill all required metrics) or similar
- Dialog remains in edit mode
- No data is persisted until all 13 metrics are filled

**Verification Points**:

- Application clearly communicates whether partial entry is allowed
- If partial save is allowed, scoring calculation later requires all metrics (scenario 7 will fail with appropriate error)
- If complete data is required, all 13 fields must be marked as required with visual indicators (asterisks, labels)

---

### 6.6 Test Cancel Functionality

**Objective**: Verify that canceling edit mode discards unsaved changes.

**Steps**:

1. Open metrics dialog and enable edit mode
2. Enter values for several metrics:
   - Коммуникабельность: 9.0
   - Обработка информации: 8.5
   - Лидерство: 7.5
3. Click button **"Отмена"** (Cancel)
4. Observe system response
5. Re-open the metrics dialog (click "Метрики" button again)
6. Check if previously entered values are present

**Expected Results**:

- After clicking "Отмена":
  - Dialog either closes immediately, OR
  - Dialog returns to view-only mode (Save/Cancel buttons replaced with "Редактировать")
- Unsaved changes are discarded
- No data is persisted to database
- When re-opening metrics dialog:
  - All fields are empty (if no previous save occurred)
  - Or fields show previously saved values (if metrics were saved in earlier session)
- No toast notification appears (silent cancel)

**UI Element Locators**:

- Cancel button: `button` with text "Отмена"

**Verification Points**:

- Cancel operation does not trigger any API calls (verify in Network tab)
- User is not prompted for confirmation (data loss warning) - this may be a UX improvement opportunity
- State resets to pre-edit mode

---

### 6.7 Test Non-Numeric Input Handling

**Objective**: Verify input validation rejects non-numeric values.

**Steps**:

1. Open metrics dialog and enable edit mode
2. Locate the "Коммуникабельность" input field
3. Attempt to type alphabetic characters: **abc**
4. Observe field behavior
5. Attempt to type special characters: **@#$**
6. Attempt to type mixed content: **7abc**
7. Try to save

**Expected Results**:

- Input field prevents non-numeric characters from being entered (characters are not accepted/displayed), OR
- Non-numeric characters are entered but validation error appears on blur/submit
- Error message: "Введите числовое значение" (Enter a numeric value) or similar
- Invalid input is not persisted

**Verification Points**:

- Input field type is `number` or has `inputmode="decimal"` attribute
- Browser-native validation prevents non-numeric input in `number` type fields
- Keyboard on mobile devices shows numeric keypad for easier entry

---

### 6.8 Known Issues and Workarounds

**BUG-001: Metric Input Fields Not Rendered in Edit Mode**

**Description**:
When clicking "Редактировать" button in the metrics dialog, the expected input fields for metric entry are not rendered. The UI shows only metric labels without editable input controls.

**Observed Behavior**:
- Edit mode is activated (Save/Cancel buttons appear)
- Metric field groups are displayed
- No visible `<input>` elements are present in the DOM
- Manual metric entry is not possible via the UI

**Expected Behavior**:
- Each metric group should contain a numeric input field
- Input fields should be enabled and focusable
- Users should be able to type values using keyboard or paste from clipboard

**Impact**:
- Scenario 6 is blocked
- Manual metrics entry feature is non-functional
- Users cannot proceed with score calculation if automatic extraction fails

**Workaround**:
- Use API to manually insert metrics via POST request to `/api/metrics/` endpoint
- Or use database admin tool to insert records into `extracted_metric` table
- Or run automatic extraction ("Извлечь метрики" button) and expect successful Vision extraction

**Recommended Fix**:
- Frontend: Review `MetricsDialog.vue` component to ensure input fields are rendered in edit mode
- Ensure v-model bindings are correct for each metric in the form
- Check if conditional rendering (v-if/v-show) is preventing input display
- Verify Element Plus form components are properly imported and configured

**Testing Priority**: **P0 - Critical** (blocks critical path)

**Status**: Open - Requires frontend code review

---

### 6.9 Close Metrics Dialog

**Objective**: Verify dialog can be closed after metrics are saved.

**Steps**:

1. After successfully saving metrics (scenario 6.3), verify dialog state
2. If dialog is still open, click the **X** (close) button in top-right corner
3. Alternatively, press **Escape** key on keyboard
4. Observe system response

**Expected Results**:

- Dialog closes smoothly (fade-out animation may occur)
- Participant detail page is visible again
- Reports table still shows the report row with "Метрики" button
- If metrics were saved, clicking "Метрики" again should display saved values in view-only mode

**UI Element Locators**:

- Close button: `button` with aria-label "Close this dialog" or class containing "el-dialog__close"

**Verification Points**:

- Close button works
- Escape key works (keyboard accessibility)
- Clicking outside dialog (on backdrop) may also close it, depending on implementation
- No unsaved data loss warnings appear (all data was already saved in 6.3)

---

## Scenario 7: Calculate Professional Suitability Score

### Overview

This scenario validates the score calculation feature, which computes a weighted suitability score based on participant metrics and professional activity requirements.

### Preconditions

- User is logged in as admin@test.com
- Participant exists with completed metrics (from scenario 6)
- Currently on participant detail page
- All 13 metrics have been entered and saved to database

### Test Data

**Professional Activity**:
- **Name**: Организация и проведение совещаний
- **Code**: meeting_facilitation

**Expected Weight Table** (example - actual weights may vary):
- Коммуникабельность: 0.15
- Комплексное решение проблем: 0.08
- Обработка информации: 0.07
- Лидерство: 0.12
- Конфликтность (низкая): 0.08
- Моральность / Нормативность: 0.07
- Невербальная логика: 0.06
- Организованность: 0.09
- Ответственность: 0.10
- Стрессоустойчивость: 0.08
- Роль «Душа команды» (Белбин): 0.04
- Командность: 0.04
- Лексика: 0.02

*Note: Sum of weights must equal 1.0*

---

### 7.1 Open Score Calculation Dialog

**Objective**: Navigate to the calculation dialog and verify initial state.

**Steps**:

1. On participant detail page, verify participant info is displayed
2. Verify participant name: "Батура Александр Александрович"
3. Locate button **"Рассчитать пригодность"** in the page header area (next to "Назад" button)
4. Click button **"Рассчитать пригодность"**
5. Wait for dialog to open

**Expected Results**:

- Dialog opens with heading **"Рассчитать профессиональную пригодность"** (Calculate Professional Suitability)
- Close button (X) is visible in top-right corner
- Form contains:
  - Label: **"*Профессиональная область"** (Professional Area) - asterisk indicates required field
  - Combobox/dropdown with placeholder text: **"Выберите область"** (Select area)
  - Blue info alert with icon and message: **"Убедитесь, что у участника загружены и обработаны отчёты с метриками"** (Ensure the participant has uploaded and processed reports with metrics)
- Dialog footer contains two buttons:
  - **"Отмена"** (Cancel) - secondary/gray button
  - **"Рассчитать"** (Calculate) - primary/blue button, **initially disabled** (grayed out)

**UI Element Locators**:

- Dialog: `dialog[role="dialog"]` with heading "Рассчитать профессиональную пригодность"
- Close button: `button` with aria-label "Close this dialog"
- Dropdown: `combobox` with label "*Профессиональная область"
- Alert: `alert` element with info icon
- Cancel button: `button` with text "Отмена"
- Calculate button: `button` with text "Рассчитать"` and `disabled` attribute

**Verification Points**:

- Dialog is modal and overlays the participant page
- Professional area dropdown is the only input required
- Info alert clearly communicates prerequisites
- Calculate button is disabled until professional area is selected

---

### 7.2 View Available Professional Activities

**Objective**: Verify that professional activities are loaded and displayed correctly in the dropdown.

**Steps**:

1. In the calculation dialog (from 7.1), click on the **"Профессиональная область"** dropdown
2. Wait for dropdown menu to expand
3. Observe the list of available options

**Expected Results**:

- Dropdown expands showing a list of professional activities
- At minimum, the following activity is visible:
  - **Primary text**: "Организация и проведение совещаний" (larger font)
  - **Secondary text/tag**: "meeting_facilitation" (smaller font, gray color)
- Additional professional activities may be listed if configured in the system
- Dropdown options are formatted with:
  - Activity name (in Russian)
  - Activity code (in English, lowercase with underscores)
- Options are clickable/selectable

**UI Element Locators**:

- Dropdown menu: `listbox` role or Element Plus dropdown component
- Option: `option` role with text "Организация и проведение совещаний"
- Activity code tag: `generic` or `span` with text "meeting_facilitation"

**Verification Points**:

- Professional activities are fetched from `prof_activity` table via API
- API endpoint: `GET /api/prof-activities` or embedded in page load
- Each activity has:
  - `code`: unique identifier (e.g., "meeting_facilitation")
  - `name`: display name (e.g., "Организация и проведение совещаний")
  - `is_active`: true (only active activities are shown)
- Dropdown is searchable/filterable if many activities exist

---

### 7.3 Select Professional Activity "meeting_facilitation"

**Objective**: Select the target professional activity for score calculation.

**Steps**:

1. With dropdown expanded (from 7.2), locate option **"Организация и проведение совещаний"**
2. Verify the code "meeting_facilitation" is displayed below the name
3. Click on the option to select it
4. Observe UI changes

**Expected Results**:

- Dropdown collapses after selection
- Selected activity is displayed in the combobox field: **"Организация и проведение совещаний"**
- The blue info alert remains visible (no change)
- **"Рассчитать"** button becomes **enabled** (blue, clickable)
  - Button is no longer grayed out
  - Clicking it will trigger the calculation

**UI Element Locators**:

- Selected value in combobox: Text displays "Организация и проведение совещаний"
- Calculate button: `button` with text "Рассчитать", **no longer** has `disabled` attribute

**Verification Points**:

- Only one professional activity can be selected at a time
- Selection is visually confirmed in the dropdown field
- Button state changes from disabled to enabled on valid selection

---

### 7.4 Execute Score Calculation

**Objective**: Trigger the score calculation and verify successful completion.

**Steps**:

1. With "Организация и проведение совещаний" selected (from 7.3)
2. Verify **"Рассчитать"** button is enabled (blue, clickable)
3. Click button **"Рассчитать"**
4. Observe system response
5. Wait for calculation to complete (typically 1-5 seconds)

**Expected Results**:

**Immediate Response**:
- Loading indicator may appear on button (e.g., spinner icon) or dialog
- Button text may change to "Расчёт..." (Calculating...) temporarily
- API request is sent: `POST /api/scoring/calculate`
  - Request body: `{"participant_id": "{uuid}", "activity_code": "meeting_facilitation"}`

**Backend Processing** (verify in logs/database):
- System loads participant metrics from `extracted_metric` table (all 13 metrics)
- System loads active weight table for `meeting_facilitation` from `weight_table` table
- Validation checks:
  - All required metrics are present (13 metrics)
  - Weight table exists and is active
  - Sum of weights = 1.0
- Calculation formula: `score_pct = Σ(metric_value × weight) × 10`
- Example calculation (using test data from scenario 6):
  ```
  score_pct = (7.5×0.15 + 7.0×0.08 + 8.0×0.07 + 7.0×0.12 + 6.5×0.08 +
               8.0×0.07 + 6.0×0.06 + 7.5×0.09 + 8.0×0.10 + 7.5×0.08 +
               6.5×0.04 + 7.0×0.04 + 6.5×0.02) × 10
            = (1.125 + 0.56 + 0.56 + 0.84 + 0.52 +
               0.56 + 0.36 + 0.675 + 0.80 + 0.60 +
               0.26 + 0.28 + 0.13) × 10
            = 7.27 × 10
            = 72.7%
  ```
  (Actual result depends on real weight table values)

- Scoring result is saved to `scoring_result` table:
  - `participant_id`: UUID
  - `activity_code`: "meeting_facilitation"
  - `score_pct`: Decimal value (e.g., 72.70)
  - `calculated_at`: Timestamp
  - `recommendations`: JSONB with strengths and development areas
  - `metrics_used`: JSONB with metric values and weights

**Successful Completion**:
- Dialog closes automatically (or remains open showing success message)
- Toast notification appears: **"Расчёт выполнен успешно"** (Calculation completed successfully) or similar
- Participant detail page reloads or updates to show new scoring result
- A new section **"Результаты профпригодности"** (Suitability Results) may appear on the page
- Scoring result row may be displayed showing:
  - Professional activity: "Организация и проведение совещаний"
  - Score: "72.7%" (or calculated value)
  - Calculation date: Current timestamp
  - Action buttons: "Просмотреть JSON", "Скачать HTML"

**UI Element Locators**:

- Success toast: `alert` or toast notification with success icon
- Results section: Heading "Результаты профпригодности" or similar
- Score display: Text showing percentage value
- JSON button: `button` with text "Просмотреть JSON"
- HTML download button: `button` with text "Скачать HTML"

**Verification Points**:

- API request succeeds with status 200 OK or 201 Created
- Response body contains:
  - `scoring_result_id`: UUID of created result
  - `score_pct`: Calculated score
  - `message`: Success message
- Database record is created in `scoring_result` table
- Score value is quantized to 0.01 precision (two decimal places)
- No errors appear in browser console or backend logs

---

### 7.5 Verify Calculation with Missing Metrics

**Objective**: Test error handling when participant lacks required metrics.

**Precondition**: Create or use a participant with no metrics or partial metrics.

**Steps**:

1. Navigate to a participant detail page for a participant **without** saved metrics
2. Click button "Рассчитать пригодность"
3. Select professional activity "Организация и проведение совещаний"
4. Click "Рассчитать"
5. Observe system response

**Expected Results**:

**Option A - Validation on Dialog Open**:
- When dialog opens, a warning alert appears:
  - **"У участника нет метрик для расчёта"** (Participant has no metrics for calculation)
  - Or: **"Недостаточно данных для расчёта"** (Insufficient data for calculation)
- "Рассчитать" button remains disabled even after selecting activity
- User cannot proceed with calculation

**Option B - Validation on Calculation Attempt**:
- Calculation is attempted
- API returns error response (400 Bad Request or 422 Unprocessable Entity)
- Error toast appears: **"Не все метрики доступны для расчёта"** (Not all metrics are available for calculation)
- Dialog may list missing metrics:
  - "Отсутствуют метрики: Коммуникабельность, Обработка информации, ..." (Missing metrics: ...)
- No scoring result is created in database

**Verification Points**:

- System prevents invalid calculations
- Error messages clearly indicate which metrics are missing
- Users are guided to complete metric entry before attempting calculation

---

### 7.6 Test Multiple Calculations for Same Participant

**Objective**: Verify that recalculating score updates the existing result rather than creating duplicates.

**Steps**:

1. With participant that already has a scoring result (from 7.4)
2. Open calculation dialog again
3. Select the same professional activity "Организация и проведение совещаний"
4. Click "Рассчитать"
5. Verify system response
6. Check database for duplicate records

**Expected Results** (One of two behaviors):

**Option A - Update Existing Result**:
- Calculation succeeds
- Existing `scoring_result` record is updated:
  - `calculated_at` is updated to new timestamp
  - `score_pct` may change if metrics were modified
  - `recommendations` may be regenerated
- No duplicate records are created
- Toast: "Расчёт обновлён" (Calculation updated)

**Option B - Create New Result Version**:
- New `scoring_result` record is created
- Old result is either:
  - Marked as inactive/archived, OR
  - Kept for audit trail with version number
- Participant page shows most recent result
- Historical results may be accessible via "История расчётов" (Calculation History) link

**Verification Points**:

- Database query to check for duplicates:
  ```sql
  SELECT COUNT(*) FROM scoring_result
  WHERE participant_id = '{uuid}'
    AND activity_code = 'meeting_facilitation';
  ```
- If Option A: COUNT should be 1
- If Option B: COUNT may be > 1, but only one result is active/current

---

### 7.7 Cancel Calculation Dialog

**Objective**: Verify canceling does not trigger any calculation.

**Steps**:

1. Open calculation dialog
2. Select professional activity
3. Click button **"Отмена"** (Cancel)
4. Observe system response

**Expected Results**:

- Dialog closes immediately
- No API request is sent to `/api/scoring/calculate`
- No scoring result is created or modified
- User returns to participant detail page
- No toast notification appears

**UI Element Locators**:

- Cancel button: `button` with text "Отмена"

**Verification Points**:

- Cancel action does not mutate any data
- No side effects occur

---

## Scenario 8: View Final Report JSON

### Overview

This scenario validates the JSON report viewing feature, which displays the complete scoring result including participant data, calculated score, strengths, development areas, and detailed metrics table.

### Preconditions

- User is logged in as admin@test.com
- Participant exists with completed scoring result (from scenario 7.4)
- Scoring calculation for "meeting_facilitation" has been completed successfully
- Currently on participant detail page
- Scoring results section is visible with "Просмотреть JSON" button

---

### 8.1 Open JSON Report View

**Objective**: Navigate to the JSON report and verify it displays correctly.

**Steps**:

1. On participant detail page, locate the **"Результаты профпригодности"** (Suitability Results) section
2. Find the scoring result row for "Организация и проведение совещаний" (meeting_facilitation)
3. Verify the row displays:
   - Professional activity name
   - Score percentage (e.g., "72.7%")
   - Calculation date/time
4. In the action buttons area, click button **"Просмотреть JSON"** (View JSON)
5. Wait for response

**Expected Results** (One of two UI patterns):

**Option A - Modal Dialog**:
- Modal dialog opens with heading **"Финальный отчёт (JSON)"** (Final Report - JSON)
- Dialog contains scrollable text area or code block displaying JSON
- JSON is formatted with syntax highlighting (keys in one color, values in another, proper indentation)
- Dialog footer may have buttons:
  - "Копировать" (Copy to clipboard)
  - "Скачать JSON" (Download as file)
  - "Закрыть" (Close)

**Option B - New Page/Tab**:
- New browser tab opens
- URL: `/api/participants/{participant_id}/final-report?activity_code=meeting_facilitation&format=json`
- Page displays raw JSON or formatted JSON viewer
- Browser may offer "Save Page As" option

**UI Element Locators** (for Modal option):

- Dialog: `dialog[role="dialog"]` with heading containing "JSON"
- JSON content area: `<pre>` or `<code>` element, or JSON viewer component
- Copy button: `button` with text "Копировать"
- Download button: `button` with text "Скачать JSON"
- Close button: `button` with text "Закрыть" or X icon

**Verification Points**:

- JSON loads within 2 seconds
- No parsing errors or malformed JSON
- Content is readable and properly formatted

---

### 8.2 Verify JSON Report Structure and Required Fields

**Objective**: Validate that the JSON report contains all required fields with correct data types and values.

**Steps**:

1. With JSON report displayed (from 8.1)
2. Scroll through the entire JSON content
3. Locate and verify each required top-level field
4. Check data types and value formats

**Expected Root Fields**:

The JSON object must contain the following top-level fields:

| Field Name | Data Type | Description | Example Value |
|------------|-----------|-------------|---------------|
| `participant_id` | String (UUID) | Unique identifier of participant | `"5bf0471b-e9c2-47c7-abf0-30a7b5e70621"` |
| `participant_name` | String | Full name of participant | `"Батура Александр Александрович"` |
| `birth_date` | String (ISO date) | Date of birth | `"1985-06-15"` |
| `external_id` | String or null | External identifier | `"BATURA_AA_TEST"` |
| `activity_code` | String | Professional activity code | `"meeting_facilitation"` |
| `activity_name` | String | Professional activity name | `"Организация и проведение совещаний"` |
| `score_pct` | Number (Decimal) | Calculated suitability score | `72.70` |
| `calculated_at` | String (ISO timestamp) | When score was calculated | `"2025-11-09T21:54:32.123Z"` |
| `strengths` | Array of Objects | Top performing metrics | `[{...}, {...}, ...]` (3-5 items) |
| `dev_areas` | Array of Objects | Development opportunities | `[{...}, {...}, ...]` (3-5 items) |
| `metrics_table` | Array of Objects | All metrics with weights | `[{...}, {...}, ...]` (13 items) |

**Validation Steps for Each Field**:

1. **participant_id**:
   - Must be a valid UUID v4 format (36 characters with hyphens)
   - Must match the participant's actual ID in the database

2. **participant_name**:
   - Must match "Батура Александр Александрович"
   - Proper encoding of Cyrillic characters (no mojibake)

3. **birth_date**:
   - Format: `YYYY-MM-DD`
   - Must be "1985-06-15"

4. **external_id**:
   - Must be "BATURA_AA_TEST" or null if not set

5. **activity_code**:
   - Must be "meeting_facilitation"
   - Lowercase with underscores

6. **activity_name**:
   - Must be "Организация и проведение совещаний"
   - Cyrillic text properly encoded

7. **score_pct**:
   - Number type (not string)
   - Decimal value with 2 decimal places (e.g., 72.70)
   - Range: 10.00 to 100.00 (representing 10% to 100%)
   - Must match calculated value from scenario 7.4

8. **calculated_at**:
   - ISO 8601 format with timezone: `YYYY-MM-DDTHH:MM:SS.sssZ`
   - Timestamp should be recent (within last 24 hours for fresh test)

9. **strengths**:
   - Array type
   - Length: 3 to 5 elements
   - Each element is an object (validated in section 8.3)

10. **dev_areas**:
    - Array type
    - Length: 3 to 5 elements
    - Each element is an object (validated in section 8.4)

11. **metrics_table**:
    - Array type
    - Length: 13 elements (matching number of metrics entered)
    - Each element is an object (validated in section 8.5)

**Example JSON Structure**:
```json
{
  "participant_id": "5bf0471b-e9c2-47c7-abf0-30a7b5e70621",
  "participant_name": "Батура Александр Александрович",
  "birth_date": "1985-06-15",
  "external_id": "BATURA_AA_TEST",
  "activity_code": "meeting_facilitation",
  "activity_name": "Организация и проведение совещаний",
  "score_pct": 72.70,
  "calculated_at": "2025-11-09T21:54:32.123Z",
  "strengths": [...],
  "dev_areas": [...],
  "metrics_table": [...]
}
```

**Verification Points**:

- All 11 required fields are present (no missing fields)
- JSON is valid (can be parsed without errors)
- Data types match specifications
- No extra/unexpected top-level fields (unless documented)
- Cyrillic text is properly encoded (UTF-8)

---

### 8.3 Verify Strengths Array Content

**Objective**: Validate the structure and content of the `strengths` array, which highlights the participant's top-performing competencies.

**Steps**:

1. In the JSON report, locate the `strengths` array
2. Verify array length is between 3 and 5
3. For each element in the array, verify field structure
4. Check that strengths represent high-scoring metrics

**Expected Strengths Object Structure**:

Each element in the `strengths` array must be an object with these fields:

| Field Name | Data Type | Description | Example Value |
|------------|-----------|-------------|---------------|
| `metric_code` | String | Unique metric identifier | `"responsibility"` |
| `metric_name` | String | Display name in Russian | `"Ответственность"` |
| `value` | Number (Decimal) | Metric score (1.0-10.0) | `8.0` |
| `weight` | Number (Decimal) | Weight in calculation | `0.10` |
| `description` | String | Explanation of strength | `"Высокий уровень ответственности..."` |

**Example Strengths Element**:
```json
{
  "metric_code": "responsibility",
  "metric_name": "Ответственность",
  "value": 8.0,
  "weight": 0.10,
  "description": "Высокий уровень ответственности способствует эффективному выполнению задач и соблюдению обязательств. Участник демонстрирует надёжность и готовность брать на себя обязательства."
}
```

**Validation Rules for Strengths**:

1. **Array Length**:
   - Minimum: 3 strengths
   - Maximum: 5 strengths
   - Typical: 3-4 strengths

2. **Metric Selection Logic**:
   - Strengths are typically metrics with values ≥ 7.0
   - Selected from metrics with high impact on the chosen professional activity
   - Sorted by value (descending) or weighted contribution (value × weight)
   - Based on test data from scenario 6, expected strengths might include:
     - Ответственность (8.0)
     - Обработка информации (8.0)
     - Моральность / Нормативность (8.0)
     - Стрессоустойчивость (7.5)
     - Организованность (7.5)

3. **Field Validation**:
   - `metric_code`: Must match a valid metric code in the system
   - `metric_name`: Must match the corresponding metric name in Russian
   - `value`: Must be the same value entered in scenario 6
   - `weight`: Must match the weight from the active weight table for "meeting_facilitation"
   - `description`: Must be meaningful text (100-300 characters), not placeholder or empty

4. **Description Quality**:
   - Text is in Russian
   - Describes why this metric is a strength
   - Provides actionable insight or positive affirmation
   - Not generic (e.g., not just "This is a strength")

**Verification Steps**:

1. Count elements in `strengths` array: `strengths.length >= 3 && strengths.length <= 5`
2. For each strength object, verify all 5 fields are present
3. Check that `value` fields are among the higher values from entered metrics
4. Verify `metric_code` and `metric_name` pairs match known metrics
5. Confirm `description` text is substantive (not empty or placeholder)
6. Check for Cyrillic encoding issues

**Example Verification (pseudocode)**:
```javascript
strengths.forEach(strength => {
  assert(strength.metric_code, "metric_code is required");
  assert(strength.metric_name, "metric_name is required");
  assert(strength.value >= 1.0 && strength.value <= 10.0, "value in valid range");
  assert(strength.weight >= 0 && strength.weight <= 1, "weight in valid range");
  assert(strength.description.length >= 50, "description is substantial");
});
```

**Verification Points**:

- Strengths array is not empty
- Each strength object is complete (no missing fields)
- Values match metrics entered in scenario 6
- Weights match the weight table for "meeting_facilitation"
- Descriptions are meaningful and participant-specific

---

### 8.4 Verify Development Areas Array Content

**Objective**: Validate the structure and content of the `dev_areas` array, which identifies opportunities for improvement.

**Steps**:

1. In the JSON report, locate the `dev_areas` array
2. Verify array length is between 3 and 5
3. For each element in the array, verify field structure
4. Check that development areas represent lower-scoring metrics or high-impact improvement opportunities

**Expected Development Area Object Structure**:

Each element in the `dev_areas` array must be an object with these fields:

| Field Name | Data Type | Description | Example Value |
|------------|-----------|-------------|---------------|
| `metric_code` | String | Unique metric identifier | `"nonverbal_logic"` |
| `metric_name` | String | Display name in Russian | `"Невербальная логика"` |
| `value` | Number (Decimal) | Metric score (1.0-10.0) | `6.0` |
| `weight` | Number (Decimal) | Weight in calculation | `0.06` |
| `recommendation` | String | Improvement suggestion | `"Развитие навыков невербальной логики..."` |

**Example Development Area Element**:
```json
{
  "metric_code": "nonverbal_logic",
  "metric_name": "Невербальная логика",
  "value": 6.0,
  "weight": 0.06,
  "recommendation": "Развитие навыков невербальной логики поможет улучшить способность анализировать визуальную информацию и распознавать паттерны. Рекомендуется работа с диаграммами, схемами и задачами на пространственное мышление."
}
```

**Validation Rules for Development Areas**:

1. **Array Length**:
   - Minimum: 3 development areas
   - Maximum: 5 development areas
   - Typical: 3-4 areas

2. **Metric Selection Logic**:
   - Development areas are typically metrics with:
     - Lower absolute values (< 7.0), OR
     - High weights (indicating importance to the professional activity)
     - High potential impact if improved
   - Based on test data from scenario 6, expected dev areas might include:
     - Невербальная логика (6.0)
     - Конфликтность (низкая) (6.5)
     - Лексика (6.5)
     - Роль «Душа команды» (Белбин) (6.5)

3. **Field Validation**:
   - `metric_code`: Must match a valid metric code
   - `metric_name`: Must match the metric name in Russian
   - `value`: Must match the value entered in scenario 6
   - `weight`: Must match the weight from the weight table
   - `recommendation`: Must be actionable, constructive advice (100-400 characters)

4. **Recommendation Quality**:
   - Text is in Russian
   - Provides specific, actionable advice for improvement
   - Explains benefits of developing this competency
   - Tone is constructive and supportive (not critical)
   - May include suggested resources, exercises, or learning approaches

**Verification Steps**:

1. Count elements: `dev_areas.length >= 3 && dev_areas.length <= 5`
2. For each dev area, verify all 5 fields are present
3. Check that `value` fields are among the lower values OR high-weight metrics
4. Verify `metric_code` and `metric_name` pairs match known metrics
5. Confirm `recommendation` text is actionable and constructive
6. Check for Cyrillic encoding

**Example Verification (pseudocode)**:
```javascript
dev_areas.forEach(area => {
  assert(area.metric_code, "metric_code is required");
  assert(area.metric_name, "metric_name is required");
  assert(area.value >= 1.0 && area.value <= 10.0, "value in valid range");
  assert(area.weight >= 0 && area.weight <= 1, "weight in valid range");
  assert(area.recommendation.length >= 50, "recommendation is substantial");
});
```

**Verification Points**:

- Development areas array is not empty
- Each area object is complete
- Values match metrics entered in scenario 6
- Recommendations are helpful and specific
- No overlap between strengths and dev areas (a metric should not appear in both arrays)

---

### 8.5 Verify Metrics Table Array Content

**Objective**: Validate the complete metrics table, which shows all metrics used in the calculation with their values, weights, and weighted contributions.

**Steps**:

1. In the JSON report, locate the `metrics_table` array
2. Verify array length is 13 (matching number of metrics)
3. For each element, verify field structure and calculations
4. Validate that sum of weights equals 1.0
5. Validate that score calculation is correct

**Expected Metric Table Entry Structure**:

Each element in the `metrics_table` array must be an object with these fields:

| Field Name | Data Type | Description | Example Value |
|------------|-----------|-------------|---------------|
| `metric_code` | String | Unique identifier | `"communicability"` |
| `metric_name` | String | Display name | `"Коммуникабельность"` |
| `value` | Number (Decimal) | Metric score | `7.5` |
| `weight` | Number (Decimal) | Weight coefficient | `0.15` |
| `weighted_score` | Number (Decimal) | value × weight | `1.125` |

**Example Metrics Table Element**:
```json
{
  "metric_code": "communicability",
  "metric_name": "Коммуникабельность",
  "value": 7.5,
  "weight": 0.15,
  "weighted_score": 1.125
}
```

**Complete Expected Metrics Table** (based on scenario 6 test data):

| # | metric_code | metric_name | value | weight | weighted_score |
|---|-------------|-------------|-------|--------|----------------|
| 1 | communicability | Коммуникабельность | 7.5 | 0.15 | 1.125 |
| 2 | complex_problem_solving | Комплексное решение проблем | 7.0 | 0.08 | 0.560 |
| 3 | information_processing | Обработка информации | 8.0 | 0.07 | 0.560 |
| 4 | leadership | Лидерство | 7.0 | 0.12 | 0.840 |
| 5 | conflict_low | Конфликтность (низкая) | 6.5 | 0.08 | 0.520 |
| 6 | morality_normativity | Моральность / Нормативность | 8.0 | 0.07 | 0.560 |
| 7 | nonverbal_logic | Невербальная логика | 6.0 | 0.06 | 0.360 |
| 8 | organization | Организованность | 7.5 | 0.09 | 0.675 |
| 9 | responsibility | Ответственность | 8.0 | 0.10 | 0.800 |
| 10 | stress_resistance | Стрессоустойчивость | 7.5 | 0.08 | 0.600 |
| 11 | team_soul_role | Роль «Душа команды» (Белбин) | 6.5 | 0.04 | 0.260 |
| 12 | teamwork | Командность | 7.0 | 0.04 | 0.280 |
| 13 | vocabulary | Лексика | 6.5 | 0.02 | 0.130 |

*Note: Weight values are illustrative. Actual weights come from the active weight table.*

**Validation Rules**:

1. **Array Length**:
   - Must equal 13 (number of metrics entered in scenario 6)
   - Each metric from scenario 6 must appear exactly once

2. **Field Presence**:
   - All 5 fields must be present in each object
   - No null or undefined values

3. **Value Matching**:
   - Each `value` must match the corresponding value entered in scenario 6.3
   - Example: If "Коммуникабельность" was entered as 7.5, the table must show `"value": 7.5`

4. **Weight Validation**:
   - Each `weight` must be between 0.0 and 1.0
   - Sum of all weights must equal 1.0 (with tolerance ±0.001 for floating point precision)
   - Calculation to verify:
     ```javascript
     const sum = metrics_table.reduce((acc, m) => acc + m.weight, 0);
     assert(Math.abs(sum - 1.0) < 0.001, "Sum of weights equals 1.0");
     ```

5. **Weighted Score Calculation**:
   - Each `weighted_score` must equal `value × weight` (with tolerance ±0.001)
   - Calculation to verify:
     ```javascript
     metrics_table.forEach(m => {
       const expected = m.value * m.weight;
       assert(Math.abs(m.weighted_score - expected) < 0.001,
              `weighted_score for ${m.metric_code} is correct`);
     });
     ```

6. **Final Score Verification**:
   - Sum of all `weighted_score` values × 10 should equal `score_pct` (root-level field)
   - Calculation:
     ```javascript
     const totalWeightedScore = metrics_table.reduce((acc, m) => acc + m.weighted_score, 0);
     const calculatedScore = totalWeightedScore * 10;
     assert(Math.abs(calculatedScore - score_pct) < 0.1,
            "Calculated score matches score_pct");
     ```
   - Example: If sum of weighted_score = 7.27, then score_pct should be ≈ 72.7

**Verification Steps**:

1. Count entries: `metrics_table.length === 13`
2. Extract all `metric_code` values and verify no duplicates
3. For each metric, verify:
   - `metric_code` matches expected code
   - `metric_name` matches expected Russian name
   - `value` matches value from scenario 6.3
   - `weight` is reasonable (0.0 to 1.0)
   - `weighted_score === value × weight` (within tolerance)
4. Sum all `weight` values: should equal 1.0 (±0.001)
5. Sum all `weighted_score` values and multiply by 10: should match `score_pct` (±0.1)

**Verification Points**:

- All 13 metrics are present
- No missing or extra metrics
- Values match entered data exactly
- Weight sum validation passes
- Weighted score calculations are correct
- Final score derivation is correct
- Metric names are properly encoded (Cyrillic)

---

### 8.6 Copy JSON to Clipboard (Optional Feature)

**Objective**: Test the copy-to-clipboard functionality if available.

**Precondition**: JSON view dialog includes a "Копировать" (Copy) button.

**Steps**:

1. With JSON report displayed in dialog (from 8.1)
2. Locate button **"Копировать"** (Copy) or similar
3. Click the button
4. Observe system response

**Expected Results**:

- Toast notification appears: **"JSON скопирован в буфер обмена"** (JSON copied to clipboard)
- JSON content is copied to system clipboard
- To verify: Open a text editor (Notepad, VS Code, etc.) and paste (Ctrl+V / Cmd+V)
  - Pasted content should be the complete JSON string
  - Formatting/indentation may or may not be preserved depending on implementation

**UI Element Locators**:

- Copy button: `button` with text "Копировать" or clipboard icon

**Verification Points**:

- Clipboard operation succeeds without errors
- Entire JSON is copied (not truncated)
- JSON in clipboard is valid (can be parsed)

---

### 8.7 Download JSON as File (Optional Feature)

**Objective**: Test the JSON file download functionality if available.

**Precondition**: JSON view dialog includes a "Скачать JSON" (Download JSON) button.

**Steps**:

1. With JSON report displayed (from 8.1)
2. Locate button **"Скачать JSON"** (Download JSON)
3. Click the button
4. Wait for download to initiate
5. Check browser's download folder

**Expected Results**:

- File download starts immediately (no additional prompts)
- File is saved to browser's default download location
- Filename format: `final_report_{participant_name}_{activity_code}.json`
  - Example: `final_report_Batura_A.A._meeting_facilitation.json`
  - Or: `final_report_5bf0471b-e9c2-47c7-abf0-30a7b5e70621.json` (using participant ID)
- File contents are identical to displayed JSON
- File encoding is UTF-8 (Cyrillic characters render correctly)

**Verification Steps**:

1. Navigate to download folder (typically `~/Downloads/`)
2. Locate the downloaded JSON file
3. Open file in text editor or JSON viewer
4. Verify contents match the displayed JSON in the dialog
5. Parse JSON to ensure validity: `JSON.parse(fileContents)`

**Verification Points**:

- File downloads without errors
- Filename is descriptive and unique
- File contents are valid JSON
- File size is reasonable (typically 2-10 KB)

---

### 8.8 Close JSON Report View

**Objective**: Exit the JSON report view and return to participant page.

**Steps**:

1. With JSON report displayed (from 8.1)
2. If modal dialog:
   - Click button **"Закрыть"** (Close), OR
   - Click X button in top-right corner, OR
   - Press Escape key
3. If new tab:
   - Close the tab or return to previous tab

**Expected Results**:

- Modal dialog closes (with fade-out animation)
- User returns to participant detail page
- Scoring results section is still visible
- No data is lost (can re-open JSON report at any time)

**Verification Points**:

- Close action is smooth and responsive
- Multiple ways to close are available (button, X, Escape key)

---

## Scenario 9: Download Final Report HTML

### Overview

This scenario validates the HTML report download feature, which generates a professionally formatted, printable report with all scoring details, suitable for business documentation and archival.

### Preconditions

- User is logged in as admin@test.com
- Participant exists with completed scoring result (from scenario 7.4)
- Scoring calculation for "meeting_facilitation" has been completed
- Currently on participant detail page
- Scoring results section displays "Скачать HTML" button

---

### 9.1 Trigger HTML Report Download

**Objective**: Initiate the HTML report download and verify file is received.

**Steps**:

1. On participant detail page, locate the **"Результаты профпригодности"** (Suitability Results) section
2. Find the scoring result row for "Организация и проведение совещаний"
3. In the action buttons area, click button **"Скачать HTML"** (Download HTML)
4. Wait for download to start (typically 1-3 seconds)
5. Check browser's download notification or download folder

**Expected Results**:

**HTTP Request**:
- Browser sends GET request to: `/api/participants/{participant_id}/final-report`
- Query parameters:
  - `activity_code=meeting_facilitation`
  - `format=html`
- Full URL example: `http://localhost:9187/api/participants/5bf0471b-e9c2-47c7-abf0-30a7b5e70621/final-report?activity_code=meeting_facilitation&format=html`

**HTTP Response**:
- Status code: **200 OK**
- Headers:
  - `Content-Type: text/html; charset=utf-8`
  - `Content-Disposition: attachment; filename="final_report_Batura_A.A._meeting_facilitation.html"` (or similar)
- Response body: Complete HTML document

**File Download**:
- File download initiates immediately (no intermediate dialogs)
- File is saved to browser's download folder (typically `~/Downloads/`)
- Filename format: `final_report_{participant_name}_{activity_code}.html`
  - Example: `final_report_Batura_A.A._meeting_facilitation.html`
  - Spaces in participant name may be replaced with underscores
  - Non-ASCII characters may be transliterated (e.g., "Батура" → "Batura")
- File size: Typically 20-100 KB (depends on template complexity and CSS inlining)

**UI Element Locators**:

- Download button: `button` with text "Скачать HTML"

**Verification Points**:

- Download completes within 3 seconds
- No error messages appear
- Browser console shows no JavaScript errors
- Network tab shows successful API request (status 200)

---

### 9.2 Verify Downloaded HTML File Properties

**Objective**: Confirm the downloaded file is a valid HTML document with correct metadata.

**Steps**:

1. Navigate to browser's download folder
2. Locate the downloaded HTML file (from 9.1)
3. Right-click file and select "Properties" or "Get Info"
4. Verify file metadata
5. Open file in text editor (VS Code, Notepad++, or Sublime Text)
6. Inspect HTML source code

**Expected File Properties**:

- **File type**: HTML Document (`.html` extension)
- **File size**: 20-100 KB (reasonable size for styled HTML report)
- **Encoding**: UTF-8 (verify in text editor - Cyrillic characters should render correctly)
- **Created date**: Current timestamp (when download occurred)

**Expected HTML Document Structure** (source code inspection):

```html
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Финальный отчёт - Батура Александр Александрович</title>
    <style>
        /* Inline CSS styles or <link> to external stylesheet */
        body { font-family: Arial, sans-serif; ... }
        .header { ... }
        .score { font-size: 32px; color: #409EFF; ... }
        ...
    </style>
</head>
<body>
    <!-- Header section -->
    <div class="header">
        <h1>Финальный отчёт по профессиональной пригодности</h1>
        ...
    </div>

    <!-- Participant info section -->
    <div class="participant-info">
        <h2>Информация об участнике</h2>
        ...
    </div>

    <!-- Scoring summary section -->
    <div class="scoring-summary">
        <h2>Результаты оценки</h2>
        <div class="score">72.7%</div>
        ...
    </div>

    <!-- Strengths section -->
    <div class="strengths">
        <h2>Сильные стороны</h2>
        <ul>
            <li><strong>Ответственность (8.0):</strong> ...</li>
            ...
        </ul>
    </div>

    <!-- Development areas section -->
    <div class="dev-areas">
        <h2>Зоны развития</h2>
        <ul>
            <li><strong>Невербальная логика (6.0):</strong> ...</li>
            ...
        </ul>
    </div>

    <!-- Metrics table -->
    <div class="metrics-table">
        <h2>Таблица метрик</h2>
        <table>
            <thead>
                <tr>
                    <th>Метрика</th>
                    <th>Значение</th>
                    <th>Вес</th>
                    <th>Взвешенный балл</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Коммуникабельность</td>
                    <td>7.5</td>
                    <td>0.15</td>
                    <td>1.125</td>
                </tr>
                ...
            </tbody>
        </table>
    </div>

    <!-- Footer -->
    <div class="footer">
        <p>Сгенерировано: 2025-11-09 21:54:32</p>
        <p>Система управления компетенциями v1.0</p>
    </div>
</body>
</html>
```

**Validation Checks**:

1. **DOCTYPE and HTML tag**:
   - Must start with `<!DOCTYPE html>`
   - `<html lang="ru">` for Russian language content

2. **Head section**:
   - `<meta charset="UTF-8">` for proper encoding
   - `<title>` tag with participant name
   - `<style>` tag with CSS (inline styles preferred for portability)

3. **Body structure**:
   - Well-formed HTML (all tags properly closed)
   - Logical section divisions (header, info, results, strengths, dev areas, metrics, footer)
   - Semantic HTML tags (h1, h2, p, ul, li, table, etc.)

4. **CSS Styles**:
   - Professional styling applied (fonts, colors, spacing)
   - Print-friendly layout (good page breaks, readable fonts)
   - Responsive design (works on different screen sizes)

**Verification Points**:

- HTML is valid (passes W3C validator if checked)
- All required sections are present
- No broken tags or syntax errors
- File opens successfully in browsers and text editors

---

### 9.3 Verify HTML Report Content and Layout (Browser Rendering)

**Objective**: Open the HTML file in a browser and verify visual presentation and content accuracy.

**Steps**:

1. Locate the downloaded HTML file in download folder
2. Double-click to open in default browser (or right-click → Open With → Browser)
3. Wait for page to load
4. Visually inspect each section of the report
5. Compare content with JSON report (from scenario 8) for consistency

**Expected Visual Layout**:

The HTML report should display a professionally formatted page with the following sections:

---

#### **Section 1: Report Header**

**Visual Elements**:
- Page title/heading: **"Финальный отчёт по профессиональной пригодности"** (Final Professional Suitability Report)
- Organization logo or branding (if configured)
- Report generation date/time: **"Дата формирования: 09.11.2025, 21:54"**

**Styling**:
- Large, bold heading (h1)
- Professional color scheme (e.g., blue/gray palette)
- Clear visual hierarchy

---

#### **Section 2: Participant Information**

**Visual Elements**:
- Heading: **"Информация об участнике"** (Participant Information)
- Data fields displayed in table or definition list format:
  - **ФИО**: Батура Александр Александрович
  - **Дата рождения**: 15.06.1985 (format: DD.MM.YYYY)
  - **Внешний ID**: BATURA_AA_TEST
  - **Дата создания**: 09.11.2025, 21:54

**Styling**:
- Clean, readable layout
- Labels in bold, values in regular weight
- Adequate spacing between fields

---

#### **Section 3: Scoring Summary**

**Visual Elements**:
- Heading: **"Результаты оценки"** (Assessment Results)
- Professional activity: **"Организация и проведение совещаний"** (meeting_facilitation)
- **Score percentage**: Displayed prominently (large font, color-coded)
  - Value: **72.7%** (or calculated value from scenario 7.4)
  - Color coding:
    - Green (≥75%): High suitability
    - Orange (60-74%): Moderate suitability
    - Red (<60%): Low suitability
- Calculation date: **"Рассчитано: 09.11.2025, 21:54"**

**Styling**:
- Score is the focal point (large font size, e.g., 32-48px)
- Color badge or background highlight for score
- Clear association with professional activity

**Verification**:
- Score value matches `score_pct` from JSON report (scenario 8.2)

---

#### **Section 4: Strengths (Сильные стороны)**

**Visual Elements**:
- Heading: **"Сильные стороны"** (Strengths)
- Bulleted or numbered list with 3-5 items
- Each item format:
  - **Metric name (value)**: Description
  - Example: **Ответственность (8.0):** Высокий уровень ответственности способствует эффективному выполнению задач...

**Expected Content** (based on JSON from scenario 8.3):
- 3-5 strength items
- Metrics with high values (typically ≥7.0)
- Descriptions are meaningful and encouraging

**Styling**:
- Clear visual distinction from dev areas
- Icons or positive indicators (e.g., checkmark, green color)
- Good readability (font size 14-16px, adequate line height)

**Verification**:
- Number of strengths matches JSON report (3-5)
- Metric names and values match JSON `strengths` array
- Descriptions match JSON content

---

#### **Section 5: Development Areas (Зоны развития)**

**Visual Elements**:
- Heading: **"Зоны развития"** (Development Areas)
- Bulleted or numbered list with 3-5 items
- Each item format:
  - **Metric name (value)**: Recommendation
  - Example: **Невербальная логика (6.0):** Развитие навыков невербальной логики поможет улучшить...

**Expected Content** (based on JSON from scenario 8.4):
- 3-5 development area items
- Metrics with lower values or high improvement impact
- Recommendations are constructive and actionable

**Styling**:
- Distinct from strengths section
- Neutral or growth-oriented visual indicators (e.g., upward arrow, blue color)
- Supportive tone in presentation

**Verification**:
- Number of dev areas matches JSON report (3-5)
- Metric names and values match JSON `dev_areas` array
- Recommendations match JSON content
- No duplication with strengths (metrics should not appear in both sections)

---

#### **Section 6: Detailed Metrics Table (Таблица метрик)**

**Visual Elements**:
- Heading: **"Детализированная таблица метрик"** (Detailed Metrics Table)
- HTML table with 4 columns and 14 rows (header + 13 metrics)
- **Column headers**:
  1. **Метрика** (Metric)
  2. **Значение** (Value)
  3. **Вес** (Weight)
  4. **Взвешенный балл** (Weighted Score)

**Expected Table Rows** (based on scenario 8.5):

| Метрика | Значение | Вес | Взвешенный балл |
|---------|----------|-----|-----------------|
| Коммуникабельность | 7.5 | 0.15 | 1.125 |
| Комплексное решение проблем | 7.0 | 0.08 | 0.560 |
| Обработка информации | 8.0 | 0.07 | 0.560 |
| Лидерство | 7.0 | 0.12 | 0.840 |
| Конфликтность (низкая) | 6.5 | 0.08 | 0.520 |
| Моральность / Нормативность | 8.0 | 0.07 | 0.560 |
| Невербальная логика | 6.0 | 0.06 | 0.360 |
| Организованность | 7.5 | 0.09 | 0.675 |
| Ответственность | 8.0 | 0.10 | 0.800 |
| Стрессоустойчивость | 7.5 | 0.08 | 0.600 |
| Роль «Душа команды» (Белбин) | 6.5 | 0.04 | 0.260 |
| Командность | 7.0 | 0.04 | 0.280 |
| Лексика | 6.5 | 0.02 | 0.130 |

**Table Footer (Optional)**:
- **Итого** (Total) row showing:
  - Sum of weights: **1.00**
  - Sum of weighted scores: **7.27** (or calculated total)
  - Final score: **72.7%** (sum × 10)

**Styling**:
- Alternating row colors (zebra striping) for readability
- Header row with bold text and background color
- Right-aligned numeric columns
- Border or grid lines for clarity
- Monospace font for numbers (optional, improves alignment)

**Verification**:
- Table contains exactly 13 metric rows
- All metric names match JSON `metrics_table` array
- All values match scenario 6.3 test data
- All weights match JSON weights
- All weighted scores = value × weight
- Sum of weights = 1.0 (displayed in footer)
- Sum of weighted scores × 10 = score_pct

---

#### **Section 7: Footer**

**Visual Elements**:
- Horizontal line separator or visual divider
- **Generation timestamp**: "Сгенерировано: 09.11.2025, 21:54:32"
- **System version**: "Система управления компетенциями v1.0"
- Optional: Legal disclaimer, confidentiality notice, or copyright

**Styling**:
- Smaller font size (10-12px)
- Gray or muted color
- Centered or right-aligned

**Verification**:
- Timestamp reflects current date/time (when report was generated)
- Version number matches system version

---

### Visual Design Quality Checks

**Overall Presentation**:
- Professional business report aesthetic
- Consistent branding (colors, fonts, spacing)
- Good use of whitespace (not cramped)
- Clear section hierarchy (headings, subheadings)

**Typography**:
- Sans-serif font (e.g., Arial, Helvetica, Roboto) for readability
- Consistent font sizes (headings: 24-32px, body: 14-16px, footer: 10-12px)
- Adequate line height (1.5-1.8) for comfortable reading

**Color Scheme**:
- Professional colors (blue, gray, white)
- Sufficient contrast for text readability (WCAG AA compliance)
- Color-coded score (green/orange/red)

**Layout**:
- Centered or fixed-width container (max-width: 900-1200px)
- Padding/margins around content
- Responsive design (adapts to window size)

**Print Optimization**:
- Page breaks avoid splitting sections awkwardly
- All content visible (no truncation)
- Background colors print correctly (or use print-specific CSS)

---

### 9.4 Verify HTML Report Content Accuracy

**Objective**: Perform detailed content verification by comparing HTML report with JSON report data.

**Steps**:

1. Open HTML report in browser (from 9.3)
2. Open JSON report in a separate browser tab or window (from scenario 8)
3. Systematically compare each section

**Comparison Checklist**:

| Section | HTML Content | JSON Source | Verification Method |
|---------|--------------|-------------|---------------------|
| Participant Name | Visual check | `participant_name` | Must match exactly |
| Birth Date | Visual check | `birth_date` | Format may differ (DD.MM.YYYY vs YYYY-MM-DD) |
| External ID | Visual check | `external_id` | Must match exactly |
| Professional Activity | Visual check | `activity_name` | Must match exactly |
| Score Percentage | Visual check | `score_pct` | Must match (e.g., 72.7% vs 72.70) |
| Calculation Date | Visual check | `calculated_at` | Format may differ (localized vs ISO) |
| Strengths Count | Count list items | `strengths.length` | Must match (3-5) |
| Strengths Content | Read each item | `strengths` array | Names, values, descriptions match |
| Dev Areas Count | Count list items | `dev_areas.length` | Must match (3-5) |
| Dev Areas Content | Read each item | `dev_areas` array | Names, values, recommendations match |
| Metrics Table Rows | Count table rows | `metrics_table.length` | Must be 13 |
| Metrics Table Data | Read each row | `metrics_table` array | All columns match |

**Detailed Verification Steps**:

1. **Participant Info**:
   - HTML name = JSON `participant_name` ✓
   - HTML DOB = JSON `birth_date` (accounting for format difference) ✓
   - HTML external ID = JSON `external_id` ✓

2. **Scoring Summary**:
   - HTML activity = JSON `activity_name` ✓
   - HTML score = JSON `score_pct` (e.g., both show 72.7%) ✓

3. **Strengths**:
   - Count HTML list items = JSON `strengths.length` ✓
   - For each strength:
     - HTML metric name = JSON `strengths[i].metric_name` ✓
     - HTML value = JSON `strengths[i].value` ✓
     - HTML description = JSON `strengths[i].description` ✓

4. **Dev Areas**:
   - Count HTML list items = JSON `dev_areas.length` ✓
   - For each dev area:
     - HTML metric name = JSON `dev_areas[i].metric_name` ✓
     - HTML value = JSON `dev_areas[i].value` ✓
     - HTML recommendation = JSON `dev_areas[i].recommendation` ✓

5. **Metrics Table**:
   - Count HTML table rows = JSON `metrics_table.length` + 1 (for header) ✓
   - For each metric (row by row):
     - HTML metric name = JSON `metrics_table[i].metric_name` ✓
     - HTML value = JSON `metrics_table[i].value` ✓
     - HTML weight = JSON `metrics_table[i].weight` ✓
     - HTML weighted score = JSON `metrics_table[i].weighted_score` ✓

**Verification Points**:

- All data from JSON is accurately represented in HTML
- No missing content
- No extra/fabricated content
- Formatting differences are acceptable (date formats, decimal places)
- Content is semantically identical even if presentation differs

---

### 9.5 Test HTML Report Cross-Browser Rendering

**Objective**: Verify the HTML report displays correctly in multiple browsers.

**Steps**:

1. Open the downloaded HTML file in **Google Chrome**
2. Visually inspect layout and formatting (use checklist from 9.3)
3. Open the same file in **Mozilla Firefox**
4. Compare rendering with Chrome version
5. Open in **Safari** (if on macOS)
6. Note any rendering differences

**Expected Results**:

- Report displays correctly in all tested browsers
- Layout is consistent (sections, spacing, alignment)
- Fonts render properly (no missing glyphs)
- Colors are accurate (no color shifts)
- Tables are well-formatted
- No broken CSS or layout issues

**Known Potential Issues**:

- Font rendering may vary slightly between browsers
- Color accuracy may differ on different displays
- Some CSS properties may have limited browser support (flexbox, grid)
- Print preview may differ between browsers

**Verification Points**:

- No major layout breaks in any browser
- Content is fully readable
- Interactive elements work (if any, e.g., collapsible sections)
- PDF export/print preview looks good in each browser

---

### 9.6 Test HTML Report Print Functionality

**Objective**: Verify the report can be printed or exported to PDF with good formatting.

**Steps**:

1. Open HTML report in browser (Chrome recommended)
2. Press **Ctrl+P** (Windows) or **Cmd+P** (macOS) to open print dialog
3. In print preview, observe layout
4. Select "Save as PDF" as the destination (do not print to physical printer)
5. Adjust settings:
   - Orientation: Portrait
   - Margins: Default
   - Background graphics: Enabled (to preserve colors)
6. Click "Save" or "Print"
7. Save PDF to a test location
8. Open the PDF and verify content

**Expected Print Preview Results**:

- All content is visible (no truncation)
- Page breaks occur at logical points (between sections, not mid-paragraph)
- Headers and footers are appropriate
- Colors print (if background graphics enabled)
- Tables fit within page width (no horizontal overflow)
- Fonts are readable (minimum 10pt size)

**Expected PDF Results**:

- PDF file is created successfully (filename: e.g., `final_report_Batura_A.A..pdf`)
- PDF opens in PDF viewer (Adobe Acrobat, Preview, Edge, etc.)
- All content from HTML is present
- Formatting is preserved (bold, colors, table borders)
- Text is selectable (searchable, not rasterized)
- PDF file size is reasonable (typically 50-500 KB)

**Verification Points**:

- Print CSS is applied (if defined in HTML)
- Page breaks avoid orphaning headers or splitting important content
- Footer appears on each page (if multi-page report)
- PDF is professional quality (suitable for archival or sharing)

---

### 9.7 Test HTML Report Download for Different Professional Activities (Edge Case)

**Objective**: Verify that downloading reports for different professional activities generates distinct files with correct content.

**Precondition**: Participant has scoring results for multiple professional activities (requires running scenario 7 for a second activity).

**Steps**:

1. On participant detail page, verify there are 2+ scoring results for different activities
2. Click "Скачать HTML" for the first activity (e.g., "meeting_facilitation")
3. Wait for file to download: `final_report_..._meeting_facilitation.html`
4. Click "Скачать HTML" for the second activity (e.g., "project_management" if available)
5. Wait for file to download: `final_report_..._project_management.html`
6. Open both HTML files in browser
7. Compare content

**Expected Results**:

- Two distinct HTML files are downloaded with different filenames
- File 1 content:
  - Activity: "Организация и проведение совещаний" (meeting_facilitation)
  - Score: Calculated for meeting_facilitation weights
  - Metrics table: Uses meeting_facilitation weight table
- File 2 content:
  - Activity: Different activity name (e.g., "Управление проектами")
  - Score: Different score (due to different weight table)
  - Metrics table: Uses different weight table

**Verification Points**:

- No file overwriting (both files exist in download folder)
- Each file reflects the correct professional activity
- Scores and weighted calculations are activity-specific

---

### 9.8 Test HTML Download Error Handling

**Objective**: Verify appropriate error handling when HTML generation fails.

**Precondition**: Create a scenario where HTML generation might fail (e.g., missing scoring result).

**Steps**:

1. Attempt to download HTML for a participant **without** a scoring result
2. Or delete the scoring result from the database and try to download
3. Click "Скачать HTML"
4. Observe system response

**Expected Results**:

- Error toast appears: **"Результат не найден"** (Result not found) or **"Ошибка при формировании отчёта"** (Error generating report)
- HTTP response: 404 Not Found or 500 Internal Server Error
- No file is downloaded
- User remains on participant detail page

**Verification Points**:

- System gracefully handles missing data
- Clear error message is displayed
- No broken file downloads
- Backend logs the error for debugging

---

## Test Execution Summary

### Scenario Coverage Matrix

| Scenario | Test Cases | Priority | Estimated Time |
|----------|-----------|----------|----------------|
| 6. Manual Metrics Entry | 6.1-6.9 | P0 | 30-45 min |
| 7. Calculate Score | 7.1-7.7 | P0 | 20-30 min |
| 8. View Final Report JSON | 8.1-8.8 | P1 | 25-35 min |
| 9. Download Final Report HTML | 9.1-9.8 | P1 | 30-40 min |
| **Total** | **32 test cases** | - | **105-150 min** |

### Success Criteria

A test scenario passes if:

1. All steps execute without blocking errors
2. All expected results are observed
3. All verification points are confirmed
4. No unexpected errors in browser console or backend logs
5. Database state is consistent after test completion

### Known Issues Tracking

**BUG-001**: Manual metrics entry input fields not rendered (see section 6.2, 6.8)
- **Severity**: P0 - Critical
- **Impact**: Blocks scenario 6 (Manual Metrics Entry)
- **Workaround**: Use API or database to insert metrics
- **Status**: Open - Requires frontend fix

### Test Environment Requirements

**Browser**:
- Chrome 90+ (primary)
- Firefox 88+ (secondary)
- Safari 14+ (tertiary, macOS only)

**Screen Resolution**:
- Minimum: 1280x720 (HD)
- Recommended: 1920x1080 (Full HD)

**Network**:
- Local development (localhost:9187)
- No external network required (all resources are local)

**Test Data**:
- Admin user: admin@test.com / admin123
- Participant: Батура Александр Александрович (created in scenario 4)
- Report file: `Batura_A.A._Biznes-Profil_Biznes-otchyot_1718107.docx`

---

## Appendix

### Metric Codes and Names Reference

| Code | Russian Name | English Name |
|------|--------------|--------------|
| communicability | Коммуникабельность | Communicability |
| complex_problem_solving | Комплексное решение проблем | Complex Problem Solving |
| information_processing | Обработка информации | Information Processing |
| leadership | Лидерство | Leadership |
| conflict_low | Конфликтность (низкая) | Conflict (Low) |
| morality_normativity | Моральность / Нормативность | Morality/Normativity |
| nonverbal_logic | Невербальная логика | Non-verbal Logic |
| organization | Организованность | Organization |
| responsibility | Ответственность | Responsibility |
| stress_resistance | Стрессоустойчивость | Stress Resistance |
| team_soul_role | Роль «Душа команды» (Белбин) | Team Soul Role (Belbin) |
| teamwork | Командность | Teamwork |
| vocabulary | Лексика | Vocabulary |

### API Endpoints Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/participants/{id}` | GET | Get participant details |
| `/api/reports` | POST | Upload report |
| `/api/reports/{id}/metrics` | GET | Get report metrics |
| `/api/metrics` | POST/PUT | Save metrics |
| `/api/scoring/calculate` | POST | Calculate score |
| `/api/participants/{id}/final-report` | GET | Download final report (JSON or HTML) |

### Troubleshooting Guide

**Issue**: Metrics dialog shows no input fields
- **Cause**: Frontend rendering bug (BUG-001)
- **Solution**: Use API to insert metrics or wait for frontend fix

**Issue**: Score calculation fails with "Missing metrics" error
- **Cause**: Not all 13 metrics are saved in database
- **Solution**: Verify all metrics are present in `extracted_metric` table for the report

**Issue**: JSON report shows empty strengths/dev_areas
- **Cause**: Recommendation generation failed or disabled
- **Solution**: Check `AI_RECOMMENDATIONS_ENABLED=1` in environment, verify Gemini API keys

**Issue**: HTML download returns 404
- **Cause**: Scoring result not found
- **Solution**: Verify scoring calculation completed successfully (scenario 7.4)

**Issue**: HTML report has encoding issues (mojibake)
- **Cause**: Incorrect charset or encoding mismatch
- **Solution**: Ensure `<meta charset="UTF-8">` is in HTML head, server sends correct Content-Type header

---

**Document Revision History**:

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-09 | Test Planning Team | Initial release |

---

**Approval**:

- [ ] Reviewed by: QA Lead
- [ ] Approved by: Product Owner
- [ ] Ready for Execution: Yes / No

---

**End of Test Plan**
