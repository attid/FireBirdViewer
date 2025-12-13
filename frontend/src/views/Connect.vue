<template>
  <div class="flex items-center justify-center min-h-screen bg-surface-100 dark:bg-surface-900">
    <div class="w-full max-w-md p-6 bg-white dark:bg-surface-800 rounded-lg shadow-lg">
      <h1 class="text-2xl font-bold mb-6 text-center text-surface-900 dark:text-surface-0">Connect to Firebird</h1>

      <div class="flex flex-col gap-4">
        <div class="flex flex-col gap-2">
            <label for="database" class="font-medium text-surface-700 dark:text-surface-200">Database</label>
            <InputText id="database" v-model="form.database" placeholder="localhost:/var/lib/firebird/data/employee.fdb" />
            <small class="text-surface-500">Format: host:/path/to/db or alias</small>
        </div>

        <div class="flex flex-col gap-2">
            <label for="user" class="font-medium text-surface-700 dark:text-surface-200">User</label>
            <InputText id="user" v-model="form.user" placeholder="SYSDBA" />
        </div>

        <div class="flex flex-col gap-2">
            <label for="password" class="font-medium text-surface-700 dark:text-surface-200">Password</label>
            <Password inputId="password" v-model="form.password" :feedback="false" toggleMask placeholder="Password" />
        </div>

        <Button label="Connect" @click="connect" :loading="loading" class="mt-4" />

        <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

        <DemoInfo v-if="isDemo" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Button from 'primevue/button'
import Message from 'primevue/message'
import DemoInfo from '../components/DemoInfo.vue'

const router = useRouter()
const isDemo = ref(false)
const form = ref({
  database: 'localhost:/var/lib/firebird/data/employee.fdb',
  user: 'SYSDBA',
  password: 'masterkey'
})
const loading = ref(false)
const error = ref('')

const connect = async () => {
  loading.value = true
  error.value = ''
  try {
    const response = await axios.post('/api/connect', form.value)
    const token = response.data.token
    localStorage.setItem('token', token)
    router.push('/dashboard')
  } catch (err) {
    console.error(err)
    error.value = err.response?.data?.error || 'Failed to connect'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    const response = await axios.get('/api/config')
    isDemo.value = response.data.demo
  } catch (e) {
    console.error('Failed to fetch config', e)
  }
})
</script>
