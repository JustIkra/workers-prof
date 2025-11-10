// spec: e2e/TEST_PLAN_S3-05_CRITICAL_PATH.md
// seed: e2e/seed.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Create Participant', () => {
  test('Successful Participant Creation', async ({ page }) => {
    // Generate unique external ID
    const timestamp = Date.now();
    const externalId = `BATURA_AA_TEST_${timestamp}`;

    // Login as testuser@example.com
    await page.goto('http://localhost:9187/login');
    await page.getByRole('textbox', { name: '*Email' }).fill('testuser@example.com');
    await page.getByRole('textbox', { name: '*Пароль' }).fill('Test1234');
    await page.getByRole('button', { name: 'Войти' }).click();

    // Wait for redirect to participants page
    await expect(page).toHaveURL(/\/participants/);

    // 2. Click button "Добавить участника"
    await page.getByRole('button', { name: 'Добавить участника' }).click();

    // 3. Verify dialog opens with heading "Добавить участника"
    await expect(page.getByRole('heading', { name: 'Добавить участника' })).toBeVisible();

    // 4. Type full name: Батура Александр Александрович
    await page.getByRole('textbox', { name: '*ФИО' }).fill('Батура Александр Александрович');

    // 5. Select birth date: 1985-06-15
    await page.getByRole('combobox', { name: 'Дата рождения' }).click();

    // Navigate to year selection
    await page.getByRole('button', { name: '2025' }).click();

    // Navigate backwards to 1985
    await page.getByRole('button', { name: 'Предыдущий год' }).click();
    await page.getByRole('button', { name: 'Предыдущий год' }).click();
    await page.getByRole('button', { name: 'Предыдущий год' }).click();
    await page.getByRole('button', { name: 'Предыдущий год' }).click();

    // Select 1985
    await page.getByRole('gridcell', { name: '1985' }).click();

    // Select June
    await page.getByRole('gridcell', { name: 'Июнь' }).click();

    // Select day 15
    await page.getByRole('gridcell', { name: '15' }).click();

    // 6. Type external ID: BATURA_AA_TEST
    await page.getByPlaceholder('Внешний идентификатор (необязательно)').fill(externalId);

    // 7. Click button "Создать"
    await page.getByRole('button', { name: 'Создать' }).click();

    // 10. Verify new participant appears in the table
    await expect(page.getByText(externalId).first()).toBeVisible();
    await expect(page.getByText(/Всего \d+/)).toBeVisible();
  });
});
