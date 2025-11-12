// spec: e2e/TEST_PLAN_S3-05_CRITICAL_PATH.md
// seed: e2e/seed.spec.ts

import { test, expect } from '@playwright/test';

test.describe('User Registration', () => {
  test('Successful User Registration', async ({ page }) => {
    // Generate unique email to avoid conflicts
    const timestamp = Date.now();
    const testEmail = `testuser-${timestamp}@example.com`;

    // 1. Navigate to http://localhost:9187
    await page.goto('http://localhost:9187');

    // 2. Verify page displays heading "Цифровая модель управления компетенциями"
    await expect(page.getByRole('heading', { name: 'Цифровая модель управления компетенциями' })).toBeVisible();

    // 3. Click button with text "Зарегистрироваться"
    await page.getByRole('button', { name: 'Зарегистрироваться' }).first().click();

    // 4. Verify redirect to `/register` page
    await page.waitForURL(/\/register/, { timeout: 10000 });
    await expect(page).toHaveURL(/\/register/);

    // 5. Verify heading "Регистрация" is displayed
    await expect(page.getByRole('heading', { name: 'Регистрация' })).toBeVisible();

    // 6. Type email: testuser@example.com
    await page.getByRole('textbox', { name: '*Email' }).fill(testEmail);

    // 7. Type password: Test1234
    await page.getByRole('textbox', { name: '*Пароль' }).fill('Test1234');

    // 8. Type password confirmation: Test1234
    await page.getByRole('textbox', { name: '*Подтверждение пароля' }).fill('Test1234');

    // 9. Click button "Зарегистрироваться" and wait for API response
    const responsePromise = page.waitForResponse(
      response => response.url().includes('/api/auth/register') && response.status() === 201,
      { timeout: 30000 } // 30 second timeout for parallel test execution
    );

    await page.getByRole('button', { name: 'Зарегистрироваться' }).click();

    // Wait for the API call to complete
    await responsePromise;

    // 10. Wait for success message with increased timeout
    await expect(page.getByText('Регистрация успешна! Ожидайте одобрения администратора.')).toBeVisible({ timeout: 10000 });
  });
});
