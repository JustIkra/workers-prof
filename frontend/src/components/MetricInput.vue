<template>
  <el-input
    ref="inputRef"
    v-model="displayValue"
    :placeholder="placeholder"
    :disabled="disabled"
    :class="{ 'is-invalid': hasError }"
    @input="handleInput"
    @blur="handleBlur"
    @focus="handleFocus"
  >
    <template
      v-if="showControls"
      #append
    >
      <el-button-group>
        <el-button
          :icon="Minus"
          :disabled="disabled || isMinDisabled"
          @click="decrement"
        />
        <el-button
          :icon="Plus"
          :disabled="disabled || isMaxDisabled"
          @click="increment"
        />
      </el-button-group>
    </template>
  </el-input>
  <div
    v-if="hasError"
    class="error-message"
  >
    {{ errorMessage }}
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Plus, Minus } from '@element-plus/icons-vue'
import { formatNumber, parseNumber } from '@/utils/numberFormat'

const props = defineProps({
  modelValue: {
    type: [Number, String],
    default: null
  },
  min: {
    type: Number,
    default: 1
  },
  max: {
    type: Number,
    default: 10
  },
  step: {
    type: Number,
    default: 0.1
  },
  precision: {
    type: Number,
    default: 1
  },
  placeholder: {
    type: String,
    default: 'Введите значение'
  },
  disabled: {
    type: Boolean,
    default: false
  },
  showControls: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['update:modelValue', 'change', 'blur'])

const inputRef = ref(null)
const displayValue = ref('')
const isFocused = ref(false)
const hasError = ref(false)
const errorMessage = ref('')

// Computed
const numericValue = computed(() => {
  return parseNumber(displayValue.value)
})

const isMinDisabled = computed(() => {
  const val = numericValue.value
  return val === null || val <= props.min
})

const isMaxDisabled = computed(() => {
  const val = numericValue.value
  return val === null || val >= props.max
})

// Methods
const updateDisplayValue = (value) => {
  if (value === null || value === undefined || value === '') {
    displayValue.value = ''
    return
  }

  // Если не в фокусе, форматируем красиво
  if (!isFocused.value) {
    displayValue.value = formatNumber(value, props.precision)
  } else {
    // В фокусе показываем как есть
    displayValue.value = String(value).replace('.', ',')
  }
}

const validate = (value) => {
  if (value === null || value === undefined || value === '') {
    hasError.value = false
    errorMessage.value = ''
    return true
  }

  const num = parseNumber(value)

  if (num === null) {
    hasError.value = true
    errorMessage.value = 'Некорректное число'
    return false
  }

  if (num < props.min) {
    hasError.value = true
    errorMessage.value = `Значение должно быть не меньше ${formatNumber(props.min, props.precision)}`
    return false
  }

  if (num > props.max) {
    hasError.value = true
    errorMessage.value = `Значение должно быть не больше ${formatNumber(props.max, props.precision)}`
    return false
  }

  hasError.value = false
  errorMessage.value = ''
  return true
}

const handleInput = (value) => {
  // Разрешаем ввод только цифр, запятой, точки и минуса
  const cleaned = value.replace(/[^\d,.-]/g, '')

  // Разрешаем только одну запятую/точку
  let hasDecimal = false
  const filtered = cleaned.split('').filter(char => {
    if (char === ',' || char === '.') {
      if (hasDecimal) return false
      hasDecimal = true
      return true
    }
    return true
  }).join('').replace('.', ',')

  displayValue.value = filtered

  // Валидация и эмит
  const num = parseNumber(filtered)
  if (num !== null) {
    emit('update:modelValue', num)
  } else if (filtered === '' || filtered === '-') {
    emit('update:modelValue', null)
  }
}

const handleBlur = () => {
  isFocused.value = false

  const num = parseNumber(displayValue.value)

  // Валидируем при потере фокуса
  if (validate(displayValue.value)) {
    // Округляем до нужной точности
    if (num !== null) {
      const rounded = Math.round(num * Math.pow(10, props.precision)) / Math.pow(10, props.precision)

      // Ограничиваем диапазоном
      const clamped = Math.max(props.min, Math.min(props.max, rounded))

      emit('update:modelValue', clamped)
      updateDisplayValue(clamped)
      emit('change', clamped)
    }
  } else {
    // Если невалидное, сбрасываем
    if (num !== null && (num < props.min || num > props.max)) {
      // Для вне диапазона - ограничиваем
      const clamped = Math.max(props.min, Math.min(props.max, num))
      emit('update:modelValue', clamped)
      updateDisplayValue(clamped)
      emit('change', clamped)
      hasError.value = false
      errorMessage.value = ''
    }
  }

  emit('blur')
}

const handleFocus = () => {
  isFocused.value = true
  // В фокусе показываем значение с запятой для редактирования
  if (numericValue.value !== null) {
    displayValue.value = String(numericValue.value).replace('.', ',')
  }
}

const increment = () => {
  const current = numericValue.value || 0
  const newValue = Math.min(props.max, current + props.step)
  const rounded = Math.round(newValue * Math.pow(10, props.precision)) / Math.pow(10, props.precision)

  emit('update:modelValue', rounded)
  emit('change', rounded)
  updateDisplayValue(rounded)
}

const decrement = () => {
  const current = numericValue.value || 0
  const newValue = Math.max(props.min, current - props.step)
  const rounded = Math.round(newValue * Math.pow(10, props.precision)) / Math.pow(10, props.precision)

  emit('update:modelValue', rounded)
  emit('change', rounded)
  updateDisplayValue(rounded)
}

// Watch для внешних изменений
watch(() => props.modelValue, (newValue) => {
  updateDisplayValue(newValue)
}, { immediate: true })

// Инициализация
updateDisplayValue(props.modelValue)
</script>

<style scoped>
.is-invalid :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px var(--el-color-danger) inset;
}

.error-message {
  color: var(--el-color-danger);
  font-size: 12px;
  line-height: 1.4;
  margin-top: 4px;
}

:deep(.el-input-group__append) {
  padding: 0;
  background-color: var(--el-fill-color-blank);
}

:deep(.el-button-group) {
  display: flex;
}

:deep(.el-button-group .el-button) {
  margin: 0;
  border-radius: 0;
  padding: 8px 12px;
}

:deep(.el-button-group .el-button:first-child) {
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
}

:deep(.el-button-group .el-button:last-child) {
  border-top-right-radius: var(--el-input-border-radius, var(--el-border-radius-base));
  border-bottom-right-radius: var(--el-input-border-radius, var(--el-border-radius-base));
}
</style>
