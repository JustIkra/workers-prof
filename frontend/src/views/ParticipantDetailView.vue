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

        <el-table
          v-loading="loadingReports"
          :data="reports"
          stripe
        >
          <el-table-column
            prop="report_type"
            label="Тип"
            width="120"
          >
            <template #default="{ row }">
              <el-tag>{{ formatReportType(row.report_type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column
            prop="status"
            label="Статус"
            width="150"
          >
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)">
                {{ formatStatus(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            prop="created_at"
            label="Дата загрузки"
            width="180"
          >
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column
            label="Действия"
            width="400"
            fixed="right"
          >
            <template #default="{ row }">
              <el-button
                size="small"
                @click="downloadReport(row.id)"
              >
                <el-icon><Download /></el-icon>
                Скачать
              </el-button>
              <el-button
                size="small"
                type="primary"
                :disabled="row.status === 'EXTRACTED'"
                @click="extractMetrics(row.id)"
              >
                <el-icon><DataAnalysis /></el-icon>
                Извлечь метрики
              </el-button>
              <el-button
                size="small"
                type="info"
                @click="viewMetrics(row.id)"
              >
                <el-icon><View /></el-icon>
                Метрики
              </el-button>
              <el-button
                size="small"
                type="danger"
                @click="confirmDeleteReport(row)"
              >
                <el-icon><Delete /></el-icon>
                Удалить
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-empty
          v-if="!reports.length && !loadingReports"
          description="Нет загруженных отчётов"
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
                  <div
                    v-if="result.recommendations && result.recommendations.length"
                    class="score-section"
                  >
                    <h5>Рекомендации:</h5>
                    <ul>
                      <li
                        v-for="(rec, idx) in result.recommendations"
                        :key="idx"
                      >
                        {{ rec }}
                      </li>
                    </ul>
                  </div>
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
            label="Тип отчёта"
            prop="report_type"
          >
            <el-select
              v-model="uploadForm.report_type"
              placeholder="Выберите тип"
              style="width: 100%"
            >
              <el-option
                label="Отчёт 1"
                value="REPORT_1"
              />
              <el-option
                label="Отчёт 2"
                value="REPORT_2"
              />
              <el-option
                label="Отчёт 3"
                value="REPORT_3"
              />
            </el-select>
          </el-form-item>
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
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Upload,
  Download,
  DataAnalysis,
  View,
  Delete,
  TrendCharts
} from '@element-plus/icons-vue'
import AppLayout from '@/components/AppLayout.vue'
import MetricsEditor from '@/components/MetricsEditor.vue'
import { useParticipantsStore } from '@/stores'
import { reportsApi, profActivitiesApi, scoringApi } from '@/api'
import { formatFromApi } from '@/utils/numberFormat'

const router = useRouter()
const route = useRoute()
const participantsStore = useParticipantsStore()

const loading = ref(false)
const loadingReports = ref(false)
const loadingActivities = ref(false)
const uploading = ref(false)
const calculating = ref(false)

const participant = computed(() => participantsStore.currentParticipant)
const reports = ref([])
const scoringResults = ref([])
const profActivities = ref([])
const currentMetrics = ref([])
const currentReportId = ref(null)

const showUploadDialog = ref(false)
const showScoringDialog = ref(false)
const showMetricsDialog = ref(false)

const uploadFormRef = ref(null)
const fileList = ref([])
const uploadForm = reactive({
  report_type: '',
  file: null
})

const uploadRules = {
  report_type: [{ required: true, message: 'Выберите тип отчёта', trigger: 'change' }],
  file: [{ required: true, message: 'Выберите файл', trigger: 'change' }]
}

const scoringForm = reactive({
  activityCode: ''
})

// Format helpers
const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('ru-RU', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatReportType = (type) => {
  const types = {
    REPORT_1: 'Отчёт 1',
    REPORT_2: 'Отчёт 2',
    REPORT_3: 'Отчёт 3'
  }
  return types[type] || type
}

const formatStatus = (status) => {
  const statuses = {
    UPLOADED: 'Загружен',
    EXTRACTED: 'Обработан',
    FAILED: 'Ошибка'
  }
  return statuses[status] || status
}

const getStatusType = (status) => {
  const types = {
    UPLOADED: 'info',
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

const getConfidenceColor = (confidence) => {
  if (confidence >= 0.8) return '#67C23A'
  if (confidence >= 0.6) return '#E6A23C'
  return '#F56C6C'
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

const loadReports = async () => {
  loadingReports.value = true
  try {
    // API endpoint для получения списка отчётов участника
    // Пока используем заглушку, т.к. endpoint может быть не реализован
    reports.value = []
    ElMessage.info('Функция загрузки списка отчётов будет доступна после реализации соответствующего API')
  } catch (error) {
    console.error('Error loading reports:', error)
  } finally {
    loadingReports.value = false
  }
}

const loadScoringResults = async () => {
  try {
    const response = await scoringApi.getHistory(route.params.id)
    scoringResults.value = response.results || []
  } catch (error) {
    console.error('Error loading scoring results:', error)
  }
}

const loadProfActivities = async () => {
  loadingActivities.value = true
  try {
    const response = await profActivitiesApi.list()
    profActivities.value = response.activities || []
  } catch (error) {
    ElMessage.error('Ошибка загрузки профессиональных областей')
  } finally {
    loadingActivities.value = false
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
      await reportsApi.upload(route.params.id, uploadForm.report_type, uploadForm.file)
      ElMessage.success('Отчёт загружен успешно')
      showUploadDialog.value = false
      uploadForm.report_type = ''
      uploadForm.file = null
      fileList.value = []
      await loadReports()
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
    setTimeout(() => loadReports(), 2000)
  } catch (error) {
    ElMessage.error('Ошибка запуска извлечения метрик')
  }
}

const viewMetrics = async (reportId) => {
  currentReportId.value = reportId
  showMetricsDialog.value = true
}

const handleMetricsUpdated = () => {
  ElMessage.success('Метрики обновлены')
  // Можно обновить список отчётов, если нужно
}

const confirmDeleteReport = (report) => {
  ElMessageBox.confirm(
    `Вы уверены, что хотите удалить отчёт "${formatReportType(report.report_type)}"?`,
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
    scoringResults.value.unshift({
      id: result.scoring_result_id,
      prof_activity_name: result.prof_activity_name,
      score_pct: parseFloat(result.score_pct),
      strengths: result.strengths || [],
      dev_areas: result.dev_areas || [],
      recommendations: result.recommendations || [],
      created_at: new Date().toISOString()
    })

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

onMounted(async () => {
  await loadParticipant()
  await loadReports()
  await loadScoringResults()
  await loadProfActivities()
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
