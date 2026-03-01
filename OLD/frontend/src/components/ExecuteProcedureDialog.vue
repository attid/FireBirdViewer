<template>
  <Dialog
    v-model:visible="visible"
    :header="'Execute ' + procedureName"
    :modal="true"
    :style="{ width: '50vw' }"
    :draggable="false"
    :resizable="false"
  >
    <div v-if="loading" class="flex justify-center items-center p-4">
      <i class="pi pi-spin pi-spinner text-2xl text-primary-500"></i>
    </div>
    <div v-else-if="error" class="p-4 text-red-500">
      {{ error }}
    </div>
    <div v-else class="flex flex-col gap-4">
      <div v-if="parameters.length === 0" class="text-gray-500 italic">
        No input parameters required.
      </div>
      <div v-for="param in parameters" :key="param.name" class="flex flex-col gap-1">
        <label :for="param.name" class="font-semibold">{{ param.name }}</label>
        <InputText
          :id="param.name"
          v-model="paramValues[param.name]"
          class="w-full"
          :placeholder="param.type"
        />
      </div>
    </div>
    <template #footer>
      <div class="flex justify-end gap-2">
        <Button label="Cancel" icon="pi pi-times" text @click="visible = false" />
        <Button label="Execute" icon="pi pi-play" @click="execute" :loading="executing" />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import axios from 'axios'

const props = defineProps({
  procedureName: {
    type: String,
    required: true
  },
  api: {
    type: Function, // axios instance
    required: true
  }
})

const emit = defineEmits(['execute'])

const visible = defineModel('visible')

const parameters = ref([])
const paramValues = ref({})
const loading = ref(false)
const executing = ref(false)
const error = ref('')

watch(visible, (newVal) => {
  if (newVal && props.procedureName) {
    loadParameters()
  }
})

const loadParameters = async () => {
  loading.value = true
  error.value = ''
  parameters.value = []
  paramValues.value = {}

  try {
    const res = await props.api.get(`/api/procedure/${props.procedureName}/parameters`)
    parameters.value = res.data || []
    // Initialize values
    parameters.value.forEach(p => {
      paramValues.value[p.name] = ''
    })
  } catch (err) {
    console.error(err)
    error.value = "Failed to load parameters"
  } finally {
    loading.value = false
  }
}

const execute = async () => {
  executing.value = true
  try {
    // Send request
    const res = await props.api.post(`/api/procedure/${props.procedureName}/execute`, paramValues.value)
    emit('execute', res.data)
    visible.value = false
  } catch (err) {
    console.error(err)
    // Show error in dialog or let parent handle?
    // Let's show error here
    error.value = err.response?.data?.error || "Execution failed"
  } finally {
    executing.value = false
  }
}
</script>
