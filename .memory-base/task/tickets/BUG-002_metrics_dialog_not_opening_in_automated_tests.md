# BUG-002: Metrics Dialog Does Not Open in Automated Tests

**Status:** Open
**Priority:** High
**Component:** Frontend (Vue/Element Plus)
**Affects:** Manual Metrics Entry E2E Tests
**Created:** 2025-11-10

## Summary

The "Метрики отчёта" dialog does not open when clicking the "Метрики" button during automated Playwright test execution, even though the same interaction works correctly in debug mode and manual testing. This prevents automated testing of the manual metrics entry feature.

## Description

When running automated E2E tests for manual metrics entry (`e2e/ui-manual-metrics-entry.spec.js`), all 8 tests fail because the metrics dialog does not open after clicking the "Метрики" button. However, when the same test is run in Playwright debug mode and the button is clicked manually using the browser tools, the dialog opens correctly.

## Steps to Reproduce

1. Run automated E2E tests:
   ```bash
   npx playwright test e2e/ui-manual-metrics-entry.spec.js --project=chromium
   ```

2. Observe that all tests fail with timeout waiting for the dialog:
   ```
   Error: expect(locator).toBeVisible() failed
   Locator: getByRole('dialog', { name: 'Метрики отчёта' })
   Expected: visible
   Timeout: 10000ms
   Error: element(s) not found
   ```

3. Run the same test in debug mode:
   ```bash
   npx playwright test e2e/ui-manual-metrics-entry.spec.js:43 --project=chromium --debug
   ```

4. When the test pauses at the failure point, manually click the "Метрики" button using browser DevTools or evaluate:
   ```javascript
   document.querySelector('button[aria-label="Метрики"]').click()
   ```

5. Observe that the dialog opens successfully.

## Expected Behavior

Clicking the "Метрики" button should open the "Метрики отчёта" dialog consistently in both automated and manual testing.

## Actual Behavior

- **Automated tests:** Button click does not trigger the dialog to open
- **Debug mode:** Button click works correctly
- **Manual testing:** Button click works correctly

## Investigation Findings

### What Works
- The "Метрики" button is visible and enabled
- The button has proper ARIA attributes
- Playwright successfully targets and clicks the button
- In debug/manual mode, the dialog opens immediately when clicked
- All input fields and UI elements render correctly in the dialog

### What Doesn't Work
- Playwright's `locator.click()` does not trigger the dialog in automated runs
- Multiple retry attempts don't help
- Force clicking (`click({ force: true })`) doesn't help
- Scrolling into view before clicking doesn't help

### Attempted Solutions
1. ✗ Using `click({ force: true })`
2. ✗ Scrolling button into view with `scrollIntoViewIfNeeded()`
3. ✗ Adding longer waits (up to 3 seconds) before clicking
4. ✗ Clicking multiple times in a retry loop
5. ✗ Using different selectors (role, text, CSS)
6. ✗ Using API to create test data to reduce UI interactions

## Root Cause Hypothesis

This is likely a **Vue reactivity or Element Plus event handling issue** where:

1. The dialog component's `v-model` or `visible` prop is not reactive to programmatic clicks in headless/automated mode
2. The Element Plus `<el-dialog>` component may have event listener timing issues
3. Vue's event delegation might not fire correctly for automated clicks vs. real user clicks
4. There might be a missing `await nextTick()` or similar in the frontend code

## Evidence

### Screenshot from Failed Test
The test fails showing:
- Page is loaded correctly
- "Метрики" button is visible and enabled
- Toast notification showing "Извлечение метрик запущено" is present
- Dialog is NOT visible in the DOM

### Playwright Debug Session
When manually clicking in debug mode:
- Dialog appears immediately with `role="dialog"` and `name="Метрики отчёта"`
- All 13 metric input fields render correctly
- "Редактировать" button is visible
- Alert message about no extracted metrics is shown

## Impact

- **8 E2E tests** covering manual metrics entry are currently marked as `test.fixme()` and skipped
- Manual metrics entry feature cannot be tested automatically
- Risk of regression if manual metrics functionality breaks

## Affected Tests

All tests in `e2e/ui-manual-metrics-entry.spec.js`:
1. Scenario 6.1: Navigate to Metrics Dialog
2. Scenario 6.3: Enable Edit Mode
3. Scenario 6.4: Manually Enter Valid Metric Values
4. Scenario 6.5: Validate Input Restrictions - Maximum Value
5. Scenario 6.6: Validate Input Restrictions - Minimum Value
6. Scenario 6.9: Cancel Edit Mode
7. Scenario 6.11: Close Metrics Dialog
8. Scenario 6.12: Verify Metrics Persistence After Dialog Reopen

## Recommended Fix

### Frontend Investigation

1. Check the Vue component that handles the "Метрики" button click (likely in `ParticipantDetailView.vue` or similar)
2. Verify the dialog's `v-model` binding and ensure it's properly reactive
3. Add explicit `await nextTick()` calls after state changes
4. Consider if Element Plus `<el-dialog>` needs additional configuration for programmatic opening

### Potential Code Locations

```
frontend/src/views/ParticipantDetailView.vue
frontend/src/components/MetricsEditor.vue
```

### Debugging Steps

1. Add console.log statements to track when button click handler fires
2. Check if `dialogVisible` or similar state variable is being updated
3. Verify Element Plus dialog's `beforeClose` or `beforeOpen` hooks aren't preventing opening
4. Test with a simple button that just sets a state variable to isolate the issue

## Workaround

Currently, tests are marked with `test.fixme()` to skip them during CI runs. Manual testing of the metrics entry feature is required until this bug is fixed.

## Related Files

- `e2e/ui-manual-metrics-entry.spec.js` - Affected test file
- `frontend/src/components/MetricsEditor.vue` - Metrics dialog component
- `frontend/src/views/ParticipantDetailView.vue` - Parent view with button
- `.memory-base/task/tickets/BUG-001_metrics_input_fields_not_rendering.md` - Related (was actually misdiagnosed)

## Next Steps

1. Frontend developer to investigate the button click handler and dialog visibility logic
2. Add explicit state logging to track when dialog should open
3. Test fix with both automated and manual tests
4. Re-enable tests by removing `test.fixme()` once issue is resolved

## Notes

- The dialog functionality itself works perfectly in manual testing
- This is specifically an automated testing issue, not a user-facing bug
- The issue might be environmental (headless browser behavior) rather than code
- Consider if this is a known Element Plus issue with dialog visibility in automated tests
