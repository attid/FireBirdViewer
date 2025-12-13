<template>
  <div class="flex h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-0">
    <!-- Sidebar -->
    <div class="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col flex-shrink-0">
      <div class="p-4 font-bold text-lg border-b border-gray-200 dark:border-gray-700 flex justify-between items-center text-primary-600 dark:text-primary-400">
        <span>FireBirdViewer <span class="text-xs font-normal text-gray-400">v{{ version }}</span></span>
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
    <div class="flex-1 flex flex-col overflow-hidden w-0">
        <header class="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4 shadow-sm h-16 flex items-center justify-between shrink-0">
            <h2 class="text-xl font-semibold text-gray-800 dark:text-white truncate" v-if="selectedTable">
                <i class="pi pi-table mr-2 text-primary-500"></i>
                {{ selectedTable }}
                <span v-if="totalRecords !== null" class="ml-2 text-sm text-gray-500 font-normal">({{ totalRecords }} rows)</span>
            </h2>
            <h2 class="text-xl font-semibold text-gray-400" v-else>Select a table</h2>
        </header>

        <main class="flex-1 overflow-auto p-4 bg-gray-50 dark:bg-gray-900 relative">
            <div v-if="selectedTable" class="h-full flex flex-col">
                <div v-if="error" class="p-4">
                     <Message severity="error">{{ error }}</Message>
                </div>

                <!-- DataTable Container -->
                <div v-else class="flex-1 overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm">
                    <DataTable
                        :value="virtualData"
                        scrollable
                        scrollHeight="flex"
                        class="p-datatable-sm text-sm"
                        stripedRows
                        showGridlines
                        :virtualScrollerOptions="{ itemSize: 35, lazy: true, onLazyLoad: loadDataLazy, showLoader: true, loading: loadingLazy, delay: 200 }"
                        :totalRecords="totalRecords"
                        :loading="loadingData"
                    >
                        <!-- Actions Column -->
                        <Column header="Actions" style="width: 50px; text-align: center">
                           <template #body="{ data }">
                               <Button
                                  v-if="data"
                                  icon="pi pi-pencil"
                                  text
                                  rounded
                                  size="small"
                                  @click="openEditDialog(data)"
                                  class="text-gray-400 hover:text-primary-600"
                               />
                           </template>
                        </Column>

                        <Column v-for="col in displayColumns" :key="col.name" :field="col.name" :header="col.name" style="min-width: 150px">
                            <template #body="{ data }">
                                <span v-if="data" class="truncate block" :title="data[col.name]">{{ data[col.name] }}</span>
                                <span v-else class="flex items-center gap-2">
                                    <i class="pi pi-spin pi-spinner text-xs text-gray-300"></i>
                                </span>
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

    <!-- Edit Dialog -->
    <EditRowDialog
      v-model:visible="editDialogVisible"
      :rowData="editingRow"
      :columns="columns"
      @save="saveRow"
    />
    <Toast />
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
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'
import EditRowDialog from '../components/EditRowDialog.vue'

const router = useRouter()
const toast = useToast()
const tables = ref([])
const loadingTables = ref(false)
const selectedTable = ref(null)
const error = ref('')
const version = ref('')

// Virtual Scroll Data
const virtualData = ref([])
const totalRecords = ref(0)
const loadingData = ref(false)
const loadingLazy = ref(false)
const columns = ref([]) // Array of {name, type}

// Edit Dialog
const editDialogVisible = ref(false)
const editingRow = ref(null)

const displayColumns = computed(() => {
    // Hide DB_KEY from main view
    return columns.value.filter(col => col.name !== 'DB_KEY' && col.name !== 'RDB$DB_KEY')
})

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
    if (selectedTable.value === tableName) return;

    selectedTable.value = tableName
    error.value = ''
    virtualData.value = []
    totalRecords.value = 0
    loadingData.value = true
    columns.value = []

    // Initial fetch to get columns and first page of data + count
    try {
        const res = await api.get(`/api/table/${tableName}/data`, {
            params: { limit: 100, offset: 0 }
        })

        // Backend returns: { data: [], columns: [], total: int, limit: int, offset: int }
        const initialData = res.data.data || []
        columns.value = res.data.columns || []
        totalRecords.value = res.data.total

        if (initialData.length > 0) {
            // Initialize virtualData array with empty slots for lazy loading
            virtualData.value = Array.from({ length: totalRecords.value })
            // Fill the first chunk
            initialData.forEach((item, index) => {
                virtualData.value[index] = item
            })
        } else if (columns.value.length > 0) {
             // If no data but we have columns (e.g. empty table), we are good
             virtualData.value = []
        }
    } catch (err) {
        error.value = err.response?.data?.error || "Failed to load data"
    } finally {
        loadingData.value = false
    }
}

const loadDataLazy = async (event) => {
    if (!selectedTable.value) return;

    const { first, last } = event
    const limit = last - first
    const offset = first

    // Check if we already have this data loaded (basic caching)
    if (virtualData.value[first]) {
        return
    }

    loadingLazy.value = true

    try {
        const res = await api.get(`/api/table/${selectedTable.value}/data`, {
            params: { limit, offset }
        })

        const chunk = res.data.data || []

        chunk.forEach((item, index) => {
            if (first + index < virtualData.value.length) {
                 virtualData.value[first + index] = item
            }
        })

    } catch (err) {
        console.error("Lazy load failed", err)
    } finally {
        loadingLazy.value = false
    }
}

const openEditDialog = (row) => {
    editingRow.value = row
    editDialogVisible.value = true
}

const saveRow = async (changes) => {
    try {
        // DB_KEY is in the original row, changes map might not have it.
        const dbKey = editingRow.value.DB_KEY || editingRow.value['RDB$DB_KEY']

        if (!dbKey) {
            toast.add({ severity: 'error', summary: 'Error', detail: 'Missing DB_KEY for update', life: 3000 });
            return
        }

        await api.put(`/api/table/${selectedTable.value}/data`, {
            db_key: dbKey,
            data: changes
        })

        toast.add({ severity: 'success', summary: 'Success', detail: 'Record updated', life: 3000 });
        editDialogVisible.value = false

        // Update local state
        Object.assign(editingRow.value, changes)

    } catch (err) {
        console.error(err)
        toast.add({ severity: 'error', summary: 'Error', detail: err.response?.data?.error || 'Update failed', life: 3000 });
    }
}

onMounted(async () => {
    fetchTables()
    try {
        const res = await api.get('/api/config')
        if (res.data.version) {
            version.value = res.data.version
        }
    } catch (e) {
        console.error("Failed to fetch version", e)
    }
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
