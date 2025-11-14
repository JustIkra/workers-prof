import { describe, beforeEach, afterEach, it, expect, vi } from 'vitest'
import { nextTick } from 'vue'
import { useFieldErrorAnimation } from '../useFieldErrorAnimation'

describe('useFieldErrorAnimation', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2025-01-01T00:00:00Z').getTime())
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('применяет классы ошибки и анимации при handleValidationErrors', async () => {
    const { getFormItemClass, handleValidationErrors } = useFieldErrorAnimation(['email'])

    handleValidationErrors({
      email: [{ message: 'Ошибка' }]
    })

    await nextTick()

    expect(getFormItemClass('email')).toEqual({
      'auth-field-error': true,
      'auth-field-animate': true
    })

    vi.advanceTimersByTime(400)
    await nextTick()

    expect(getFormItemClass('email')).toEqual({
      'auth-field-error': true,
      'auth-field-animate': false
    })
  })

  it('не запускает анимацию чаще одного раза за 2 секунды', async () => {
    const { getFormItemClass, triggerForFields } = useFieldErrorAnimation(['password'])

    triggerForFields(['password'])
    await nextTick()
    expect(getFormItemClass('password')).toEqual({
      'auth-field-error': false,
      'auth-field-animate': true
    })

    vi.advanceTimersByTime(360)
    await nextTick()

    triggerForFields(['password'])
    await nextTick()
    expect(getFormItemClass('password')).toEqual({
      'auth-field-error': false,
      'auth-field-animate': false
    })

    vi.advanceTimersByTime(2000)
    triggerForFields(['password'])
    await nextTick()

    expect(getFormItemClass('password')).toEqual({
      'auth-field-error': false,
      'auth-field-animate': true
    })
  })
})



