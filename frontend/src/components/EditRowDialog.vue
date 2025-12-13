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
    localData.value = JSON.parse(JSON.stringify(newVal))
  }
}, { immediate: true })

const isHidden = (col) => {
  return col.name === 'DB_KEY' || col.name === 'RDB$DB_KEY'
}

const isBlob = (col) => {
  const type = (col.type || '').toUpperCase()
  return type.includes('BLOB')
}

const getInputType = (col) => {
  const type = (col.type || '').toUpperCase()
  if (type.includes('INT') || type.includes('FLOAT') || type.includes('DOUBLE') || type.includes('DECIMAL') || type.includes('NUMERIC')) {
    return 'number'
  }
  return 'text'
}

const save = () => {
  saving.value = true

  // Calculate changes
  const changes = {}
  // Always include DB_KEY (or find it in original rowData if hidden in localData?)
  // Assuming localData has it even if hidden

  // Actually, we should just emit the diff + db_key.
  // But for simplicity, let's just emit the whole object for now?
  // NO, user requested to send only changes.

  // Need to compare localData with props.rowData
  for (const key in localData.value) {
    // If it's DB_KEY, skip adding to changes map logic (handled by parent?)
    // Or just check equality.
    if (localData.value[key] !== props.rowData[key]) {
      changes[key] = localData.value[key]
    }
  }

  // If no changes, maybe just close? Or warn?
  if (Object.keys(changes).length === 0) {
      // No changes
      saving.value = false
      emit('update:visible', false) // Just close
      return
  }

  // We need to pass the keys so the parent can identify the row
  // DB_KEY might be in rowData but not changed.
  // Let's pass the changes map, but we need to ensure the parent has access to the original DB_KEY
  // The parent has 'editingRow' which is the original object.
  // So we just emit 'changes'.

  emit('save', changes)
  saving.value = false
}
</script>
