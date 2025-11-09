<template>
  <app-layout>
    <div class="admin-weights-view">
      <el-card class="header-card">
        <div class="header-content">
          <div>
            <h1>Управление весовыми таблицами</h1>
            <p>Каждая профессиональная область имеет свою уникальную весовую таблицу</p>
          </div>
          <div class="header-buttons">
            <el-button @click="showProfActivityDialog" size="large" type="primary">
              <el-icon><FolderAdd /></el-icon>
              Новая область
            </el-button>
          </div>
        </div>
      </el-card>

      <!-- Поиск по названию области -->
      <el-card class="search-card">
        <el-input
          v-model="searchQuery"
          placeholder="Поиск по названию профессиональной области..."
          :prefix-icon="Search"
          size="large"
          clearable
        />
      </el-card>

      <!-- Группировка по профессиональным областям -->
      <div v-loading="loading" class="areas-container">
        <el-empty
          v-if="filteredAreas.length === 0"
          description="Нет профессиональных областей"
        />

        <div v-else class="areas-grid">
          <div
            v-for="area in filteredAreas"
            :key="area.id"
            class="area-card-wrapper"
          >
            <el-card class="area-card" shadow="hover">
              <template #header>
                <div class="area-header">
                  <div class="area-title">
                    <el-icon :size="24" color="#409EFF"><Folder /></el-icon>
                    <h3>{{ area.name }}</h3>
                  </div>
                  <el-button
                    size="small"
                    @click="editProfActivity(area)"
                    circle
                  >
                    <el-icon><Edit /></el-icon>
                  </el-button>
                </div>
                <div v-if="area.description" class="area-description">
                  {{ area.description }}
                </div>
              </template>

              <!-- Весовая таблица области -->
              <div v-if="!area.weightTable" class="no-table">
                <el-empty description="Весовая таблица не создана" :image-size="80">
                  <el-button
                    type="primary"
                    @click="createTableForArea(area)"
                  >
                    <el-icon><Plus /></el-icon>
                    Создать таблицу
                  </el-button>
                </el-empty>
              </div>

              <div v-else class="table-info">
                <div class="table-stats">
                  <div class="stat-item">
                    <span class="stat-label">Компетенций:</span>
                    <el-tag size="large">{{ area.weightTable.weights.length }}</el-tag>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Сумма весов:</span>
                    <el-tag
                      :type="getWeightSumType(area.weightTable)"
                      size="large"
                    >
                      {{ calculateWeightSum(area.weightTable).toFixed(4) }}
                    </el-tag>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Обновлена:</span>
                    <el-text type="info">{{ formatDate(area.weightTable.created_at) }}</el-text>
                  </div>
                </div>

                <div class="table-actions">
                  <el-button @click="viewDetails(area.weightTable)" type="info">
                    <el-icon><View /></el-icon>
                    Просмотр
                  </el-button>
                  <el-button @click="editTable(area.weightTable)" type="primary">
                    <el-icon><Edit /></el-icon>
                    Редактировать
                  </el-button>
                </div>
              </div>
            </el-card>
          </div>
        </div>
      </div>
    </div>

    <!-- Диалог создания/редактирования весовой таблицы -->
    <el-dialog
      v-model="tableDialogVisible"
      :title="dialogTitle"
      width="900px"
      :close-on-click-modal="false"
      align-center
    >
      <el-form :model="tableForm" label-width="200px" ref="formRef" label-position="top">
        <el-form-item v-if="!editingTable" label="Профессиональная область" required>
          <el-card shadow="never" class="area-display-card">
            <div class="selected-area">
              <el-icon :size="20" color="#409EFF"><Folder /></el-icon>
              <span class="area-name">{{ selectedActivityName }}</span>
            </div>
          </el-card>
        </el-form-item>
        <el-form-item v-else label="Профессиональная область">
          <el-card shadow="never" class="area-display-card">
            <div class="selected-area">
              <el-icon :size="20" color="#409EFF"><Folder /></el-icon>
              <span class="area-name">{{ selectedActivityName }}</span>
            </div>
          </el-card>
        </el-form-item>

        <el-divider content-position="left">Компетенции и веса</el-divider>

        <div class="weights-editor">
          <!-- Индикатор суммы весов -->
          <el-alert
            :type="weightSumAlertType"
            :title="`Сумма весов: ${currentWeightSum.toFixed(4)} (требуется: 1.0000)`"
            :closable="false"
            show-icon
            style="margin-bottom: 16px"
          >
            <template v-if="currentWeightSum !== 1.0">
              <span v-if="currentWeightSum < 1.0">
                Осталось распределить: {{ (1.0 - currentWeightSum).toFixed(4) }}
              </span>
              <span v-else>
                Превышение: {{ (currentWeightSum - 1.0).toFixed(4) }}
              </span>
            </template>
          </el-alert>

          <!-- Список компетенций -->
          <div
            v-for="(weight, index) in tableForm.weights"
            :key="index"
            class="weight-row"
          >
            <el-select
              v-model="weight.metric_code"
              placeholder="Выберите метрику"
              filterable
              style="width: 420px"
            >
              <el-option
                v-for="metric in availableMetrics"
                :key="metric.code"
                :label="`${metric.name} (${metric.code})`"
                :value="metric.code"
              />
            </el-select>

            <el-input-number
              v-model="weight.weight"
              :min="0"
              :max="1"
              :step="0.01"
              :precision="4"
              placeholder="Вес"
              style="width: 180px"
            />

            <el-button
              type="danger"
              size="small"
              :icon="Delete"
              circle
              @click="removeWeight(index)"
            />
          </div>

          <!-- Кнопка добавления компетенции -->
          <el-button
            type="primary"
            plain
            @click="addWeight"
            :icon="Plus"
            style="margin-top: 16px"
          >
            Добавить компетенцию
          </el-button>
        </div>

        <el-divider />

        <el-form-item label="Метаданные (опционально)">
          <el-input
            v-model="tableForm.metadata.description"
            type="textarea"
            :rows="3"
            placeholder="Описание версии таблицы, примечания и т.д."
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="tableDialogVisible = false">Отмена</el-button>
        <el-button
          type="primary"
          @click="saveTable"
          :loading="saving"
          :disabled="!isValidWeightSum"
        >
          {{ editingTable ? 'Сохранить' : 'Создать' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Диалог просмотра весовой таблицы -->
    <el-dialog
      v-model="detailsDialogVisible"
      :title="`Весовая таблица: ${selectedTable?.prof_activity_name}`"
      width="900px"
      align-center
    >
      <div v-if="selectedTable">
        <el-card shadow="never" class="table-summary-card">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="Профессиональная область" :span="2">
              {{ selectedTable.prof_activity_name }}
            </el-descriptions-item>
            <el-descriptions-item label="Создана">
              {{ formatDate(selectedTable.created_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="Сумма весов">
              <el-tag :type="getWeightSumType(selectedTable)" size="large">
                {{ calculateWeightSum(selectedTable).toFixed(4) }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-divider content-position="left">
          <el-icon><View /></el-icon>
          Компетенции ({{ selectedTable.weights.length }})
        </el-divider>

        <el-table :data="enrichedWeights(selectedTable.weights)" stripe max-height="500" size="large">
          <el-table-column type="index" label="#" width="60" align="center" />
          <el-table-column label="Метрика" min-width="250">
            <template #default="{ row }">
              <div class="metric-cell">
                <strong>{{ row.metric_name }}</strong>
                <br />
                <el-text size="small" type="info">{{ row.metric_code }}</el-text>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="weight" label="Вес" width="140" align="center">
            <template #default="{ row }">
              <el-tag size="large">{{ parseFloat(row.weight).toFixed(4) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="Процент" width="140" align="center">
            <template #default="{ row }">
              <el-tag type="info" size="large">
                {{ (parseFloat(row.weight) * 100).toFixed(2) }}%
              </el-tag>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="selectedTable.metadata && selectedTable.metadata.description" style="margin-top: 20px">
          <el-divider content-position="left">Описание</el-divider>
          <el-card shadow="never" class="metadata-card">
            {{ selectedTable.metadata.description }}
          </el-card>
        </div>
      </div>

      <template #footer>
        <el-button @click="detailsDialogVisible = false" size="large">Закрыть</el-button>
        <el-button
          type="primary"
          @click="editTable(selectedTable)"
          size="large"
        >
          <el-icon><Edit /></el-icon>
          Редактировать
        </el-button>
      </template>
    </el-dialog>

    <!-- Диалог создания/редактирования профессиональной области -->
    <el-dialog
      v-model="profActivityDialogVisible"
      :title="editingProfActivity ? 'Редактировать область' : 'Создать область'"
      width="600px"
    >
      <el-form :model="profActivityForm" label-width="120px">
        <el-form-item label="Код" required>
          <el-input
            v-model="profActivityForm.code"
            :disabled="!!editingProfActivity"
            placeholder="meeting_facilitation"
          />
        </el-form-item>
        <el-form-item label="Название" required>
          <el-input
            v-model="profActivityForm.name"
            placeholder="Проведение совещаний"
          />
        </el-form-item>
        <el-form-item label="Описание">
          <el-input
            v-model="profActivityForm.description"
            type="textarea"
            :rows="3"
            placeholder="Описание профессиональной области"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="profActivityDialogVisible = false">Отмена</el-button>
        <el-button type="danger" v-if="editingProfActivity" @click="deleteProfActivity">
          Удалить
        </el-button>
        <el-button
          type="primary"
          @click="saveProfActivity"
          :loading="saving"
        >
          {{ editingProfActivity ? 'Сохранить' : 'Создать' }}
        </el-button>
      </template>
    </el-dialog>
  </app-layout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Edit, View, FolderAdd, Folder, Search } from '@element-plus/icons-vue'
import AppLayout from '@/components/AppLayout.vue'
import { weightsApi } from '@/api/weights'
import { profActivitiesApi } from '@/api/profActivities'
import { metricsApi } from '@/api/metrics'

// Состояние
const loading = ref(false)
const saving = ref(false)
const searchQuery = ref('')

// Данные
const weightTables = ref([])
const profActivities = ref([])
const availableMetrics = ref([])

// Диалоги
const tableDialogVisible = ref(false)
const detailsDialogVisible = ref(false)
const profActivityDialogVisible = ref(false)

const selectedTable = ref(null)
const editingTable = ref(null)
const editingProfActivity = ref(null)

// Формы
const formRef = ref(null)
const tableForm = ref({
  prof_activity_code: '',
  weights: [],
  metadata: {
    description: ''
  }
})

const profActivityForm = ref({
  code: '',
  name: '',
  description: ''
})

// Вычисляемые свойства
const filteredAreas = computed(() => {
  // Объединяем области с их таблицами
  const areasWithTables = profActivities.value.map(activity => {
    const table = weightTables.value.find(t => t.prof_activity_code === activity.code)
    return {
      ...activity,
      weightTable: table || null
    }
  })

  // Фильтруем по поисковому запросу
  if (!searchQuery.value) {
    return areasWithTables
  }

  const query = searchQuery.value.toLowerCase()
  return areasWithTables.filter(area =>
    area.name.toLowerCase().includes(query) ||
    (area.description && area.description.toLowerCase().includes(query))
  )
})

const selectedActivityName = computed(() => {
  const activity = profActivities.value.find(a => a.code === tableForm.value.prof_activity_code)
  return activity ? activity.name : ''
})

const dialogTitle = computed(() => {
  if (editingTable.value) {
    return `Редактировать весовую таблицу: ${selectedActivityName.value}`
  }
  return `Создать весовую таблицу: ${selectedActivityName.value}`
})

const currentWeightSum = computed(() => {
  return tableForm.value.weights.reduce((sum, w) => sum + (parseFloat(w.weight) || 0), 0)
})

const isValidWeightSum = computed(() => {
  return Math.abs(currentWeightSum.value - 1.0) < 0.0001 && tableForm.value.weights.length > 0
})

const weightSumAlertType = computed(() => {
  if (Math.abs(currentWeightSum.value - 1.0) < 0.0001) return 'success'
  if (currentWeightSum.value < 1.0) return 'warning'
  return 'error'
})

// Методы
const loadWeightTables = async () => {
  try {
    loading.value = true
    const data = await weightsApi.list()
    weightTables.value = data
  } catch (error) {
    console.error('Failed to load weight tables:', error)
    ElMessage.error('Ошибка загрузки весовых таблиц')
  } finally {
    loading.value = false
  }
}

const createTableForArea = (area) => {
  editingTable.value = null
  tableForm.value = {
    prof_activity_code: area.code,
    weights: [],
    metadata: {
      description: ''
    }
  }
  tableDialogVisible.value = true
}

const loadProfActivities = async () => {
  try {
    const data = await profActivitiesApi.list()
    profActivities.value = data
  } catch (error) {
    console.error('Failed to load prof activities:', error)
    ElMessage.error('Ошибка загрузки профессиональных областей')
  }
}

const loadMetrics = async () => {
  try {
    const data = await metricsApi.listMetricDefs(true)
    availableMetrics.value = data.items || []
  } catch (error) {
    console.error('Failed to load metrics:', error)
    ElMessage.error('Ошибка загрузки метрик')
  }
}

const showCreateDialog = () => {
  editingTable.value = null
  tableForm.value = {
    prof_activity_code: '',
    weights: [],
    metadata: {
      description: ''
    }
  }
  tableDialogVisible.value = true
}

const editTable = (table) => {
  editingTable.value = table
  tableForm.value = {
    prof_activity_code: table.prof_activity_code,
    weights: table.weights.map(w => ({
      metric_code: w.metric_code,
      weight: parseFloat(w.weight)
    })),
    metadata: table.metadata || { description: '' }
  }
  tableDialogVisible.value = true
}

const addWeight = () => {
  tableForm.value.weights.push({
    metric_code: '',
    weight: 0
  })
}

const removeWeight = (index) => {
  tableForm.value.weights.splice(index, 1)
}

const saveTable = async () => {
  try {
    saving.value = true

    // Валидация
    if (!tableForm.value.prof_activity_code) {
      ElMessage.warning('Выберите профессиональную область')
      return
    }

    if (tableForm.value.weights.length === 0) {
      ElMessage.warning('Добавьте хотя бы одну компетенцию')
      return
    }

    // Проверка уникальности метрик
    const metricCodes = tableForm.value.weights.map(w => w.metric_code)
    const uniqueCodes = new Set(metricCodes.filter(c => c))
    if (uniqueCodes.size !== tableForm.value.weights.length) {
      ElMessage.warning('Компетенции должны быть уникальными')
      return
    }

    // Проверка заполненности
    if (tableForm.value.weights.some(w => !w.metric_code)) {
      ElMessage.warning('Все компетенции должны быть заполнены')
      return
    }

    // Подготовка данных
    const payload = {
      prof_activity_code: tableForm.value.prof_activity_code,
      weights: tableForm.value.weights.map(w => ({
        metric_code: w.metric_code,
        weight: parseFloat(w.weight)
      })),
      metadata: tableForm.value.metadata.description ? tableForm.value.metadata : null
    }

    await weightsApi.upload(payload)
    ElMessage.success(editingTable.value ? 'Таблица сохранена' : 'Таблица создана')
    tableDialogVisible.value = false
    await loadWeightTables()
  } catch (error) {
    console.error('Failed to save weight table:', error)
    ElMessage.error(error.response?.data?.detail || 'Ошибка сохранения таблицы')
  } finally {
    saving.value = false
  }
}

const viewDetails = (table) => {
  selectedTable.value = table
  detailsDialogVisible.value = true
}

const showProfActivityDialog = () => {
  editingProfActivity.value = null
  profActivityForm.value = {
    code: '',
    name: '',
    description: ''
  }
  profActivityDialogVisible.value = true
}

const editProfActivity = (activity) => {
  editingProfActivity.value = activity
  profActivityForm.value = {
    code: activity.code,
    name: activity.name,
    description: activity.description || ''
  }
  profActivityDialogVisible.value = true
}

const saveProfActivity = async () => {
  try {
    saving.value = true

    if (!profActivityForm.value.code || !profActivityForm.value.name) {
      ElMessage.warning('Заполните обязательные поля')
      return
    }

    if (editingProfActivity.value) {
      await profActivitiesApi.update(editingProfActivity.value.id, {
        name: profActivityForm.value.name,
        description: profActivityForm.value.description
      })
      ElMessage.success('Область обновлена')
    } else {
      await profActivitiesApi.create(profActivityForm.value)
      ElMessage.success('Область создана')
    }

    profActivityDialogVisible.value = false
    await loadProfActivities()
  } catch (error) {
    console.error('Failed to save prof activity:', error)
    ElMessage.error(error.response?.data?.detail || 'Ошибка сохранения области')
  } finally {
    saving.value = false
  }
}

const deleteProfActivity = async () => {
  try {
    await ElMessageBox.confirm(
      `Удалить профессиональную область "${editingProfActivity.value.name}"? Это действие нельзя отменить.`,
      'Предупреждение',
      {
        confirmButtonText: 'Удалить',
        cancelButtonText: 'Отмена',
        type: 'error'
      }
    )

    await profActivitiesApi.delete(editingProfActivity.value.id)
    ElMessage.success('Область удалена')
    profActivityDialogVisible.value = false
    await loadProfActivities()
    await loadWeightTables()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete prof activity:', error)
      ElMessage.error(error.response?.data?.detail || 'Ошибка удаления области')
    }
  }
}

const calculateWeightSum = (table) => {
  return table.weights.reduce((sum, w) => sum + parseFloat(w.weight), 0)
}

const getWeightSumType = (table) => {
  const sum = calculateWeightSum(table)
  if (Math.abs(sum - 1.0) < 0.0001) return 'success'
  return 'danger'
}

const enrichedWeights = (weights) => {
  return weights.map(w => {
    const metric = availableMetrics.value.find(m => m.code === w.metric_code)
    return {
      ...w,
      metric_name: metric?.name || w.metric_code,
      metric_code: w.metric_code
    }
  })
}

const formatDate = (dateStr) => {
  return new Date(dateStr).toLocaleString('ru-RU')
}

// Инициализация
onMounted(async () => {
  await Promise.all([
    loadWeightTables(),
    loadProfActivities(),
    loadMetrics()
  ])
})
</script>

<style scoped>
.admin-weights-view {
  max-width: 1600px;
  margin: 0 auto;
  padding: 20px;
}

/* Header */
.header-card {
  margin-bottom: 24px;
  border-radius: 12px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-buttons {
  display: flex;
  gap: 12px;
}

.header-card h1 {
  margin: 0 0 8px 0;
  font-size: 28px;
  font-weight: 600;
  color: #303133;
}

.header-card p {
  margin: 0;
  color: #606266;
  font-size: 15px;
}

/* Search */
.search-card {
  margin-bottom: 24px;
  border-radius: 12px;
}

/* Areas Grid */
.areas-container {
  min-height: 300px;
}

.areas-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(450px, 1fr));
  gap: 24px;
}

.area-card-wrapper {
  min-height: 200px;
}

.area-card {
  border-radius: 12px;
  height: 100%;
  transition: all 0.3s ease;
}

.area-card:hover {
  transform: translateY(-4px);
}

/* Area Header */
.area-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.area-title {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.area-title h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.area-description {
  margin-top: 8px;
  color: #909399;
  font-size: 14px;
  line-height: 1.5;
}

/* Table Info */
.no-table {
  padding: 20px;
  text-align: center;
}

.table-info {
  padding: 16px 0;
}

.table-stats {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 20px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background-color: #f5f7fa;
  border-radius: 8px;
}

.stat-label {
  font-weight: 500;
  color: #606266;
}

.table-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

/* Dialog Styles */
.area-display-card {
  background-color: #f0f9ff;
  border: 1px solid #409EFF;
}

.selected-area {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px;
}

.area-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.table-summary-card {
  background-color: #f5f7fa;
  margin-bottom: 20px;
}

.metric-cell {
  padding: 8px 0;
}

.metadata-card {
  background-color: #f5f7fa;
  padding: 16px;
  line-height: 1.6;
}

/* Weights Editor */
.weights-editor {
  padding: 20px;
  background-color: #f5f7fa;
  border-radius: 8px;
}

.weight-row {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
  padding: 12px;
  background-color: white;
  border-radius: 8px;
}
</style>
