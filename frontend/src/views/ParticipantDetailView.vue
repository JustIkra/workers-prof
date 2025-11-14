<template>
  <app-layout>
    <div
      v-loading="loading"
      class="participant-detail"
    >
      <!-- Participant Info Card -->
      <el-card
        v-if="participant"
        class="detail-card"
      >
        <template #header>
          <div class="card-header">
            <h2>{{ participant.full_name }}</h2>
            <div class="header-actions">
              <el-button @click="router.back()">
                Назад
              </el-button>
              <el-button
                type="primary"
                @click="showScoringDialog = true"
              >
                <el-icon><TrendCharts /></el-icon>
                Рассчитать пригодность
              </el-button>
            </div>
          </div>
        </template>

        <el-descriptions
          :column="2"
          border
        >
          <el-descriptions-item label="ФИО">
            {{ participant.full_name }}
          </el-descriptions-item>
          <el-descriptions-item label="Дата рождения">
            {{ participant.birth_date || 'Не указана' }}
          </el-descriptions-item>
          <el-descriptions-item label="Внешний ID">
            {{ participant.external_id || 'Не указан' }}
          </el-descriptions-item>
          <el-descriptions-item label="Дата создания">
            {{ formatDate(participant.created_at) }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- Reports Section -->
      <el-card class="section-card">
        <template #header>
          <div class="section-header">
            <h3>Отчёты</h3>
            <el-button
              type="primary"
              @click="showUploadDialog = true"
            >
              <el-icon><Upload /></el-icon>
              Загрузить отчёт
            </el-button>
          </div>
        </template>

        <report-list
          :reports="reports"
          :loading="loadingReports"
          @view="viewMetrics"
          @edit="viewMetrics"
          @extract="extractMetrics"
          @download="downloadReport"
          @delete="handleDeleteReport"
          @upload="showUploadDialog = true"
        />
      </el-card>

      <!-- Participant Metrics Section (S2-08) -->
      <el-card class="section-card">
        <template #header>
          <div class="section-header">
            <h3>Актуальные метрики участника</h3>
            <el-button
              type="primary"
              size="small"
              @click="loadParticipantMetrics"
            >
              <el-icon><Refresh /></el-icon>
              Обновить
            </el-button>
          </div>
        </template>

        <el-table
          v-loading="loadingMetrics"
          :data="participantMetrics"
          stripe
        >
          <el-table-column
            prop="metric_code"
            label="Код метрики"
            width="200"
          />
          <el-table-column
            label="Название метрики"
            min-width="250"
          >
            <template #default="{ row }">
              {{ getMetricName(row.metric_code) }}
            </template>
          </el-table-column>
          <el-table-column
            prop="value"
            label="Значение"
            width="120"
          >
            <template #default="{ row }">
              <el-tag type="success">
                {{ formatFromApi(row.value) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            prop="confidence"
            label="Уверенность"
            width="150"
          >
            <template #default="{ row }">
              <span
                v-if="row.confidence !== null"
                :style="{ color: getConfidenceColor(row.confidence) }"
              >
                {{ (row.confidence * 100).toFixed(0) }}%
              </span>
              <span v-else>—</span>
            </template>
          </el-table-column>
          <el-table-column
            prop="updated_at"
            label="Обновлено"
            width="180"
          >
            <template #default="{ row }">
              {{ formatDate(row.updated_at) }}
            </template>
          </el-table-column>
          <el-table-column
            prop="last_source_report_id"
            label="Источник"
          >
            <template #default="{ row }">
              <el-tag
                v-if="row.last_source_report_id"
                size="small"
              >
                Из отчёта
              </el-tag>
              <span v-else>—</span>
            </template>
          </el-table-column>
        </el-table>

        <el-empty
          v-if="!participantMetrics.length && !loadingMetrics"
          description="Метрики ещё не извлечены. Загрузите и обработайте отчёты."
        />
      </el-card>

      <!-- Scoring Results Section -->
      <el-card
        v-if="scoringResults.length > 0"
        class="section-card"
      >
        <template #header>
          <h3>История оценок пригодности</h3>
        </template>

        <el-timeline>
          <el-timeline-item
            v-for="result in scoringResults"
            :key="result.id"
            :timestamp="formatDate(result.created_at)"
            placement="top"
          >
            <el-card>
              <h4>{{ result.prof_activity_name }}</h4>
              <div class="scoring-result">
                <div class="score-value">
                  <span class="score-number">{{ result.score_pct }}%</span>
                  <el-progress
                    :percentage="result.score_pct"
                    :status="getScoreStatus(result.score_pct)"
                  />
                </div>
                <div class="score-details">
                  <div class="score-section">
                    <h5>Сильные стороны:</h5>
                    <ul v-if="result.strengths && result.strengths.length">
                      <li
                        v-for="(strength, idx) in result.strengths"
                        :key="idx"
                      >
                        <strong>{{ strength.metric_name }}</strong> — {{ formatFromApi(strength.value) }}
                        (вес {{ formatFromApi(strength.weight, 2) }})
                      </li>
                    </ul>
                    <el-empty
                      v-else
                      description="Нет данных"
                      :image-size="60"
                    />
                  </div>
                  <div class="score-section">
                    <h5>Зоны развития:</h5>
                    <ul v-if="result.dev_areas && result.dev_areas.length">
                      <li
                        v-for="(area, idx) in result.dev_areas"
                        :key="idx"
                      >
                        <strong>{{ area.metric_name }}</strong> — {{ formatFromApi(area.value) }}
                        (вес {{ formatFromApi(area.weight, 2) }})
                      </li>
                    </ul>
                    <el-empty
                      v-else
                      description="Нет данных"
                      :image-size="60"
                    />
                  </div>
                  <div class="score-section">
                    <h5>
                      Рекомендации:
                      <el-tag
                        v-if="result.recommendations_status"
                        :type="getRecommendationStatusType(result.recommendations_status)"
                        size="small"
                        class="recommendation-status-tag"
                      >
                        {{ formatRecommendationStatus(result.recommendations_status) }}
                      </el-tag>
                    </h5>
                    <template v-if="hasReadyRecommendations(result)">
                      <ul>
                        <li
                          v-for="(rec, idx) in result.recommendations"
                          :key="idx"
                          class="recommendation-item"
                        >
                          <strong>{{ rec.title }}</strong>
                          <div v-if="rec.skill_focus" class="recommendation-skill-focus">
                            <strong>Навык:</strong> {{ rec.skill_focus }}
                          </div>
                          <div v-if="rec.development_advice" class="recommendation-advice">
                            {{ rec.development_advice }}
                          </div>
                          <div v-if="rec.recommended_formats && rec.recommended_formats.length > 0" class="recommendation-formats">
                            <strong>Рекомендуемые форматы:</strong>
                            <ul class="formats-list">
                              <li v-for="(format, fmtIdx) in rec.recommended_formats" :key="fmtIdx">
                                {{ format }}
                              </li>
                            </ul>
                          </div>
                        </li>
                      </ul>
                    </template>
                    <el-alert
                      v-else-if="result.recommendations_status === 'pending'"
                      title="Рекомендации формируются. Обновите страницу через пару минут."
                      type="info"
                      :closable="false"
                      show-icon
                    />
                    <el-alert
                      v-else-if="result.recommendations_status === 'error'"
                      :title="getRecommendationErrorTitle(result)"
                      type="error"
                      :closable="false"
                      show-icon
                    />
                    <el-alert
                      v-else-if="result.recommendations_status === 'disabled'"
                      title="Генерация рекомендаций отключена для данного окружения."
                      type="warning"
                      :closable="false"
                      show-icon
                    />
                    <el-empty
                      v-else
                      description="Нет данных"
                      :image-size="60"
                    />
                  </div>
                </div>
                <div
                  v-if="result.prof_activity_code"
                  class="final-report-actions"
                >
                  <el-button
                    type="info"
                    size="small"
                    @click="viewFinalReportJSON(result)"
                  >
                    <el-icon><DocumentCopy /></el-icon>
                    Просмотреть JSON
                  </el-button>
                  <el-button
                    type="primary"
                    size="small"
                    @click="downloadFinalReportHTML(result)"
                  >
                    <el-icon><Download /></el-icon>
                    Скачать HTML
                  </el-button>
                </div>
              </div>
            </el-card>
          </el-timeline-item>
        </el-timeline>
      </el-card>

      <!-- Upload Dialog -->
      <el-dialog
        v-model="showUploadDialog"
        title="Загрузить отчёт"
        width="500px"
      >
        <el-form
          ref="uploadFormRef"
          :model="uploadForm"
          :rules="uploadRules"
          label-position="top"
        >
          <el-form-item
            label="Файл (DOCX)"
            prop="file"
          >
            <el-upload
              ref="uploadRef"
              :auto-upload="false"
              :limit="1"
              accept=".docx"
              :on-change="handleFileChange"
              :file-list="fileList"
            >
              <el-button type="primary">
                Выбрать файл
              </el-button>
              <template #tip>
                <div class="el-upload__tip">
                  Только файлы DOCX, максимум 20 МБ
                </div>
              </template>
            </el-upload>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showUploadDialog = false">
            Отмена
          </el-button>
          <el-button
            type="primary"
            :loading="uploading"
            @click="handleUpload"
          >
            Загрузить
          </el-button>
        </template>
      </el-dialog>

      <!-- Scoring Dialog -->
      <el-dialog
        v-model="showScoringDialog"
        title="Рассчитать профессиональную пригодность"
        width="500px"
      >
        <el-form
          :model="scoringForm"
          label-position="top"
        >
          <el-form-item
            label="Профессиональная область"
            required
          >
            <el-select
              v-model="scoringForm.activityCode"
              v-loading="loadingActivities"
              placeholder="Выберите область"
              style="width: 100%"
            >
              <el-option
                v-for="activity in profActivities"
                :key="activity.code"
                :label="activity.name"
                :value="activity.code"
              >
                <span>{{ activity.name }}</span>
                <span style="float: right; color: #8492a6; font-size: 13px">
                  {{ activity.code }}
                </span>
              </el-option>
            </el-select>
          </el-form-item>
          <el-alert
            title="Убедитесь, что у участника загружены и обработаны отчёты с метриками"
            type="info"
            :closable="false"
            show-icon
          />
          <el-alert
            v-if="reports.length === 0"
            title="У участника нет загруженных отчётов"
            type="warning"
            :closable="false"
            show-icon
            style="margin-top: 12px;"
          />
        </el-form>
        <template #footer>
          <el-button @click="showScoringDialog = false">
            Отмена
          </el-button>
          <el-button
            type="primary"
            :loading="calculating"
            :disabled="!scoringForm.activityCode || reports.length === 0"
            @click="calculateScoring"
          >
            Рассчитать
          </el-button>
        </template>
      </el-dialog>

      <!-- Metrics Dialog -->
      <el-dialog
        v-model="showMetricsDialog"
        title="Метрики отчёта"
        width="90%"
        top="5vh"
      >
        <MetricsEditor
          v-if="currentReportId"
          :report-id="currentReportId"
          @metrics-updated="handleMetricsUpdated"
        />
      </el-dialog>
    </div>
  </app-layout>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Upload,
  Download,
  DataAnalysis,
  View,
  Delete,
  TrendCharts,
  DocumentCopy,
  Refresh
} from '@element-plus/icons-vue'
import AppLayout from '@/components/AppLayout.vue'
import MetricsEditor from '@/components/MetricsEditor.vue'
import ReportList from '@/components/ReportList.vue'
import { useParticipantsStore } from '@/stores'
import { reportsApi, profActivitiesApi, scoringApi, participantsApi, metricsApi } from '@/api'
import { formatFromApi } from '@/utils/numberFormat'
import { getMetricDisplayName } from '@/utils/metricNames'

const router = useRouter()
const route = useRoute()
const participantsStore = useParticipantsStore()

const loading = ref(false)
const loadingReports = ref(false)
const loadingActivities = ref(false)
const loadingMetrics = ref(false)
const uploading = ref(false)
const calculating = ref(false)

const participant = computed(() => participantsStore.currentParticipant)
const reports = ref([])
const scoringResults = ref([])
const profActivities = ref([])
const participantMetrics = ref([])
const metricDefs = ref([])
const currentMetrics = ref([])
const currentReportId = ref(null)
const refreshInterval = ref(null)
const recommendationsRefreshInterval = ref(null)

// Check if any report is being processed
const hasProcessingReports = computed(() => {
  return reports.value.some(report => report.status === 'PROCESSING')
})

const hasPendingRecommendations = computed(() => {
  return scoringResults.value.some(
    result => result.recommendations_status === 'pending'
  )
})

const showUploadDialog = ref(false)
const showScoringDialog = ref(false)
const showMetricsDialog = ref(false)

const uploadFormRef = ref(null)
const fileList = ref([])
const uploadForm = reactive({
  file: null
})

const uploadRules = {
  file: [{ required: true, message: 'Выберите файл', trigger: 'change' }]
}

const scoringForm = reactive({
  activityCode: ''
})

// Format helpers
const formatDate = (dateStr) => {
  if (!dateStr) return '—'
  const parsedDate = new Date(dateStr)
  if (Number.isNaN(parsedDate.getTime())) return '—'
  return parsedDate.toLocaleString('ru-RU', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatStatus = (status) => {
  const statuses = {
    UPLOADED: 'Загружен',
    PROCESSING: 'Извлечение метрик...',
    EXTRACTED: 'Метрики извлечены',
    FAILED: 'Ошибка'
  }
  return statuses[status] || status
}

const getStatusType = (status) => {
  const types = {
    UPLOADED: 'info',
    PROCESSING: 'warning',
    EXTRACTED: 'success',
    FAILED: 'danger'
  }
  return types[status] || 'info'
}

const getScoreStatus = (score) => {
  if (score >= 80) return 'success'
  if (score >= 60) return ''
  return 'warning'
}

const formatRecommendationStatus = (status) => {
  const statuses = {
    pending: 'Формируются',
    ready: 'Готовы',
    error: 'Ошибка',
    disabled: 'Отключены'
  }
  return statuses[status] || status
}

const getRecommendationStatusType = (status) => {
  const types = {
    pending: 'info',
    ready: 'success',
    error: 'danger',
    disabled: 'warning'
  }
  return types[status] || 'info'
}

const getConfidenceColor = (confidence) => {
  if (confidence >= 0.8) return '#67C23A'
  if (confidence >= 0.6) return '#E6A23C'
  return '#F56C6C'
}

// Get metric name by code
const warnedMetricCodes = new Set()

const getMetricName = (metricCode) => {
  if (!metricCode) return '—'
  const metricDef = metricDefs.value.find(m => m.code === metricCode)

  const logger =
    warnedMetricCodes.has(metricCode)
      ? { warn: () => {} }
      : {
          warn: (message) => {
            warnedMetricCodes.add(metricCode)
            console.warn(message)
          }
        }

  return getMetricDisplayName(metricDef, metricCode, logger)
}

// Load data
const loadParticipant = async () => {
  loading.value = true
  try {
    await participantsStore.getParticipant(route.params.id)
  } catch (error) {
    ElMessage.error('Участник не найден')
    router.push('/participants')
  } finally {
    loading.value = false
  }
}

const loadReports = async ({ silent = false } = {}) => {
  if (!silent) {
    loadingReports.value = true
  }
  try {
    const response = await participantsApi.getReports(route.params.id)
    reports.value = response.items || []
  } catch (error) {
    console.error('Error loading reports:', error)
    ElMessage.error('Ошибка загрузки списка отчётов')
  } finally {
    if (!silent) {
      loadingReports.value = false
    }
  }
}

const normalizeScoringResult = (item) => {
  if (!item) return item
  const recommendations = Array.isArray(item.recommendations) ? item.recommendations : []
  let status = item.recommendations_status || item.recommendationsStatus || null

  if (!status) {
    status = recommendations.length > 0 ? 'ready' : 'pending'
  }

  const numericScore = Number(item.score_pct)
  const scorePct = Number.isNaN(numericScore) ? item.score_pct : numericScore

  return {
    ...item,
    score_pct: scorePct,
    recommendations,
    recommendations_status: status,
    recommendations_error: item.recommendations_error || item.recommendationsError || null
  }
}

const loadScoringResults = async () => {
  try {
    const response = await scoringApi.getHistory(route.params.id)
    const items = Array.isArray(response.items) ? response.items : []
    scoringResults.value = items.map(normalizeScoringResult)
  } catch (error) {
    console.error('Error loading scoring results:', error)
  }
}

const loadProfActivities = async () => {
  loadingActivities.value = true
  try {
    const response = await profActivitiesApi.list()
    profActivities.value = response || []
  } catch (error) {
    ElMessage.error('Ошибка загрузки профессиональных областей')
  } finally {
    loadingActivities.value = false
  }
}

// Load metric definitions
const loadMetricDefs = async () => {
  try {
    const response = await metricsApi.listMetricDefs(true) // activeOnly = true
    metricDefs.value = response.items || []
  } catch (error) {
    console.error('Error loading metric definitions:', error)
  }
}

// S2-08: Load participant metrics
const loadParticipantMetrics = async ({ silent = false } = {}) => {
  if (!silent) {
    loadingMetrics.value = true
  }
  try {
    const response = await participantsApi.getMetrics(route.params.id)
    participantMetrics.value = response.metrics || []
  } catch (error) {
    console.error('Error loading participant metrics:', error)
    ElMessage.error('Ошибка загрузки метрик участника')
  } finally {
    if (!silent) {
      loadingMetrics.value = false
    }
  }
}

// File upload
const handleFileChange = (file) => {
  uploadForm.file = file.raw
  fileList.value = [file]
}

const handleUpload = async () => {
  if (!uploadFormRef.value) return

  await uploadFormRef.value.validate(async (valid) => {
    if (!valid) return

    if (!uploadForm.file) {
      ElMessage.error('Выберите файл')
      return
    }

    uploading.value = true
    try {
      await reportsApi.upload(route.params.id, uploadForm.file)
      ElMessage.success('Отчёт загружен успешно')
      showUploadDialog.value = false
      uploadForm.file = null
      fileList.value = []
      await loadReports()
      // S2-08: Reload participant metrics after report upload
      await loadParticipantMetrics()
    } catch (error) {
      ElMessage.error('Ошибка загрузки отчёта')
    } finally {
      uploading.value = false
    }
  })
}

// Report actions
const downloadReport = async (reportId) => {
  try {
    const response = await reportsApi.download(reportId)
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `report_${reportId}.docx`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success('Отчёт скачан')
  } catch (error) {
    ElMessage.error('Ошибка скачивания отчёта')
  }
}

const extractMetrics = async (reportId) => {
  try {
    await reportsApi.extract(reportId)
    ElMessage.success('Извлечение метрик запущено')
    // Немедленно обновим список отчетов
    await loadReports()
  } catch (error) {
    ElMessage.error('Ошибка запуска извлечения метрик')
  }
}

// Auto-refresh functions
const startAutoRefresh = () => {
  if (refreshInterval.value) return // Already running

  // Обновляем каждые 3 секунды
  refreshInterval.value = setInterval(async () => {
    try {
      await loadReports({ silent: true })
      // S2-08: Also reload participant metrics to reflect newly extracted values
      await loadParticipantMetrics({ silent: true })
    } catch (error) {
      console.error('Auto-refresh error:', error)
    }
  }, 3000)
}

const stopAutoRefresh = () => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
    refreshInterval.value = null
  }
}

const startRecommendationsRefresh = () => {
  if (recommendationsRefreshInterval.value) return

  recommendationsRefreshInterval.value = setInterval(async () => {
    try {
      await loadScoringResults()
    } catch (error) {
      console.error('Recommendations auto-refresh error:', error)
    }
  }, 15000)
}

const stopRecommendationsRefresh = () => {
  if (recommendationsRefreshInterval.value) {
    clearInterval(recommendationsRefreshInterval.value)
    recommendationsRefreshInterval.value = null
  }
}

// Watch for processing reports to enable/disable auto-refresh
watch(hasProcessingReports, (hasProcessing) => {
  if (hasProcessing) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
})

watch(hasPendingRecommendations, (hasPending) => {
  if (hasPending) {
    startRecommendationsRefresh()
  } else {
    stopRecommendationsRefresh()
  }
})

const viewMetrics = async (reportId) => {
  currentReportId.value = reportId
  await nextTick() // Wait for DOM to update before opening dialog
  showMetricsDialog.value = true
}

const handleMetricsUpdated = async () => {
  ElMessage.success('Метрики обновлены')
  // S2-08: Reload participant metrics after manual update
  await loadParticipantMetrics()
}

const confirmDeleteReport = (report) => {
  ElMessageBox.confirm(
    'Вы уверены, что хотите удалить этот отчёт?',
    'Подтверждение удаления',
    {
      confirmButtonText: 'Удалить',
      cancelButtonText: 'Отмена',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await reportsApi.delete(report.id)
      ElMessage.success('Отчёт удалён')
      await loadReports()
    } catch (error) {
      ElMessage.error('Ошибка удаления отчёта')
    }
  }).catch(() => {})
}

const handleDeleteReport = async (reportId) => {
  try {
    await reportsApi.delete(reportId)
    ElMessage.success('Отчёт удалён')
    await loadReports()
  } catch (error) {
    ElMessage.error('Ошибка удаления отчёта')
  }
}

// Scoring
const calculateScoring = async () => {
  if (!scoringForm.activityCode) {
    ElMessage.warning('Выберите профессиональную область')
    return
  }

  calculating.value = true
  try {
    const result = await scoringApi.calculate(route.params.id, scoringForm.activityCode)

    // Добавляем новый результат в начало списка
    const normalized = normalizeScoringResult({
      id: result.scoring_result_id,
      participant_id: route.params.id,
      prof_activity_code: result.prof_activity_code || scoringForm.activityCode,
      prof_activity_name: result.prof_activity_name,
      score_pct: parseFloat(result.score_pct),
      strengths: result.strengths || [],
      dev_areas: result.dev_areas || [],
      recommendations: result.recommendations || [],
      recommendations_status:
        result.recommendations_status ||
        ((result.recommendations || []).length > 0 ? 'ready' : 'pending'),
      recommendations_error: result.recommendations_error || null,
      created_at: new Date().toISOString()
    })
    scoringResults.value.unshift(normalized)

    ElMessage.success('Расчёт пригодности выполнен')
    showScoringDialog.value = false
    scoringForm.activityCode = ''
  } catch (error) {
    console.error('Scoring calculation error:', error)
    const errorMessage = error.response?.data?.detail || 'Ошибка расчёта пригодности'
    ElMessage.error(errorMessage)
  } finally {
    calculating.value = false
  }
}

// Final Report
const viewFinalReportJSON = async (result) => {
  if (!result.prof_activity_code) {
    ElMessage.warning('Код профессиональной деятельности не найден')
    return
  }

  try {
    const reportData = await scoringApi.getFinalReport(
      route.params.id,
      result.prof_activity_code,
      'json'
    )

    // Открываем JSON в новой вкладке
    const jsonStr = JSON.stringify(reportData, null, 2)
    const blob = new Blob([jsonStr], { type: 'application/json' })
    const url = window.URL.createObjectURL(blob)
    window.open(url, '_blank')
    window.URL.revokeObjectURL(url)

    ElMessage.success('Отчёт JSON открыт в новой вкладке')
  } catch (error) {
    console.error('Error viewing final report JSON:', error)
    const errorMessage = error.response?.data?.detail || 'Ошибка загрузки финального отчёта'
    ElMessage.error(errorMessage)
  }
}

const downloadFinalReportHTML = async (result) => {
  if (!result.prof_activity_code) {
    ElMessage.warning('Код профессиональной деятельности не найден')
    return
  }

  try {
    const htmlContent = await scoringApi.getFinalReport(
      route.params.id,
      result.prof_activity_code,
      'html'
    )

    // Скачиваем HTML файл
    const blob = new Blob([htmlContent], { type: 'text/html' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `final_report_${result.prof_activity_code}_${new Date().toISOString().split('T')[0]}.html`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)

    ElMessage.success('Отчёт HTML скачан')
  } catch (error) {
    console.error('Error downloading final report HTML:', error)
    const errorMessage = error.response?.data?.detail || 'Ошибка загрузки финального отчёта'
    ElMessage.error(errorMessage)
  }
}

const hasReadyRecommendations = (result) => {
  return (
    result?.recommendations_status === 'ready' &&
    Array.isArray(result?.recommendations) &&
    result.recommendations.length > 0
  )
}

const getRecommendationErrorTitle = (result) => {
  if (result?.recommendations_error) {
    return `Ошибка генерации: ${result.recommendations_error}`
  }
  return 'Не удалось получить рекомендации'
}

onMounted(async () => {
  await loadParticipant()
  await loadReports()
  await loadScoringResults()
  await loadProfActivities()
  await loadMetricDefs() // Load metric definitions for names
  await loadParticipantMetrics() // S2-08: Load participant metrics
})

onUnmounted(() => {
  stopAutoRefresh()
  stopRecommendationsRefresh()
})
</script>

<style scoped>
.participant-detail {
  max-width: 1400px;
  margin: 0 auto;
}

.detail-card,
.section-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.card-header h2 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-header h3 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.scoring-result {
  margin-top: 16px;
}

.score-value {
  margin-bottom: 20px;
}

.score-number {
  font-size: 32px;
  font-weight: 700;
  color: var(--color-primary);
  display: block;
  margin-bottom: 12px;
}

.score-details {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.score-section h5 {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 12px 0;
  color: #303133;
}

.recommendation-status-tag {
  margin-left: 8px;
}

.score-section ul {
  margin: 0;
  padding-left: 20px;
  list-style-type: disc;
}

.score-section li {
  margin-bottom: 8px;
  color: #606266;
  line-height: 1.5;
}

.recommendation-item {
  margin-bottom: 16px;
}

.recommendation-skill-focus {
  margin-top: 8px;
  font-size: 13px;
  color: #606266;
}

.recommendation-advice {
  margin-top: 8px;
  font-size: 13px;
  color: #303133;
  line-height: 1.5;
}

.recommendation-formats {
  margin-top: 10px;
  font-size: 13px;
  color: #606266;
}

.recommendation-formats .formats-list {
  margin: 5px 0 0 20px;
  padding: 0;
  list-style-type: disc;
}

.recommendation-formats .formats-list li {
  margin-top: 4px;
}

.final-report-actions {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #EBEEF5;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.actions-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: stretch;
  width: 100%;
}

.actions-group .el-button {
  width: 100%;
  justify-content: center;
}

.actions-group__danger {
  margin-top: 4px;
}

.reports-actions-group {
  display: flex;
  flex-direction: row;
  gap: 8px;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.reports-actions-group .el-button {
  flex-shrink: 0;
}

.reports-table :deep(colgroup col) {
  width: 25% !important;
}

.reports-table :deep(.el-table__cell) {
  text-align: center;
}

@media (max-width: 768px) {
  .card-header {
    flex-direction: column;
    align-items: stretch;
  }

  .header-actions {
    flex-direction: column;
  }

  .score-details {
    grid-template-columns: 1fr;
  }
}
</style>
