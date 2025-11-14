import { nextTick, reactive } from 'vue'

const DEFAULT_ANIMATION_DURATION = 280
const DEFAULT_MIN_INTERVAL = 2000
const ANIMATION_BUFFER = 40

export function useFieldErrorAnimation(initialFields = [], options = {}) {
  const minInterval = options.minInterval ?? DEFAULT_MIN_INTERVAL
  const animationDuration = options.duration ?? DEFAULT_ANIMATION_DURATION

  const state = reactive({
    errors: {},
    animations: {},
    timestamps: {},
    timers: {}
  })

  const ensureField = (prop) => {
    if (!(prop in state.errors)) {
      state.errors[prop] = false
    }
    if (!(prop in state.animations)) {
      state.animations[prop] = false
    }
    if (!(prop in state.timestamps)) {
      state.timestamps[prop] = 0
    }
    if (!(prop in state.timers)) {
      state.timers[prop] = null
    }
  }

  const clearTimer = (prop) => {
    if (state.timers[prop]) {
      clearTimeout(state.timers[prop])
      state.timers[prop] = null
    }
  }

  const triggerForField = (prop, { force = false } = {}) => {
    ensureField(prop)
    const now = Date.now()
    if (!force && now - state.timestamps[prop] < minInterval) {
      return
    }
    state.timestamps[prop] = now
    clearTimer(prop)
    state.animations[prop] = false
    nextTick(() => {
      state.animations[prop] = true
      state.timers[prop] = setTimeout(() => {
        state.animations[prop] = false
        state.timers[prop] = null
      }, animationDuration + ANIMATION_BUFFER)
    })
  }

  const triggerForFields = (props, optionsArg = {}) => {
    props.forEach((prop) => triggerForField(prop, optionsArg))
  }

  const handleValidationErrors = (fields = {}) => {
    const props = Object.keys(fields)
    if (!props.length) {
      return
    }
    props.forEach((prop) => {
      ensureField(prop)
      state.errors[prop] = true
    })
    triggerForFields(props)
  }

  const handleFieldValidate = (prop, isValid) => {
    if (!prop) return
    ensureField(prop)
    state.errors[prop] = !isValid
    if (!isValid) {
      triggerForField(prop)
    }
  }

  const markExternalErrors = (props = []) => {
    props.forEach((prop) => {
      ensureField(prop)
      state.errors[prop] = true
    })
  }

  const clearFieldError = (prop) => {
    ensureField(prop)
    state.errors[prop] = false
  }

  const clearAll = () => {
    Object.keys(state.errors).forEach((prop) => {
      state.errors[prop] = false
      state.animations[prop] = false
      state.timestamps[prop] = 0
      clearTimer(prop)
    })
  }

  const getFormItemClass = (prop) => ({
    'auth-field-error': Boolean(state.errors[prop]),
    'auth-field-animate': Boolean(state.animations[prop])
  })

  const isFieldErrored = (prop) => Boolean(state.errors[prop])

  initialFields.forEach((prop) => ensureField(prop))

  return {
    getFormItemClass,
    handleValidationErrors,
    handleFieldValidate,
    triggerForFields,
    markExternalErrors,
    clearFieldError,
    clearAll,
    isFieldErrored
  }
}



