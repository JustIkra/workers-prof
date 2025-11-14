# Workers-Prof Application - Scenario 7: Calculate Score - Comprehensive Test Plan

## Application Overview

The **Workers-Prof** scoring calculation feature allows users to assess a participant's professional suitability for specific professional activities. The system uses a weighted formula that combines metric values with activity-specific weights to calculate a percentage score representing professional fit.

**Key Features:**
- **Professional Activity Selection**: Choose from available professional activities (e.g., "Организация и проведение совещаний")
- **Weighted Scoring Algorithm**: Uses formula `score_pct = Σ(metric_value × weight) × 10`
- **Prerequisites Validation**: Ensures reports are uploaded and metrics are entered before calculation
- **Results Display**: Shows calculated score with strengths and development areas
- **Error Handling**: Provides clear feedback for missing data or calculation errors

---

## Test Execution Environment

- **Application URL**: http://localhost:9187
- **Test User**: testuser@example.com / Test1234
- **Professional Activity Code**: meeting_facilitation
- **Professional Activity Name**: Организация и проведение совещаний
- **Expected Score Range**: 70-75% (based on sample metric values)

---

## Test Scenarios

### Scenario 7: Calculate Score

**Seed**: `e2e/seed.spec.ts`

**Test Objectives:**
1. Verify the scoring calculation dialog opens correctly
2. Test professional activity selection from dropdown
3. Validate the scoring calculation process
4. Verify error handling for missing or incomplete data
5. Confirm calculation results are displayed accurately
6. Test edge cases (no metrics, partial metrics, no reports)

---

### 7.1 Open Calculate Score Dialog

**Preconditions:**
- User is logged in as `testuser@example.com`
- Participant "Тестов Тест Тестович" exists in the system
- User is on the participant detail page (`/participants/{participant_id}`)

**Steps:**
1. Verify you are on the participant detail page
2. Verify participant name "Тестов Тест Тестович" is displayed in the heading
3. Locate button with text "Рассчитать пригодность" in the action buttons area
4. Verify button is visible and enabled
5. Click button "Рассчитать пригодность"
6. Wait for dialog to appear

**Expected Results:**
- Dialog opens with heading "Рассчитать профессиональную пригодность"
- Dialog contains:
  - Label "*Профессиональная область" (marked as required with asterisk)
  - Combobox/dropdown for professional activity selection
  - Placeholder text "Выберите область" in the dropdown
  - Information alert with text: "Убедитесь, что у участника загружены и обработаны отчёты с метриками"
  - Button "Отмена" (Cancel)
  - Button "Рассчитать" (Calculate) - initially **disabled**
  - Close dialog button (X) in top-right corner

**Verification Points:**
- Dialog appears as modal overlay (background is dimmed)
- Calculate button is disabled until an activity is selected
- Dialog is properly centered on screen
- All text is in Russian (Cyrillic characters display correctly)

---

### 7.2 Select Professional Activity

**Preconditions:**
- Calculate Score dialog is open (from 7.1)

**Steps:**
1. Verify combobox labeled "*Профессиональная область" is visible
2. Click on the combobox to expand dropdown
3. Wait for dropdown options to appear

**Expected Results:**
- Dropdown expands and displays list of available professional activities
- List contains at least one option: "Организация и проведение совещаний"
- Each option shows:
  - **Primary text**: Professional activity name (e.g., "Организация и проведение совещаний")
  - **Secondary text/code**: Activity code in smaller font (e.g., "meeting_facilitation")
- Options are displayed in a scrollable list if more than ~10 items
- Currently selected option is highlighted or shows checkmark

**Verification Points:**
- Dropdown loads within 2 seconds
- No loading errors appear in console
- Activity codes are displayed correctly
- Professional activities are loaded from database (`prof_activity` table)

**Steps (continued):**
4. Locate option "Организация и проведение совещаний meeting_facilitation"
5. Verify code "meeting_facilitation" appears below the name
6. Click on the option to select it
7. Wait for dropdown to close

**Expected Results:**
- Dropdown closes
- Selected activity appears in the combobox: "Организация и проведение совещаний"
- Button "Рассчитать" becomes **enabled** (clickable)
- Button styling changes to indicate active state (color change, cursor: pointer)

**Verification Points:**
- Selected value persists in the combobox
- No validation errors appear
- Calculate button is now clickable

---

### 7.3 Calculate Suitability Score - Happy Path

**Preconditions:**
- User is logged in
- Participant exists with:
  - At least one uploaded report (status: "Загружен" or "Обработан")
  - All required metrics entered manually or extracted automatically
  - Metrics include all metrics defined in the weight table for "meeting_facilitation"
- Calculate Score dialog is open
- Professional activity "Организация и проведение совещаний" is selected

**Sample Metric Values** (for reference):
- Коммуникабельность (Communicability): 7.5
- Работа в команде (Teamwork): 6.5
- Ответственность (Responsibility): 8.0
- Лидерство (Leadership): 7.0
- Стрессоустойчивость (Stress Resistance): 7.5
- Тайм-менеджмент (Time Management): 6.0

**Steps:**
1. In the Calculate Score dialog, verify "Организация и проведение совещаний" is selected
2. Verify button "Рассчитать" is enabled
3. Click button "Рассчитать"
4. Observe dialog behavior

**Expected Results:**
- Dialog shows loading state or spinner (optional)
- API request is sent: `POST /api/scoring/calculate`
- Request payload includes:
  ```json
  {
    "participant_id": "{participant_uuid}",
    "activity_code": "meeting_facilitation"
  }
  ```
- Response status: 200 OK
- Response includes:
  ```json
  {
    "score_pct": 71.0,
    "strengths": [...],
    "dev_areas": [...],
    "calculated_at": "2025-11-09T17:00:00Z"
  }
  ```

**Steps (continued):**
5. Wait for calculation to complete (typically 2-5 seconds)
6. Observe toast notification

**Expected Results:**
- Toast notification appears with success message: "Расчёт выполнен успешно" or "Пригодность рассчитана"
- Dialog closes automatically
- User is returned to participant detail page
- Page shows updated "Результаты профпригодности" section (if UI supports it)

**Verification Points:**
- Calculation completes within 5 seconds
- No errors appear in browser console
- Backend logs show successful calculation
- Database record created in `scoring_result` table with:
  - `participant_id`: matches participant UUID
  - `activity_code`: "meeting_facilitation"
  - `score_pct`: calculated percentage (e.g., 71.00)
  - `recommendations`: JSON with strengths and dev_areas
  - `created_at`: current timestamp

**Expected Score Calculation:**
Using the formula: `score_pct = Σ(metric_value × weight) × 10`

Assuming weight table for `meeting_facilitation`:
- Communicability (0.20) × 7.5 = 1.5
- Teamwork (0.15) × 6.5 = 0.975
- Responsibility (0.15) × 8.0 = 1.2
- Leadership (0.20) × 7.0 = 1.4
- Stress Resistance (0.15) × 7.5 = 1.125
- Time Management (0.15) × 6.0 = 0.9

**Sum**: 7.1
**Score**: 7.1 × 10 = **71.0%**

**Tolerance**: ±2% due to possible variations in weight table or metric rounding

---

### 7.4 View Calculation Results on Participant Page

**Preconditions:**
- Scoring calculation completed successfully (from 7.3)
- User is on participant detail page

**Steps:**
1. Scroll down on participant detail page
2. Locate section with heading "Результаты профпригодности" or "Расчёты пригодности"
3. Verify section displays scoring results

**Expected Results:**
- Section is visible below the reports table
- Table or card layout shows:
  - **Professional Activity Name**: "Организация и проведение совещаний"
  - **Activity Code**: "meeting_facilitation" (may be hidden or shown in tooltip)
  - **Score Percentage**: "71%" or "71.0%" (formatted as percentage)
  - **Calculation Date**: Current date/time (e.g., "09.11.2025, 17:00")
  - **Action Buttons**:
    - "Просмотреть JSON" (View JSON)
    - "Скачать HTML" (Download HTML)
- Score may be color-coded:
  - Green: ≥70%
  - Yellow: 50-69%
  - Red: <50%

**Verification Points:**
- Score matches expected calculation (71% ± 2%)
- Buttons are enabled and clickable
- Multiple scoring results can be displayed if calculated for different activities
- Most recent calculation appears first or is highlighted

---

### 7.5 Calculate Score - Error: No Reports Uploaded

**Preconditions:**
- User is logged in
- Participant exists with **no reports** uploaded
- User is on participant detail page

**Steps:**
1. Click button "Рассчитать пригодность"
2. Verify dialog opens
3. Select professional activity "Организация и проведение совещаний"
4. Click button "Рассчитать"
5. Observe response

**Expected Results:**
- One of the following behaviors occurs:
  - **Option A**: Error toast appears: "У участника нет загруженных отчётов" or "Недостаточно данных для расчёта"
  - **Option B**: Dialog shows warning alert before calculation: "У участника нет загруженных отчётов"
  - **Option C**: System automatically redirects user to metrics entry dialog
- Calculation does NOT proceed
- No database record is created in `scoring_result` table
- User remains on participant detail page

**Verification Points:**
- Error message is clear and actionable
- Dialog does not close unexpectedly
- User can dismiss dialog and upload reports
- No partial or invalid scoring results are saved

---

### 7.6 Calculate Score - Error: No Metrics Entered

**Preconditions:**
- User is logged in
- Participant exists with:
  - At least one report uploaded
  - **No metrics entered** (either not extracted or not manually entered)
- User is on participant detail page

**Steps:**
1. Click button "Рассчитать пригодность"
2. Select professional activity "Организация и проведение совещаний"
3. Click button "Рассчитать"
4. Observe response

**Expected Results:**
- Error message appears: "У участника нет метрик для расчёта" or "Метрики не найдены"
- Or system automatically opens "Метрики отчёта" dialog to prompt user to enter metrics
- Toast notification may appear: "Сначала введите метрики"
- Calculation is prevented
- Dialog may remain open or close with error toast

**Verification Points:**
- System guides user to enter metrics
- Error message suggests corrective action
- No scoring result is created with missing data
- User can cancel and navigate to metrics entry page

**Steps (if metrics dialog opens automatically):**
1. Verify "Метрики отчёта" dialog is displayed
2. Verify alert message: "Метрики для этого отчёта ещё не извлечены. Вы можете ввести их вручную."
3. Verify all metric input fields are empty
4. Verify buttons "Отмена" and "Сохранить" are present

**Expected Results:**
- User can enter metrics manually in the dialog
- After entering and saving metrics, user can retry calculation
- System provides seamless workflow from error to correction

---

### 7.7 Calculate Score - Error: Incomplete Metrics

**Preconditions:**
- User is logged in
- Participant exists with:
  - At least one report uploaded
  - **Partial metrics entered** (e.g., only 5 out of 13 required metrics for "meeting_facilitation")
- User is on participant detail page

**Steps:**
1. Click button "Рассчитать пригодность"
2. Select professional activity "Организация и проведение совещаний"
3. Click button "Рассчитать"
4. Observe response

**Expected Results:**
- Error message appears: "Не все метрики доступны для расчёта" or "Не хватает данных для расчёта"
- Error may list missing metrics:
  - Example: "Отсутствуют метрики: Лидерство, Тайм-менеджмент, Организованность"
- Calculation is prevented
- Toast notification with error details
- Dialog closes or remains open with error state

**Verification Points:**
- System identifies which specific metrics are missing
- Error message is informative and actionable
- User can return to metrics entry to complete missing values
- No partial score is calculated or displayed

**Steps (alternative flow):**
1. If system allows partial calculation with warning
2. Verify warning message: "Некоторые метрики отсутствуют. Расчёт может быть неточным."
3. Verify user can proceed at their own risk
4. Scoring result is flagged as incomplete or low confidence

---

### 7.8 Calculate Score - Error: No Active Weight Table

**Preconditions:**
- User is logged in
- Participant exists with all metrics entered
- Professional activity "meeting_facilitation" has **no active weight table** in the database
- User is on participant detail page

**Steps:**
1. Click button "Рассчитать пригодность"
2. Attempt to select "Организация и проведение совещаний" from dropdown
3. Observe dropdown state

**Expected Results (Option A - Prevention at Selection):**
- Dropdown shows "Организация и проведение совещаний" but:
  - Option is **disabled** (grayed out)
  - Tooltip or warning icon appears: "Нет активной весовой таблицы"
  - User cannot select this activity

**Expected Results (Option B - Error After Selection):**
- User can select the activity
- Click "Рассчитать"
- Error message appears: "Весовая таблица для данной области не найдена" or "Невозможно выполнить расчёт"
- Calculation is prevented
- Dialog remains open or closes with error toast

**Verification Points:**
- System checks for active weight table before calculation
- Error message is clear: "Please contact administrator to configure weight table"
- Backend logs the missing configuration error
- User cannot proceed with calculation
- Admin is notified (if notification system exists)

---

### 7.9 Calculate Score - Cancel Dialog

**Preconditions:**
- Calculate Score dialog is open
- Professional activity may or may not be selected

**Steps:**
1. In the dialog, locate button "Отмена"
2. Click button "Отмена"
3. Observe dialog behavior

**Expected Results:**
- Dialog closes immediately
- No calculation is performed
- No API request is sent
- User returns to participant detail page
- Page state is unchanged (no data saved)

**Verification Points:**
- Cancel action is instantaneous (no loading state)
- No side effects occur
- User can reopen dialog and selections are reset

**Steps (alternative - Close via X button):**
1. In the dialog, locate close button (X) in top-right corner
2. Click the X button
3. Observe behavior

**Expected Results:**
- Same as clicking "Отмена"
- Dialog closes without saving
- No calculation performed

**Steps (alternative - Close via backdrop click):**
1. Click outside the dialog on the dimmed background
2. Observe behavior

**Expected Results:**
- Dialog closes (if backdrop close is enabled)
- Or dialog remains open (if backdrop close is disabled for this dialog)
- No calculation performed if closed via backdrop

---

### 7.10 Calculate Score - Multiple Calculations for Different Activities

**Preconditions:**
- User is logged in
- Participant exists with all metrics entered
- Multiple professional activities are available (e.g., "meeting_facilitation", "project_management")
- User has already calculated score for "meeting_facilitation" (from 7.3)

**Steps:**
1. On participant detail page, click button "Рассчитать пригодность" again
2. Verify dialog opens
3. Click combobox "*Профессиональная область"
4. Select a different activity (e.g., "Project Management" if available)
5. Click button "Рассчитать"
6. Wait for calculation to complete
7. Verify toast notification: "Расчёт выполнен успешно"
8. Return to participant detail page
9. Scroll to "Результаты профпригодности" section

**Expected Results:**
- Section now shows **two** scoring results:
  - Result 1: "Организация и проведение совещаний" - 71%
  - Result 2: "Project Management" - [calculated score]
- Each result has independent action buttons
- Results are sorted by calculation date (most recent first)
- User can view JSON or download HTML for each result separately
- Database contains two records in `scoring_result` table for the same participant

**Verification Points:**
- System allows multiple scoring calculations for the same participant
- Each calculation is independent and stored separately
- Results do not overwrite each other
- User can compare scores across different professional activities

---

### 7.11 Calculate Score - Recalculate for Same Activity

**Preconditions:**
- User is logged in
- Participant exists with scoring result already calculated for "meeting_facilitation"
- User modifies one or more metric values (e.g., changes Communicability from 7.5 to 8.5)

**Steps:**
1. After modifying metrics, click button "Рассчитать пригодность"
2. Select "Организация и проведение совещаний" (same activity as before)
3. Click button "Рассчитать"
4. Observe behavior

**Expected Results (Option A - Overwrite Existing Result):**
- Calculation proceeds
- Existing scoring result is **updated** with new score
- Toast notification: "Расчёт обновлён"
- Only one result appears for "meeting_facilitation"
- Updated score reflects new metric values (e.g., 73% instead of 71%)

**Expected Results (Option B - Create New Result with Version):**
- Calculation proceeds
- New scoring result is **created** alongside existing one
- Results section shows:
  - "Организация и проведение совещаний" - 73% (09.11.2025, 18:00) [latest]
  - "Организация и проведение совещаний" - 71% (09.11.2025, 17:00) [previous]
- User can view history of calculations
- Database tracks all versions with timestamps

**Expected Results (Option C - Confirmation Dialog):**
- System detects existing result
- Confirmation dialog appears: "Расчёт для этой области уже существует. Пересчитать?"
- Buttons: "Да, пересчитать" and "Отмена"
- If user confirms, result is updated or new version is created

**Verification Points:**
- System handles recalculation gracefully
- Data integrity is maintained (no orphaned records)
- User is informed of update or versioning behavior
- Updated score is correctly calculated based on new metric values

---

### 7.12 Calculate Score - Validation: Invalid Metric Values

**Preconditions:**
- User is logged in
- Participant exists with metrics entered
- One or more metrics have **invalid values** (e.g., value = 15.0, which is outside range 1.0-10.0)

**Steps:**
1. Ensure at least one metric has invalid value (if manual entry allows it temporarily)
2. Click button "Рассчитать пригодность"
3. Select professional activity "Организация и проведение совещаний"
4. Click button "Рассчитать"
5. Observe response

**Expected Results:**
- Backend validation detects invalid metric values
- Error response: 400 Bad Request
- Error message: "Некорректные значения метрик" or "Metric values must be between 1.0 and 10.0"
- Toast notification with validation error
- Calculation is prevented
- User is prompted to correct metric values

**Verification Points:**
- Backend enforces metric range validation (1.0-10.0)
- Frontend prevents saving invalid values in metrics entry (client-side validation)
- System does not calculate score with invalid data
- Error message identifies which metrics are invalid (if possible)

---

### 7.13 Calculate Score - Empty Participant Name Edge Case

**Preconditions:**
- Participant exists with:
  - Empty or null full name (edge case/data issue)
  - Metrics entered
  - Reports uploaded

**Steps:**
1. Navigate to participant detail page
2. Click button "Рассчитать пригодность"
3. Select professional activity
4. Click button "Рассчитать"
5. Wait for calculation to complete
6. Attempt to download HTML report or view JSON

**Expected Results:**
- Calculation proceeds (participant name is not required for calculation logic)
- Scoring result is created successfully
- Score percentage is calculated correctly
- JSON report shows `participant_name: null` or `participant_name: ""`
- HTML report handles missing name gracefully:
  - Shows placeholder: "Участник без имени" or "N/A"
  - Or displays participant ID instead
- No critical errors occur

**Verification Points:**
- System handles missing participant data gracefully
- Calculation logic is independent of display fields
- Reports are still generated with partial participant info
- User is warned if participant name is missing

---

### 7.14 Calculate Score - Extremely High Score (Edge Case)

**Preconditions:**
- Participant has all metrics set to **10.0** (maximum value)

**Steps:**
1. Enter metrics with all values = 10.0
2. Save metrics
3. Click button "Рассчитать пригодность"
4. Select professional activity "Организация и проведение совещаний"
5. Click button "Рассчитать"
6. Observe calculation result

**Expected Results:**
- Calculation succeeds
- Calculated score: **100.0%**
  - Formula: `Σ(10.0 × weight) × 10 = Σ(weight) × 10 = 1.0 × 10 × 10 = 100.0`
- Score is displayed as "100%" or "100.0%"
- Strengths section includes all or most metrics (since all are high)
- Development areas may be empty or show generic recommendations
- System does not flag this as an error or anomaly

**Verification Points:**
- Calculation handles maximum boundary correctly
- Score does not exceed 100% (no overflow)
- Recommendations are still generated appropriately
- System does not throw errors for perfect scores

---

### 7.15 Calculate Score - Extremely Low Score (Edge Case)

**Preconditions:**
- Participant has all metrics set to **1.0** (minimum value)

**Steps:**
1. Enter metrics with all values = 1.0
2. Save metrics
3. Click button "Рассчитать пригодность"
4. Select professional activity
5. Click button "Рассчитать"
6. Observe calculation result

**Expected Results:**
- Calculation succeeds
- Calculated score: **10.0%**
  - Formula: `Σ(1.0 × weight) × 10 = Σ(weight) × 10 = 1.0 × 10 = 10.0`
- Score is displayed as "10%" or "10.0%"
- Strengths section may be empty or show metrics with least poor scores
- Development areas include most or all metrics
- System does not reject low scores (valid business scenario)

**Verification Points:**
- Calculation handles minimum boundary correctly
- Score is not negative (no underflow)
- Development recommendations are comprehensive
- UI displays low scores clearly (possibly color-coded red)

---

### 7.16 Calculate Score - Rapid Consecutive Calculations (Idempotency Test)

**Preconditions:**
- User is logged in
- Participant has metrics entered

**Steps:**
1. Click button "Рассчитать пригодность"
2. Select professional activity "Организация и проведение совещаний"
3. Click button "Рассчитать"
4. **Immediately** click dialog backdrop or close button (if still visible)
5. Repeat steps 1-3 rapidly **5 times in a row** without waiting for completion
6. Observe system behavior

**Expected Results:**
- System handles concurrent requests gracefully:
  - **Option A**: Only the first calculation proceeds, subsequent requests are queued or ignored
  - **Option B**: Each calculation is processed independently, creating multiple results with same timestamp
  - **Option C**: System shows loading state and prevents additional clicks until current calculation completes
- No duplicate scoring results are created (if Option A or C)
- No database deadlocks or race conditions occur
- All requests complete successfully or are properly rejected
- Final state is consistent (one or more valid scoring results)

**Verification Points:**
- Backend API is idempotent or handles concurrent requests safely
- Frontend disables "Рассчитать" button during calculation
- Database transactions ensure data integrity
- No orphaned or corrupted records in `scoring_result` table

---

## Edge Cases and Error Scenarios Summary

### User Experience Edge Cases

1. **Large Number of Professional Activities**: Dropdown with 50+ activities - verify scrollability and search functionality (if available)
2. **Long Activity Names**: Professional activity with 100+ character name - verify UI layout does not break
3. **Special Characters in Activity Name**: Name contains Cyrillic, emoji, or HTML entities - verify proper encoding
4. **No Professional Activities Available**: Database has zero active activities - verify graceful message: "Нет доступных областей"

### Data Edge Cases

5. **Metric Values with High Precision**: Metrics with values like 7.12345678 - verify rounding to 0.01 precision
6. **Weight Table Sum ≠ 1.0**: Misconfigured weight table (sum of weights = 0.95 or 1.05) - verify validation error
7. **Missing Metric in Weight Table**: Weight table references metric that doesn't exist in database - verify error handling
8. **Circular References**: If metrics can reference other metrics (unlikely) - verify no infinite loops

### Performance Edge Cases

9. **Large Participant Dataset**: Participant with 1000+ reports and metrics - verify calculation performance (<5 seconds)
10. **Network Timeout**: Slow API response - verify frontend shows loading state and timeout message after 30 seconds
11. **Concurrent Users**: Multiple users calculating scores simultaneously - verify no resource conflicts

### Security Edge Cases

12. **Unauthorized Access**: Non-logged-in user attempts API call `POST /api/scoring/calculate` - verify 401 Unauthorized
13. **Calculate Score for Another User's Participant**: User A tries to calculate score for User B's participant - verify 403 Forbidden
14. **SQL Injection in Activity Code**: Attempt to inject SQL via activity code parameter - verify parameterized queries prevent injection
15. **XSS in Professional Activity Name**: Activity name contains `<script>alert('XSS')</script>` - verify HTML escaping

---

## Success Criteria

### Test Pass Conditions

A test scenario passes if:
1. All steps execute without errors
2. All expected results are observed
3. Expected score matches calculated value (±2% tolerance for rounding)
4. Error messages are clear, actionable, and user-friendly
5. No unexpected errors in browser console or backend logs
6. Database state is consistent (no orphaned or duplicate records)
7. UI remains responsive (no freezing or infinite loading states)

### Coverage Goals

- **Happy Path**: Scenario 7.3 (Calculate Suitability Score) passes with correct score calculation
- **Error Handling**: At least 80% of error scenarios (7.5, 7.6, 7.7, 7.8) pass with appropriate messages
- **Edge Cases**: At least 70% of edge cases (7.13-7.16) pass without critical errors
- **User Experience**: All dialog interactions (7.1, 7.2, 7.9) are smooth and intuitive

### Performance Benchmarks

- **Dialog Open Time**: Calculate Score dialog opens within 1 second
- **Dropdown Load Time**: Professional activities dropdown loads within 2 seconds
- **Calculation Time**: Score calculation completes within 5 seconds (95th percentile)
- **Results Display**: Calculation results appear within 1 second after API response

---

## Appendix

### Expected Weight Table for "meeting_facilitation"

**Note**: Actual weights may vary based on database configuration. Verify weights before testing.

| Metric Code           | Metric Name (Russian)            | Weight | Example Value | Weighted Score |
|-----------------------|----------------------------------|--------|---------------|----------------|
| communicability       | Коммуникабельность               | 0.20   | 7.5           | 1.5            |
| teamwork              | Командность                      | 0.15   | 6.5           | 0.975          |
| responsibility        | Ответственность                  | 0.15   | 8.0           | 1.2            |
| leadership            | Лидерство                        | 0.20   | 7.0           | 1.4            |
| stress_resistance     | Стрессоустойчивость              | 0.15   | 7.5           | 1.125          |
| time_management       | Организованность                 | 0.15   | 6.0           | 0.9            |
| **Total**             |                                  | **1.0**| —             | **7.1**        |

**Calculated Score**: 7.1 × 10 = **71.0%**

### API Endpoints Reference

**Calculate Score:**
- **Endpoint**: `POST /api/scoring/calculate`
- **Headers**: `Authorization: Bearer {jwt_token}`
- **Request Body**:
  ```json
  {
    "participant_id": "uuid-string",
    "activity_code": "meeting_facilitation"
  }
  ```
- **Response (Success - 200 OK)**:
  ```json
  {
    "id": "scoring-result-uuid",
    "participant_id": "participant-uuid",
    "activity_code": "meeting_facilitation",
    "activity_name": "Организация и проведение совещаний",
    "score_pct": 71.0,
    "calculated_at": "2025-11-09T17:00:00Z",
    "recommendations": {
      "strengths": [...],
      "dev_areas": [...]
    }
  }
  ```
- **Response (Error - 400 Bad Request)**:
  ```json
  {
    "detail": "Недостаточно данных для расчёта: отсутствуют метрики"
  }
  ```
- **Response (Error - 404 Not Found)**:
  ```json
  {
    "detail": "Весовая таблица не найдена для activity_code=meeting_facilitation"
  }
  ```

### Database Verification Queries

**Check Scoring Result Created:**
```sql
SELECT * FROM scoring_result
WHERE participant_id = '{participant_uuid}'
  AND activity_code = 'meeting_facilitation'
ORDER BY created_at DESC
LIMIT 1;
```

**Verify Weight Table:**
```sql
SELECT * FROM weight_table
WHERE activity_code = 'meeting_facilitation'
  AND is_active = true
ORDER BY created_at DESC
LIMIT 1;
```

**Check Participant Metrics:**
```sql
SELECT em.metric_code, em.value, md.name
FROM extracted_metric em
JOIN metric_def md ON em.metric_code = md.code
WHERE em.participant_id = '{participant_uuid}'
ORDER BY em.metric_code;
```

### Troubleshooting Guide

**Issue**: "Рассчитать" button remains disabled after selecting activity
**Cause**: Validation error or UI state not updated
**Fix**: Check browser console for errors, refresh page, clear local storage

**Issue**: "Недостаточно данных для расчёта" error despite metrics being entered
**Cause**: Metrics not saved to database, or weight table references different metric codes
**Fix**: Verify metrics in database via SQL query, check weight table configuration

**Issue**: Calculated score is 0.0% or 100% unexpectedly
**Cause**: Weight table misconfiguration or metric values not loaded
**Fix**: Verify sum of weights = 1.0, check metric values are in range 1-10

**Issue**: Dialog does not open when clicking "Рассчитать пригодность"
**Cause**: JavaScript error, authentication expired, or API unreachable
**Fix**: Check browser console, verify user is still logged in, test API health

---

**Document Version**: 1.0
**Date**: 2025-11-09
**Author**: Test Planning Team
**Status**: Ready for Implementation
**Related Document**: `/Users/maksim/git_projects/workers-prof/e2e/TEST_PLAN_S3-05_CRITICAL_PATH.md` (Scenario 7, lines 635-746)
