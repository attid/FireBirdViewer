<template>
  <div class="flex h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-0">
    <!-- Sidebar -->
    <div class="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col flex-shrink-0">
      <div class="p-4 font-bold text-lg border-b border-gray-200 dark:border-gray-700 flex justify-between items-center text-primary-600 dark:text-primary-400">
        <span>FireBirdViewer</span>
        <Button icon="pi pi-sign-out" text rounded aria-label="Logout" @click="logout" size="small" />
      </div>
      <div class="flex-1 overflow-y-auto p-2 scrollbar-thin">
         <h3 class="font-semibold px-2 py-2 text-xs text-gray-400 uppercase tracking-wider">Tables</h3>
         <div v-if="loadingTables" class="p-4 flex justify-center">
            <i class="pi pi-spin pi-spinner text-2xl text-primary-500"></i>
         </div>
         <ul v-else class="space-y-0.5">
           <li v-for="table in tables" :key="table.name">
             <button
                @click="selectTable(table.name)"
                :class="['w-full text-left px-3 py-2 rounded-md text-sm transition-colors truncate flex items-center gap-2',
                    selectedTable === table.name
                    ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300 font-medium'
                    : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700']"
             >
               <i class="pi pi-table text-gray-400" style="font-size: 0.9rem"></i>
               <span class="truncate">{{ table.name }}</span>
             </button>
           </li>
         </ul>
      </div>
    </div>

    <!-- Main Content -->
    <div class="flex-1 flex flex-col overflow-hidden w-0"> <!-- w-0 ensures flex child doesn't overflow parent -->
        <header class="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4 shadow-sm h-16 flex items-center justify-between shrink-0">
            <h2 class="text-xl font-semibold text-gray-800 dark:text-white truncate" v-if="selectedTable">
                <i class="pi pi-table mr-2 text-primary-500"></i>
                {{ selectedTable }}
            </h2>
            <h2 class="text-xl font-semibold text-gray-400" v-else>Select a table</h2>
        </header>

        <main class="flex-1 overflow-auto p-4 bg-gray-50 dark:bg-gray-900 relative">
            <div v-if="selectedTable" class="h-full flex flex-col">
                <div v-if="loadingData" class="absolute inset-0 flex justify-center items-center bg-white/50 dark:bg-gray-900/50 z-10">
                    <i class="pi pi-spin pi-spinner text-4xl text-primary-500"></i>
                </div>

                <div v-if="error" class="p-4">
                     <Message severity="error">{{ error }}</Message>
                </div>

                <!-- DataTable Container -->
                <div v-else class="flex-1 overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm">
                    <DataTable :value="tableData" scrollable scrollHeight="flex" class="p-datatable-sm text-sm" stripedRows showGridlines>
                        <Column v-for="col in columns" :key="col" :field="col" :header="col" style="min-width: 150px">
                            <template #body="{ data }">
                                <span class="truncate block" :title="data[col]">{{ data[col] }}</span>
                            </template>
                        </Column>
                        <template #empty>
                            <div class="p-4 text-center text-gray-500">No records found.</div>
                        </template>
                    </DataTable>
                </div>
            </div>

            <div v-else class="flex flex-col items-center justify-center h-full text-gray-300 dark:text-gray-600 select-none">
                <i class="pi pi-database text-8xl mb-6 opacity-50"></i>
                <p class="text-2xl font-light">Welcome to FireBirdViewer</p>
                <p class="text-sm mt-2 opacity-70">Select a table from the sidebar to view data</p>
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

<style>
/* Custom Scrollbar for Sidebar */
.scrollbar-thin::-webkit-scrollbar {
  width: 6px;
}
.scrollbar-thin::-webkit-scrollbar-track {
  background: transparent;
}
.scrollbar-thin::-webkit-scrollbar-thumb {
  background-color: rgba(156, 163, 175, 0.5);
  border-radius: 20px;
}
</style>
