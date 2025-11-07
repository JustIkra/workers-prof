<template>
  <app-layout>
    <div class="participants-view">
      <el-card class="header-card">
        <div class="header-content">
          <h1>Участники</h1>
          <el-button
            type="primary"
            @click="showCreateDialog = true"
          >
            <el-icon><Plus /></el-icon>
            Добавить участника
          </el-button>
        </div>
      </el-card>

      <el-card class="search-card">
        <el-form
          :inline="true"
          :model="searchForm"
        >
          <el-form-item label="Поиск">
            <el-input
              v-model="searchForm.query"
              placeholder="Введите имя"
              clearable
              style="width: 300px"
              @change="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-form-item>
          <el-form-item label="Внешний ID">
            <el-input
              v-model="searchForm.external_id"
              placeholder="Внешний ID"
              clearable
              style="width: 200px"
              @change="handleSearch"
            />
          </el-form-item>
        </el-form>
      </el-card>

      <el-card
        v-loading="participantsStore.loading"
        class="table-card"
      >
        <el-table
          :data="participantsStore.participants"
          stripe
        >
          <el-table-column
            prop="full_name"
            label="ФИО"
            min-width="200"
          />
          <el-table-column
            prop="birth_date"
            label="Дата рождения"
            width="150"
          />
          <el-table-column
            prop="external_id"
            label="Внешний ID"
            width="150"
          />
          <el-table-column
            label="Действия"
            width="180"
            fixed="right"
          >
            <template #default="{ row }">
              <el-button
                type="primary"
                size="small"
                @click="viewParticipant(row.id)"
              >
                Открыть
              </el-button>
              <el-button
                type="danger"
                size="small"
                @click="confirmDelete(row)"
              >
                Удалить
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination">
          <el-pagination
            v-model:current-page="searchForm.page"
            v-model:page-size="searchForm.size"
            :total="participantsStore.pagination.total"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            @current-change="handleSearch"
            @size-change="handleSearch"
          />
        </div>
      </el-card>

      <!-- Диалог создания -->
      <el-dialog
        v-model="showCreateDialog"
        title="Добавить участника"
        width="500px"
      >
        <el-form
          ref="createFormRef"
          :model="createForm"
          :rules="createRules"
          label-position="top"
        >
          <el-form-item
            label="ФИО"
            prop="full_name"
          >
            <el-input
              v-model="createForm.full_name"
              placeholder="Введите полное имя"
            />
          </el-form-item>
          <el-form-item
            label="Дата рождения"
            prop="birth_date"
          >
            <el-date-picker
              v-model="createForm.birth_date"
              type="date"
              placeholder="Выберите дату"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item
            label="Внешний ID"
            prop="external_id"
          >
            <el-input
              v-model="createForm.external_id"
              placeholder="Внешний идентификатор (необязательно)"
            />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showCreateDialog = false">
            Отмена
          </el-button>
          <el-button
            type="primary"
            :loading="participantsStore.loading"
            @click="handleCreate"
          >
            Создать
          </el-button>
        </template>
      </el-dialog>
    </div>
  </app-layout>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import AppLayout from '@/components/AppLayout.vue'
import { useParticipantsStore } from '@/stores'

const router = useRouter()
const participantsStore = useParticipantsStore()

const searchForm = reactive({
  query: '',
  external_id: '',
  page: 1,
  size: 20
})

const showCreateDialog = ref(false)
const createFormRef = ref(null)
const createForm = reactive({
  full_name: '',
  birth_date: '',
  external_id: ''
})

const createRules = {
  full_name: [
    { required: true, message: 'Введите ФИО', trigger: 'blur' },
    { min: 1, max: 255, message: 'От 1 до 255 символов', trigger: 'blur' }
  ]
}

const handleSearch = async () => {
  try {
    await participantsStore.searchParticipants(searchForm)
  } catch (error) {
    ElMessage.error('Ошибка загрузки участников')
  }
}

const handleCreate = async () => {
  if (!createFormRef.value) return

  await createFormRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      await participantsStore.createParticipant(createForm)
      ElMessage.success('Участник создан')
      showCreateDialog.value = false
      createForm.full_name = ''
      createForm.birth_date = ''
      createForm.external_id = ''
      await handleSearch()
    } catch (error) {
      ElMessage.error(participantsStore.error || 'Ошибка создания участника')
    }
  })
}

const viewParticipant = (id) => {
  router.push(`/participants/${id}`)
}

const confirmDelete = (participant) => {
  ElMessageBox.confirm(
    `Вы уверены, что хотите удалить участника "${participant.full_name}"?`,
    'Подтверждение удаления',
    {
      confirmButtonText: 'Удалить',
      cancelButtonText: 'Отмена',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await participantsStore.deleteParticipant(participant.id)
      ElMessage.success('Участник удалён')
      await handleSearch()
    } catch (error) {
      ElMessage.error(participantsStore.error || 'Ошибка удаления участника')
    }
  }).catch(() => {})
}

onMounted(() => {
  handleSearch()
})
</script>

<style scoped>
.participants-view {
  max-width: 1400px;
  margin: 0 auto;
}

.header-card {
  margin-bottom: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-content h1 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.search-card {
  margin-bottom: 20px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
