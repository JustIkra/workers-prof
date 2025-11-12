<template>
  <div class="register-container">
    <el-card class="register-card">
      <template #header>
        <div class="card-header">
          <h2>Регистрация</h2>
          <p>Создайте аккаунт для работы с системой</p>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleRegister"
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
            placeholder="Введите пароль (минимум 8 символов, буквы и цифры)"
            size="large"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>

        <el-form-item
          label="Подтверждение пароля"
          prop="confirmPassword"
        >
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="Повторите пароль"
            size="large"
            show-password
            autocomplete="new-password"
            @keyup.enter="handleRegister"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            style="width: 100%"
            :loading="authStore.loading"
            @click="handleRegister"
          >
            Зарегистрироваться
          </el-button>
        </el-form-item>

        <div class="login-link">
          <span>Уже есть аккаунт?</span>
          <router-link to="/login">
            Войти
          </router-link>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores'

const router = useRouter()
const authStore = useAuthStore()

const formRef = ref(null)
const form = reactive({
  email: '',
  password: '',
  confirmPassword: ''
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('Подтвердите пароль'))
  } else if (value !== form.password) {
    callback(new Error('Пароли не совпадают'))
  } else {
    callback()
  }
}

const rules = {
  email: [
    { required: true, message: 'Введите email', trigger: 'blur' },
    { type: 'email', message: 'Некорректный email', trigger: 'blur' }
  ],
  password: [
    { required: true, message: 'Введите пароль', trigger: 'blur' },
    { min: 8, message: 'Пароль должен быть не менее 8 символов', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

const handleRegister = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      await authStore.register(form.email, form.password)
      ElMessage.success({
        message: 'Регистрация успешна! Ожидайте одобрения администратора.',
        duration: 5000
      })
      router.push('/login?message=pending')
    } catch (error) {
      ElMessage.error(authStore.error || 'Ошибка регистрации')
    }
  })
}
</script>

<style scoped>
.register-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-primary-light) 0%, #fff 100%);
  padding: 20px;
}

.register-card {
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

.login-link {
  text-align: center;
  color: #666;
}

.login-link a {
  color: var(--color-primary);
  text-decoration: none;
  margin-left: 5px;
}

.login-link a:hover {
  text-decoration: underline;
}
</style>
