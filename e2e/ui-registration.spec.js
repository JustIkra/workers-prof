// spec: /Users/maksim/git_projects/workers-prof/e2e/TEST_PLAN_S3-05_CRITICAL_PATH.md
// seed: e2e/seed.spec.ts

import { test, expect } from '@playwright/test';

test.describe('User Registration', () => {
  test('User Registration', async ({ page }) => {
    // 1. Navigate to application home page at http://localhost:9187
    await page.goto('http://localhost:9187');

    // 2. Verify landing page displays with heading "Цифровая модель управления компетенциями"
    await expect(page.getByRole('heading', { name: 'Цифровая модель управления компетенциями' })).toBeVisible();

    // 3. Click on "Зарегистрироваться" button
    await page.getByRole('button', { name: 'Зарегистрироваться' }).first().click();

    // 5. Verify registration form displays with heading "Регистрация"
    await expect(page.getByRole('heading', { name: 'Регистрация' })).toBeVisible();

    // 6. In the "*Email" textbox, enter a unique test email address
    const testEmail = `e2e-test-user-${Date.now()}@test.com`;
    await page.getByRole('textbox', { name: '*Email' }).fill(testEmail);

    // 7. In the "*Пароль" textbox, enter a valid password: TestPass123
    await page.getByRole('textbox', { name: '*Пароль' }).fill('TestPass123');

    // 8. In the "*Подтверждение пароля" textbox, enter the same password: TestPass123
    await page.getByRole('textbox', { name: '*Подтверждение пароля' }).fill('TestPass123');

    // 9. Click the "Зарегистрироваться" button to submit the form
    await page.getByRole('button', { name: 'Зарегистрироваться' }).click();

    // Verify successful registration - user is redirected to login page with pending approval message
    await expect(page.getByText('Ваш аккаунт ожидает одобрения администратором.')).toBeVisible();
  });
});
