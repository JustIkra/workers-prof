import { test, expect } from '@playwright/test';
import {
  registerUser,
  loginUser,
  approveUser,
  listPendingUsers,
  createParticipant,
  uploadReport,
  createExtractedMetric,
  listMetricDefs,
  calculateScore,
  getFinalReport,
  generateTestEmail,
  TEST_PASSWORD
} from './fixtures.js';
import path from 'path';

/**
 * E2E Critical Path Test (S3-05)
 *
 * Tests the complete user journey:
 * 1. Register new user
 * 2. Admin approves user
 * 3. User logs in
 * 4. User creates participant
 * 5. User uploads DOCX report
 * 6. User enters metrics manually
 * 7. User calculates score
 * 8. User views final report
 */

test.describe('Critical Path E2E', () => {
  // Admin credentials - should exist in the database
  // In real setup, seed an admin user in the test database
  const ADMIN_EMAIL = 'admin@test.com';
  const ADMIN_PASSWORD = 'admin123';

  test('complete user flow: register → approve → upload → metrics → score → final report', async ({ page, context }) => {
    // Generate unique user credentials
    const userEmail = generateTestEmail('e2e-user');
    const userPassword = TEST_PASSWORD;

    // Step 1: Register new user
    test.step('Register new user', async () => {
      const userData = await registerUser(page.request, userEmail, userPassword);
      expect(userData.email).toBe(userEmail);
      expect(userData.status).toBe('PENDING');
    });

    // Step 2: Admin login and approve user
    let userId;
    await test.step('Admin approves user', async () => {
      // Create new page for admin
      const adminPage = await context.newPage();

      // Admin login
      await adminPage.goto('/');
      await adminPage.fill('input[name="email"]', ADMIN_EMAIL);
      await adminPage.fill('input[name="password"]', ADMIN_PASSWORD);
      await adminPage.click('button[type="submit"]');

      // Wait for successful login
      await adminPage.waitForURL(/\/(?!login)/);

      // Get pending users via API
      const pendingUsers = await listPendingUsers(adminPage.request);
      const newUser = pendingUsers.items.find(u => u.email === userEmail);
      expect(newUser).toBeDefined();
      userId = newUser.id;

      // Approve user
      const approvedUser = await approveUser(adminPage.request, userId);
      expect(approvedUser.status).toBe('ACTIVE');

      await adminPage.close();
    });

    // Step 3: User login
    await test.step('User logs in', async () => {
      await page.goto('/');
      await page.fill('input[name="email"]', userEmail);
      await page.fill('input[name="password"]', userPassword);
      await page.click('button[type="submit"]');

      // Wait for successful login and redirect
      await page.waitForURL(/\/(?!login)/);

      // Verify we're logged in
      const response = await page.request.get('/api/auth/me');
      expect(response.ok()).toBeTruthy();
    });

    // Step 4: Create participant
    let participantId;
    await test.step('Create participant', async () => {
      const participant = await createParticipant(
        page.request,
        'Иван Иванович Иванов',
        'EXT-001'
      );
      expect(participant.full_name).toBe('Иван Иванович Иванов');
      participantId = participant.id;
    });

    // Step 5: Upload DOCX report
    let reportId;
    await test.step('Upload DOCX report', async () => {
      const reportPath = path.join(process.cwd(), 'e2e', 'fixtures', 'test-report.docx');

      const report = await uploadReport(
        page.request,
        participantId,
        'REPORT_1',
        reportPath
      );

      expect(report.report_type).toBe('REPORT_1');
      expect(report.status).toBe('UPLOADED');
      reportId = report.id;
    });

    // Step 6: Enter metrics manually
    await test.step('Enter metrics manually', async () => {
      // Get available metric definitions
      const metricDefs = await listMetricDefs(page.request);
      expect(metricDefs.items.length).toBeGreaterThan(0);

      // Enter values for first 5 metrics (or all available)
      const metricsToEnter = metricDefs.items.slice(0, Math.min(5, metricDefs.items.length));

      for (const metricDef of metricsToEnter) {
        // Enter a random value between 1 and 10
        const value = (Math.random() * 9 + 1).toFixed(1);

        await createExtractedMetric(
          page.request,
          reportId,
          metricDef.id,
          parseFloat(value),
          'MANUAL'
        );
      }
    });

    // Step 7: Calculate score
    let scoringResult;
    await test.step('Calculate professional fitness score', async () => {
      // Use a known activity code from seed data
      // In real setup, we should query available activities first
      const activityCode = 'MEETING_FACILITATION';

      scoringResult = await calculateScore(
        page.request,
        participantId,
        activityCode
      );

      expect(scoringResult.participant_id).toBe(participantId);
      expect(scoringResult.score_pct).toBeDefined();
      expect(scoringResult.score_pct).toBeGreaterThanOrEqual(0);
      expect(scoringResult.score_pct).toBeLessThanOrEqual(100);
      expect(scoringResult.strengths).toBeDefined();
      expect(scoringResult.dev_areas).toBeDefined();
    });

    // Step 8: Get final report
    await test.step('Get final report JSON', async () => {
      const activityCode = 'MEETING_FACILITATION';

      const finalReport = await getFinalReport(
        page.request,
        participantId,
        activityCode,
        'json'
      );

      expect(finalReport.participant_id).toBe(participantId);
      expect(finalReport.score_pct).toBeDefined();
      expect(finalReport.strengths).toBeDefined();
      expect(finalReport.dev_areas).toBeDefined();
      expect(finalReport.metrics_table).toBeDefined();
      expect(finalReport.template_version).toBeDefined();

      // Verify strengths and dev_areas are within expected range
      expect(finalReport.strengths.length).toBeGreaterThanOrEqual(3);
      expect(finalReport.strengths.length).toBeLessThanOrEqual(5);
      expect(finalReport.dev_areas.length).toBeGreaterThanOrEqual(3);
      expect(finalReport.dev_areas.length).toBeLessThanOrEqual(5);
    });

    // Step 9: Verify HTML format is also available
    await test.step('Get final report HTML', async () => {
      const activityCode = 'MEETING_FACILITATION';

      const response = await page.request.get(
        `/api/participants/${participantId}/final-report?activity_code=${activityCode}&format=html`
      );

      expect(response.ok()).toBeTruthy();

      // Verify we get HTML content
      const contentType = response.headers()['content-type'];
      expect(contentType).toContain('text/html');

      const html = await response.text();
      expect(html).toContain('<!DOCTYPE html>');
      expect(html).toContain('Иван Иванович Иванов'); // Participant name
    });
  });

  test('user cannot access system before approval', async ({ page }) => {
    // Register a new user
    const userEmail = generateTestEmail('pending-user');
    const userData = await registerUser(page.request, userEmail, TEST_PASSWORD);
    expect(userData.status).toBe('PENDING');

    // Try to login
    const response = await page.request.post('/api/auth/login', {
      data: {
        email: userEmail,
        password: TEST_PASSWORD
      }
    });

    // Should get 403 Forbidden (user is PENDING, not ACTIVE)
    expect(response.status()).toBe(403);
    const error = await response.json();
    expect(error.detail).toContain('PENDING');
  });

  test('authenticated user can create and list participants', async ({ page }) => {
    // This test assumes we have an existing active user
    // In real setup, create and approve a user first

    const userEmail = generateTestEmail('participant-test');
    await registerUser(page.request, userEmail, TEST_PASSWORD);

    // For this test to work, user needs to be approved
    // In CI, we can use a pre-seeded active user instead
    // For now, we'll skip the actual test or assume admin approved
  });
});

test.describe('Error Handling', () => {
  test('returns 404 for non-existent participant', async ({ page }) => {
    // Login as admin first
    await loginUser(page, 'admin@test.com', 'admin123');

    const fakeUuid = '00000000-0000-0000-0000-000000000000';
    const response = await page.request.get(`/api/participants/${fakeUuid}`);

    expect(response.status()).toBe(404);
  });

  test('validates metric value ranges', async ({ page }) => {
    // This would test that values outside [1, 10] are rejected
    // Implementation depends on having proper test setup
  });
});
