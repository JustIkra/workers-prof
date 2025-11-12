// spec: e2e/TEST_PLAN_S3-05_CRITICAL_PATH.md
// seed: e2e/seed.spec.ts

import { test, expect } from '@playwright/test';

// Configure this test file to run serially to avoid conflicts
test.describe.configure({ mode: 'serial' });

test.describe('Admin Approval', () => {
  test('Admin Login and User Approval', async ({ page }) => {
    // First, register a user to approve
    const timestamp = Date.now();
    const testEmail = `approval-test-${timestamp}@example.com`;

    await page.goto('http://localhost:9187');
    await page.getByRole('button', { name: 'Зарегистрироваться' }).first().click();
    await page.getByRole('textbox', { name: '*Email' }).fill(testEmail);
    await page.getByRole('textbox', { name: '*Пароль' }).fill('Test1234');
    await page.getByRole('textbox', { name: '*Подтверждение пароля' }).fill('Test1234');

    // Wait for registration API call to complete
    const [response] = await Promise.all([
      page.waitForResponse(resp => resp.url().includes('/api/auth/register')),
      page.getByRole('button', { name: 'Зарегистрироваться' }).click()
    ]);

    // Ensure registration was successful (201 Created)
    expect(response.status()).toBe(201);

    // 1. Navigate to http://localhost:9187/login
    await page.goto('http://localhost:9187/login');

    // 2. Verify heading "Вход в систему" is displayed
    await expect(page.getByRole('heading', { name: 'Вход в систему' })).toBeVisible();

    // 3. Type email: admin@test.com
    await page.getByRole('textbox', { name: '*Email' }).fill('admin@test.com');

    // 4. Type password: admin123
    await page.getByRole('textbox', { name: '*Пароль' }).fill('admin123');

    // 5. Click button "Войти"
    await page.getByRole('button', { name: 'Войти' }).click();

    // 6. Wait for redirect to /participants
    await expect(page).toHaveURL(/\/participants/);

    // 8. Navigate to Admin → Users
    // 9. Click menuitem "Админ" in top navigation
    await page.getByRole('menuitem', { name: 'Админ' }).locator('div').click();

    // 10. Click menuitem "Пользователи"
    await page.getByRole('menuitem', { name: 'Пользователи' }).click();

    // 11. Wait for page load at /admin/users
    await expect(page).toHaveURL(/\/admin\/users/);

    // 12. Verify heading "Управление пользователями" is displayed
    await expect(page.getByRole('heading', { name: 'Управление пользователями' })).toBeVisible();

    // 13. Verify pending user is listed
    await expect(page.getByText(testEmail)).toBeVisible();

    // 14. Click "Одобрить" button next to the user email (find the row with the email)
    const userRow = page.getByRole('row', { name: new RegExp(testEmail) });
    await userRow.getByRole('button', { name: 'Одобрить' }).click();

    // 15. Verify pending users count decreased
    await expect(page.getByRole('heading', { name: /Ожидают одобрения \(\d+\)/ })).toBeVisible();
  });
});
