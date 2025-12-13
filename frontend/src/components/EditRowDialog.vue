<template>
  <Dialog
    :visible="visible"
    modal
    header="Edit Record"
    :style="{ width: '50vw' }"
    @update:visible="val => $emit('update:visible', val)"
  >
    <div v-if="localData" class="flex flex-col gap-4">
      <template v-for="col in columns" :key="col.name">
      <div v-if="!isHidden(col)" class="flex flex-col gap-1">
        <label class="font-medium text-gray-700 dark:text-gray-200">{{ col.name }}</label>

        <!-- BLOB Handling -->
        <div v-if="isBlob(col)" class="p-2 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded text-yellow-700 dark:text-yellow-400 text-sm">
          BLOB editing not supported yet.
        </div>

        <!-- Boolean/Checkbox (Future improvement, currently using text/dropdown if type known) -->

        <!-- Read-Only Handling -->
        <div v-else-if="col.read_only" class="p-2 bg-gray-100 dark:bg-gray-800 rounded border border-gray-300 dark:border-gray-700 text-gray-500 font-mono text-sm">
           {{ localData[col.name] }}
           <span class="ml-2 text-xs text-gray-400 italic">(Read Only)</span>
        </div>

        <!-- Date/Time Picker -->
        <DatePicker
          v-else-if="isDate(col)"
          v-model="localData[col.name]"
          :showTime="isTimestamp(col)"
          hourFormat="24"
          fluid
          dateFormat="yy-mm-dd"
        />

        <!-- Default Text Input -->
        <InputText
          v-else
          v-model="localData[col.name]"
          class="w-full"
          :type="getInputType(col)"
        />
        <small class="text-xs text-gray-400">Type: {{ col.type }}</small>
      </div>
      </template>
    </div>

    <template #footer>
      <Button label="Cancel" icon="pi pi-times" text @click="$emit('update:visible', false)" />
      <Button label="Save" icon="pi pi-check" @click="save" :loading="saving" />
    </template>
  </Dialog>
</template>

<script setup>
import { ref, watch, toRaw } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'

const props = defineProps({
  visible: Boolean,
  rowData: Object,
  columns: Array // [{name: 'ID', type: 'INTEGER'}, ...]
})

const emit = defineEmits(['update:visible', 'save'])

const localData = ref({})
const saving = ref(false)

watch(() => props.rowData, (newVal) => {
  if (newVal) {
    // Deep copy to avoid mutating parent state directly
    const copy = JSON.parse(JSON.stringify(newVal))

    // Parse Date Strings back to Date Objects for PrimeVue DatePicker
    props.columns.forEach(col => {
       if (isDate(col) && copy[col.name]) {
           copy[col.name] = new Date(copy[col.name])
       }
    })

    localData.value = copy
  }
}, { immediate: true })

const isHidden = (col) => {
  return col.name === 'DB_KEY' || col.name === 'RDB$DB_KEY'
}

const isBlob = (col) => {
  const type = (col.type || '').toUpperCase()
  return type.includes('BLOB')
}

const isDate = (col) => {
  const type = (col.type || '').toUpperCase()
  return type.includes('TIMESTAMP') || type.includes('DATE')
}

const isTimestamp = (col) => {
  const type = (col.type || '').toUpperCase()
  return type.includes('TIMESTAMP')
}

const getDateFormat = (col) => {
  // PrimeVue format
  return 'yy-mm-dd'
}

const getInputType = (col) => {
  const type = (col.type || '').toUpperCase()
  if (type.includes('INT') || type.includes('FLOAT') || type.includes('DOUBLE') || type.includes('DECIMAL') || type.includes('NUMERIC')) {
    return 'number'
  }
  return 'text'
}

const formatDateForSQL = (date, includeTime = true) => {
    if (!date) return null
    // Format: YYYY-MM-DD HH:MM:SS or YYYY-MM-DD
    const pad = (n) => n < 10 ? '0' + n : n
    const y = date.getFullYear()
    const m = pad(date.getMonth() + 1)
    const d = pad(date.getDate())

    if (!includeTime) {
        return `${y}-${m}-${d}`
    }

    const h = pad(date.getHours())
    const min = pad(date.getMinutes())
    const s = pad(date.getSeconds())
    return `${y}-${m}-${d} ${h}:${min}:${s}`
}

const save = () => {
  saving.value = true

  const changes = {}

  for (const key in localData.value) {
    let newVal = localData.value[key]
    let oldVal = props.rowData[key]

    // Find column def to check type
    const col = props.columns.find(c => c.name === key)
    if (col && isDate(col)) {
        // Handle Date Comparison
        let oldDate = oldVal ? new Date(oldVal) : null
        let newDate = newVal

        // Simple equality check on time value
        if (oldDate && newDate && oldDate.getTime() === newDate.getTime()) {
            continue;
        }

        // Handle case where one is null and other is not
        if (!oldDate && !newDate) continue;

        // If changed, format it for SQL
        if (newDate instanceof Date) {
            changes[key] = formatDateForSQL(newDate, isTimestamp(col))
        } else {
            changes[key] = newVal // Should be null or something
        }
        continue
    }

    if (newVal !== oldVal) {
      changes[key] = newVal
    }
  }

  // If no changes, maybe just close? Or warn?
  if (Object.keys(changes).length === 0) {
      // No changes
      saving.value = false
      emit('update:visible', false) // Just close
      return
  }

  emit('save', changes)
  saving.value = false
}
</script>
