import { expect } from '@playwright/test';

/**
 * Helper to register a new user
 */
export async function registerUser(request, email, password) {
  const response = await request.post('/api/auth/register', {
    data: { email, password }
  });
  expect(response.ok()).toBeTruthy();
  const data = await response.json();
  return data;
}

/**
 * Helper to login and get authentication cookie
 */
export async function loginUser(page, email, password) {
  const response = await page.request.post('/api/auth/login', {
    data: { email, password }
  });

  if (!response.ok()) {
    const error = await response.json();
    throw new Error(`Login failed: ${error.detail}`);
  }

  const data = await response.json();
  return data;
}

/**
 * Helper to approve a user (requires admin privileges)
 */
export async function approveUser(request, userId) {
  const response = await request.post(`/api/admin/approve/${userId}`);
  expect(response.ok()).toBeTruthy();
  const data = await response.json();
  return data;
}

/**
 * Helper to list pending users (requires admin privileges)
 */
export async function listPendingUsers(request) {
  const response = await request.get('/api/admin/pending-users');
  expect(response.ok()).toBeTruthy();
  const data = await response.json();
  return data;
}

/**
 * Helper to create a participant
 */
export async function createParticipant(request, fullName, externalId = null) {
  const response = await request.post('/api/participants', {
    data: {
      full_name: fullName,
      external_id: externalId
    }
  });
  expect(response.ok()).toBeTruthy();
  const data = await response.json();
  return data;
}

/**
 * Helper to upload a report
 */
export async function uploadReport(request, participantId, reportType, filePath) {
  const fs = await import('fs');
  const path = await import('path');

  const fileBuffer = fs.readFileSync(filePath);
  const fileName = path.basename(filePath);

  const response = await request.post(`/api/participants/${participantId}/reports`, {
    multipart: {
      report_type: reportType,
      file: {
        name: fileName,
        mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        buffer: fileBuffer
      }
    }
  });

  expect(response.ok()).toBeTruthy();
  const data = await response.json();
  return data;
}

/**
 * Helper to create/update an extracted metric
 */
export async function createExtractedMetric(request, reportId, metricDefId, value, source = 'MANUAL') {
  const response = await request.post(`/api/reports/${reportId}/metrics`, {
    data: {
      metric_def_id: metricDefId,
      value: value,
      source: source,
      confidence: 1.0
    }
  });
  expect(response.ok()).toBeTruthy();
  const data = await response.json();
  return data;
}

/**
 * Helper to list metric definitions
 */
export async function listMetricDefs(request) {
  const response = await request.get('/api/metric-defs');
  expect(response.ok()).toBeTruthy();
  const data = await response.json();
  return data;
}

/**
 * Helper to calculate score
 */
export async function calculateScore(request, participantId, activityCode) {
  const response = await request.post(`/api/scoring/participants/${participantId}/calculate?activity_code=${activityCode}`);
  expect(response.ok()).toBeTruthy();
  const data = await response.json();
  return data;
}

/**
 * Helper to get final report
 */
export async function getFinalReport(request, participantId, activityCode, format = 'json') {
  const response = await request.get(`/api/participants/${participantId}/final-report?activity_code=${activityCode}&format=${format}`);
  expect(response.ok()).toBeTruthy();
  const data = await response.json();
  return data;
}

/**
 * Create a test admin user and login
 */
export async function setupAdminUser(page) {
  const adminEmail = `admin-${Date.now()}@test.com`;
  const adminPassword = 'AdminPass123!';

  // Register admin
  await registerUser(page.request, adminEmail, adminPassword);

  // In a real scenario, we'd need to manually promote this user to admin in the database
  // For E2E tests, we should use an existing admin account or seed one
  // For now, let's assume there's a way to create admin or we use existing one

  return { email: adminEmail, password: adminPassword };
}

/**
 * Generate a unique test user email
 */
export function generateTestEmail(prefix = 'test') {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).substring(7)}@test.com`;
}

/**
 * Standard test password
 */
export const TEST_PASSWORD = 'TestPass123!';
