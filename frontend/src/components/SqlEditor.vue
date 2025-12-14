<template>
  <div class="flex flex-col h-full bg-white dark:bg-gray-800">
    <!-- Toolbar -->
    <div class="flex items-center justify-between p-2 border-b border-gray-200 dark:border-gray-700">
      <div class="flex gap-2">
        <Button
          label="Run"
          icon="pi pi-play"
          size="small"
          severity="success"
          @click="executeSql"
          :loading="loading"
        />
        <Button
          label="Load Hints"
          icon="pi pi-cloud-download"
          size="small"
          severity="secondary"
          @click="loadHints"
          :loading="loadingHints"
          v-tooltip.bottom="'Load database schema for autocompletion'"
        />
      </div>
      <div class="flex gap-2 items-center">
         <Button
            v-if="history.length > 0"
            icon="pi pi-history"
            text
            rounded
            @click="showHistory = true"
            v-tooltip.bottom="'History'"
         />
      </div>
    </div>

    <!-- Editor -->
    <div class="flex-1 border-b border-gray-200 dark:border-gray-700 relative">
       <vue-monaco-editor
          v-model:value="code"
          theme="vs-dark"
          language="sql"
          :options="editorOptions"
          @mount="handleMount"
          class="h-full w-full"
       />
    </div>

    <!-- Results -->
    <div class="h-1/2 flex flex-col overflow-hidden">
        <div v-if="error" class="p-2 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm border-b border-red-200 dark:border-red-800">
            {{ error }}
        </div>

        <DataTable
            v-if="data.length > 0 || columns.length > 0"
            :value="data"
            scrollable
            scrollHeight="flex"
            class="p-datatable-sm text-sm flex-1"
            stripedRows
            showGridlines
            paginator
            :rows="50"
            :rowsPerPageOptions="[25, 50, 100]"
        >
            <Column
                v-for="col in columns"
                :key="col.name"
                :field="col.name"
                :header="col.name"
                style="min-width: 150px"
                sortable
            >
                <template #body="{ data }">
                    <span class="truncate block" :title="data[col.name]">{{ data[col.name] }}</span>
                </template>
            </Column>
             <template #empty>
                <div class="p-4 text-center text-gray-500">No records returned.</div>
            </template>
        </DataTable>

        <div v-else-if="executed && !error" class="flex-1 flex items-center justify-center text-gray-400">
            <span class="text-sm">Query executed successfully. No rows returned.</span>
        </div>

        <div v-else-if="!executed" class="flex-1 flex items-center justify-center text-gray-400 select-none">
            <div class="text-center">
                <i class="pi pi-code text-4xl mb-2 opacity-50"></i>
                <p>Enter SQL query and press Run (Ctrl+Enter)</p>
            </div>
        </div>
    </div>

    <!-- History Dialog -->
    <Dialog v-model:visible="showHistory" modal header="Query History" :style="{ width: '50vw' }">
        <div class="flex flex-col gap-2">
            <div v-if="history.length === 0" class="text-gray-500 text-center py-4">
                No history yet.
            </div>
            <div v-for="(item, idx) in history" :key="idx" class="p-3 border border-gray-200 dark:border-gray-700 rounded hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer flex justify-between items-center group" @click="restoreQuery(item.sql)">
                <div class="font-mono text-sm truncate flex-1 mr-4 text-gray-700 dark:text-gray-300">{{ item.sql }}</div>
                <div class="flex items-center gap-2">
                    <span class="text-xs text-gray-400">{{ formatTime(item.timestamp) }}</span>
                    <Button icon="pi pi-times" text rounded severity="danger" size="small" class="opacity-0 group-hover:opacity-100" @click.stop="deleteHistory(idx)" />
                </div>
            </div>
        </div>
        <template #footer>
            <Button label="Clear All" icon="pi pi-trash" severity="danger" text @click="clearHistory" v-if="history.length > 0"/>
        </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, shallowRef } from 'vue'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Dialog from 'primevue/dialog'
import { useToast } from 'primevue/usetoast'
import axios from 'axios'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'

const props = defineProps(['api'])
const toast = useToast()

const code = ref('SELECT * FROM EMPLOYEE')
const editorRef = shallowRef(null)
const monacoRef = shallowRef(null)

const loading = ref(false)
const loadingHints = ref(false)
const error = ref('')
const executed = ref(false)
const data = ref([])
const columns = ref([])

const showHistory = ref(false)
const history = ref([])
const completionProviderDisposable = shallowRef(null)

const editorOptions = {
    automaticLayout: true,
    fontSize: 14,
    fontFamily: 'Fira Code, Consolas, monospace',
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    padding: { top: 10, bottom: 10 }
}

// Load history
onMounted(() => {
    const saved = localStorage.getItem('sql_history')
    if (saved) {
        try {
            history.value = JSON.parse(saved)
        } catch (e) {
            console.error(e)
        }
    }
})

onBeforeUnmount(() => {
    if (completionProviderDisposable.value) {
        completionProviderDisposable.value.dispose()
    }
})

const handleMount = (editor, monaco) => {
    editorRef.value = editor
    monacoRef.value = monaco

    // Key binding for Run (Ctrl+Enter)
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
        executeSql()
    })
}

const loadHints = async () => {
    if (!monacoRef.value) return
    loadingHints.value = true

    try {
        const res = await props.api.get('/api/metadata')
        const metadata = res.data // Array of {name, type, columns}

        registerCompletionProvider(monacoRef.value, metadata)
        toast.add({ severity: 'success', summary: 'Hints Loaded', detail: 'Database schema loaded for autocompletion', life: 3000 })
    } catch (err) {
        console.error(err)
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load metadata', life: 3000 })
    } finally {
        loadingHints.value = false
    }
}

const registerCompletionProvider = (monaco, metadata) => {
    // Dispose previous provider
    if (completionProviderDisposable.value) {
        completionProviderDisposable.value.dispose()
    }

    // Flatten tables and columns for easier lookup
    const tables = metadata.map(m => ({ label: m.name, kind: monaco.languages.CompletionItemKind.Class, insertText: m.name }))

    // Map of table -> columns
    const tableColumns = {}
    metadata.forEach(m => {
        tableColumns[m.name.toUpperCase()] = m.columns
    })

    // All unique columns (for fuzzy match)
    const allColumns = new Set()
    metadata.forEach(m => {
        m.columns.forEach(c => allColumns.add(c))
    })

    const columnItems = Array.from(allColumns).map(c => ({
         label: c,
         kind: monaco.languages.CompletionItemKind.Field,
         insertText: c
    }))

    // SQL Keywords
    const keywords = ['SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'ORDER BY', 'GROUP BY', 'HAVING', 'LIMIT', 'OFFSET', 'INSERT', 'UPDATE', 'DELETE', 'LEFT JOIN', 'INNER JOIN', 'RIGHT JOIN']
    const keywordItems = keywords.map(k => ({
        label: k,
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: k
    }))

    // Register and store disposable
    completionProviderDisposable.value = monaco.languages.registerCompletionItemProvider('sql', {
        triggerCharacters: [' ', '.', '\n'],
        provideCompletionItems: (model, position) => {
            const textUntilPosition = model.getValueInRange({
                startLineNumber: position.lineNumber,
                startColumn: 1,
                endLineNumber: position.lineNumber,
                endColumn: position.column
            })

            const word = model.getWordUntilPosition(position)
            const range = {
                startLineNumber: position.lineNumber,
                endLineNumber: position.lineNumber,
                startColumn: word.startColumn,
                endColumn: word.endColumn
            }

            // Alias detection logic (Simplified)
            const matches = textUntilPosition.match(/(\w+)\.$/)
            if (matches) {
                const alias = matches[1]
                const fullText = model.getValue()
                const aliasRegex = new RegExp(`\\b([a-zA-Z0-9_$]+)\\s+(?:AS\\s+)?\\b${alias}\\b`, 'i')
                const aliasMatch = fullText.match(aliasRegex)

                if (aliasMatch) {
                    const tableName = aliasMatch[1].toUpperCase()
                    if (tableColumns[tableName]) {
                        return {
                            suggestions: tableColumns[tableName].map(c => ({
                                label: c,
                                kind: monaco.languages.CompletionItemKind.Field,
                                insertText: c,
                                range: range
                            }))
                        }
                    }
                }
            }

            // Default suggestions
            return {
                suggestions: [
                    ...tables.map(t => ({...t, range})),
                    ...columnItems.map(c => ({...c, range})),
                    ...keywordItems.map(k => ({...k, range}))
                ]
            }
        }
    })
}

const executeSql = async () => {
    if (!code.value.trim()) return

    loading.value = true
    error.value = ''
    data.value = []
    columns.value = []
    executed.value = false

    try {
        // Simple client-side check to prevent destructive queries?
        // No, let backend handle permissions or user beware.

        const res = await props.api.post('/api/execute', { sql: code.value })
        data.value = res.data.data || []
        columns.value = res.data.columns || []

        executed.value = true
        addToHistory(code.value)

    } catch (err) {
        console.error(err)
        error.value = err.response?.data?.error || "Execution failed"
    } finally {
        loading.value = false
    }
}

const addToHistory = (sql) => {
    // Remove if exists
    const existingIdx = history.value.findIndex(h => h.sql === sql)
    if (existingIdx !== -1) {
        history.value.splice(existingIdx, 1)
    }

    history.value.unshift({ sql, timestamp: new Date() })
    if (history.value.length > 20) {
        history.value.pop()
    }
    localStorage.setItem('sql_history', JSON.stringify(history.value))
}

const restoreQuery = (sql) => {
    code.value = sql
    showHistory.value = false
}

const deleteHistory = (idx) => {
    history.value.splice(idx, 1)
    localStorage.setItem('sql_history', JSON.stringify(history.value))
}

const clearHistory = () => {
    history.value = []
    localStorage.removeItem('sql_history')
}

const formatTime = (ts) => {
    return new Date(ts).toLocaleTimeString()
}
</script>

<style scoped>
/* Ensure editor takes available space */
</style>
