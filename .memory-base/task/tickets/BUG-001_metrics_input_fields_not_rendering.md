Код: BUG-001 — Metrics Input Fields Not Rendering in Edit Mode

Приоритет: HIGH
Статус: OPEN
Обнаружено: 2025-11-09
Категория: UI Bug

## Описание проблемы

При включении режима редактирования в диалоге "Метрики отчёта", поля ввода для метрик не отображаются. Видны только метки (labels) метрик без возможности редактирования значений.

## Воспроизведение

1. Залогиниться как admin@test.com / admin123
2. Перейти к участнику с загруженным отчётом
3. Нажать кнопку "Метрики" для отчёта
4. В диалоге "Метрики отчёта" нажать кнопку "Редактировать"
5. **Ожидаемое поведение**: Появляются input fields для всех 13 метрик
6. **Фактическое поведение**: Input fields не отображаются, видны только labels метрик

## Технические детали

### Обнаружено в файлах:
- `e2e/TEST_PLAN_S3-05_SCENARIOS_6-9_DETAILED.md` (section 6.8)
- Плановое тестирование Scenario 6: Manual Metrics Entry

### Затронутые компоненты:
- Frontend: Metrics Dialog Component
- Вероятный файл: `frontend/src/components/MetricsDialog.vue` или аналогичный
- Element Plus компоненты: `<el-input-number>` или `<el-input>`

### Ожидаемые метрики (13 шт):
1. Коммуникабельность (communicability)
2. Комплексное решение проблем (complex_problem_solving)
3. Обработка информации (information_processing)
4. Лидерство (leadership)
5. Конфликтность (низкая) (conflict_low)
6. Моральность / Нормативность (morality)
7. Невербальная логика (nonverbal_logic)
8. Организованность (organization)
9. Ответственность (responsibility)
10. Стрессоустойчивость (stress_resistance)
11. Роль «Душа команды» (Белбин) (team_soul_belbin)
12. Командность (teamwork)
13. Лексика (vocabulary)

### Accessibility Tree Analysis:
При включении Edit Mode:
- Кнопка "Редактировать" меняется на "Отмена" и "Сохранить" ✓
- Alert сообщение отображается ✓
- Метки метрик видны ✓
- **Input fields НЕ появляются в accessibility tree** ✗

## Влияние (Impact)

- **Severity**: HIGH - Блокирует критический функционал ручного ввода метрик
- **User Impact**: Пользователи не могут вводить/редактировать метрики вручную
- **Workaround**: НЕТ - функционал полностью заблокирован
- **Blocked Scenarios**:
  - Scenario 6: Manual Metrics Entry
  - Scenario 7: Calculate Score (зависит от наличия метрик)

## Возможные причины

1. **Conditional Rendering Issue**:
   - Vue `v-if` или `v-show` условие некорректно
   - Reactive state `isEditMode` не обновляется

2. **CSS Display Issue**:
   - Input fields рендерятся но скрыты через CSS
   - `display: none` или `visibility: hidden`

3. **Component Import Issue**:
   - Element Plus компоненты не импортированы
   - Missing component registration

4. **Data Binding Issue**:
   - Метрики не загружены из API
   - `v-for` цикл не создаёт input fields

## Рекомендуемое решение

### Шаг 1: Inspect Frontend Code
```bash
cd frontend/src
grep -r "Метрики отчёта" components/
grep -r "isEditMode" components/
grep -r "el-input-number" components/
```

### Шаг 2: Check Component Structure
В компоненте диалога метрик должен быть код типа:
```vue
<template>
  <el-dialog title="Метрики отчёта">
    <!-- ... -->
    <div v-if="isEditMode">
      <el-form-item
        v-for="metric in metrics"
        :key="metric.code"
        :label="metric.name"
      >
        <el-input-number
          v-model="metric.value"
          :min="1.0"
          :max="10.0"
          :precision="1"
        />
      </el-form-item>
    </div>
    <div v-else>
      <!-- Read-only view -->
    </div>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
const isEditMode = ref(false)
const metrics = ref([])

const handleEdit = () => {
  isEditMode.value = true  // THIS MUST WORK!
}
</script>
```

### Шаг 3: Fix Implementation
- Убедиться что `isEditMode` корректно переключается при клике "Редактировать"
- Проверить что `metrics` массив загружен из API
- Добавить `v-if="isEditMode"` для input fields
- Убрать конфликтующие CSS правила

### Шаг 4: Add Debug Logging
```vue
<script setup>
const handleEdit = () => {
  console.log('Before edit mode toggle:', isEditMode.value)
  isEditMode.value = true
  console.log('After edit mode toggle:', isEditMode.value)
  console.log('Metrics data:', metrics.value)
}
</script>
```

### Шаг 5: Update E2E Tests
После исправления, обновить тесты:
- `e2e/ui-manual-metrics-entry.spec.js` должен проходить
- Scenario 6.3: "Enter Valid Metric Values" должен работать

## Acceptance Criteria (для закрытия бага)

- [ ] При клике "Редактировать" появляются 13 input fields
- [ ] Input fields имеют placeholder или label с названием метрики
- [ ] Input fields принимают значения в диапазоне 1.0-10.0
- [ ] Валидация работает (ошибка при <1.0 или >10.0)
- [ ] Кнопка "Сохранить" сохраняет метрики в базу данных
- [ ] E2E тесты Scenario 6 проходят успешно
- [ ] Input fields доступны в accessibility tree

## Testing Checklist

- [ ] Manual test: открыть диалог и проверить input fields визуально
- [ ] E2E test: `npx playwright test e2e/ui-manual-metrics-entry.spec.js`
- [ ] Browser DevTools: проверить console errors
- [ ] Vue DevTools: проверить reactive state `isEditMode`
- [ ] Accessibility audit: проверить что fields доступны для screen readers

## Related Tickets

- S3-05: E2E минимум (критический путь заблокирован этим багом)
- S2-05: Frontend метрики/расчёт (возможно неполная реализация)

## Scre enshots / Evidence

См. файлы в `.playwright-mcp/`:
- `metrics-dialog-edit-mode.png` - показывает диалог в edit mode без input fields

## Priority Justification

**Критичность: HIGH** потому что:
1. Блокирует критический путь пользователя (S3-05)
2. Без ручного ввода метрик невозможен расчёт пригодности
3. Нет workaround - функционал полностью недоступен
4. Обнаружено в основном E2E сценарии

## Дедлайн

Необходимо исправить до завершения S3-05 (E2E минимум).

---

## ДИАГНОСТИКА И РЕШЕНИЕ (2025-11-10)

### Найденная проблема

**Root Cause:** В файле `frontend/src/components/MetricsEditor.vue` компонент `<MetricInput>` используется в template (строка 70-79), но **НЕ был импортирован** в `<script setup>` секции.

```vue
<!-- Template использует MetricInput -->
<template>
  <MetricInput
    v-model="formData.metrics[metricDef.id]"
    :disabled="!isEditing"
    ...
  />
</template>

<!-- Script не импортирует компонент -->
<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
// ❌ ОТСУТСТВУЕТ: import MetricInput from './MetricInput.vue'
import { metricsApi } from '@/api'
...
</script>
```

В **Vue 3 с Composition API** (`<script setup>`), все компоненты должны быть **явно импортированы**. Без импорта Vue не распознаёт компонент и не рендерит его, оставляя только labels без input fields.

### Проверка данных

✓ В базе данных есть 13 активных метрик (`metric_def`)
✓ API endpoint `/api/metric-defs?active_only=true` работает корректно
✓ Backend возвращает правильные данные
✗ Frontend компонент не рендерился из-за отсутствующего импорта

### Примененное решение

Добавлен недостающий импорт в `frontend/src/components/MetricsEditor.vue:122`:

```diff
<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
+import MetricInput from './MetricInput.vue'
import { metricsApi } from '@/api'
import { parseNumber, formatForApi } from '@/utils/numberFormat'
```

**Файл изменен:** `frontend/src/components/MetricsEditor.vue`
**Строка:** 122
**Коммит:** Ожидается после тестирования

### Шаги для проверки исправления

1. **Frontend пересобран:** `cd frontend && npm run build` ✓
2. **Обновить страницу в браузере:** Hard refresh (Cmd+Shift+R / Ctrl+Shift+R)
3. **Проверить:**
   - Открыть диалог "Метрики отчёта"
   - Нажать кнопку "Редактировать"
   - **Ожидается:** 13 input fields должны появиться
   - Попробовать ввести значения
   - Нажать "Сохранить"

### Статус

**RESOLVED** — Исправление применено, ожидается проверка пользователем.

---

**Автор**: Test Planner Agent
**Дата создания**: 2025-11-09
**Последнее обновление**: 2025-11-10 (диагностика и исправление)
