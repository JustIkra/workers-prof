// spec: e2e/TEST_PLAN_S3-05_CRITICAL_PATH.md
// seed: e2e/seed.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Upload Reports', () => {
  test('Upload Three Reports for Participant', async ({ page }) => {
    // Generate unique participant data
    const timestamp = Date.now();
    const participantName = `Тестов Тест Тестович ${timestamp}`;
    const externalId = `UPLOAD_TEST_${timestamp}`;

    // 1. Login as testuser@example.com
    await page.goto('http://localhost:9187/login');
    await page.getByRole('textbox', { name: '*Email' }).fill('testuser@example.com');
    await page.getByRole('textbox', { name: '*Пароль' }).fill('Test1234');
    await page.getByRole('button', { name: 'Войти' }).click();

    // Wait for redirect to participants page
    await expect(page).toHaveURL(/\/participants/);

    // 2. Create a new participant for this test
    // Listen for the create participant API response to get the participant ID
    const createResponsePromise = page.waitForResponse(
      response => response.url().includes('/api/participants') && response.request().method() === 'POST'
    );

    await page.getByRole('button', { name: 'Добавить участника' }).click();
    await page.getByRole('textbox', { name: '*ФИО' }).fill(participantName);

    // Select birth date: 1990-05-20
    await page.getByRole('combobox', { name: 'Дата рождения' }).click();
    await page.getByRole('button', { name: '2025' }).click();
    await page.getByRole('button', { name: 'Предыдущий год' }).click();
    await page.getByRole('button', { name: 'Предыдущий год' }).click();
    await page.getByRole('button', { name: 'Предыдущий год' }).click();
    await page.getByRole('gridcell', { name: '1990' }).click();
    await page.getByRole('gridcell', { name: 'Май' }).click();
    await page.getByRole('gridcell', { name: '20' }).click();

    await page.getByPlaceholder('Внешний идентификатор (необязательно)').fill(externalId);
    await page.getByRole('button', { name: 'Создать' }).click();

    // Wait for the create response and extract participant ID
    const createResponse = await createResponsePromise;
    const participant = await createResponse.json();
    const participantId = participant.id;

    // Wait for dialog to close
    await expect(page.getByRole('dialog', { name: 'Добавить участника' })).not.toBeVisible({ timeout: 5000 });

    // 3. Navigate directly to participant detail page using the ID
    await page.goto(`http://localhost:9187/participants/${participantId}`);

    // 4. Wait for navigation to participant detail page
    await page.waitForURL(/\/participants\/[a-f0-9-]+$/, { timeout: 10000 });

    // Verify participant name appears on detail page (just check part of the name without timestamp)
    await expect(page.getByRole('heading', { name: /Тестов Тест Тестович/, level: 2 })).toBeVisible();

    // 5. Upload REPORT_1 (Business Report)
    await page.getByRole('button', { name: 'Загрузить отчёт' }).click();
    await page.locator('div').filter({ hasText: /^Выберите тип$/ }).nth(2).click();
    await page.getByRole('option', { name: 'Отчёт 1' }).click();
    
    const [fileChooser1] = await Promise.all([
      page.waitForEvent('filechooser'),
      page.getByRole('button', { name: 'Выбрать файл' }).first().click()
    ]);
    await fileChooser1.setFiles('/Users/maksim/git_projects/workers-prof/e2e/fixtures/Batura_A.A._Biznes-Profil_Biznes-otchyot_1718107.docx');

    await page.getByRole('button', { name: 'Загрузить', exact: true }).click();

    // Wait for dialog to close and report to appear in table
    await page.waitForTimeout(1000);

    // 6. Upload REPORT_2 (Respondent Report)
    await page.getByRole('button', { name: 'Загрузить отчёт' }).click();
    await page.locator('div').filter({ hasText: /^Выберите тип$/ }).nth(1).click();
    await page.getByRole('option', { name: 'Отчёт 2' }).click();
    
    const [fileChooser2] = await Promise.all([
      page.waitForEvent('filechooser'),
      page.getByRole('button', { name: 'Выбрать файл' }).first().click()
    ]);
    await fileChooser2.setFiles('/Users/maksim/git_projects/workers-prof/e2e/fixtures/Batura_A.A._Biznes-Profil_Otchyot_dlya_respondenta_1718107.docx');

    await page.getByRole('button', { name: 'Загрузить', exact: true }).click();

    // Wait for dialog to close and report to appear in table
    await page.waitForTimeout(1000);

    // 7. Upload REPORT_3 (Competencies Report)
    await page.getByRole('button', { name: 'Загрузить отчёт' }).click();
    await page.locator('div').filter({ hasText: /^Выберите тип$/ }).nth(1).click();
    await page.getByRole('option', { name: 'Отчёт 3' }).click();
    
    const [fileChooser3] = await Promise.all([
      page.waitForEvent('filechooser'),
      page.getByRole('button', { name: 'Выбрать файл' }).first().click()
    ]);
    await fileChooser3.setFiles('/Users/maksim/git_projects/workers-prof/e2e/fixtures/Batura_A.A._Biznes-Profil_Otchyot_po_kompetentsiyam_1718107.docx');

    await page.getByRole('button', { name: 'Загрузить', exact: true }).click();

    // Wait for dialog to close and report to appear in table
    await page.waitForTimeout(1000);

    // 8. Verify all three reports appear in the reports table
    const reportsSection = page.locator('.el-card').filter({ hasText: 'Отчёты' });
    await expect(reportsSection.getByText('Отчёт 1')).toBeVisible();
    await expect(reportsSection.getByText('Отчёт 2')).toBeVisible();
    await expect(reportsSection.getByText('Отчёт 3')).toBeVisible();
  });
});
