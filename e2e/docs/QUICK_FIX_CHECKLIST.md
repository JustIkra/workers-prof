# Quick Fix Checklist - Final Report UI

**Last Updated**: 2025-11-09
**Status**: ⚠️ BLOCKED - Server needs restart

---

## ⚠️ CRITICAL BLOCKER

**The application server is running outdated code and needs to be restarted.**

### Evidence:
- `GET /api/participants/{id}/reports` returns 404 (code exists at `reports.py:32-51`)
- `GET /api/participants/{id}/scores` returns 404 (code exists at `participants.py:219-291`)
- API documentation at `/api/docs` does not list these endpoints

### Required Action:
```bash
# Restart the server
cd /Users/maksim/git_projects/workers-prof
docker-compose restart app
# OR
cd api-gateway && uvicorn main:app --reload --host 0.0.0.0 --port 9187
```

**Until the server is restarted, the frontend cannot be properly tested.**

---

## Problem
Test scenarios 9-10 (View JSON/Download HTML final reports) cannot be executed because:
1. ❌ Server is running outdated code (missing endpoints)
2. ⚠️ UI buttons may or may not exist (cannot verify due to #1)

---

## Backend Status

### ✅ S2-04: Backend Endpoints Implemented

According to the source code, the following were completed:

1. **GET /api/participants/{id}/final-report** ✅
   - File: `api-gateway/app/routers/participants.py` (lines 167-216)
   - Supports `?activity_code=X&format=json|html`
   - Returns: FinalReportResponse (JSON) or HTMLResponse

2. **GET /api/participants/{id}/scores** ✅
   - File: `api-gateway/app/routers/participants.py` (lines 219-291)
   - Returns: ScoringHistoryResponse with prof_activity_code

3. **GET /api/participants/{id}/reports** ✅
   - File: `api-gateway/app/routers/reports.py` (lines 32-51)
   - Returns: ReportListResponse with items and total

### ❌ Server Deployment

- **Status**: Server NOT restarted after backend implementation
- **Impact**: All endpoints return 404
- **Fix**: Restart server (see top of document)

---

## Frontend Status

**Cannot be verified until server is restarted.** The following MAY have been implemented:

### ⏸️ Fix #1: Enable Report List Loading
**File**: `frontend/src/api/reports.js`
**Action**: Add method to existing exports

**Status**: ⏸️ BLOCKED - Cannot test until server works

```javascript
export const reportsApi = {
  // ... existing methods ...

  /**
   * Get all reports for a participant
   * @param {string} participantId - UUID
   */
  async getList(participantId) {
    const response = await apiClient.get(`/participants/${participantId}/reports`)
    return response.data
  }
}
```

**Time**: 2 minutes

---

###⏸️ Fix #2: Call Report API Instead of Stub
**File**: `frontend/src/views/ParticipantDetailView.vue`
**Line**: 499-511
**Action**: Replace entire function

**Status**: ⏸️ BLOCKED - Cannot test until server works

**BEFORE**:
```javascript
const loadReports = async () => {
  loadingReports.value = true
  try {
    reports.value = []
    ElMessage.info('Функция загрузки списка отчётов будет доступна после реализации соответствующего API')
  } catch (error) {
    console.error('Error loading reports:', error)
  } finally {
    loadingReports.value = false
  }
}
```

**AFTER**:
```javascript
const loadReports = async () => {
  loadingReports.value = true
  try {
    const response = await reportsApi.getList(route.params.id)
    reports.value = response.items || []
  } catch (error) {
    console.error('Error loading reports:', error)
    ElMessage.error('Ошибка загрузки списка отчётов')
  } finally {
    loadingReports.value = false
  }
}
```

**Time**: 3 minutes

---

### ⏸️ Fix #3: Store Activity Code in Scoring Results
**File**: `frontend/src/views/ParticipantDetailView.vue`
**Line**: 638-646
**Action**: Add one line

**Status**: ⏸️ BLOCKED - Cannot test until server works

**BEFORE**:
```javascript
scoringResults.value.unshift({
  id: result.scoring_result_id,
  prof_activity_name: result.prof_activity_name,
  score_pct: parseFloat(result.score_pct),
  strengths: result.strengths || [],
  dev_areas: result.dev_areas || [],
  recommendations: result.recommendations || [],
  created_at: new Date().toISOString()
})
```

**AFTER**:
```javascript
scoringResults.value.unshift({
  id: result.scoring_result_id,
  prof_activity_name: result.prof_activity_name,
  prof_activity_code: result.prof_activity_code,  // ← ADD THIS LINE
  score_pct: parseFloat(result.score_pct),
  strengths: result.strengths || [],
  dev_areas: result.dev_areas || [],
  recommendations: result.recommendations || [],
  created_at: new Date().toISOString()
})
```

**Time**: 1 minute

---

### ⏸️ Fix #4: Add Final Report Buttons
**File**: `frontend/src/views/ParticipantDetailView.vue`
**Line**: After 220 (inside scoring results card)
**Action**: Add button section

**Status**: ⏸️ BLOCKED - Cannot test until server works

**LOCATION**: Inside the `<el-card>` for each timeline item, after the recommendations section:

```vue
<!-- Add this AFTER line 220 (after recommendations section closes) -->
<div
  v-if="result.prof_activity_code"
  class="report-actions"
  style="margin-top: 16px; display: flex; gap: 12px;"
>
  <el-button
    type="primary"
    @click="viewFinalReportJSON(result)"
  >
    <el-icon><Document /></el-icon>
    Просмотреть JSON
  </el-button>
  <el-button
    type="success"
    @click="downloadFinalReportHTML(result)"
  >
    <el-icon><Download /></el-icon>
    Скачать HTML
  </el-button>
</div>
```

**Time**: 5 minutes

---

### ⏸️ Fix #5: Add Icon Imports
**File**: `frontend/src/views/ParticipantDetailView.vue`
**Line**: 384-391
**Action**: Add Document icon to imports

**Status**: ⏸️ BLOCKED - Cannot test until server works

**BEFORE**:
```javascript
import {
  Upload,
  Download,
  DataAnalysis,
  View,
  Delete,
  TrendCharts
} from '@element-plus/icons-vue'
```

**AFTER**:
```javascript
import {
  Upload,
  Download,
  DataAnalysis,
  View,
  Delete,
  TrendCharts,
  Document  // ← ADD THIS
} from '@element-plus/icons-vue'
```

**Time**: 1 minute

---

### ⏸️ Fix #6: Implement Button Methods
**File**: `frontend/src/views/ParticipantDetailView.vue`
**Line**: After 658 (end of calculateScoring function)
**Action**: Add two new methods

**Status**: ⏸️ BLOCKED - Cannot test until server works

```javascript
// Add these methods after calculateScoring()

const viewFinalReportJSON = async (result) => {
  try {
    const report = await scoringApi.getFinalReport(
      route.params.id,
      result.prof_activity_code,
      'json'
    )

    // Create a formatted JSON view
    const jsonStr = JSON.stringify(report, null, 2)

    // Open in new window/tab
    const win = window.open('', '_blank')
    win.document.write('<pre>' + jsonStr + '</pre>')
    win.document.title = `Final Report - ${result.prof_activity_name}`

    ElMessage.success('Отчёт загружен')
  } catch (error) {
    console.error('Error loading final report:', error)
    const errorMessage = error.response?.data?.detail || 'Ошибка загрузки отчёта'
    ElMessage.error(errorMessage)
  }
}

const downloadFinalReportHTML = async (result) => {
  try {
    const html = await scoringApi.getFinalReport(
      route.params.id,
      result.prof_activity_code,
      'html'
    )

    // Create blob and download
    const blob = new Blob([html], { type: 'text/html' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `final_report_${participant.value.full_name}_${result.prof_activity_name}_${new Date().toISOString().split('T')[0]}.html`
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)

    ElMessage.success('HTML-отчёт скачан')
  } catch (error) {
    console.error('Error downloading final report:', error)
    const errorMessage = error.response?.data?.detail || 'Ошибка скачивания отчёта'
    ElMessage.error(errorMessage)
  }
}
```

**Time**: 15 minutes (including testing)

---

### ⏸️ Fix #7: Fix API Client URL (Bug Fix)
**File**: `frontend/src/api/scoring.js`
**Line**: 65
**Action**: Remove `/api` prefix (it's already in base URL)

**Status**: ⏸️ BLOCKED - Cannot test until server works

**BEFORE**:
```javascript
const response = await apiClient.get(`/api/participants/${participantId}/final-report`, config)
```

**AFTER**:
```javascript
const response = await apiClient.get(`/participants/${participantId}/final-report`, config)
```

**Time**: 1 minute

---

## Testing Checklist

**BLOCKED until server restart**. After server restart:

- [ ] **CRITICAL**: Restart server and verify endpoints return 200/401 (not 404)
- [ ] Verify `/api/docs` shows new endpoints
- [ ] Login as admin@test.com / admin123
- [ ] Navigate to participant "Иванов Иван Иванович"
- [ ] Verify reports list loads (not empty)
- [ ] Verify scoring history appears
- [ ] Verify "Просмотреть JSON" button exists
- [ ] Verify "Скачать HTML" button exists
- [ ] Click "Просмотреть JSON" - should open new tab with formatted JSON
- [ ] Click "Скачать HTML" - should download HTML file
- [ ] Open downloaded HTML in browser - should render properly
- [ ] No console errors

---

## Verification Commands

### Step 1: Verify Server is Running Latest Code

```bash
# Test reports endpoint (should return 401 for auth or 200, NOT 404)
curl http://localhost:9187/api/participants/d2296813-185c-449d-a639-522f30210fcd/reports

# Test scores endpoint (should return 401 for auth or 200, NOT 404)
curl http://localhost:9187/api/participants/d2296813-185c-449d-a639-522f30210fcd/scores

# Check API docs include new endpoints
open http://localhost:9187/api/docs
# Look for:
# - GET /api/participants/{participant_id}/reports
# - GET /api/participants/{participant_id}/scores
```

### Step 2: Test with Authentication

```bash
# Get token
TOKEN=$(curl -X POST http://localhost:9187/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"admin123"}' \
  | jq -r '.access_token')

# Test endpoints
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:9187/api/participants/d2296813-185c-449d-a639-522f30210fcd/reports"

curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:9187/api/participants/d2296813-185c-449d-a639-522f30210fcd/scores"
```

### Step 3: Test Frontend (after server works)

```bash
# 1. Start dev server (if testing locally)
cd frontend && npm run dev

# 2. Open browser to http://localhost:9187

# 3. Login as admin@test.com / admin123

# 4. Navigate to any participant

# 5. Verify buttons exist and work
```

---

## Rollback Plan

If issues occur after server restart:

```bash
git log --oneline -10  # Check recent commits
git checkout <previous-commit-hash>  # Rollback if needed

# Or restore from branch:
git stash  # Save uncommitted changes
git checkout main  # Or previous working branch
```

---

## Current Status Summary

| Component | Status | Blocker |
|-----------|--------|---------|
| Backend Endpoints | ✅ Code exists | ❌ Server not restarted |
| Frontend Fixes | ⏸️ Unknown | ❌ Cannot verify until server works |
| Reports List | ⏸️ Unknown | ❌ 404 error |
| Scoring History | ⏸️ Unknown | ❌ 404 error |
| Final Report Buttons | ⏸️ Unknown | ❌ Cannot load page properly |
| E2E Tests | ❌ Blocked | ❌ Server needs restart |

---

## Next Steps

### IMMEDIATE (Blocks Everything)

1. **Restart application server**
   ```bash
   cd /Users/maksim/git_projects/workers-prof
   docker-compose restart app
   ```

2. **Verify endpoints are registered**
   ```bash
   curl http://localhost:9187/api/docs | grep "participants.*reports"
   curl http://localhost:9187/api/docs | grep "participants.*scores"
   ```

3. **Test endpoints return 200/401 (not 404)**
   ```bash
   curl http://localhost:9187/api/participants/d2296813-185c-449d-a639-522f30210fcd/reports
   curl http://localhost:9187/api/participants/d2296813-185c-449d-a639-522f30210fcd/scores
   ```

### AFTER SERVER RESTART

4. **Verify frontend implementation**
   - Login and navigate to participant detail page
   - Check if reports list loads
   - Check if scoring history appears
   - Look for final report buttons

5. **If buttons missing**: Apply frontend fixes (see above)

6. **If buttons exist**: Test scenarios 9-10

7. **Update documentation** with actual findings

---

## Files Modified Summary

**Backend** (✅ Implemented in code, ❌ Not deployed):
1. `api-gateway/app/routers/participants.py`
   - Added `GET /{participant_id}/scores` (line 219-291)
   - Added `GET /{participant_id}/final-report` (line 167-216)
2. `api-gateway/app/routers/reports.py`
   - Added `GET /participants/{participant_id}/reports` (line 32-51)

**Frontend** (⏸️ Status Unknown):
1. `frontend/src/api/reports.js` - May need getList() method
2. `frontend/src/views/ParticipantDetailView.vue` - May need 4 changes:
   - Fix loadReports() function
   - Store prof_activity_code
   - Add final report buttons (HTML)
   - Add final report methods (JS)
   - Import Document icon
3. `frontend/src/api/scoring.js` - May need URL fix

**Total Files**: 3 backend (done), 3 frontend (unknown)

---

## Post-Server-Restart

After server is restarted and endpoints work:

1. **Verify frontend implementation** - Test if buttons exist
2. **Update this checklist** - Mark completed items with ✅
3. **Write E2E tests** - If buttons exist, implement automated tests
4. **Update other docs** - Mark scenarios 9-10 as ready or blocked
5. **Notify team** - Report status to QA/dev teams

---

**Created**: 2025-11-08
**Last Updated**: 2025-11-09
**Status**: ⚠️ BLOCKED - Server restart required
**Estimated Completion**: 15 minutes after server restart
**Risk Level**: Low (code ready, deployment issue only)
