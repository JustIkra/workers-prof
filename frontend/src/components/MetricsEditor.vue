<template>
  <el-card class="metrics-editor">
    <template #header>
      <div class="card-header">
        <span>Ручной ввод метрик</span>
        <el-button
          v-if="!isEditing"
          type="primary"
          size="small"
          @click="startEditing"
        >
          Редактировать
        </el-button>
        <div v-else>
          <el-button
            size="small"
            @click="cancelEditing"
          >
            Отмена
          </el-button>
          <el-button
            type="primary"
            size="small"
            :loading="saving"
            @click="saveMetrics"
          >
            Сохранить
          </el-button>
        </div>
      </div>
    </template>

    <el-alert
      v-if="error"
      type="error"
      :title="error"
      closable
      style="margin-bottom: 16px;"
      @close="error = null"
    />

    <el-alert
      v-if="!metrics || metrics.length === 0"
      type="info"
      :closable="false"
      style="margin-bottom: 16px;"
    >
      Метрики для этого отчёта ещё не извлечены. Вы можете ввести их вручную.
    </el-alert>

    <el-form
      ref="formRef"
      :model="formData"
      label-position="top"
      :disabled="!isEditing"
    >
      <el-row :gutter="20">
        <el-col
          v-for="metricDef in availableMetrics"
          :key="metricDef.id"
          :xs="24"
          :sm="12"
          :md="8"
          :lg="6"
        >
          <el-form-item
            :label="`${metricDef.name} ${metricDef.unit ? '(' + metricDef.unit + ')' : ''}`"
            :prop="`metrics.${metricDef.id}`"
            :rules="getValidationRules(metricDef)"
          >
            <el-input-number
              v-model="formData.metrics[metricDef.id]"
              :min="metricDef.min_value || 1"
              :max="metricDef.max_value || 10"
              :precision="1"
              :step="0.1"
              :controls="true"
              style="width: 100%;"
              placeholder="Введите значение"
            />
            <div
              v-if="metricDef.description"
              class="metric-description"
            >
              {{ metricDef.description }}
            </div>
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>

    <div
      v-if="metrics && metrics.length > 0"
      class="metrics-info"
    >
      <el-divider />
      <div class="info-row">
        <span class="info-label">Источник данных:</span>
        <el-tag
          v-for="source in uniqueSources"
          :key="source"
          :type="getSourceType(source)"
          size="small"
          style="margin-left: 8px;"
        >
          {{ getSourceLabel(source) }}
        </el-tag>
      </div>
      <div
        v-if="lastUpdated"
        class="info-row"
      >
        <span class="info-label">Последнее обновление:</span>
        <span>{{ formatDate(lastUpdated) }}</span>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { metricsApi } from '@/api'
import { formatNumber, parseNumber, formatForApi, formatFromApi } from '@/utils/numberFormat'

const props = defineProps({
  reportId: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['metrics-updated'])

// State
const loading = ref(false)
const saving = ref(false)
const isEditing = ref(false)
const error = ref(null)

const availableMetrics = ref([])
const metrics = ref([])
const formData = ref({ metrics: {} })
const originalData = ref({})

// Computed
const uniqueSources = computed(() => {
  if (!metrics.value || metrics.value.length === 0) return []
  return [...new Set(metrics.value.map(m => m.source))]
})

const lastUpdated = computed(() => {
  if (!metrics.value || metrics.value.length === 0) return null
  // Предполагаем, что metrics отсортированы, берём последнюю
  return new Date() // В реальности нужно брать из данных
})

// Methods
const loadMetricDefs = async () => {
  try {
    const response = await metricsApi.listMetricDefs(true)
    availableMetrics.value = response.items || []
  } catch (err) {
    console.error('Failed to load metric definitions:', err)
    error.value = 'Не удалось загрузить определения метрик'
  }
}

const loadMetrics = async () => {
  loading.value = true
  error.value = null
  try {
    const response = await metricsApi.listExtractedMetrics(props.reportId)
    metrics.value = response.items || []

    // Заполняем formData существующими значениями
    formData.value.metrics = {}
    metrics.value.forEach(metric => {
      // Используем parseNumber для корректной обработки запятой
      formData.value.metrics[metric.metric_def_id] = parseNumber(metric.value)
    })

    // Сохраняем оригинальные данные для отмены
    originalData.value = JSON.parse(JSON.stringify(formData.value.metrics))
  } catch (err) {
    console.error('Failed to load metrics:', err)
    error.value = 'Не удалось загрузить метрики'
  } finally {
    loading.value = false
  }
}

const getValidationRules = (metricDef) => {
  return [
    {
      validator: (rule, value, callback) => {
        if (value === null || value === undefined || value === '') {
          callback()
          return
        }

        const min = metricDef.min_value || 1
        const max = metricDef.max_value || 10

        if (value < min) {
          callback(new Error(`Значение должно быть не меньше ${min}`))
        } else if (value > max) {
          callback(new Error(`Значение должно быть не больше ${max}`))
        } else {
          callback()
        }
      },
      trigger: 'change'
    }
  ]
}

const startEditing = () => {
  isEditing.value = true
  originalData.value = JSON.parse(JSON.stringify(formData.value.metrics))
}

const cancelEditing = () => {
  formData.value.metrics = JSON.parse(JSON.stringify(originalData.value))
  isEditing.value = false
  error.value = null
}

const saveMetrics = async () => {
  saving.value = true
  error.value = null

  try {
    // Собираем метрики для отправки
    const metricsToSave = []

    for (const [metricDefId, value] of Object.entries(formData.value.metrics)) {
      if (value !== null && value !== undefined && value !== '') {
        // Используем formatForApi для корректной отправки на сервер
        const apiValue = formatForApi(value)
        if (apiValue !== null) {
          metricsToSave.push({
            metric_def_id: metricDefId,
            value: apiValue,
            source: 'MANUAL',
            notes: null
          })
        }
      }
    }

    if (metricsToSave.length === 0) {
      ElMessage.warning('Не введено ни одного значения метрики')
      saving.value = false
      return
    }

    // Отправляем массовый запрос
    await metricsApi.bulkCreateExtractedMetrics(props.reportId, metricsToSave)

    ElMessage.success(`Успешно сохранено ${metricsToSave.length} метрик`)
    isEditing.value = false

    // Перезагружаем метрики
    await loadMetrics()

    emit('metrics-updated')
  } catch (err) {
    console.error('Failed to save metrics:', err)
    // Улучшенная обработка ошибок
    let errorMessage = 'Не удалось сохранить метрики'
    if (err.response?.data?.detail) {
      if (typeof err.response.data.detail === 'string') {
        errorMessage = err.response.data.detail
      } else if (Array.isArray(err.response.data.detail)) {
        errorMessage = err.response.data.detail.map(e => e.msg || e.message).join(', ')
      }
    }
    error.value = errorMessage
    ElMessage.error(errorMessage)
  } finally {
    saving.value = false
  }
}

const getSourceType = (source) => {
  switch (source) {
    case 'OCR': return 'info'
    case 'LLM': return 'warning'
    case 'MANUAL': return 'success'
    default: return ''
  }
}

const getSourceLabel = (source) => {
  switch (source) {
    case 'OCR': return 'OCR'
    case 'LLM': return 'Gemini Vision'
    case 'MANUAL': return 'Ручной ввод'
    default: return source
  }
}

const formatDate = (date) => {
  return new Date(date).toLocaleString('ru-RU', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Lifecycle
onMounted(async () => {
  await loadMetricDefs()
  await loadMetrics()
})

// Watch для изменения reportId
watch(() => props.reportId, async (newId) => {
  if (newId) {
    await loadMetrics()
  }
})
</script>

<style scoped>
.metrics-editor {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.metric-description {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
  line-height: 1.4;
}

.metrics-info {
  margin-top: 16px;
}

.info-row {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  font-size: 14px;
}

.info-label {
  font-weight: 500;
  color: var(--el-text-color-secondary);
  margin-right: 8px;
}
</style>
