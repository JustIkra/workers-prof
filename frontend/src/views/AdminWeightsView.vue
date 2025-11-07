<template>
  <app-layout>
    <div class="admin-weights-view">
      <el-card class="header-card">
        <h1>Управление весовыми таблицами</h1>
        <p>Загрузка и активация весовых таблиц для расчёта профессиональной пригодности</p>
      </el-card>

      <el-card>
        <el-alert
          title="Функционал управления весовыми таблицами"
          type="info"
          :closable="false"
          show-icon
        >
          <p>Здесь будет реализован функционал:</p>
          <ul>
            <li>Загрузка новых весовых таблиц в формате JSON</li>
            <li>Просмотр существующих таблиц с фильтрацией по профессиональной области</li>
            <li>Активация нужной версии таблицы</li>
            <li>Валидация весов (сумма должна быть = 1.0)</li>
          </ul>
        </el-alert>
      </el-card>
    </div>
  </app-layout>
</template>

<script setup>
import AppLayout from '@/components/AppLayout.vue'
</script>

<style scoped>
.admin-weights-view {
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

ul {
  margin: 10px 0 0 0;
}
</style>
