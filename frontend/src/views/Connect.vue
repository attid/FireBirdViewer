<template>
  <div class="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900 font-sans">
    <div class="w-full max-w-md p-8 bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-100 dark:border-gray-700">
      <h1 class="text-3xl font-bold mb-8 text-center text-gray-900 dark:text-white">FireBirdViewer</h1>

      <!-- Tabs Header -->
      <div class="flex border-b border-gray-200 dark:border-gray-700 mb-6">
        <button
          class="flex-1 pb-2 text-center font-medium transition-colors duration-200 border-b-2 focus:outline-none"
          :class="mode === 'quick' ? 'border-primary-500 text-primary-600 dark:text-primary-400' : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'"
          @click="mode = 'quick'"
        >
          Quick Connect
        </button>
        <button
          class="flex-1 pb-2 text-center font-medium transition-colors duration-200 border-b-2 focus:outline-none"
          :class="mode === 'auth' ? 'border-primary-500 text-primary-600 dark:text-primary-400' : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'"
          @click="mode = 'auth'"
        >
          Authorization
        </button>
      </div>

      <!-- Quick Connect Form -->
      <div v-if="mode === 'quick'" class="flex flex-col gap-5">
        <div class="flex flex-col gap-2">
            <label for="database" class="font-semibold text-gray-700 dark:text-gray-200">Database Connection</label>
            <InputText id="database" v-model="form.database" placeholder="host:/path/to/db.fdb" class="w-full" />
            <small class="text-gray-500 dark:text-gray-400 text-xs">Format: <code>host:/path/to/db.fdb</code> or alias</small>
        </div>

        <div class="flex flex-col gap-2">
            <label for="user" class="font-semibold text-gray-700 dark:text-gray-200">User</label>
            <InputText id="user" v-model="form.user" placeholder="SYSDBA" class="w-full" />
        </div>

        <div class="flex flex-col gap-2">
            <label for="password" class="font-semibold text-gray-700 dark:text-gray-200">Password</label>
            <Password inputId="password" v-model="form.password" :feedback="false" toggleMask placeholder="masterkey" class="w-full" :pt="{ input: { class: 'w-full' } }" />
        </div>

        <Button label="Connect" @click="connect" :loading="loading" class="mt-4 w-full" size="large" />

        <Message v-if="error" severity="error" :closable="false" class="mt-2">{{ error }}</Message>

        <DemoInfo v-if="isDemo" />
      </div>

      <!-- Authorization (Stub) -->
      <div v-else class="flex flex-col items-center justify-center py-10 text-center gap-4">
          <i class="pi pi-lock text-5xl text-gray-300 dark:text-gray-600"></i>
          <div>
            <h3 class="text-xl font-semibold text-gray-800 dark:text-gray-100">Secure Workspace</h3>
            <p class="text-gray-500 dark:text-gray-400 mt-2 max-w-xs mx-auto">
                Secure login with Passkey (WebAuthn) and encrypted connection storage is coming soon.
            </p>
          </div>
          <Button label="Coming Soon" disabled severity="secondary" outlined class="mt-2" />
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
const mode = ref('quick') // 'quick' or 'auth'

const isDemo = ref(false)
const form = ref({
  database: 'firebird5:employee',
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

    // Save successful connection database to localStorage
    localStorage.setItem('lastDatabase', form.value.database)

    router.push('/dashboard')
  } catch (err) {
    console.error(err)
    error.value = err.response?.data?.error || 'Failed to connect'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  // Load saved database if exists
  const savedDatabase = localStorage.getItem('lastDatabase')
  if (savedDatabase) {
    form.value.database = savedDatabase
  }

  try {
    const response = await axios.get('/api/config')
    isDemo.value = response.data.demo
  } catch (e) {
    console.error('Failed to fetch config', e)
  }
})
</script>

<style scoped>
/* Scoped styles if needed, but Tailwind handles most */
</style>
