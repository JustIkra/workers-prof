// spec: e2e/TEST_PLAN_S3-05_CRITICAL_PATH.md
// seed: e2e/seed.spec.ts

import { test, expect } from '@playwright/test';

test.describe('User Login', () => {
  test('Successful Login with Approved User', async ({ page }) => {
    // 1. Navigate to http://localhost:9187/login
    await page.goto('http://localhost:9187/login');

    // 2. Type email: testuser@example.com
    await page.getByRole('textbox', { name: '*Email' }).fill('testuser@example.com');

    // 3. Type password: Test1234
    await page.getByRole('textbox', { name: '*Пароль' }).fill('Test1234');

    // 4. Click button "Войти"
    await page.getByRole('button', { name: 'Войти' }).click();

    // 5. Wait for redirect to /participants
    await expect(page).toHaveURL(/\/participants/);

    // 6. Verify user email "testuser@example.com" is visible in navigation
    await expect(page.getByRole('button', { name: 'testuser@example.com' })).toBeVisible();

    // Verify "Админ" menu is NOT visible (non-admin user)
    await expect(page.getByRole('menuitem', { name: 'Админ' })).not.toBeVisible();
  });
});
