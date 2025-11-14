// spec: /Users/maksim/git_projects/workers-prof/e2e/TEST_PLAN_MANUAL_METRICS_ENTRY.md
// seed: e2e/seed.spec.ts

import { test, expect } from '@playwright/test';
import path from 'path';
import { createParticipant, uploadReport } from './fixtures.js';

/**
 * Manual Metrics Entry E2E Tests
 *
 * This test suite covers the complete workflow for manual metrics entry:
 * - Opening the metrics dialog
 * - Enabling edit mode
 * - Entering valid metric values
 * - Validating input restrictions (min/max)
 * - Saving metrics and verifying persistence
 *
 * Prerequisites:
 * - Admin user exists (admin@test.com / admin123)
 * - Test fixture file available at e2e/fixtures/Batura_A.A._Biznes-Profil_Biznes-otchyot_1718107.docx
 */

test.describe('Manual Metrics Entry - Complete Workflow', () => {
  let participantId;
  let reportId;
  const testUserEmail = 'admin@test.com';
  const testUserPassword = 'admin123';
  const fixturePath = path.join(process.cwd(), 'e2e', 'fixtures', 'Batura_A.A._Biznes-Profil_Biznes-otchyot_1718107.docx');

  test.beforeEach(async ({ page }) => {
    // Login as admin
    // Add simple retry to mitigate occasional connection reset during parallel runs
    try {
      await page.goto('http://localhost:9187');
    } catch (e) {
      await page.waitForTimeout(500);
      await page.goto('http://localhost:9187');
    }
    await page.getByRole('button', { name: 'Войти в систему' }).click();
    await page.getByRole('textbox', { name: '*Email' }).fill(testUserEmail);
    await page.getByRole('textbox', { name: '*Пароль' }).fill(testUserPassword);
    await page.getByRole('button', { name: 'Войти' }).click();

    // Wait for successful login
    await expect(page.getByText('Вход выполнен успешно')).toBeVisible();
    await page.waitForURL(/.*\/participants/);
  });

  // См. @tickets/BUG-002_metrics_dialog_not_opening_in_automated_tests.md
  test.fixme('Scenario 6.1: Navigate to Metrics Dialog', async ({ page }) => {
    // Setup: Create participant and upload report via API
    const timestamp = Date.now();
    const participantName = `Тест Метрики Участник ${timestamp}`;
    const externalId = `METRICS_TEST_${timestamp}`;

    const participant = await createParticipant(page.request, participantName, externalId);
    const report = await uploadReport(page.request, participant.id, 'REPORT_1', fixturePath);

    // Navigate to participant detail page
    await page.goto(`http://localhost:9187/participants/${participant.id}`);
    await expect(page.getByRole('heading', { name: participantName, level: 2 })).toBeVisible();

    // Wait for the report table to be visible
    await expect(page.getByRole('button', { name: 'Метрики' }).first()).toBeVisible();

    // Wait for extraction to complete by checking if button is no longer in active state
    await page.waitForTimeout(3000);

    // Step 7: Locate "Метрики" button and click it
    // Use a different approach - click via page.click with text selector
    const metricsButton = page.getByRole('button', { name: 'Метрики' }).first();
    await metricsButton.scrollIntoViewIfNeeded();
    await expect(metricsButton).toBeEnabled();

    // Try clicking multiple times if needed (Vue reactivity issue workaround)
    for (let attempt = 0; attempt < 3; attempt++) {
      await metricsButton.click();
      // Check if dialog appeared
      const dialog = page.getByRole('dialog', { name: 'Метрики отчёта' });
      try {
        await expect(dialog).toBeVisible({ timeout: 2000 });
        break; // Dialog appeared, exit loop
      } catch (e) {
        if (attempt === 2) throw e; // Last attempt failed
        await page.waitForTimeout(500);
      }
    }

    // Step 8: Verify dialog is now visible
    const dialog = page.getByRole('dialog', { name: 'Метрики отчёта' });
    await expect(dialog).toBeVisible();

    // Verify dialog contents
    await expect(page.getByText('Ручной ввод метрик')).toBeVisible();
    await expect(page.getByText('Метрики для этого отчёта ещё не извлечены. Вы можете ввести их вручную.')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Редактировать' })).toBeVisible();

    // Verify metric labels are displayed
    const expectedMetrics = [
      'Коммуникабельность',
      'Комплексное решение проблем',
      'Обработка информации',
      'Лидерство',
      'Конфликтность (низкая)',
      'Моральность / Нормативность',
      'Невербальная логика',
      'Организованность',
      'Ответственность',
      'Стрессоустойчивость',
      'Роль «Душа команды» (Белбин)',
      'Командность',
      'Лексика'
    ];

    for (const metricName of expectedMetrics) {
      await expect(page.getByText(metricName, { exact: false })).toBeVisible();
    }
  });

  // FIXME: Same issue as 6.1 - metrics dialog does not open in automated tests
  test.fixme('Scenario 6.3: Enable Edit Mode', async ({ page }) => {
    // Setup: Create participant and upload report
    await test.step('Setup: Create participant and upload report', async () => {
      const timestamp = Date.now();
      await page.getByRole('button', { name: 'Добавить участника' }).click();
      await page.getByRole('textbox', { name: '*ФИО' }).fill(`Участник ${timestamp}`);
      await page.getByRole('combobox', { name: 'Дата рождения' }).click();
      await page.getByRole('button', { name: /^20\d{2}$/ }).click();
      // Navigate to 1990s decade (3 clicks back from 2020s)
      await page.getByRole('button', { name: 'Предыдущий год' }).click();
      await page.getByRole('button', { name: 'Предыдущий год' }).click();
      await page.getByRole('button', { name: 'Предыдущий год' }).click();
      await page.getByRole('gridcell', { name: '1990' }).click();
      await page.getByRole('gridcell', { name: 'Январь' }).click();
      await page.getByRole('gridcell', { name: '15' }).click();
      await page.getByPlaceholder('Внешний идентификатор (необязательно)').fill(`TEST_${timestamp}`);
      await page.getByRole('button', { name: 'Создать' }).click();
      await expect(page.getByText('Участник создан')).toBeVisible();

      const row = page.getByRole('row', { name: new RegExp(`TEST_${timestamp}`) });
      await row.getByRole('button', { name: 'Открыть' }).click();

      await page.getByRole('button', { name: 'Загрузить отчёт' }).click();
      // Robust select open (combobox → fallback) and option pick (role → fallback)
      {
        const reportTypeCombobox = page.getByRole('combobox', { name: /Тип отчёта|Выберите тип/i });
        if (await reportTypeCombobox.count()) {
          await reportTypeCombobox.first().click();
        } else {
          await page.locator('.el-select .el-select__wrapper, .el-select .el-select__selected-item').first().click();
        }
        const optionByRole = page.getByRole('option', { name: 'Отчёт 1' });
        if (await optionByRole.count()) {
          await optionByRole.first().click();
        } else {
          await page.locator('.el-select-dropdown__item').filter({ hasText: 'Отчёт 1' }).first().click();
        }
      }
      const fileChooserPromise = page.waitForEvent('filechooser');
      await page.getByRole('button', { name: 'Выбрать файл' }).first().click();
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles(fixturePath);
      await page.getByRole('button', { name: 'Загрузить', exact: true }).click();
      await expect(page.getByText('Отчёт загружен успешно')).toBeVisible();
      await page.waitForTimeout(2000); // Wait for extraction to complete
    });

    // Open metrics dialog
    const metricsBtn = page.getByRole('button', { name: 'Метрики' }).first();
    await expect(metricsBtn).toBeEnabled();
    await metricsBtn.click();
    await expect(page.getByRole('dialog', { name: 'Метрики отчёта' })).toBeVisible({ timeout: 10000 });

    // Verify "Редактировать" button is visible and enabled
    const editButton = page.getByRole('button', { name: 'Редактировать' });
    await expect(editButton).toBeVisible();
    await expect(editButton).toBeEnabled();

    // Click "Редактировать"
    await editButton.click();

    // Verify UI changes
    await expect(page.getByRole('button', { name: 'Отмена' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Сохранить' })).toBeVisible();
    await expect(editButton).not.toBeVisible();

    // Verify input fields are enabled
    // Note: Input fields should now be interactive
    const firstInput = page.locator('input[placeholder*="Введите значение"]').first();
    await expect(firstInput).toBeEnabled();
  });

  // FIXME: Same issue as 6.1 - metrics dialog does not open in automated tests
  test.fixme('Scenario 6.4: Manually Enter Valid Metric Values', async ({ page }) => {
    // Setup
    await test.step('Setup: Create participant and upload report', async () => {
      const timestamp = Date.now();
      await page.getByRole('button', { name: 'Добавить участника' }).click();
      await page.getByRole('textbox', { name: '*ФИО' }).fill(`Участник ${timestamp}`);
      await page.getByRole('combobox', { name: 'Дата рождения' }).click();
      await page.getByRole('button', { name: /^20\d{2}$/ }).click();
      // Navigate to 1990s decade (3 clicks back from 2020s)
      await page.getByRole('button', { name: 'Предыдущий год' }).click();
      await page.getByRole('button', { name: 'Предыдущий год' }).click();
      await page.getByRole('button', { name: 'Предыдущий год' }).click();
      await page.getByRole('gridcell', { name: '1990' }).click();
      await page.getByRole('gridcell', { name: 'Январь' }).click();
      await page.getByRole('gridcell', { name: '15' }).click();
      await page.getByPlaceholder('Внешний идентификатор (необязательно)').fill(`TEST_${timestamp}`);
      await page.getByRole('button', { name: 'Создать' }).click();
      await expect(page.getByText('Участник создан')).toBeVisible();

      const row = page.getByRole('row', { name: new RegExp(`TEST_${timestamp}`) });
      await row.getByRole('button', { name: 'Открыть' }).click();

      await page.getByRole('button', { name: 'Загрузить отчёт' }).click();
      {
        const reportTypeCombobox = page.getByRole('combobox', { name: /Тип отчёта|Выберите тип/i });
        if (await reportTypeCombobox.count()) {
          await reportTypeCombobox.first().click();
        } else {
          await page.locator('.el-select .el-select__wrapper, .el-select .el-select__selected-item').first().click();
        }
        const optionByRole = page.getByRole('option', { name: 'Отчёт 1' });
        if (await optionByRole.count()) {
          await optionByRole.first().click();
        } else {
          await page.locator('.el-select-dropdown__item').filter({ hasText: 'Отчёт 1' }).first().click();
        }
      }
      const fileChooserPromise = page.waitForEvent('filechooser');
      await page.getByRole('button', { name: 'Выбрать файл' }).first().click();
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles(fixturePath);
      await page.getByRole('button', { name: 'Загрузить', exact: true }).click();
      await expect(page.getByText('Отчёт загружен успешно')).toBeVisible();
      await page.waitForTimeout(1000);
    });

    // Open metrics dialog and enable edit mode
    await page.getByRole('button', { name: 'Метрики' }).first().click();
    await expect(page.getByRole('dialog', { name: 'Метрики отчёта' })).toBeVisible();
    await page.getByRole('button', { name: 'Редактировать' }).click();

    // Define metric values to enter
    const metricValues = {
      'Коммуникабельность': '7,5',
      'Комплексное решение проблем': '6,0',
      'Обработка информации': '8,0',
      'Лидерство': '9,0',
      'Конфликтность (низкая)': '7,5',
      'Моральность / Нормативность': '8,5',
      'Невербальная логика': '6,5',
      'Организованность': '7,0',
      'Ответственность': '6,5',
      'Стрессоустойчивость': '7,0',
      'Роль «Душа команды» (Белбин)': '8,0',
      'Командность': '8,0',
      'Лексика': '7,5'
    };

    // Enter values for each metric
    for (const [metricName, value] of Object.entries(metricValues)) {
      // Find the form item by label
      const formItem = page.locator('.el-form-item').filter({ hasText: metricName });
      const input = formItem.locator('input[placeholder*="Введите значение"]');

      await expect(input).toBeVisible();
      await input.click();
      await input.fill(value);

      // Verify value is entered
      await expect(input).toHaveValue(value);
    }

    // Save metrics
    await page.getByRole('button', { name: 'Сохранить' }).click();

    // Verify success message
    await expect(page.getByText(/Успешно сохранено \d+ метрик/)).toBeVisible({ timeout: 10000 });

    // Verify edit mode is disabled
    await expect(page.getByRole('button', { name: 'Редактировать' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Сохранить' })).not.toBeVisible();
  });

  // FIXME: Same issue as 6.1 - metrics dialog does not open in automated tests
  test.fixme('Scenario 6.5: Validate Input Restrictions - Maximum Value', async ({ page }) => {
    // Setup
    await test.step('Setup: Create participant and upload report', async () => {
      const timestamp = Date.now();
      await page.getByRole('button', { name: 'Добавить участника' }).click();
      await page.getByRole('textbox', { name: '*ФИО' }).fill(`Участник ${timestamp}`);
      await page.getByRole('combobox', { name: 'Дата рождения' }).click();
      await page.getByRole('button', { name: /^20\d{2}$/ }).click();
      // Navigate to 1990s decade (3 clicks back from 2020s)
      await page.getByRole('button', { name: 'Предыдущий год' }).click();
      await page.getByRole('button', { name: 'Предыдущий год' }).click();
      await page.getByRole('button', { name: 'Предыдущий год' }).click();
      await page.getByRole('gridcell', { name: '1990' }).click();
      await page.getByRole('gridcell', { name: 'Январь' }).click();
      await page.getByRole('gridcell', { name: '15' }).click();
      await page.getByPlaceholder('Внешний идентификатор (необязательно)').fill(`TEST_${timestamp}`);
      await page.getByRole('button', { name: 'Создать' }).click();
      await expect(page.getByText('Участник создан')).toBeVisible();

      const row = page.getByRole('row', { name: new RegExp(`TEST_${timestamp}`) });
      await row.getByRole('button', { name: 'Открыть' }).click();

      await page.getByRole('button', { name: 'Загрузить отчёт' }).click();
      {
        const reportTypeCombobox = page.getByRole('combobox', { name: /Тип отчёта|Выберите тип/i });
        if (await reportTypeCombobox.count()) {
          await reportTypeCombobox.first().click();
        } else {
          await page.locator('.el-select .el-select__wrapper, .el-select .el-select__selected-item').first().click();
        }
        const optionByRole = page.getByRole('option', { name: 'Отчёт 1' });
        if (await optionByRole.count()) {
          await optionByRole.first().click();
        } else {
          await page.locator('.el-select-dropdown__item').filter({ hasText: 'Отчёт 1' }).first().click();
        }
      }
      const fileChooserPromise = page.waitForEvent('filechooser');
      await page.getByRole('button', { name: 'Выбрать файл' }).first().click();
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles(fixturePath);
      await page.getByRole('button', { name: 'Загрузить', exact: true }).click();
      await expect(page.getByText('Отчёт загружен успешно')).toBeVisible();
      await page.waitForTimeout(1000);
    });

    // Open metrics dialog and enable edit mode
    await page.getByRole('button', { name: 'Метрики' }).first().click();
    await expect(page.getByRole('dialog', { name: 'Метрики отчёта' })).toBeVisible();
    await page.getByRole('button', { name: 'Редактировать' }).click();

    // Try to enter value above maximum (11.0)
    const formItem = page.locator('.el-form-item').filter({ hasText: 'Коммуникабельность' }).first();
    const input = formItem.locator('input[placeholder*="Введите значение"]');

    await input.click();
    await input.fill('11,0');

    // Trigger validation by blurring the field
    await input.blur();

    // Verify error message appears
    await expect(page.getByText(/Значение должно быть не больше/)).toBeVisible();

    // Verify input has error state (red border)
    const errorInput = page.locator('.is-invalid');
    await expect(errorInput).toBeVisible();
  });

  // FIXME: Same issue as 6.1 - metrics dialog does not open in automated tests
  test.fixme('Scenario 6.6: Validate Input Restrictions - Minimum Value', async ({ page }) => {
    // Setup
    await test.step('Setup: Create participant and upload report', async () => {
      const timestamp = Date.now();
      await page.getByRole('button', { name: 'Добавить участника' }).click();
      await page.getByRole('textbox', { name: '*ФИО' }).fill(`Участник ${timestamp}`);
      await page.getByRole('combobox', { name: 'Дата рождения' }).click();
      await page.getByRole('button', { name: /^20\d{2}$/ }).click();
      // Navigate to 1990s decade (3 clicks back from 2020s)
      await page.getByRole('button', { name: 'Предыдущий год' }).click();
      await page.getByRole('button', { name: 'Предыдущий год' }).click();
      await page.getByRole('button', { name: 'Предыдущий год' }).click();
      await page.getByRole('gridcell', { name: '1990' }).click();
      await page.getByRole('gridcell', { name: 'Январь' }).click();
      await page.getByRole('gridcell', { name: '15' }).click();
      await page.getByPlaceholder('Внешний идентификатор (необязательно)').fill(`TEST_${timestamp}`);
      await page.getByRole('button', { name: 'Создать' }).click();
      await expect(page.getByText('Участник создан')).toBeVisible();

      const row = page.getByRole('row', { name: new RegExp(`TEST_${timestamp}`) });
      await row.getByRole('button', { name: 'Открыть' }).click();

      await page.getByRole('button', { name: 'Загрузить отчёт' }).click();
      {
        const reportTypeCombobox = page.getByRole('combobox', { name: /Тип отчёта|Выберите тип/i });
        if (await reportTypeCombobox.count()) {
          await reportTypeCombobox.first().click();
        } else {
          await page.locator('.el-select .el-select__wrapper, .el-select .el-select__selected-item').first().click();
        }
        const optionByRole = page.getByRole('option', { name: 'Отчёт 1' });
        if (await optionByRole.count()) {
          await optionByRole.first().click();
        } else {
          await page.locator('.el-select-dropdown__item').filter({ hasText: 'Отчёт 1' }).first().click();
        }
      }
      const fileChooserPromise = page.waitForEvent('filechooser');
      await page.getByRole('button', { name: 'Выбрать файл' }).first().click();
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles(fixturePath);
      await page.getByRole('button', { name: 'Загрузить', exact: true }).click();
      await expect(page.getByText('Отчёт загружен успешно')).toBeVisible();
      await page.waitForTimeout(1000);
    });

    // Open metrics dialog and enable edit mode
    await page.getByRole('button', { name: 'Метрики' }).first().click();
    await expect(page.getByRole('dialog', { name: 'Метрики отчёта' })).toBeVisible();
    await page.getByRole('button', { name: 'Редактировать' }).click();

    // Try to enter value below minimum (0.5)
    const formItem = page.locator('.el-form-item').filter({ hasText: 'Коммуникабельность' }).first();
    const input = formItem.locator('input[placeholder*="Введите значение"]');

    await input.click();
    await input.fill('0,5');

    // Trigger validation by blurring the field
    await input.blur();

    // Verify error message appears
    await expect(page.getByText(/Значение должно быть не меньше/)).toBeVisible();

    // Verify input has error state (red border)
    const errorInput = page.locator('.is-invalid');
    await expect(errorInput).toBeVisible();
  });

  // FIXME: Same issue as 6.1 - metrics dialog does not open in automated tests
  test.fixme('Scenario 6.12: Verify Metrics Persistence After Dialog Reopen', async ({ page }) => {
    // Setup
    await test.step('Setup: Create participant and upload report', async () => {
      const timestamp = Date.now();
      await page.getByRole('button', { name: 'Добавить участника' }).click();
      await page.getByRole('textbox', { name: '*ФИО' }).fill(`Участник ${timestamp}`);
      await page.getByRole('combobox', { name: 'Дата рождения' }).click();
      await page.getByRole('button', { name: /^20\d{2}$/ }).click();
      // Navigate to 1990s decade (3 clicks back from 2020s)
      await page.getByRole('button', { name: 'Предыдущий год' }).click();
      await page.getByRole('button', { name: 'Предыдущий год' }).click();
      await page.getByRole('button', { name: 'Предыдущий год' }).click();
      await page.getByRole('gridcell', { name: '1990' }).click();
      await page.getByRole('gridcell', { name: 'Январь' }).click();
      await page.getByRole('gridcell', { name: '15' }).click();
      await page.getByPlaceholder('Внешний идентификатор (необязательно)').fill(`TEST_${timestamp}`);
      await page.getByRole('button', { name: 'Создать' }).click();
      await expect(page.getByText('Участник создан')).toBeVisible();

      const row = page.getByRole('row', { name: new RegExp(`TEST_${timestamp}`) });
      await row.getByRole('button', { name: 'Открыть' }).click();

      await page.getByRole('button', { name: 'Загрузить отчёт' }).click();
      {
        const reportTypeCombobox = page.getByRole('combobox', { name: /Тип отчёта|Выберите тип/i });
        if (await reportTypeCombobox.count()) {
          await reportTypeCombobox.first().click();
        } else {
          await page.locator('.el-select .el-select__wrapper, .el-select .el-select__selected-item').first().click();
        }
        const optionByRole = page.getByRole('option', { name: 'Отчёт 1' });
        if (await optionByRole.count()) {
          await optionByRole.first().click();
        } else {
          await page.locator('.el-select-dropdown__item').filter({ hasText: 'Отчёт 1' }).first().click();
        }
      }
      const fileChooserPromise = page.waitForEvent('filechooser');
      await page.getByRole('button', { name: 'Выбрать файл' }).first().click();
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles(fixturePath);
      await page.getByRole('button', { name: 'Загрузить', exact: true }).click();
      await expect(page.getByText('Отчёт загружен успешно')).toBeVisible();
      await page.waitForTimeout(1000);
    });

    // Open metrics dialog and enable edit mode
    await page.getByRole('button', { name: 'Метрики' }).first().click();
    await expect(page.getByRole('dialog', { name: 'Метрики отчёта' })).toBeVisible();
    await page.getByRole('button', { name: 'Редактировать' }).click();

    // Enter a few metric values
    const testMetrics = {
      'Коммуникабельность': '7,5',
      'Лидерство': '9,0',
      'Командность': '8,0'
    };

    for (const [metricName, value] of Object.entries(testMetrics)) {
      const formItem = page.locator('.el-form-item').filter({ hasText: metricName });
      const input = formItem.locator('input[placeholder*="Введите значение"]');
      await input.click();
      await input.fill(value);
    }

    // Save metrics
    await page.getByRole('button', { name: 'Сохранить' }).click();
    await expect(page.getByText(/Успешно сохранено/)).toBeVisible({ timeout: 10000 });

    // Close the dialog
    const closeButton = page.locator('.el-dialog__headerbtn');
    await closeButton.first().click();
    await expect(page.getByRole('dialog', { name: 'Метрики отчёта' })).not.toBeVisible();

    // Wait a moment
    await page.waitForTimeout(500);

    // Reopen the metrics dialog
    await page.getByRole('button', { name: 'Метрики' }).first().click();
    await expect(page.getByRole('dialog', { name: 'Метрики отчёта' })).toBeVisible();

    // Verify alert message is gone (metrics now exist)
    await expect(page.getByText('Метрики для этого отчёта ещё не извлечены')).not.toBeVisible();

    // Enable edit mode to see the values
    await page.getByRole('button', { name: 'Редактировать' }).click();

    // Verify the saved values are still present
    for (const [metricName, expectedValue] of Object.entries(testMetrics)) {
      const formItem = page.locator('.el-form-item').filter({ hasText: metricName });
      const input = formItem.locator('input[placeholder*="Введите значение"]');

      // Get the actual value from the input
      const actualValue = await input.inputValue();

      // Verify the value matches (normalize comma/dot)
      expect(actualValue.replace('.', ',')).toBe(expectedValue);
    }

    // Verify source tags are displayed
    await expect(page.getByText('Источник данных:')).toBeVisible();
    await expect(page.getByText('Ручной ввод')).toBeVisible();
  });
});

test.describe('Manual Metrics Entry - Additional Scenarios', () => {
  const testUserEmail = 'admin@test.com';
  const testUserPassword = 'admin123';
  const fixturePath = path.join(process.cwd(), 'e2e', 'fixtures', 'Batura_A.A._Biznes-Profil_Biznes-otchyot_1718107.docx');

  test.beforeEach(async ({ page }) => {
    // Login as admin
    await page.goto('http://localhost:9187');
    await page.getByRole('button', { name: 'Войти в систему' }).click();
    await page.getByRole('textbox', { name: '*Email' }).fill(testUserEmail);
    await page.getByRole('textbox', { name: '*Пароль' }).fill(testUserPassword);
    await page.getByRole('button', { name: 'Войти' }).click();
    await expect(page.getByText('Вход выполнен успешно')).toBeVisible();
    await page.waitForURL(/.*\/participants/);
  });

  // FIXME: Same issue as 6.1 - metrics dialog does not open in automated tests
  test.fixme('Scenario 6.9: Cancel Edit Mode', async ({ page }) => {
    // Setup
    await test.step('Setup: Create participant and upload report', async () => {
      const timestamp = Date.now();
      await page.getByRole('button', { name: 'Добавить участника' }).click();
      await page.getByRole('textbox', { name: '*ФИО' }).fill(`Участник ${timestamp}`);
      await page.getByRole('combobox', { name: 'Дата рождения' }).click();
      await page.getByRole('button', { name: /^20\d{2}$/ }).click();
      // Navigate to 1990s decade (3 clicks back from 2020s)
      await page.getByRole('button', { name: 'Предыдущий год' }).click();
      await page.getByRole('button', { name: 'Предыдущий год' }).click();
      await page.getByRole('button', { name: 'Предыдущий год' }).click();
      await page.getByRole('gridcell', { name: '1990' }).click();
      await page.getByRole('gridcell', { name: 'Январь' }).click();
      await page.getByRole('gridcell', { name: '15' }).click();
      await page.getByPlaceholder('Внешний идентификатор (необязательно)').fill(`TEST_${timestamp}`);
      await page.getByRole('button', { name: 'Создать' }).click();
      await expect(page.getByText('Участник создан')).toBeVisible();

      const row = page.getByRole('row', { name: new RegExp(`TEST_${timestamp}`) });
      await row.getByRole('button', { name: 'Открыть' }).click();

      await page.getByRole('button', { name: 'Загрузить отчёт' }).click();
      await page.locator('div').filter({ hasText: /^Выберите тип$/ }).nth(2).click();
      await page.getByRole('option', { name: 'Отчёт 1' }).click();
      const fileChooserPromise = page.waitForEvent('filechooser');
      await page.getByRole('button', { name: 'Выбрать файл' }).first().click();
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles(fixturePath);
      await page.getByRole('button', { name: 'Загрузить', exact: true }).click();
      await expect(page.getByText('Отчёт загружен успешно')).toBeVisible();
      await page.waitForTimeout(1000);
    });

    // Open metrics dialog and enable edit mode
    await page.getByRole('button', { name: 'Метрики' }).first().click();
    await expect(page.getByRole('dialog', { name: 'Метрики отчёта' })).toBeVisible();
    await page.getByRole('button', { name: 'Редактировать' }).click();

    // Enter some values (don't save)
    const formItem = page.locator('.el-form-item').filter({ hasText: 'Коммуникабельность' }).first();
    const input = formItem.locator('input[placeholder*="Введите значение"]');
    await input.click();
    await input.fill('7,5');

    // Click "Отмена"
    await page.getByRole('button', { name: 'Отмена' }).click();

    // Verify edit mode is disabled
    await expect(page.getByRole('button', { name: 'Редактировать' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Сохранить' })).not.toBeVisible();
    await expect(page.getByRole('button', { name: 'Отмена' })).not.toBeVisible();

    // Verify unsaved changes are discarded
    await page.getByRole('button', { name: 'Редактировать' }).click();
    const inputAfterCancel = formItem.locator('input[placeholder*="Введите значение"]');
    const valueAfterCancel = await inputAfterCancel.inputValue();
    expect(valueAfterCancel).toBe('');
  });

  // FIXME: Same issue as 6.1 - metrics dialog does not open in automated tests
  test.fixme('Scenario 6.11: Close Metrics Dialog', async ({ page }) => {
    // Setup
    await test.step('Setup: Create participant and upload report', async () => {
      const timestamp = Date.now();
      await page.getByRole('button', { name: 'Добавить участника' }).click();
      await page.getByRole('textbox', { name: '*ФИО' }).fill(`Участник ${timestamp}`);
      await page.getByRole('combobox', { name: 'Дата рождения' }).click();
      await page.getByRole('button', { name: /^20\d{2}$/ }).click();
      // Navigate to 1990s decade (3 clicks back from 2020s)
      await page.getByRole('button', { name: 'Предыдущий год' }).click();
      await page.getByRole('button', { name: 'Предыдущий год' }).click();
      await page.getByRole('button', { name: 'Предыдущий год' }).click();
      await page.getByRole('gridcell', { name: '1990' }).click();
      await page.getByRole('gridcell', { name: 'Январь' }).click();
      await page.getByRole('gridcell', { name: '15' }).click();
      await page.getByPlaceholder('Внешний идентификатор (необязательно)').fill(`TEST_${timestamp}`);
      await page.getByRole('button', { name: 'Создать' }).click();
      await expect(page.getByText('Участник создан')).toBeVisible();

      const row = page.getByRole('row', { name: new RegExp(`TEST_${timestamp}`) });
      await row.getByRole('button', { name: 'Открыть' }).click();

      await page.getByRole('button', { name: 'Загрузить отчёт' }).click();
      await page.locator('div').filter({ hasText: /^Выберите тип$/ }).nth(2).click();
      await page.getByRole('option', { name: 'Отчёт 1' }).click();
      const fileChooserPromise = page.waitForEvent('filechooser');
      await page.getByRole('button', { name: 'Выбрать файл' }).first().click();
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles(fixturePath);
      await page.getByRole('button', { name: 'Загрузить', exact: true }).click();
      await expect(page.getByText('Отчёт загружен успешно')).toBeVisible();
      await page.waitForTimeout(2000); // Wait for extraction to complete
    });

    // Open metrics dialog
    const metricsBtn = page.getByRole('button', { name: 'Метрики' }).first();
    await expect(metricsBtn).toBeEnabled();
    await metricsBtn.click();
    await expect(page.getByRole('dialog', { name: 'Метрики отчёта' })).toBeVisible({ timeout: 10000 });

    // Enable edit mode and make changes
    await page.getByRole('button', { name: 'Редактировать' }).click();
    const formItem = page.locator('.el-form-item').filter({ hasText: 'Коммуникабельность' }).first();
    const input = formItem.locator('input[placeholder*="Введите значение"]');
    await input.click();
    await input.fill('7,5');

    // Close dialog using X button
    const closeButton = page.locator('.el-dialog__headerbtn');
    await closeButton.first().click();

    // Verify dialog is closed
    await expect(page.getByRole('dialog', { name: 'Метрики отчёта' })).not.toBeVisible();

    // Verify we're back on participant detail page
    await expect(page.getByText('Отчёты')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Метрики' }).first()).toBeVisible();
  });
});
