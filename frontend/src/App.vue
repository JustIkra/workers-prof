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
</style>
