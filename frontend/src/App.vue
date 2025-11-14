<template>
  <el-config-provider :locale="locale">
    <router-view />
  </el-config-provider>
</template>

<script setup>
import { ref } from 'vue'
import ru from 'element-plus/es/locale/lang/ru'

const locale = ref(ru)
</script>

<style>
@import url('/assets/theme-tokens.css');

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: var(--font-family-base);
  background-color: var(--color-bg-page);
}

#app {
  min-height: 100vh;
}

.actions-group {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: var(--spacing-sm, 8px);
  width: 220px;
  margin: 0 auto;
}

.actions-group .el-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: var(--button-height-default, 32px);
  font-size: var(--font-size-base, 14px);
  border-radius: var(--border-radius-base, 4px);
}

.actions-group .el-button :deep(.el-icon) {
  margin-right: var(--spacing-sm, 8px);
}

.actions-group__danger {
  align-self: stretch;
}
</style>
