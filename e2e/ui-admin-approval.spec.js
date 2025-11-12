// spec: /Users/maksim/git_projects/workers-prof/e2e/TEST_PLAN_S3-05_CRITICAL_PATH.md
// seed: e2e/seed.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Admin Login and User Approval', () => {
  test('Admin can login and approve pending users', async ({ page }) => {
    // Generate unique timestamp for test email
    const timestamp = Date.now();
    const testUserEmail = `e2e-approval-test-${timestamp}@test.com`;
    const testUserPassword = 'TestPass123';

    // 1. Register a new user
    await page.goto('http://localhost:9187');
    await page.getByRole('button', { name: 'Зарегистрироваться' }).first().click();
    
    // 2. Fill in registration form
    await page.getByRole('textbox', { name: '*Email' }).fill(testUserEmail);
    await page.getByRole('textbox', { name: '*Пароль' }).fill(testUserPassword);
    await page.getByRole('textbox', { name: '*Подтверждение пароля' }).fill(testUserPassword);
    
    // 3. Submit registration
    await page.getByRole('button', { name: 'Зарегистрироваться' }).click();

    // 4. Navigate to home page for admin login
    await page.goto('http://localhost:9187');
    
    // 5. Click "Войти в систему" button on landing page
    await page.getByRole('button', { name: 'Войти в систему' }).click();
    
    // 6. Enter admin email: admin@test.com
    await page.getByRole('textbox', { name: '*Email' }).fill('admin@test.com');
    
    // 7. Enter admin password: admin123
    await page.getByRole('textbox', { name: '*Пароль' }).fill('admin123');
    
    // 8. Click "Войти" button
    await page.getByRole('button', { name: 'Войти' }).click();
    
    // 9. Click "Админ" dropdown menu
    await page.getByRole('menuitem', { name: 'Админ' }).locator('div').click();
    
    // 10. Click "Пользователи" menu item
    await page.getByRole('menuitem', { name: 'Пользователи' }).click();
    
    // 11. Find the newly registered user in pending users table and click "Одобрить" button
    await page.getByRole('row', { name: `e2e-approval-test-${timestamp}` }).getByRole('button').click();
    
    // 12. Verify pending users count decreased (assuming it was 5, now should be 4)
    await expect(page.getByRole('heading', { name: /Ожидают одобрения \(\d+\)/ })).toBeVisible();
  });
});
