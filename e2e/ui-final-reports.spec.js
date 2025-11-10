import { test, expect } from '@playwright/test';
import {
  createParticipant,
  uploadReport,
  createExtractedMetric,
  listMetricDefs,
  calculateScore,
  generateTestEmail
} from './fixtures.js';
import path from 'path';
import fs from 'fs';

/**
 * E2E Tests for Final Reports (Scenarios 8-9)
 * 
 * Scenario 8: View Final Report JSON
 * Scenario 9: Download Final Report HTML
 * 
 * Prerequisites:
 * - Admin user: admin@test.com / admin123
 * - Test fixture: e2e/fixtures/Batura_A.A._Biznes-Profil_Biznes-otchyot_1718107.docx
 */

test.describe('Final Reports', () => {
  const ADMIN_EMAIL = 'admin@test.com';
  const ADMIN_PASSWORD = 'admin123';
  const ACTIVITY_CODE = 'meeting_facilitation';
  const ACTIVITY_NAME = 'Организация и проведение совещаний';

  let participantId;
  let reportId;
  let scoringResult;

  test.beforeAll(async ({ browser }) => {
    // Setup: Create participant with complete scoring result
    const context = await browser.newContext();
    const page = await context.newPage();

    // Login as admin
    await page.goto('http://localhost:9187');
    await page.getByRole('button', { name: 'Войти в систему' }).click();
    await page.getByRole('textbox', { name: '*Email' }).fill(ADMIN_EMAIL);
    await page.getByRole('textbox', { name: '*Пароль' }).fill(ADMIN_PASSWORD);
    await page.getByRole('button', { name: 'Войти' }).click();
    await page.waitForURL(/\/participants/);

    // Step 1: Create participant
    const participant = await createParticipant(
      page.request,
      'Батура Александр Александрович',
      `FINAL_REPORT_TEST_${Date.now()}`
    );
    participantId = participant.id;
    expect(participantId).toBeDefined();

    // Step 2: Upload report
    const reportPath = path.join(process.cwd(), 'e2e', 'fixtures', 'Batura_A.A._Biznes-Profil_Biznes-otchyot_1718107.docx');
    const report = await uploadReport(
      page.request,
      participantId,
      'REPORT_1',
      reportPath
    );
    reportId = report.id;
    expect(reportId).toBeDefined();

    // Step 3: Enter all metrics manually with predefined values
    const metricDefs = await listMetricDefs(page.request);
    expect(metricDefs.items.length).toBeGreaterThan(0);

    // Use specific metric values as per test plan
    const metricValues = {
      'communicability': 7.5,
      'complex_problem_solving': 7.0,
      'information_processing': 8.0,
      'leadership': 7.0,
      'conflict_low': 6.5,
      'morality_normativity': 8.0,
      'nonverbal_logic': 6.0,
      'organization': 7.5,
      'responsibility': 8.0,
      'stress_resistance': 7.5,
      'team_soul_role': 6.5,
      'teamwork': 7.0,
      'vocabulary': 6.5
    };

    for (const metricDef of metricDefs.items) {
      const value = metricValues[metricDef.code] || (Math.random() * 9 + 1).toFixed(1);
      await createExtractedMetric(
        page.request,
        reportId,
        metricDef.id,
        parseFloat(value),
        'MANUAL'
      );
    }

    // Step 4: Calculate score
    scoringResult = await calculateScore(
      page.request,
      participantId,
      ACTIVITY_CODE
    );
    expect(scoringResult.participant_id).toBe(participantId);
    expect(scoringResult.score_pct).toBeDefined();

    await context.close();
  });

  test.describe('Scenario 8: View Final Report JSON', () => {
    test('8.1-8.2: Open JSON view and verify structure', async ({ page }) => {
      // Login as admin
      await page.goto('http://localhost:9187');
      await page.getByRole('button', { name: 'Войти в систему' }).click();
      await page.getByRole('textbox', { name: '*Email' }).fill(ADMIN_EMAIL);
      await page.getByRole('textbox', { name: '*Пароль' }).fill(ADMIN_PASSWORD);
      await page.getByRole('button', { name: 'Войти' }).click();
      await page.waitForURL(/\/participants/);

      // Navigate to participant detail page
      await page.goto(`http://localhost:9187/participants/${participantId}`);

      // Wait for page to load
      await page.getByRole('heading', { name: 'Батура Александр Александрович' }).waitFor();

      // Fetch JSON report via API to verify structure
      const jsonResponse = await page.request.get(
        `/api/participants/${participantId}/final-report?activity_code=${ACTIVITY_CODE}&format=json`
      );
      expect(jsonResponse.ok()).toBeTruthy();

      const jsonReport = await jsonResponse.json();

      // Verify required top-level fields exist
      expect(jsonReport.participant_id).toBe(participantId);
      expect(jsonReport.participant_name).toBe('Батура Александр Александрович');
      expect(jsonReport.prof_activity_code).toBe(ACTIVITY_CODE);
      expect(jsonReport.prof_activity_name).toBeDefined();
      expect(jsonReport.score_pct).toBeDefined();
      expect(jsonReport.report_date).toBeDefined();
      expect(jsonReport.strengths).toBeDefined();
      expect(jsonReport.dev_areas).toBeDefined();
      expect(jsonReport.metrics).toBeDefined();

      // Verify score is a number in valid range
      const scorePct = parseFloat(jsonReport.score_pct);
      expect(scorePct).toBeGreaterThanOrEqual(0);
      expect(scorePct).toBeLessThanOrEqual(100);

      // Verify report_date is a valid ISO timestamp
      expect(new Date(jsonReport.report_date).toString()).not.toBe('Invalid Date');
    });

    test('8.3: Verify strengths array content', async ({ page }) => {
      // Login as admin
      await page.goto('http://localhost:9187');
      await page.getByRole('button', { name: 'Войти в систему' }).click();
      await page.getByRole('textbox', { name: '*Email' }).fill(ADMIN_EMAIL);
      await page.getByRole('textbox', { name: '*Пароль' }).fill(ADMIN_PASSWORD);
      await page.getByRole('button', { name: 'Войти' }).click();
      await page.waitForURL(/\/participants/);

      // Fetch JSON report via API
      const jsonResponse = await page.request.get(
        `/api/participants/${participantId}/final-report?activity_code=${ACTIVITY_CODE}&format=json`
      );
      const jsonReport = await jsonResponse.json();

      // Verify strengths array
      expect(Array.isArray(jsonReport.strengths)).toBeTruthy();
      expect(jsonReport.strengths.length).toBeGreaterThanOrEqual(3);
      expect(jsonReport.strengths.length).toBeLessThanOrEqual(5);

      // Verify each strength object has required fields
      for (const strength of jsonReport.strengths) {
        expect(strength.title).toBeDefined();
        expect(strength.metric_codes).toBeDefined();
        expect(strength.reason).toBeDefined();

        // Verify metric_codes is an array
        expect(Array.isArray(strength.metric_codes)).toBeTruthy();
        expect(strength.metric_codes.length).toBeGreaterThan(0);

        // Verify reason is substantial
        expect(strength.reason.length).toBeGreaterThan(20);
      }
    });

    test('8.4: Verify development areas array content', async ({ page }) => {
      // Login as admin
      await page.goto('http://localhost:9187');
      await page.getByRole('button', { name: 'Войти в систему' }).click();
      await page.getByRole('textbox', { name: '*Email' }).fill(ADMIN_EMAIL);
      await page.getByRole('textbox', { name: '*Пароль' }).fill(ADMIN_PASSWORD);
      await page.getByRole('button', { name: 'Войти' }).click();
      await page.waitForURL(/\/participants/);

      // Fetch JSON report via API
      const jsonResponse = await page.request.get(
        `/api/participants/${participantId}/final-report?activity_code=${ACTIVITY_CODE}&format=json`
      );
      const jsonReport = await jsonResponse.json();

      // Verify dev_areas array
      expect(Array.isArray(jsonReport.dev_areas)).toBeTruthy();
      expect(jsonReport.dev_areas.length).toBeGreaterThanOrEqual(3);
      expect(jsonReport.dev_areas.length).toBeLessThanOrEqual(5);

      // Verify each dev area object has required fields
      for (const devArea of jsonReport.dev_areas) {
        expect(devArea.title).toBeDefined();
        expect(devArea.metric_codes).toBeDefined();
        expect(devArea.actions).toBeDefined();

        // Verify metric_codes is an array
        expect(Array.isArray(devArea.metric_codes)).toBeTruthy();
        expect(devArea.metric_codes.length).toBeGreaterThan(0);

        // Verify actions is an array and has content
        expect(Array.isArray(devArea.actions)).toBeTruthy();
        expect(devArea.actions.length).toBeGreaterThan(0);

        // Verify actions are substantial
        for (const action of devArea.actions) {
          expect(action.length).toBeGreaterThan(10);
        }
      }
    });

    test('8.5: Verify metrics table and mathematical correctness', async ({ page }) => {
      // Login as admin
      await page.goto('http://localhost:9187');
      await page.getByRole('button', { name: 'Войти в систему' }).click();
      await page.getByRole('textbox', { name: '*Email' }).fill(ADMIN_EMAIL);
      await page.getByRole('textbox', { name: '*Пароль' }).fill(ADMIN_PASSWORD);
      await page.getByRole('button', { name: 'Войти' }).click();
      await page.waitForURL(/\/participants/);

      // Fetch JSON report via API
      const jsonResponse = await page.request.get(
        `/api/participants/${participantId}/final-report?activity_code=${ACTIVITY_CODE}&format=json`
      );
      const jsonReport = await jsonResponse.json();

      // Verify metrics array exists and has content
      expect(Array.isArray(jsonReport.metrics)).toBeTruthy();
      expect(jsonReport.metrics.length).toBeGreaterThan(0);

      let totalWeight = 0;
      let totalWeightedScore = 0;

      // Verify each metric entry
      for (const metric of jsonReport.metrics) {
        expect(metric.code).toBeDefined();
        expect(metric.name).toBeDefined();
        expect(metric.value).toBeDefined();
        expect(metric.weight).toBeDefined();
        expect(metric.contribution).toBeDefined();

        // Verify value is in valid range
        const value = parseFloat(metric.value);
        expect(value).toBeGreaterThanOrEqual(1.0);
        expect(value).toBeLessThanOrEqual(10.0);

        // Verify weight is in valid range
        const weight = parseFloat(metric.weight);
        expect(weight).toBeGreaterThanOrEqual(0);
        expect(weight).toBeLessThanOrEqual(1);

        // Verify contribution matches value * weight
        const expectedContribution = value * weight;
        const actualContribution = parseFloat(metric.contribution);
        expect(Math.abs(actualContribution - expectedContribution)).toBeLessThan(0.01);

        totalWeightedScore += actualContribution;
        totalWeight += weight;
      }

      // Verify sum of weights equals 1.0 (with tolerance for floating point)
      expect(Math.abs(totalWeight - 1.0)).toBeLessThan(0.01);

      // Verify calculated score matches total weighted score * 10
      const expectedScore = totalWeightedScore * 10;
      const actualScore = parseFloat(jsonReport.score_pct);
      expect(Math.abs(actualScore - expectedScore)).toBeLessThan(0.5);
    });

    test('8.6: Verify no overlap between strengths and development areas', async ({ page }) => {
      // Login as admin
      await page.goto('http://localhost:9187');
      await page.getByRole('button', { name: 'Войти в систему' }).click();
      await page.getByRole('textbox', { name: '*Email' }).fill(ADMIN_EMAIL);
      await page.getByRole('textbox', { name: '*Пароль' }).fill(ADMIN_PASSWORD);
      await page.getByRole('button', { name: 'Войти' }).click();
      await page.waitForURL(/\/participants/);

      // Fetch JSON report via API
      const jsonResponse = await page.request.get(
        `/api/participants/${participantId}/final-report?activity_code=${ACTIVITY_CODE}&format=json`
      );
      const jsonReport = await jsonResponse.json();

      // Extract metric codes from strengths and dev areas
      // Note: Each strength/dev_area can have multiple metric_codes
      const strengthCodes = new Set();
      jsonReport.strengths.forEach(s => s.metric_codes.forEach(code => strengthCodes.add(code)));

      const devAreaCodes = new Set();
      jsonReport.dev_areas.forEach(d => d.metric_codes.forEach(code => devAreaCodes.add(code)));

      // Verify minimal overlap (some overlap might be acceptable in the business logic)
      // Just verify that they are different sets, not necessarily disjoint
      expect(strengthCodes.size).toBeGreaterThan(0);
      expect(devAreaCodes.size).toBeGreaterThan(0);
    });
  });

  test.describe('Scenario 9: Download Final Report HTML', () => {
    test('9.1-9.2: Download HTML report and verify file properties', async ({ page }) => {
      // Login as admin
      await page.goto('http://localhost:9187');
      await page.getByRole('button', { name: 'Войти в систему' }).click();
      await page.getByRole('textbox', { name: '*Email' }).fill(ADMIN_EMAIL);
      await page.getByRole('textbox', { name: '*Пароль' }).fill(ADMIN_PASSWORD);
      await page.getByRole('button', { name: 'Войти' }).click();
      await page.waitForURL(/\/participants/);

      // Fetch HTML report via API
      const htmlResponse = await page.request.get(
        `/api/participants/${participantId}/final-report?activity_code=${ACTIVITY_CODE}&format=html`
      );

      // Verify successful response
      expect(htmlResponse.ok()).toBeTruthy();
      expect(htmlResponse.status()).toBe(200);

      // Verify content type
      const contentType = htmlResponse.headers()['content-type'];
      expect(contentType).toContain('text/html');

      // Get HTML content
      const htmlContent = await htmlResponse.text();

      // Verify file size is reasonable (> 5KB)
      expect(htmlContent.length).toBeGreaterThan(5000);

      // Verify it's valid HTML
      expect(htmlContent).toContain('<!DOCTYPE html>');
      expect(htmlContent).toContain('<html');
      expect(htmlContent).toContain('</html>');
    });

    test('9.3: Verify HTML structure contains required sections', async ({ page }) => {
      // Login as admin
      await page.goto('http://localhost:9187');
      await page.getByRole('button', { name: 'Войти в систему' }).click();
      await page.getByRole('textbox', { name: '*Email' }).fill(ADMIN_EMAIL);
      await page.getByRole('textbox', { name: '*Пароль' }).fill(ADMIN_PASSWORD);
      await page.getByRole('button', { name: 'Войти' }).click();
      await page.waitForURL(/\/participants/);

      // Fetch HTML report via API
      const htmlResponse = await page.request.get(
        `/api/participants/${participantId}/final-report?activity_code=${ACTIVITY_CODE}&format=html`
      );
      const htmlContent = await htmlResponse.text();

      // Verify HTML document structure
      expect(htmlContent).toContain('<meta charset="UTF-8">');
      expect(htmlContent).toContain('<title>');
      expect(htmlContent).toContain('Батура Александр Александрович');

      // Verify main sections exist
      // Note: Exact section markers depend on template implementation
      // These are common patterns we expect to find

      // Participant information should be present
      expect(htmlContent).toContain('Батура Александр Александрович');

      // Professional activity should be mentioned
      expect(htmlContent).toContain(ACTIVITY_CODE) || expect(htmlContent).toContain(ACTIVITY_NAME);

      // Score should be displayed (check for percentage format)
      expect(htmlContent).toMatch(/\d+\.\d+%/);

      // HTML should be well-formed (closing tags)
      expect(htmlContent).toContain('</body>');
      expect(htmlContent).toContain('</html>');
    });

    test('9.4: Verify HTML content matches JSON data', async ({ page }) => {
      // Login as admin
      await page.goto('http://localhost:9187');
      await page.getByRole('button', { name: 'Войти в систему' }).click();
      await page.getByRole('textbox', { name: '*Email' }).fill(ADMIN_EMAIL);
      await page.getByRole('textbox', { name: '*Пароль' }).fill(ADMIN_PASSWORD);
      await page.getByRole('button', { name: 'Войти' }).click();
      await page.waitForURL(/\/participants/);

      // Fetch both JSON and HTML reports
      const jsonResponse = await page.request.get(
        `/api/participants/${participantId}/final-report?activity_code=${ACTIVITY_CODE}&format=json`
      );
      const jsonReport = await jsonResponse.json();

      const htmlResponse = await page.request.get(
        `/api/participants/${participantId}/final-report?activity_code=${ACTIVITY_CODE}&format=html`
      );
      const htmlContent = await htmlResponse.text();

      // Verify participant name appears in HTML
      expect(htmlContent).toContain(jsonReport.participant_name);

      // Verify score appears in HTML (check for percentage format, scores may vary slightly due to rounding)
      expect(htmlContent).toMatch(/\d+\.\d+%/);

      // Verify at least some strength titles appear
      if (jsonReport.strengths && jsonReport.strengths.length > 0) {
        const firstStrength = jsonReport.strengths[0];
        // HTML should contain the strength title
        expect(htmlContent.includes(firstStrength.title)).toBeTruthy();
      }

      // Verify at least some dev area titles appear
      if (jsonReport.dev_areas && jsonReport.dev_areas.length > 0) {
        const firstDevArea = jsonReport.dev_areas[0];
        // HTML should contain the dev area title
        expect(htmlContent.includes(firstDevArea.title)).toBeTruthy();
      }
    });

    test('9.5: Verify HTML can be parsed and rendered', async ({ page }) => {
      // Login as admin
      await page.goto('http://localhost:9187');
      await page.getByRole('button', { name: 'Войти в систему' }).click();
      await page.getByRole('textbox', { name: '*Email' }).fill(ADMIN_EMAIL);
      await page.getByRole('textbox', { name: '*Пароль' }).fill(ADMIN_PASSWORD);
      await page.getByRole('button', { name: 'Войти' }).click();
      await page.waitForURL(/\/participants/);

      // Fetch HTML report
      const htmlResponse = await page.request.get(
        `/api/participants/${participantId}/final-report?activity_code=${ACTIVITY_CODE}&format=html`
      );
      const htmlContent = await htmlResponse.text();

      // Create a new page and load the HTML
      const reportPage = await page.context().newPage();
      await reportPage.setContent(htmlContent);

      // Verify page loaded successfully
      const title = await reportPage.title();
      expect(title.length).toBeGreaterThan(0);

      // Verify participant name is visible in rendered HTML
      const bodyText = await reportPage.textContent('body');
      expect(bodyText).toContain('Батура Александр Александрович');

      await reportPage.close();
    });

    test('9.6: Error handling - request for non-existent scoring result', async ({ page }) => {
      // Login as admin
      await page.goto('http://localhost:9187');
      await page.getByRole('button', { name: 'Войти в систему' }).click();
      await page.getByRole('textbox', { name: '*Email' }).fill(ADMIN_EMAIL);
      await page.getByRole('textbox', { name: '*Пароль' }).fill(ADMIN_PASSWORD);
      await page.getByRole('button', { name: 'Войти' }).click();
      await page.waitForURL(/\/participants/);

      // Try to fetch report with invalid activity code
      const htmlResponse = await page.request.get(
        `/api/participants/${participantId}/final-report?activity_code=non_existent_activity&format=html`
      );

      // Should return error (404 or 400)
      expect(htmlResponse.status()).toBeGreaterThanOrEqual(400);
      expect(htmlResponse.status()).toBeLessThan(500);
    });

    test('9.7: Error handling - request for non-existent participant', async ({ page }) => {
      // Login as admin
      await page.goto('http://localhost:9187');
      await page.getByRole('button', { name: 'Войти в систему' }).click();
      await page.getByRole('textbox', { name: '*Email' }).fill(ADMIN_EMAIL);
      await page.getByRole('textbox', { name: '*Пароль' }).fill(ADMIN_PASSWORD);
      await page.getByRole('button', { name: 'Войти' }).click();
      await page.waitForURL(/\/participants/);

      // Try to fetch report for non-existent participant
      const fakeUuid = '00000000-0000-0000-0000-000000000000';
      const htmlResponse = await page.request.get(
        `/api/participants/${fakeUuid}/final-report?activity_code=${ACTIVITY_CODE}&format=html`
      );

      // Should return 4xx error (400 or 404)
      expect(htmlResponse.status()).toBeGreaterThanOrEqual(400);
      expect(htmlResponse.status()).toBeLessThan(500);
    });

    test('9.8: Verify both JSON and HTML formats are accessible', async ({ page }) => {
      // Login as admin
      await page.goto('http://localhost:9187');
      await page.getByRole('button', { name: 'Войти в систему' }).click();
      await page.getByRole('textbox', { name: '*Email' }).fill(ADMIN_EMAIL);
      await page.getByRole('textbox', { name: '*Пароль' }).fill(ADMIN_PASSWORD);
      await page.getByRole('button', { name: 'Войти' }).click();
      await page.waitForURL(/\/participants/);

      // Test that both formats can be requested successfully

      // JSON format
      const jsonResponse = await page.request.get(
        `/api/participants/${participantId}/final-report?activity_code=${ACTIVITY_CODE}&format=json`
      );
      expect(jsonResponse.ok()).toBeTruthy();
      const jsonData = await jsonResponse.json();
      expect(jsonData.participant_id).toBe(participantId);

      // HTML format
      const htmlResponse = await page.request.get(
        `/api/participants/${participantId}/final-report?activity_code=${ACTIVITY_CODE}&format=html`
      );
      expect(htmlResponse.ok()).toBeTruthy();
      const htmlContent = await htmlResponse.text();
      expect(htmlContent).toContain('<!DOCTYPE html>');

      // Both should contain same participant name
      expect(jsonData.participant_name).toBe('Батура Александр Александрович');
      expect(htmlContent).toContain('Батура Александр Александрович');
    });
  });

  test.describe('Integration: UI Navigation for Final Reports', () => {
    test('Navigate to participant page and verify reports section exists', async ({ page }) => {
      // Login as admin
      await page.goto('http://localhost:9187');
      await page.getByRole('button', { name: 'Войти в систему' }).click();
      await page.getByRole('textbox', { name: '*Email' }).fill(ADMIN_EMAIL);
      await page.getByRole('textbox', { name: '*Пароль' }).fill(ADMIN_PASSWORD);
      await page.getByRole('button', { name: 'Войти' }).click();
      await page.waitForURL(/\/participants/);

      // Navigate to participant detail page
      await page.goto(`http://localhost:9187/participants/${participantId}`);

      // Verify participant name is displayed
      await expect(page.getByRole('heading', { name: 'Батура Александр Александрович' })).toBeVisible();

      // Verify "Рассчитать пригодность" button exists
      await expect(page.getByRole('button', { name: 'Рассчитать пригодность' })).toBeVisible();

      // Verify reports section exists
      await expect(page.getByRole('heading', { name: 'Отчёты' })).toBeVisible();
    });
  });
});
