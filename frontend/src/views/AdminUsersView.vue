<template>
  <app-layout>
    <div class="admin-users-view">
      <el-card class="header-card">
        <h1>Управление пользователями</h1>
        <p>Одобрение новых пользователей системы</p>
      </el-card>

      <el-card
        v-loading="adminStore.loading"
        class="users-card"
      >
        <h3>Ожидают одобрения ({{ adminStore.pendingUsers.length }})</h3>

        <el-empty
          v-if="adminStore.pendingUsers.length === 0"
          description="Нет пользователей, ожидающих одобрения"
        />

        <el-table
          v-else
          :data="adminStore.pendingUsers"
          stripe
        >
          <el-table-column
            prop="email"
            label="Email"
            min-width="250"
          />
          <el-table-column
            label="Статус"
            width="120"
          >
            <template #default="{ row }">
              <el-tag type="warning">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            prop="created_at"
            label="Дата регистрации"
            width="180"
          >
            <template #default="{ row }">
              {{ new Date(row.created_at).toLocaleDateString('ru-RU') }}
            </template>
          </el-table-column>
          <el-table-column
            label="Действия"
            width="150"
            fixed="right"
          >
            <template #default="{ row }">
              <div class="actions-group">
                <el-button
                  type="success"
                  size="small"
                  @click="handleApprove(row)"
                >
                  Одобрить
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </app-layout>
</template>

<script setup>
import { onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import AppLayout from '@/components/AppLayout.vue'
import { useAdminStore } from '@/stores'

const adminStore = useAdminStore()

const handleApprove = async (user) => {
  try {
    await adminStore.approveUser(user.id)
    ElMessage.success(`Пользователь ${user.email} одобрен`)
  } catch (error) {
    ElMessage.error(adminStore.error || 'Ошибка одобрения пользователя')
  }
}

onMounted(async () => {
  try {
    await adminStore.fetchPendingUsers()
  } catch (error) {
    ElMessage.error('Ошибка загрузки пользователей')
  }
})
</script>

<style scoped>
.admin-users-view {
  max-width: 1200px;
  margin: 0 auto;
}

.header-card {
  margin-bottom: 20px;
}

.header-card h1 {
  margin: 0 0 8px 0;
  font-size: 24px;
  color: #303133;
}

.header-card p {
  margin: 0;
  color: #606266;
}

.users-card h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  color: #303133;
}

.actions-group {
  width: 120px;
  margin: 0;
}
</style>
