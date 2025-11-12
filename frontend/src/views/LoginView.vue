<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <div class="card-header">
          <h2>Вход в систему</h2>
          <p>Цифровая модель универсальных компетенций</p>
        </div>
      </template>

      <el-alert
        v-if="route.query.message === 'pending'"
        title="Ожидание одобрения"
        type="warning"
        :closable="false"
        show-icon
        style="margin-bottom: 20px"
      >
        Ваш аккаунт ожидает одобрения администратором.
      </el-alert>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleLogin"
      >
        <el-form-item
          label="Email"
          prop="email"
        >
          <el-input
            v-model="form.email"
            type="email"
            placeholder="Введите email"
            size="large"
            autocomplete="email"
          />
        </el-form-item>

        <el-form-item
          label="Пароль"
          prop="password"
        >
          <el-input
            v-model="form.password"
            type="password"
            placeholder="Введите пароль"
            size="large"
            show-password
            autocomplete="current-password"
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            style="width: 100%"
            :loading="authStore.loading"
            @click="handleLogin"
          >
            Войти
          </el-button>
        </el-form-item>

        <div class="register-link">
          <span>Нет аккаунта?</span>
          <router-link to="/register">
            Зарегистрироваться
          </router-link>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref(null)
const form = reactive({
  email: '',
  password: ''
})

const rules = {
  email: [
    { required: true, message: 'Введите email', trigger: 'blur' },
    { type: 'email', message: 'Некорректный email', trigger: 'blur' }
  ],
  password: [
    { required: true, message: 'Введите пароль', trigger: 'blur' },
    { min: 6, message: 'Пароль должен быть не менее 6 символов', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      await authStore.login(form.email, form.password)
      ElMessage.success('Вход выполнен успешно')

      const redirect = route.query.redirect || '/participants'
      router.push(redirect)
    } catch (error) {
      ElMessage.error(authStore.error || 'Ошибка входа')
    }
  })
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-primary-light) 0%, #fff 100%);
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 450px;
}

.card-header {
  text-align: center;
}

.card-header h2 {
  margin: 0 0 8px 0;
  color: var(--color-primary);
  font-size: 24px;
}

.card-header p {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.register-link {
  text-align: center;
  color: #666;
}

.register-link a {
  color: var(--color-primary);
  text-decoration: none;
  margin-left: 5px;
}

.register-link a:hover {
  text-decoration: underline;
}
</style>
