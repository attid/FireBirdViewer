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
  // Emit save event with the modified data
  emit('save', localData.value)
  saving.value = false
}
</script>
