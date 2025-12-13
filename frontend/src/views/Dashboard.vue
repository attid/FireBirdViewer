<template>
  <div class="flex h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-0">
    <!-- Sidebar -->
    <div class="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col flex-shrink-0">
      <div class="p-4 font-bold text-lg border-b border-gray-200 dark:border-gray-700 flex justify-between items-center text-primary-600 dark:text-primary-400">
        <span>FireBirdViewer <span class="text-xs font-normal text-gray-400">v{{ version }}</span></span>
        <Button icon="pi pi-sign-out" text rounded aria-label="Logout" @click="logout" size="small" />
      </div>
      <div class="flex-1 overflow-y-auto p-2 scrollbar-thin">
         <h3 class="font-semibold px-2 py-2 text-xs text-gray-400 uppercase tracking-wider">{{ activeSectionTitle }}</h3>
         <div v-if="loadingTables" class="p-4 flex justify-center">
            <i class="pi pi-spin pi-spinner text-2xl text-primary-500"></i>
         </div>
         <ul v-else class="space-y-0.5">
           <li v-for="item in tables" :key="item.name">
             <button
                @click="selectTable(item.name)"
                :class="['w-full text-left px-3 py-2 rounded-md text-sm transition-colors truncate flex items-center gap-2',
                    selectedTable === item.name
                    ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300 font-medium'
                    : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700']"
             >
               <i :class="['pi', sectionIcon, 'text-gray-400']" style="font-size: 0.9rem"></i>
               <span class="truncate">{{ item.name }}</span>
             </button>
           </li>
         </ul>
      </div>

      <!-- Navigation -->
      <div class="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-2 grid grid-cols-3 gap-1">
          <button
              v-for="section in ['tables', 'views', 'procedures']"
              :key="section"
              @click="switchSection(section)"
              :class="['flex flex-col items-center justify-center p-2 rounded-md transition-colors',
                  activeSection === section
                  ? 'bg-primary-50 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400'
                  : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700']"
              :title="section"
          >
              <i :class="['pi', getSectionIcon(section), 'text-lg mb-1']"></i>
              <span class="text-[10px] uppercase font-bold">{{ section }}</span>
          </button>
      </div>
    </div>

    <!-- Main Content -->
    <div class="flex-1 flex flex-col overflow-hidden w-0">
        <header class="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4 shadow-sm h-16 flex items-center justify-between shrink-0">
            <h2 class="text-xl font-semibold text-gray-800 dark:text-white truncate" v-if="selectedTable">
                <i :class="['pi', sectionIcon, 'mr-2 text-primary-500']"></i>
                {{ selectedTable }}
                <span v-if="activeSection !== 'procedures' && totalRecords !== null" class="ml-2 text-sm text-gray-500 font-normal">({{ totalRecords }} rows)</span>
            </h2>
            <h2 class="text-xl font-semibold text-gray-400" v-else>Select {{ activeSectionSingular }}</h2>
        </header>

        <main class="flex-1 overflow-auto p-4 bg-gray-50 dark:bg-gray-900 relative">
            <div v-if="selectedTable" class="h-full flex flex-col">
                <div v-if="error" class="p-4">
                     <Message severity="error">{{ error }}</Message>
                </div>

                <!-- Procedure View -->
                <div v-else-if="activeSection === 'procedures'" class="flex-1 flex flex-col h-full overflow-hidden bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm p-4">
                    <div class="flex justify-end mb-4 gap-2">
                        <Button label="Execute" icon="pi pi-play" severity="success" disabled title="Coming soon" />
                    </div>
                    <div v-if="loadingData" class="flex-1 flex justify-center items-center">
                         <i class="pi pi-spin pi-spinner text-3xl text-primary-500"></i>
                    </div>
                    <pre v-else class="flex-1 overflow-auto p-4 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 font-mono text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap">{{ procedureSource }}</pre>
                </div>

                <!-- DataTable Container (Tables & Views) -->
                <div v-else class="flex-1 overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm">
                    <DataTable
                        :key="selectedTable"
                        :value="data"
                        scrollable
                        scrollHeight="flex"
                        class="p-datatable-sm text-sm"
                        stripedRows
                        showGridlines
                        lazy
                        paginator
                        :rows="rows"
                        :rowsPerPageOptions="[25, 50, 100]"
                        :first="first"
                        :totalRecords="totalRecords"
                        :loading="loadingData"
                        @page="onPage"
                        @sort="onSort"
                        removableSort
                    >
                        <!-- Actions Column (Only for Tables) -->
                        <Column v-if="activeSection === 'tables'" header="Actions" style="width: 50px; text-align: center">
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

                        <Column
                            v-for="col in displayColumns"
                            :key="col.name"
                            :field="col.name"
                            :header="col.name"
                            style="min-width: 150px"
                            :sortable="col.type !== 'BLOB'"
                        >
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
                <p class="text-sm mt-2 opacity-70">Select a {{ activeSectionSingular }} from the sidebar to view details</p>
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

// Section state
const activeSection = ref('tables')
const procedureSource = ref('')

// Data State
const data = ref([])
const totalRecords = ref(0)
const loadingData = ref(false)
const columns = ref([]) // Array of {name, type}

// Pagination & Sort State
const first = ref(0)
const rows = ref(25)
const sortField = ref(null)
const sortOrder = ref(null) // 1 for asc, -1 for desc

// Edit Dialog
const editDialogVisible = ref(false)
const editingRow = ref(null)

const activeSectionTitle = computed(() => {
    switch(activeSection.value) {
        case 'views': return 'Views'
        case 'procedures': return 'Procedures'
        default: return 'Tables'
    }
})

const activeSectionSingular = computed(() => {
    switch(activeSection.value) {
        case 'views': return 'view'
        case 'procedures': return 'procedure'
        default: return 'table'
    }
})

const sectionIcon = computed(() => getSectionIcon(activeSection.value))

function getSectionIcon(section) {
    switch(section) {
        case 'views': return 'pi-eye'
        case 'procedures': return 'pi-cog'
        default: return 'pi-table'
    }
}

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

const switchSection = async (section) => {
    if (activeSection.value === section) return
    activeSection.value = section
    selectedTable.value = null
    tables.value = []
    error.value = ''
    await fetchList()
}

const fetchList = async () => {
    loadingTables.value = true
    try {
        let endpoint = '/api/tables'
        if (activeSection.value === 'views') endpoint = '/api/views'
        if (activeSection.value === 'procedures') endpoint = '/api/procedures'

        const res = await api.get(endpoint)
        tables.value = res.data
    } catch (err) {
        console.error("Failed to load list", err)
        error.value = "Failed to load list"
    } finally {
        loadingTables.value = false
    }
}

const selectTable = async (itemName) => {
    if (selectedTable.value === itemName) return;

    selectedTable.value = itemName
    error.value = ''
    data.value = []
    totalRecords.value = 0
    loadingData.value = true
    columns.value = []
    procedureSource.value = ''

    // Reset pagination and sort on new table selection
    first.value = 0
    rows.value = 25
    sortField.value = null
    sortOrder.value = null

    if (activeSection.value === 'procedures') {
        try {
            const res = await api.get(`/api/procedure/${itemName}/source`)
            procedureSource.value = res.data.source || 'No source code available or empty.'
        } catch(err) {
            error.value = err.response?.data?.error || "Failed to load procedure source"
        } finally {
            loadingData.value = false
        }
    } else {
        await loadTableData()
    }
}

const onPage = (event) => {
    first.value = event.first
    rows.value = event.rows
    loadTableData()
}

const onSort = (event) => {
    sortField.value = event.sortField
    sortOrder.value = event.sortOrder
    loadTableData()
}

const loadTableData = async () => {
    loadingData.value = true
    error.value = ''

    try {
        const params = {
            limit: rows.value,
            offset: first.value
        }

        if (sortField.value) {
            params.sort_field = sortField.value
            params.sort_order = sortOrder.value // 1 or -1
        }

        const res = await api.get(`/api/table/${selectedTable.value}/data`, { params })

        // Backend returns: { data: [], columns: [], total: int, limit: int, offset: int, sort_field, sort_order }
        data.value = res.data.data || []
        columns.value = res.data.columns || []
        totalRecords.value = res.data.total
    } catch (err) {
        error.value = err.response?.data?.error || "Failed to load data"
    } finally {
        loadingData.value = false
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

        // Update local state by reloading current page
        await loadTableData()

    } catch (err) {
        console.error(err)
        toast.add({ severity: 'error', summary: 'Error', detail: err.response?.data?.error || 'Update failed', life: 3000 });
    }
}

onMounted(async () => {
    fetchList()
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
