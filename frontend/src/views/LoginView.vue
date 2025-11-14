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
        @validate="onFieldValidate"
      >
        <el-form-item
          label="Email"
          prop="email"
          :class="getFormItemClass('email')"
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
          :class="getFormItemClass('password')"
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

        <div
          v-if="serverErrors.length"
          :class="['auth-form-error', { 'auth-field-animate': serverErrorAnimated }]"
          role="alert"
        >
          <span
            class="auth-form-error__icon"
            aria-hidden="true"
          >
            !
          </span>
          <div class="auth-form-error__content">
            <template v-if="serverErrors.length === 1">
              {{ serverErrors[0] }}
            </template>
            <template v-else>
              <ul class="auth-form-error__list">
                <li
                  v-for="(message, index) in serverErrors"
                  :key="index"
                >
                  {{ message }}
                </li>
              </ul>
            </template>
          </div>
        </div>

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
import { reactive, ref, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores'
import { useFieldErrorAnimation } from '@/composables/useFieldErrorAnimation'
import { ElMessage } from 'element-plus'
import { normalizeApiError } from '@/utils/normalizeError'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref(null)
const form = reactive({
  email: '',
  password: ''
})

const authFields = ['email', 'password']
const {
  getFormItemClass,
  handleValidationErrors,
  handleFieldValidate,
  triggerForFields,
  markExternalErrors
} = useFieldErrorAnimation(authFields)

const serverErrors = ref([])
const serverErrorAnimated = ref(false)

const restartServerErrorAnimation = () => {
  serverErrorAnimated.value = false
  nextTick(() => {
    serverErrorAnimated.value = true
    setTimeout(() => {
      serverErrorAnimated.value = false
    }, 360)
  })
}

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

const onFieldValidate = (prop, isValid) => {
  handleFieldValidate(prop, isValid)
  if (isValid && serverErrors.value.length) {
    serverErrors.value = []
  }
}

const handleLogin = async () => {
  if (!formRef.value) return

  serverErrors.value = []

  await formRef.value.validate(async (valid, fields) => {
    if (!valid) {
      handleValidationErrors(fields)
      return
    }

    try {
      await authStore.login(form.email, form.password)
      ElMessage.success('Вход выполнен успешно')
      const redirect = route.query.redirect || '/participants'
      router.push(redirect)
    } catch (error) {
      const normalized = error.normalizedError || normalizeApiError(error, authStore.error || 'Ошибка входа')
      serverErrors.value = normalized.messages
      const fieldsWithErrors = Object.keys(normalized.fieldErrors)
      const fieldsToMark = fieldsWithErrors.length ? fieldsWithErrors : authFields
      markExternalErrors(fieldsToMark)
      triggerForFields(fieldsToMark)
      restartServerErrorAnimation()
    }
  })
}

watch(
  () => [form.email, form.password],
  () => {
    if (serverErrors.value.length) {
      serverErrors.value = []
    }
  }
)
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
