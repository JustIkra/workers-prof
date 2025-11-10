# Manual Metrics Entry - Comprehensive Test Plan

## Application Overview

The **Workers-Prof** application provides a manual metrics entry interface that allows users to review automatically extracted metrics and manually enter or correct metric values for participant assessment reports. This interface is accessible through a modal dialog from the participant detail page and supports validation, editing, and persistence of metric data.

## Test Execution Environment

- **Application URL**: http://localhost:9187
- **Test Fixtures Location**: `/Users/maksim/git_projects/workers-prof/e2e/fixtures/`
- **Admin Credentials**: admin@test.com / admin123
- **Test Data Files**:
  - REPORT_1: `Batura_A.A._Biznes-Profil_Biznes-otchyot_1718107.docx`

---

## Test Scenarios

### Scenario 6: Manual Metrics Entry

**Seed**: `e2e/seed.spec.ts`

**Preconditions**:
- User is logged in as admin (admin@test.com / admin123)
- Participant exists in the system
- At least one report has been uploaded for the participant
- Browser is on the participant detail page

---

### 6.1 Navigate to Metrics Dialog

**Objective**: Verify that the metrics dialog can be accessed from the participant detail page for an uploaded report.

**Steps**:
1. Login to application as admin@test.com / admin123
2. Navigate to Participants page (http://localhost:9187/participants)
3. Click "Открыть" button for participant "Батура Александр Александрович"
4. Verify participant detail page loads with URL pattern `/participants/{participant_id}`
5. Locate the "Отчёты" (Reports) section
6. Verify at least one report is present in the reports table
7. For a report with status "Загружен", locate the "Метрики" button in the actions column
8. Click the "Метрики" button

**Expected Results**:
- Dialog opens with heading "Метрики отчёта"
- Dialog contains section labeled "Ручной ввод метрик"
- Close button (X) is visible in top-right corner
- If no metrics have been extracted, an alert message displays: "Метрики для этого отчёта ещё не извлечены. Вы можете ввести их вручную."
- "Редактировать" button is visible
- All metric labels are displayed in read-only mode

**Metric Labels Displayed** (13 metrics total):
1. Коммуникабельность (балл) - Communicability
2. Комплексное решение проблем (балл) - Complex Problem Solving
3. Обработка информации (балл) - Information Processing
4. Лидерство (балл) - Leadership
5. Конфликтность (низкая) (балл) - Conflict (Low)
6. Моральность / Нормативность (балл) - Morality / Normativity
7. Невербальная логика (балл) - Non-verbal Logic
8. Организованность (балл) - Organization
9. Ответственность (балл) - Responsibility
10. Стрессоустойчивость (балл) - Stress Resistance
11. Роль «Душа команды» (Белбин) (балл) - "Team Soul" Role (Belbin)
12. Командность (балл) - Teamwork
13. Лексика (балл) - Vocabulary

**Verification Points**:
- Dialog is modal (overlays the participant detail page)
- Dialog is centered on screen
- Metrics are displayed in a grid/column layout
- All 13 metrics are visible (may require scrolling within dialog)

---

### 6.2 Review Auto-Extracted Metrics (If Available)

**Objective**: Verify that auto-extracted metrics from Vision/AI processing are displayed with their values, confidence scores, and source information.

**Preconditions**:
- Report has been processed with "Извлечь метрики" action
- Metrics extraction completed successfully

**Steps**:
1. Open metrics dialog for a processed report
2. Review each metric field for extracted values
3. Check for confidence score indicators
4. Check for source indicators (LLM or MANUAL)
5. Identify metrics flagged for review (low confidence < 0.8)

**Expected Results**:
- Metrics with auto-extracted values display numeric values in range 1.0-10.0
- Each extracted metric shows:
  - Metric name (label)
  - Extracted value (number with up to 1 decimal place)
  - Confidence score (if available, e.g., "85%", "0.92")
  - Source indicator (LLM or MANUAL badge/label)
- Metrics with confidence < 0.8 are highlighted or marked for review
- Empty metrics show placeholder or blank field
- Values are displayed in read-only format until "Редактировать" is clicked

**Verification Points**:
- Values are within valid range (1.0-10.0)
- Confidence scores are displayed as percentages or decimals (0.0-1.0)
- Source labels are clear (LLM = Gemini Vision by default)
- Low-confidence metrics have visual indicator (yellow/orange highlight, warning icon)

**Note**: Based on current exploration, the metrics dialog shows metric labels in groups but does not display input fields in read-only mode. The actual UI implementation may vary from the specification.

---

### 6.3 Enable Edit Mode

**Objective**: Verify that clicking "Редактировать" enables edit mode for manual metrics entry.

**Steps**:
1. Open metrics dialog for any report
2. Verify "Редактировать" button is visible and enabled
3. Click "Редактировать" button
4. Observe UI changes

**Expected Results**:
- "Редактировать" button is replaced with two buttons:
  - "Отмена" (Cancel) - styled as secondary/default button
  - "Сохранить" (Save) - styled as primary button
- Input fields appear for each metric (if not visible before)
- Input fields are enabled for editing
- Existing values (if any) remain populated in fields
- Cursor focus may move to first input field
- Dialog remains open

**Verification Points**:
- Button text changes from "Редактировать" to "Отмена" and "Сохранить"
- Input fields are interactive (clickable, typeable)
- No validation errors appear prematurely
- Alert message about missing metrics persists

**Current Implementation Note**:
Based on exploration, clicking "Редактировать" shows Cancel/Save buttons, but the actual input fields for each metric may not be immediately visible in the accessibility tree. Further investigation needed to determine if fields are rendered as:
- Number input fields (`<input type="number">`)
- Text input fields with numeric validation
- Custom Element Plus components (el-input-number)

---

### 6.4 Manually Enter Valid Metric Values

**Objective**: Verify that users can enter valid numeric metric values in the range 1.0-10.0.

**Steps**:
1. Enable edit mode (click "Редактировать")
2. Locate input field for "Коммуникабельность (балл)"
3. Click on the input field
4. Clear any existing value
5. Type value: `7.5`
6. Press Tab or click next field
7. For "Командность (балл)", enter value: `8.0`
8. For "Ответственность (балл)", enter value: `6.5`
9. For "Лидерство (балл)", enter value: `9.0`
10. For "Стрессоустойчивость (балл)", enter value: `7.0`
11. Continue entering values for all 13 metrics
12. Click "Сохранить" button

**Sample Metric Values**:
- Коммуникабельность: 7.5
- Комплексное решение проблем: 6.0
- Обработка информации: 8.0
- Лидерство: 9.0
- Конфликтность (низкая): 7.5
- Моральность / Нормативность: 8.5
- Невербальная логика: 6.5
- Организованность: 7.0
- Ответственность: 6.5
- Стрессоустойчивость: 7.0
- Роль «Душа команды» (Белбин): 8.0
- Командность: 8.0
- Лексика: 7.5

**Expected Results**:
- All valid values are accepted without errors
- Input fields accept decimal values (e.g., 7.5, 8.0, 6.5)
- Values are displayed in input fields as typed
- No validation errors appear during entry
- After clicking "Сохранить":
  - Toast/alert notification appears: "Метрики сохранены успешно" or similar
  - Dialog may close automatically
  - If dialog remains open, edit mode is disabled and values are shown in read-only mode
  - Database records are created/updated in `extracted_metric` table
  - Metric source is set to "MANUAL" or "USER"
  - Confidence is set to 1.0 for manual entries

**Verification Points**:
- Input accepts both integer (e.g., 8) and decimal (e.g., 8.5) formats
- Decimal precision is limited (typically 1 decimal place)
- Tab navigation works between fields
- Values persist in UI after save
- Backend API is called: `POST /api/reports/{report_id}/metrics` or similar
- Response status: 200 OK or 201 Created

---

### 6.5 Validate Input Restrictions - Maximum Value

**Objective**: Verify that values above 10.0 are rejected with appropriate error message.

**Steps**:
1. Enable edit mode
2. Locate input field for "Коммуникабельность (балл)"
3. Enter value: `11.0`
4. Attempt to move to next field or save

**Expected Results**:
- Validation error appears immediately or on blur/save attempt
- Error message indicates valid range: "Значение должно быть от 1 до 10" or "Максимум 10"
- Field is highlighted with error state (red border, error icon)
- "Сохранить" button may be disabled while error exists
- Value is not saved to database

**Additional Test Cases**:
- Enter `15.5` - rejected
- Enter `100` - rejected
- Enter `10.1` - rejected (just above max)

**Verification Points**:
- Error message is clear and localized (Russian)
- Multiple fields can show errors simultaneously
- Errors persist until corrected
- Field validation occurs on blur or on save attempt

---

### 6.6 Validate Input Restrictions - Minimum Value

**Objective**: Verify that values below 1.0 are rejected.

**Steps**:
1. Enable edit mode
2. Enter value: `0.5` in any metric field
3. Attempt to save

**Expected Results**:
- Validation error: "Значение должно быть от 1 до 10" or "Минимум 1"
- Field shows error state
- Value is not saved

**Additional Test Cases**:
- Enter `0` - rejected
- Enter `0.9` - rejected (just below min)
- Enter `-5.0` - rejected (negative value)
- Enter `1.0` - accepted (boundary value)
- Enter `10.0` - accepted (boundary value)

---

### 6.7 Validate Input Restrictions - Non-Numeric Values

**Objective**: Verify that non-numeric input is rejected.

**Steps**:
1. Enable edit mode
2. Enter value: `abc` in a metric field
3. Attempt to save

**Expected Results**:
- Input is either:
  - A) Prevented from being typed (numeric-only field)
  - B) Shows validation error on blur/save
- Error message: "Введите число" or "Неверный формат"
- Value is not saved

**Additional Test Cases**:
- Enter `seven` - rejected
- Enter `7,5` (comma instead of dot) - may be accepted and converted, or rejected depending on locale
- Enter `7.5.3` - rejected (invalid number format)
- Enter special characters: `!@#$%` - rejected

---

### 6.8 Save Partial Metrics

**Objective**: Verify system behavior when only some metrics are filled.

**Steps**:
1. Enable edit mode
2. Enter values for only 3 metrics out of 13
3. Leave remaining 10 fields empty
4. Click "Сохранить"

**Expected Results**:
- Either:
  - **A) Partial save allowed**:
    - Success message appears
    - Only filled metrics are saved to database
    - Empty metrics remain null or are not inserted
    - Warning may appear: "Не все метрики заполнены"
  - **B) Validation requires all metrics**:
    - Error message: "Заполните все метрики"
    - Save is prevented
    - Empty fields are highlighted

**Verification Points**:
- If partial save allowed:
  - Scoring calculation later will check for required metrics
  - Missing metrics prevent score calculation
- If all metrics required:
  - Clear indication of which fields are missing
  - User can identify and fill missing fields

**Note**: Based on domain requirements (scoring requires all metrics from weight table), full validation is likely enforced.

---

### 6.9 Cancel Edit Mode

**Objective**: Verify that clicking "Отмена" discards unsaved changes.

**Steps**:
1. Enable edit mode
2. Enter new values in several metric fields (do not save)
3. Click "Отмена" button

**Expected Results**:
- Edit mode is disabled
- Input fields revert to read-only mode (or become hidden)
- "Отмена" and "Сохранить" buttons are replaced with "Редактировать" button
- All unsaved changes are discarded
- Original values (if any) are restored
- No database changes occur
- No confirmation dialog appears (changes are lost immediately)

**Alternative Behavior**:
- Confirmation dialog may appear: "Отменить изменения? Несохранённые данные будут потеряны."
  - "Да, отменить" - discards changes
  - "Продолжить редактирование" - returns to edit mode

**Verification Points**:
- No API calls are made on cancel
- Values revert to previous state
- User can re-enable edit mode with "Редактировать"

---

### 6.10 Edit Existing Metrics

**Objective**: Verify that previously saved metrics can be edited and updated.

**Preconditions**:
- Metrics have been saved previously (either auto-extracted or manually entered)

**Steps**:
1. Open metrics dialog for report with existing metrics
2. Verify existing values are displayed
3. Click "Редактировать"
4. Modify value for "Коммуникабельность" from `7.5` to `8.5`
5. Modify value for "Лидерство" from `9.0` to `8.0`
6. Leave other values unchanged
7. Click "Сохранить"

**Expected Results**:
- Existing values populate input fields on edit mode entry
- Modified values are accepted
- Unmodified values remain unchanged
- Success message appears
- Database updates only modified metrics
- Update timestamp is recorded
- Source may change to "MANUAL" or remain as original with updated timestamp
- Confidence may update to 1.0 for manually edited values

**Verification Points**:
- API call: `PUT /api/reports/{report_id}/metrics` or `PATCH /api/reports/{report_id}/metrics`
- Only changed metrics are sent in request body (efficient update)
- Or all metrics are sent (full replacement)
- Response includes updated metrics with new values

---

### 6.11 Close Metrics Dialog

**Objective**: Verify that the metrics dialog can be closed without saving changes.

**Steps**:
1. Open metrics dialog
2. Enable edit mode and make some changes
3. Click the close button (X) in top-right corner of dialog

**Expected Results**:
- Either:
  - **A) Dialog closes immediately**:
    - Unsaved changes are lost
    - No confirmation dialog
  - **B) Confirmation dialog appears**:
    - Message: "У вас есть несохранённые изменения. Закрыть без сохранения?"
    - "Да, закрыть" - closes dialog, discards changes
    - "Отмена" - keeps dialog open

**After dialog closes**:
- User returns to participant detail page
- Reports table is still visible
- Metrics button is still available for re-opening dialog

**Verification Points**:
- Clicking outside dialog (backdrop) may also close it
- ESC key may close dialog (depending on Element Plus configuration)
- Close behavior is consistent across different close methods (X button, ESC, backdrop)

---

### 6.12 Verify Metrics Persistence After Dialog Reopen

**Objective**: Verify that saved metrics persist and are displayed when dialog is reopened.

**Steps**:
1. Open metrics dialog
2. Enable edit mode
3. Enter values for all metrics
4. Click "Сохранить"
5. Wait for success confirmation
6. Close metrics dialog (X button or backdrop)
7. Reopen metrics dialog by clicking "Метрики" button again

**Expected Results**:
- Dialog opens with all previously saved metrics displayed
- Values match what was saved earlier
- Metrics are in read-only mode initially
- "Редактировать" button is available
- No alert about missing metrics (since metrics now exist)
- Source and confidence indicators (if shown) reflect saved data

**Verification Points**:
- Data is fetched from database, not cached in browser
- API call on dialog open: `GET /api/reports/{report_id}/metrics`
- Response includes all 13 metrics with values, sources, and confidence scores
- UI correctly renders all fetched data

---

### 6.13 Metrics Dialog Layout and Responsiveness

**Objective**: Verify that the metrics dialog has a professional, user-friendly layout.

**Steps**:
1. Open metrics dialog
2. Observe layout and styling
3. Resize browser window (if testing responsiveness)

**Expected Results - Dialog Layout**:
- Dialog width: 600-800px (responsive to screen size)
- Dialog height: auto or max-height with scroll if content exceeds viewport
- Header section:
  - Heading "Метрики отчёта" aligned left
  - Close button (X) aligned right
- Subheader section:
  - Label "Ручной ввод метрик" aligned left
  - "Редактировать" / "Отмена" + "Сохранить" buttons aligned right
- Content section:
  - Alert message (if metrics not extracted) - full width, blue info style
  - Metrics grid/list:
    - 13 metric fields arranged in columns (e.g., 2-4 columns)
    - Each metric has label above or beside input field
    - Fields have consistent spacing and alignment
- Footer section (optional):
  - May contain additional action buttons or help text

**Responsiveness**:
- On smaller screens (< 768px), metrics stack into single column
- Dialog adapts to mobile viewport (full-screen or near full-screen)
- Buttons stack vertically on narrow screens

**Styling**:
- Uses Element Plus component library styling
- Consistent colors, fonts, and spacing
- Input fields have clear borders and focus states
- Error states use red color scheme
- Success states use green color scheme

**Verification Points**:
- Dialog is accessible (keyboard navigation works)
- Labels are properly associated with input fields (for screen readers)
- Focus management: first field receives focus on edit mode entry
- Visual hierarchy is clear (important elements stand out)

---

### 6.14 Metrics Dialog Accessibility

**Objective**: Verify that the metrics dialog is accessible to users with disabilities.

**Steps**:
1. Open metrics dialog
2. Use keyboard only (no mouse) to navigate
3. Test with screen reader (optional, if available)

**Expected Results - Keyboard Navigation**:
- Tab key moves focus between interactive elements in logical order:
  - Close button (X)
  - "Редактировать" button
  - Each metric input field (when in edit mode)
  - "Отмена" button
  - "Сохранить" button
- Shift+Tab moves focus backward
- Enter key activates focused button
- ESC key closes dialog
- Input fields accept keyboard input
- Error messages are announced (if using ARIA live regions)

**Accessibility Attributes**:
- Dialog has `role="dialog"` and `aria-modal="true"`
- Dialog has `aria-labelledby` pointing to heading
- Input fields have associated labels (implicit or explicit)
- Error messages have `aria-live="assertive"` or similar
- Buttons have descriptive text or aria-labels

**Verification Points**:
- No keyboard traps (user can always navigate away)
- Focus returns to trigger button when dialog closes
- Color is not the only indicator of errors (icons or text also present)
- Text has sufficient contrast ratio (WCAG AA minimum)

---

## Edge Cases and Error Scenarios

### 6.15 Network Error During Save

**Steps**:
1. Enable edit mode and enter valid values
2. Simulate network failure (disconnect WiFi or use browser DevTools to block requests)
3. Click "Сохранить"

**Expected Results**:
- Save fails
- Error message appears: "Ошибка сохранения. Проверьте подключение к сети."
- Values remain in input fields (not lost)
- User can retry save after network is restored
- Dialog remains open

---

### 6.16 Concurrent Edits (Multi-User Scenario)

**Preconditions**:
- Two users have the same report metrics dialog open

**Steps**:
1. User A opens metrics dialog and enables edit mode
2. User B opens metrics dialog for same report and enables edit mode
3. User A changes "Коммуникабельность" to 7.0 and saves
4. User B changes "Коммуникабельность" to 9.0 and attempts to save

**Expected Results**:
- Either:
  - **A) Last write wins**: User B's value (9.0) overwrites User A's value (7.0)
  - **B) Optimistic locking**: User B receives error: "Данные были изменены другим пользователем. Пожалуйста, обновите и попробуйте снова."
  - **C) Merge conflict dialog**: User B is notified of conflict and can choose to overwrite or cancel

**Verification Points**:
- System handles concurrent updates gracefully
- Data integrity is maintained (no corrupt/partial saves)
- Users are informed of conflicts

---

### 6.17 Large Number of Metrics

**Scenario**: Report type with 50+ metrics (stress test)

**Expected Results**:
- Dialog scrolls vertically to accommodate all metrics
- Performance remains acceptable (no lag when scrolling or typing)
- Save operation completes within reasonable time (< 5 seconds)
- UI remains responsive

---

### 6.18 Special Characters in Metric Names

**Scenario**: Metric with name containing special characters (e.g., "Роль «Душа команды» (Белбин)")

**Expected Results**:
- Special characters (quotes, parentheses) are rendered correctly
- HTML escaping prevents XSS attacks
- Unicode characters (Cyrillic) display correctly
- No encoding issues (mojibake)

---

### 6.19 Very Long Decimal Values

**Steps**:
1. Enter value: `7.123456789` in a metric field

**Expected Results**:
- Either:
  - **A) Value is rounded/truncated to 1 decimal place**: displays as `7.1`
  - **B) Validation error**: "Максимум 1 знак после запятой"
- Database stores value with appropriate precision (DECIMAL type)
- Calculation uses correct precision (no floating-point errors)

---

### 6.20 Metrics Source and Confidence Display

**Objective**: Verify that metrics show their extraction source and confidence level.

**Preconditions**:
- Report has been processed with Vision extraction
- Some metrics extracted via LLM; others may be empty or manual

**Expected Display Elements** (if implemented):
- Each metric row/field shows:
  - Metric name (label)
  - Current value
- Source badge/icon: "LLM" or "MANUAL"
- Confidence score: "85%" or "0.85" (for LLM extracted)
  - Visual indicator for low confidence (< 80%): yellow/orange highlight, warning icon

**User Actions**:
- Low-confidence metrics are visually distinct
- User is encouraged to review and manually correct flagged metrics
- Manual edits override auto-extracted values and update source to "MANUAL"

**Verification Points**:
- Source is persisted in `extracted_metric.source` field
- Confidence is persisted in `extracted_metric.confidence` field
- UI accurately reflects database values

---

## Integration with Scoring

### 6.21 Verify Metrics Are Used in Scoring Calculation

**Objective**: Confirm that manually entered metrics are used when calculating professional suitability scores.

**Steps**:
1. Enter all 13 metric values manually (scenario 6.4)
2. Save metrics
3. Navigate to participant detail page
4. Click "Рассчитать пригодность" button
5. Select professional activity: "Организация и проведение совещаний"
6. Click "Рассчитать"
7. Wait for calculation to complete

**Expected Results**:
- Calculation succeeds without errors
- Score is calculated using manually entered metric values
- Scoring algorithm: `score_pct = Σ(metric_value × weight) × 10`
- Result is saved with reference to metrics source
- Toast notification: "Расчёт выполнен успешно"

**Example Calculation** (using values from 6.4):
```
Assuming weight table for meeting_facilitation:
- Communicability (7.5) × 0.20 = 1.50
- Teamwork (8.0) × 0.15 = 1.20
- Responsibility (6.5) × 0.15 = 0.975
- Leadership (9.0) × 0.20 = 1.80
- Stress Resistance (7.0) × 0.15 = 1.05
- (Other metrics with their weights...)

score_pct = (sum of weighted values) × 10
Expected score ≈ 70-75% (depends on actual weight table)
```

**Verification Points**:
- API call: `POST /api/scoring/calculate`
- Request includes participant_id and activity_code
- Backend fetches metrics from `extracted_metric` table
- Missing metrics cause error: "Недостаточно данных для расчёта"
- Score is persisted to `scoring_result` table

---

## Success Criteria

### Test Pass Conditions

A test scenario passes if:
1. All steps execute without errors
2. All expected results are observed
3. All verification points are confirmed
4. No unexpected errors appear in browser console or backend logs
5. Database state is consistent after scenario completion
6. Manual changes persist across page reloads and dialog reopens

### Coverage Goals

- **Happy Path**: 100% of scenarios 6.1, 6.3, 6.4, 6.10, 6.12 pass
- **Validation**: 100% of scenarios 6.5, 6.6, 6.7 pass (boundary and error cases)
- **User Experience**: 80% of scenarios 6.9, 6.11, 6.13, 6.14 pass (UX and accessibility)
- **Edge Cases**: 70% of scenarios 6.15-6.20 pass
- **Integration**: Scenario 6.21 passes (metrics used in scoring)

### Performance Benchmarks

- **Dialog Open**: Metrics dialog loads within 1 second
- **Save Operation**: Metrics save completes within 2 seconds
- **Data Fetch**: Metrics are fetched and rendered within 1 second on dialog reopen
- **Validation Feedback**: Input validation errors appear within 500ms of invalid input

---

## Technical Implementation Notes

### Current Implementation Observations

Based on UI exploration (2025-11-09), the following was observed:

**Metrics Dialog Structure**:
- Dialog opened via "Метрики" button on participant detail page (not separate page route)
- Dialog heading: "Метрики отчёта"
- Subheading: "Ручной ввод метрик"
- Alert message for reports without extracted metrics
- Metric labels displayed in groups/columns

**Edit Mode Activation**:
- "Редактировать" button switches to "Отмена" and "Сохранить" buttons
- Actual input field rendering not confirmed in accessibility tree (may use custom components)

**Potential Implementation Gap**:
- The specification describes a separate metrics page (`/reports/{report_id}` or `/participants/{participant_id}/reports/{report_id}`)
- Current implementation uses a modal dialog approach
- Input fields for metrics entry were not visible in accessibility snapshot during exploration
- This may indicate:
  - A) Input fields are custom components not exposed in aria tree
  - B) Implementation is incomplete
  - C) UI uses a different pattern (e.g., inline editing)

**Recommendation**:
- Verify actual input field implementation with frontend code inspection
- Confirm element selectors before writing automated tests
- Check if input fields are Element Plus `<el-input-number>` components
- Test with both keyboard and mouse interaction to ensure full functionality

### API Endpoints (Expected)

Based on architecture documentation:

**Fetch Metrics**:
- `GET /api/reports/{report_id}/metrics`
- Response: Array of metric objects with `metric_code`, `value`, `source`, `confidence`

**Save/Update Metrics**:
- `POST /api/reports/{report_id}/metrics` (create or bulk update)
- `PUT /api/reports/{report_id}/metrics` (full replacement)
- `PATCH /api/reports/{report_id}/metrics/{metric_code}` (update single metric)
- Request body: Array or object with metric values

**Expected Request Format**:
```json
{
  "metrics": [
    {
      "metric_code": "communicability",
      "value": 7.5,
      "source": "MANUAL",
      "confidence": 1.0
    },
    {
      "metric_code": "teamwork",
      "value": 8.0,
      "source": "MANUAL",
      "confidence": 1.0
    }
    // ... remaining metrics
  ]
}
```

**Expected Response**:
```json
{
  "message": "Метрики сохранены успешно",
  "metrics": [ /* updated metric objects */ ]
}
```

### Database Schema

**Table**: `extracted_metric`

**Key Fields**:
- `id` (UUID primary key)
- `report_id` (FK to `report`)
- `metric_def_id` (FK to `metric_def`)
- `value` (DECIMAL, range 1.0-10.0)
- `source` (ENUM: LLM, MANUAL)
- `confidence` (DECIMAL, range 0.0-1.0)
- `created_at` (timestamp)
- `updated_at` (timestamp)

**Constraints**:
- `value` CHECK constraint: `value >= 1.0 AND value <= 10.0`
- Unique index on `(report_id, metric_def_id)` to prevent duplicate metrics

---

## Appendix

### Test Data Reference

**Test Participant**:
- Full Name: `Батура Александр Александрович`
- Birth Date: `1985-06-15`
- External ID: `BATURA_AA_TEST_{timestamp}`

**Test Report**:
- Type: REPORT_1 (Business Report)
- File: `Batura_A.A._Biznes-Profil_Biznes-otchyot_1718107.docx`
- Status: "Загружен" (Uploaded)

**Metric Codes** (from `metric_def` table):
1. `communicability` - Коммуникабельность
2. `complex_problem_solving` - Комплексное решение проблем
3. `information_processing` - Обработка информации
4. `leadership` - Лидерство
5. `conflict_low` - Конфликтность (низкая)
6. `morality` - Моральность / Нормативность
7. `nonverbal_logic` - Невербальная логика
8. `organization` - Организованность
9. `responsibility` - Ответственность
10. `stress_resistance` - Стрессоустойчивость
11. `team_soul_belbin` - Роль «Душа команды» (Белбин)
12. `teamwork` - Командность
13. `vocabulary` - Лексика

---

### Troubleshooting

**Issue**: Metrics dialog opens but shows no input fields

- **Cause**: Input fields may be custom components not rendered in accessibility tree
- **Fix**: Inspect DOM elements directly, check Vue DevTools, verify Element Plus component usage

**Issue**: "Метрики сохранены успешно" appears but values don't persist

- **Cause**: API save succeeded but database transaction rolled back, or cache issue
- **Fix**: Check backend logs for database errors, verify `extracted_metric` table has records

**Issue**: Validation errors don't appear

- **Cause**: Frontend validation not implemented, or validation rules misconfigured
- **Fix**: Check Vue component validation rules, verify Element Plus form validation setup

**Issue**: Cannot edit auto-extracted metrics

- **Cause**: Edit mode not properly toggling input field disabled state
- **Fix**: Verify reactive state management in Vue component, check `:disabled` bindings

---

**Document Version**: 1.0
**Date**: 2025-11-09
**Author**: Test Planning Agent
**Status**: Ready for Review and Implementation

**Note**: This test plan is based on UI exploration and specification review. Some scenarios may need adjustment based on actual implementation. Recommend frontend code review before finalizing automated test scripts.
