<template>
  <div class="flex h-screen bg-surface-50 dark:bg-surface-900 text-surface-900 dark:text-surface-0">
    <!-- Sidebar -->
    <div class="w-64 bg-white dark:bg-surface-800 border-r border-surface-200 dark:border-surface-700 flex flex-col">
      <div class="p-4 font-bold text-lg border-b border-surface-200 dark:border-surface-700 flex justify-between items-center">
        <span>Firebird Admin</span>
        <Button icon="pi pi-sign-out" text rounded aria-label="Logout" @click="logout" />
      </div>
      <div class="flex-1 overflow-auto p-2">
         <h3 class="font-semibold px-2 py-1 text-sm text-surface-500">TABLES</h3>
         <div v-if="loadingTables" class="p-2 flex justify-center">
            <i class="pi pi-spin pi-spinner text-2xl"></i>
         </div>
         <ul v-else class="space-y-1">
           <li v-for="table in tables" :key="table.name">
             <button
                @click="selectTable(table.name)"
                :class="['w-full text-left px-3 py-2 rounded text-sm hover:bg-surface-100 dark:hover:bg-surface-700 transition-colors truncate', selectedTable === table.name ? 'bg-primary-50 text-primary-700 font-medium' : '']"
             >
               <i class="pi pi-table mr-2 text-surface-400"></i>
               {{ table.name }}
             </button>
           </li>
         </ul>
      </div>
    </div>

    <!-- Main Content -->
    <div class="flex-1 flex flex-col overflow-hidden">
        <header class="bg-white dark:bg-surface-800 border-b border-surface-200 dark:border-surface-700 p-4 shadow-sm h-16 flex items-center">
            <h2 class="text-xl font-semibold" v-if="selectedTable">Table: {{ selectedTable }}</h2>
            <h2 class="text-xl font-semibold text-surface-400" v-else>Select a table to view data</h2>
        </header>

        <main class="flex-1 overflow-auto p-4">
            <div v-if="selectedTable">
                <div v-if="loadingData" class="flex justify-center items-center h-full">
                    <i class="pi pi-spin pi-spinner text-4xl text-primary-500"></i>
                </div>
                <div v-else-if="error" class="p-4">
                     <Message severity="error">{{ error }}</Message>
                </div>
                <DataTable v-else :value="tableData" scrollable scrollHeight="flex" class="p-datatable-sm" stripedRows showGridlines>
                    <Column v-for="col in columns" :key="col" :field="col" :header="col" style="min-width: 150px">
                        <template #body="{ data }">
                            <span class="truncate block">{{ data[col] }}</span>
                        </template>
                    </Column>
                    <template #empty>No records found.</template>
                </DataTable>
            </div>
            <div v-else class="flex flex-col items-center justify-center h-full text-surface-400">
                <i class="pi pi-database text-6xl mb-4"></i>
                <p>Welcome to Firebird Web Admin</p>
            </div>
        </main>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Message from 'primevue/message'

const router = useRouter()
const tables = ref([])
const loadingTables = ref(false)
const selectedTable = ref(null)
const tableData = ref([])
const loadingData = ref(false)
const error = ref('')

const token = localStorage.getItem('token')
const api = axios.create({
    headers: { Authorization: `Bearer ${token}` }
})

api.interceptors.response.use(
    response => response,
    error => {
        if (error.response && error.response.status === 401) {
            logout()
        }
        return Promise.reject(error)
    }
)

const logout = () => {
    localStorage.removeItem('token')
    router.push('/')
}

const fetchTables = async () => {
    loadingTables.value = true
    try {
        const res = await api.get('/api/tables')
        tables.value = res.data
    } catch (err) {
        console.error("Failed to load tables", err)
    } finally {
        loadingTables.value = false
    }
}

const selectTable = async (tableName) => {
    selectedTable.value = tableName
    loadingData.value = true
    error.value = ''
    tableData.value = []
    try {
        const res = await api.get(`/api/table/${tableName}/data`)
        tableData.value = res.data
    } catch (err) {
        error.value = err.response?.data?.error || "Failed to load data"
    } finally {
        loadingData.value = false
    }
}

const columns = computed(() => {
    if (tableData.value.length === 0) return []
    return Object.keys(tableData.value[0])
})

onMounted(() => {
    fetchTables()
})
</script>
