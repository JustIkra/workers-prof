import { test, expect } from '@playwright/test';

test.describe('Test group', () => {
  test('seed', async ({ page }) => {
    // Seed test data: create and approve testuser@example.com
    // This user is used by tests 03-05

    // 1. Register testuser@example.com
    const registerResponse = await page.request.post('/api/auth/register', {
      data: {
        email: 'testuser@example.com',
        password: 'Test1234'
      }
    });

    // Ignore 400 if user already exists
    if (registerResponse.status() === 400) {
      console.log('testuser@example.com already exists, skipping registration');
      return;
    }

    expect(registerResponse.ok()).toBeTruthy();
    const userData = await registerResponse.json();
    const userId = userData.id;

    // 2. Login as admin
    await page.goto('http://localhost:9187');
    await page.getByRole('button', { name: 'Войти в систему' }).click();
    await page.getByRole('textbox', { name: '*Email' }).fill('admin@test.com');
    await page.getByRole('textbox', { name: '*Пароль' }).fill('admin123');
    await page.getByRole('button', { name: 'Войти' }).click();
    await page.waitForURL(/\/participants/);

    // 3. Approve the user via API
    const approveResponse = await page.request.post(`/api/admin/approve/${userId}`);
    expect(approveResponse.ok()).toBeTruthy();

    console.log('testuser@example.com created and approved successfully');
  });
});
