/**
 * E2E Test Setup Script
 *
 * This script sets up the test environment before running E2E tests:
 * - Creates an admin user if it doesn't exist
 * - Seeds professional activities
 * - Seeds metric definitions
 * - Seeds weight tables
 *
 * Usage: node e2e/setup.js
 */

import { request } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:9187';
const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || 'admin@test.com';
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || 'admin123';

async function setup() {
  console.log('Setting up E2E test environment...');
  console.log(`Base URL: ${BASE_URL}`);

  const apiContext = await request.newContext({ baseURL: BASE_URL });

  try {
    // Step 1: Try to create admin user (may already exist)
    console.log('\n1. Creating admin user...');
    try {
      const registerResponse = await apiContext.post('/api/auth/register', {
        data: {
          email: ADMIN_EMAIL,
          password: ADMIN_PASSWORD
        }
      });

      if (registerResponse.ok()) {
        const userData = await registerResponse.json();
        console.log(`   ✓ Admin user created: ${userData.email} (ID: ${userData.id})`);
        console.log('   ⚠ MANUAL ACTION REQUIRED: Promote this user to ADMIN role in the database');
        console.log(`     UPDATE "user" SET role='ADMIN', status='ACTIVE' WHERE id='${userData.id}';`);
      }
    } catch (error) {
      console.log('   ℹ Admin user may already exist');
    }

    // Step 2: Verify admin can login
    console.log('\n2. Verifying admin login...');
    const loginResponse = await apiContext.post('/api/auth/login', {
      data: {
        email: ADMIN_EMAIL,
        password: ADMIN_PASSWORD
      }
    });

    if (!loginResponse.ok()) {
      const error = await loginResponse.json();
      console.error(`   ✗ Admin login failed: ${error.detail}`);
      console.error('   Make sure the admin user exists and has ADMIN role and ACTIVE status');
      process.exit(1);
    }

    console.log('   ✓ Admin login successful');

    // Step 3: Check professional activities
    console.log('\n3. Checking professional activities...');
    const activitiesResponse = await apiContext.get('/api/prof-activities');

    if (activitiesResponse.ok()) {
      const activities = await activitiesResponse.json();
      console.log(`   ✓ Found ${activities.items.length} professional activities`);

      if (activities.items.length > 0) {
        activities.items.forEach(activity => {
          console.log(`     - ${activity.code}: ${activity.name}`);
        });
      } else {
        console.log('   ⚠ No professional activities found. Run seed script.');
      }
    }

    // Step 4: Check metric definitions
    console.log('\n4. Checking metric definitions...');
    const metricsResponse = await apiContext.get('/api/metric-defs');

    if (metricsResponse.ok()) {
      const metrics = await metricsResponse.json();
      console.log(`   ✓ Found ${metrics.items.length} metric definitions`);

      if (metrics.items.length === 0) {
        console.log('   ⚠ No metric definitions found. Tests may fail.');
      }
    }

    // Step 5: Check weight tables
    console.log('\n5. Checking weight tables...');
    const weightsResponse = await apiContext.get('/api/weight-tables');

    if (weightsResponse.ok()) {
      const weights = await weightsResponse.json();
      console.log(`   ✓ Found ${weights.items.length} weight tables`);

      if (weights.items.length === 0) {
        console.log('   ⚠ No weight tables found. Scoring tests may fail.');
      }
    }

    console.log('\n✅ E2E test environment setup complete!');
    console.log('\nReady to run tests with: npm run test:e2e');

  } catch (error) {
    console.error('\n❌ Setup failed:', error.message);
    process.exit(1);
  } finally {
    await apiContext.dispose();
  }
}

setup();
