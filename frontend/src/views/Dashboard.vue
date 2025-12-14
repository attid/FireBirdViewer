<template>
  <div class="flex h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-0">
    <!-- Sidebar -->
    <div class="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col flex-shrink-0">
      <div class="p-4 font-bold text-lg border-b border-gray-200 dark:border-gray-700 flex justify-between items-center text-primary-600 dark:text-primary-400">
        <span>FireBirdViewer <span class="text-xs font-normal text-gray-400">v{{ version }}</span></span>
        <Button icon="pi pi-sign-out" text rounded aria-label="Logout" @click="logout" size="small" />
      </div>

      <!-- Search Box -->
      <div class="p-2 border-b border-gray-200 dark:border-gray-700">
        <IconField iconPosition="left" class="w-full">
            <InputIcon class="pi pi-search" />
            <InputText v-model="filterText" placeholder="Search..." class="w-full p-inputtext-sm" />
        </IconField>
      </div>

      <!-- Tree -->
      <div class="flex-1 overflow-y-auto p-2 scrollbar-thin">
         <div v-if="loadingTree" class="p-4 flex justify-center">
            <i class="pi pi-spin pi-spinner text-2xl text-primary-500"></i>
         </div>
         <Tree
            v-else
            :value="filteredTreeNodes"
            selectionMode="single"
            v-model:selectionKeys="selectedNodeKey"
            v-model:expandedKeys="expandedKeys"
            @nodeSelect="onNodeSelect"
            class="w-full border-none p-0 bg-transparent text-sm"
            :pt="{
                root: { class: 'bg-transparent border-none p-0' },
                content: { class: 'p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded cursor-pointer transition-colors' },
                label: { class: 'text-gray-700 dark:text-gray-200' },
                icon: { class: 'text-gray-400 dark:text-gray-500' }
            }"
         >
            <template #default="slotProps">
                <span class="truncate">{{ slotProps.node.label }}</span>
            </template>
         </Tree>
      </div>
    </div>

    <!-- Main Content -->
    <div class="flex-1 flex flex-col overflow-hidden w-0">
        <header class="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4 shadow-sm h-16 flex items-center justify-between shrink-0">
            <h2 class="text-xl font-semibold text-gray-800 dark:text-white truncate" v-if="headerTitle">
                <i :class="['pi', headerIcon, 'mr-2 text-primary-500']"></i>
                {{ headerTitle }}
                <span v-if="activeSection === 'tables' && totalRecords !== null" class="ml-2 text-sm text-gray-500 font-normal">({{ totalRecords }} rows)</span>
            </h2>
            <h2 class="text-xl font-semibold text-gray-400" v-else>Select an item</h2>
        </header>

        <main class="flex-1 overflow-auto p-4 bg-gray-50 dark:bg-gray-900 relative">
            <div v-if="activeSection === 'tool' && selectedItemName === 'sql-editor'" class="h-full flex flex-col">
                 <SqlEditor :api="api" />
            </div>

            <div v-else-if="activeSection === 'tool' && selectedItemName === 'db-info'" class="h-full flex flex-col justify-center items-center text-gray-400">
                 <i :class="['pi', headerIcon, 'text-6xl mb-4 opacity-50']"></i>
                 <h3 class="text-2xl font-light">{{ headerTitle }}</h3>
                 <p class="mt-2 opacity-70">This tool is coming soon.</p>
            </div>

            <div v-else-if="selectedItemName" class="h-full flex flex-col">
                <div v-if="error" class="p-4">
                     <Message severity="error">{{ error }}</Message>
                </div>

                <!-- Procedure View -->
                <div v-else-if="activeSection === 'procedures'" class="flex-1 flex flex-col h-full overflow-hidden bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm p-4">
                    <div class="flex justify-end mb-4 gap-2">
                         <Button
                             v-if="procViewMode === 'results'"
                             label="Back to Source"
                             icon="pi pi-arrow-left"
                             severity="secondary"
                             @click="procViewMode = 'source'"
                         />
                        <Button label="Execute" icon="pi pi-play" severity="success" @click="openExecuteDialog" />
                    </div>

                    <!-- Source View -->
                    <div v-if="procViewMode === 'source'" class="flex-1 flex flex-col h-full overflow-hidden">
                        <div v-if="loadingData" class="flex-1 flex justify-center items-center">
                            <i class="pi pi-spin pi-spinner text-3xl text-primary-500"></i>
                        </div>
                        <pre v-else class="flex-1 overflow-auto p-4 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 font-mono text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap">{{ procedureSource }}</pre>
                    </div>

                    <!-- Results View -->
                    <div v-else class="flex-1 overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm">
                        <DataTable
                            :value="virtualData"
                            scrollable
                            scrollHeight="flex"
                            class="p-datatable-sm text-sm"
                            stripedRows
                            showGridlines
                        >
                             <Column
                                v-for="col in displayColumns"
                                :key="col.name"
                                :field="col.name"
                                :header="col.name"
                                style="min-width: 150px"
                            >
                                <template #body="{ data }">
                                    <span class="truncate block" :title="data[col.name]">{{ data[col.name] }}</span>
                                </template>
                            </Column>
                             <template #empty>
                                <div class="p-4 text-center text-gray-500">No records returned.</div>
                            </template>
                        </DataTable>
                    </div>
                </div>

                <!-- DataTable Container (Tables & Views) -->
                <div v-else class="flex-1 overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm">
                    <DataTable
                        :key="selectedItemName"
                        :value="virtualData"
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
                <p class="text-sm mt-2 opacity-70">Select an item from the sidebar</p>
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

    <!-- Execute Procedure Dialog -->
    <ExecuteProcedureDialog
      v-model:visible="executeDialogVisible"
      :procedureName="selectedItemName"
      :api="api"
      @execute="onProcedureExecuted"
    />

    <Toast />
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Message from 'primevue/message'
import Toast from 'primevue/toast'
import Tree from 'primevue/tree'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import { useToast } from 'primevue/usetoast'
import EditRowDialog from '../components/EditRowDialog.vue'
import ExecuteProcedureDialog from '../components/ExecuteProcedureDialog.vue'
import SqlEditor from '../components/SqlEditor.vue'

const router = useRouter()
const toast = useToast()

const version = ref('')
const error = ref('')

// Tree State
const loadingTree = ref(false)
const rawTreeNodes = ref([])
const filterText = ref('')
const selectedNodeKey = ref(null)
const expandedKeys = ref({})

// Main Content State
const activeSection = ref(null) // 'tables', 'views', 'procedures', 'tool'
const selectedItemName = ref(null) // Table name, View name, Proc name, or Tool ID
const procedureSource = ref('')
const procViewMode = ref('source') // 'source' or 'results'

// Data State
const data = ref([])
const virtualData = ref([])
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

// Execute Dialog
const executeDialogVisible = ref(false)

// Headers
const headerTitle = computed(() => {
    if (activeSection.value === 'tool') {
        if (selectedItemName.value === 'sql-editor') return 'SQL Editor'
        if (selectedItemName.value === 'db-info') return 'Database Info'
    }
    return selectedItemName.value
})

const headerIcon = computed(() => {
    if (activeSection.value === 'tables') return 'pi-table'
    if (activeSection.value === 'views') return 'pi-eye'
    if (activeSection.value === 'procedures') return 'pi-cog'
    if (activeSection.value === 'tool') {
        if (selectedItemName.value === 'sql-editor') return 'pi-code'
        if (selectedItemName.value === 'db-info') return 'pi-info-circle'
    }
    return 'pi-file'
})

const displayColumns = computed(() => {
    return columns.value.filter(col => col.name !== 'DB_KEY' && col.name !== 'RDB$DB_KEY')
})

// Filter Logic
const filteredTreeNodes = computed(() => {
    if (!filterText.value) return rawTreeNodes.value

    const text = filterText.value.toLowerCase()

    const filterNode = (node) => {
        // Check if node itself matches
        const labelMatches = node.label.toLowerCase().includes(text)

        // Check children
        let matchingChildren = []
        if (node.children) {
            matchingChildren = node.children.map(filterNode).filter(n => n !== null)
        }

        if (labelMatches || matchingChildren.length > 0) {
            return {
                ...node,
                children: matchingChildren
            }
        }
        return null
    }

    return rawTreeNodes.value.map(filterNode).filter(n => n !== null)
})

// Watch filter text to auto-expand
watch(filterText, (newVal) => {
    if (newVal) {
        const newKeys = { ...expandedKeys.value }
        newKeys['tools'] = true
        newKeys['tables'] = true
        newKeys['views'] = true
        newKeys['procedures'] = true
        expandedKeys.value = newKeys
    }
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

const buildTree = (tables, views, procedures) => {
    return [
        {
            key: 'tools',
            label: 'Tools',
            icon: 'pi pi-fw pi-cog',
            children: [
                { key: 'tool-sql', label: 'SQL Editor', icon: 'pi pi-fw pi-code', data: { type: 'tool', id: 'sql-editor' } },
                { key: 'tool-info', label: 'Database Info', icon: 'pi pi-fw pi-info-circle', data: { type: 'tool', id: 'db-info' } }
            ]
        },
        {
            key: 'tables',
            label: 'Tables',
            icon: 'pi pi-fw pi-table',
            children: tables.map(t => ({
                key: `table-${t.name}`,
                label: t.name,
                icon: 'pi pi-fw pi-table',
                data: { type: 'table', name: t.name }
            }))
        },
        {
            key: 'views',
            label: 'Views',
            icon: 'pi pi-fw pi-eye',
            children: views.map(v => ({
                key: `view-${v.name}`,
                label: v.name,
                icon: 'pi pi-fw pi-eye',
                data: { type: 'view', name: v.name }
            }))
        },
        {
            key: 'procedures',
            label: 'Procedures',
            icon: 'pi pi-fw pi-cog',
            children: procedures.map(p => ({
                key: `proc-${p.name}`,
                label: p.name,
                icon: 'pi pi-fw pi-cog',
                data: { type: 'procedure', name: p.name }
            }))
        }
    ]
}

const fetchAll = async () => {
    loadingTree.value = true
    try {
        const [tablesRes, viewsRes, procsRes] = await Promise.all([
            api.get('/api/tables'),
            api.get('/api/views'),
            api.get('/api/procedures')
        ])

        rawTreeNodes.value = buildTree(tablesRes.data, viewsRes.data, procsRes.data)

    } catch (err) {
        console.error("Failed to load tree data", err)
        error.value = "Failed to load database structure"
    } finally {
        loadingTree.value = false
    }
}

const onNodeSelect = (node) => {
    if (node.children && node.children.length > 0) {
        if (['tools', 'tables', 'views', 'procedures'].includes(node.key)) {
            // Toggle expansion manually since we want label click to toggle
            const newKeys = { ...expandedKeys.value }
            if (newKeys[node.key]) {
                delete newKeys[node.key]
            } else {
                newKeys[node.key] = true
            }
            expandedKeys.value = newKeys
            return
        }
    }

    if (!node.data) return

    const { type, name, id } = node.data

    if (type === 'tool') {
        activeSection.value = 'tool'
        selectedItemName.value = id
        // Reset data views
        virtualData.value = []
        columns.value = []
        totalRecords.value = 0
    } else {
        // Tables, Views, Procedures
        // Map type to section
        const sectionMap = { 'table': 'tables', 'view': 'views', 'procedure': 'procedures' }
        activeSection.value = sectionMap[type]
        selectedItemName.value = name

        loadItemData(name)
    }
}

const loadItemData = async (itemName) => {
    error.value = ''
    data.value = []
    totalRecords.value = 0
    loadingData.value = true
    columns.value = []
    procedureSource.value = ''
    procViewMode.value = 'source'

    try {
        if (activeSection.value === 'procedures') {
            const res = await api.get(`/api/procedure/${itemName}/source`)
            procedureSource.value = res.data.source || 'No source code available or empty.'
        } else {
            // Tables and Views
            const res = await api.get(`/api/table/${itemName}/data`, {
                params: { limit: 100, offset: 0 }
            })

            const initialData = res.data.data || []
            columns.value = res.data.columns || []
            totalRecords.value = res.data.total

            if (initialData.length > 0) {
                virtualData.value = Array.from({ length: totalRecords.value })
                initialData.forEach((item, index) => {
                    virtualData.value[index] = item
                })
            } else {
                virtualData.value = []
            }
        }
    } catch (err) {
        console.error("Failed to load item data", err)
        error.value = err.response?.data?.error || "Failed to load data"
    } finally {
        loadingData.value = false
    }
}

const onPage = (event) => {
    first.value = event.first
    rows.value = event.rows
    loadDataLazy(event)
}

const onSort = (event) => {
    sortField.value = event.sortField
    sortOrder.value = event.sortOrder
    // Trigger reload
    loadDataLazy({ first: first.value, last: first.value + rows.value })
}

const loadDataLazy = async (event) => {
    if (!selectedItemName.value || activeSection.value === 'procedures' || activeSection.value === 'tool') return;

    const { first: offset, last } = event
    const limit = last - offset

    if (limit <= 0) return

    await loadTableData(offset, limit)
}

const loadTableData = async (offset, limit) => {
    loadingData.value = true
    error.value = ''

    try {
        const params = { limit, offset }
        if (sortField.value) {
            params.sortField = sortField.value
            params.sortOrder = sortOrder.value
        }

        const res = await api.get(`/api/table/${selectedItemName.value}/data`, {
            params
        })

        const chunk = res.data.data || []
        chunk.forEach((item, index) => {
            if (offset + index < virtualData.value.length) {
                 virtualData.value[offset + index] = item
            }
        })
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
        const dbKey = editingRow.value.DB_KEY || editingRow.value['RDB$DB_KEY']
        if (!dbKey) {
            toast.add({ severity: 'error', summary: 'Error', detail: 'Missing DB_KEY for update', life: 3000 });
            return
        }

        await api.put(`/api/table/${selectedItemName.value}/data`, {
            db_key: dbKey,
            data: changes
        })

        toast.add({ severity: 'success', summary: 'Success', detail: 'Record updated', life: 3000 });
        editDialogVisible.value = false
        Object.assign(editingRow.value, changes)
    } catch (err) {
        console.error(err)
        toast.add({ severity: 'error', summary: 'Error', detail: err.response?.data?.error || 'Update failed', life: 3000 });
    }
}

const openExecuteDialog = () => {
    executeDialogVisible.value = true
}

const onProcedureExecuted = (result) => {
    virtualData.value = result.data || []
    columns.value = result.columns || []
    procViewMode.value = 'results'
}

onMounted(async () => {
    fetchAll()
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
