<template>
  <div class="skills-manager-container extension-page-root">
    <div v-if="loading" class="loading-bar-wrapper">
      <div class="loading-bar"></div>
    </div>
    <div class="layout-wrapper" :class="{ 'content-loading': loading }">
      <!-- 详情面板 -->
      <div class="main-panel">
        <div class="panel-top-bar">
        </div>
        <div class="workspace">
          <div class="tree-container">
            <div class="tree-header">
              <span class="label">全部文件</span>
              <div class="tree-actions">
                <a-tooltip title="新建文件"
                  ><button @click="openCreateModal(false)"><FilePlus :size="14" /></button
                ></a-tooltip>
                <a-tooltip title="新建目录"
                  ><button @click="openCreateModal(true)"><FolderPlus :size="14" /></button
                ></a-tooltip>
                <a-tooltip title="刷新"
                  ><button @click="reloadTree"><RotateCw :size="14" /></button
                ></a-tooltip>
              </div>
            </div>
            <div class="tree-content">
              <FileTreeComponent
                v-model:selectedKeys="selectedTreeKeys"
                v-model:expandedKeys="expandedKeys"
                :tree-data="treeData"
                @select="handleTreeSelect"
              />
            </div>
          </div>

          <div class="editor-container">
            <div class="editor-header">
              <div class="current-path">
                <File :size="14" />
                <span>{{ selectedPath || '未选择文件' }}</span>
                <span v-if="canSave" class="save-hint">●</span>
              </div>
              <div class="header-actions">
                <a-button
                  v-if="isMarkdownFile && selectedPath"
                  size="small"
                  @click="viewMode = viewMode === 'edit' ? 'preview' : 'edit'"
                  class="lucide-icon-btn view-toggle-btn"
                  :title="viewMode === 'edit' ? '预览' : '编辑'"
                >
                  <Eye v-if="viewMode === 'edit'" :size="14" />
                  <Edit3 v-else :size="14" />
                  <span>{{ viewMode === 'edit' ? '预览' : '编辑' }}</span>
                </a-button>
                <a-button 
                  size="small" 
                  @click="copyCurrentFile" 
                  :disabled="!canCopy"
                  class="lucide-icon-btn">
                  <Copy :size="14" />
                  <span>复制</span>
                </a-button>
                <a-button 
                  size="small" 
                  @click="copyRenderedContent" 
                  :disabled="!canCopy"
                  class="lucide-icon-btn">
                  <FileText :size="14" />
                  <span>渲染并复制</span>
                </a-button>
                <a-button
                  type="primary"
                  size="small"
                  @click="saveCurrentFile"
                  :disabled="!canSave"
                  :loading="savingFile"
                  class="lucide-icon-btn"
                >
                  <Save :size="14" />
                  <span>保存</span>
                </a-button>
                <a-button
                  size="small"
                  danger
                  ghost
                  @click="confirmDeleteNode"
                  class="lucide-icon-btn"
                >
                  <Trash2 :size="14" />
                  <span>删除</span>
                </a-button>
              </div>
            </div>
            <div class="editor-main">
              <a-empty
                v-if="!selectedPath || selectedIsDir"
                description="选择文件以开始编辑"
                class="mt-40"
              />
              <template v-else>
                <MdPreview
                  v-if="viewMode === 'preview'"
                  :modelValue="previewContent"
                  :theme="theme"
                  previewTheme="github"
                  class="markdown-preview flat-md-preview"
                />
                <a-textarea
                  ref="editorTextarea"
                  v-else
                  v-model:value="fileContent"
                  class="pure-editor"
                  spellcheck="false"
                  @blur="parseVariablesOnBlur"
                />
              </template>
            </div>
          </div>
          <!-- 变量管理面板 -->
          <div class="variable-panel">
            <div class="variable-header">
              <div class="variable-title">
                <Variable :size="14" />
                <span>变量</span>
              </div>
            </div>
            <div class="variable-content">
              <div class="variable-add">
                <a-input
                  v-model:value="newVariableName"
                  placeholder="输入变量名"
                  @pressEnter="addVariable"
                  size="small"
                />
                <a-button type="primary" size="small" @click="addVariable">
                  <Plus :size="12" />
                </a-button>
              </div>
              <div class="variable-list">
                <div
                  v-for="variable in variableList"
                  :key="variable.name"
                  class="variable-item"
                >
                  <div class="variable-info">
                    <span class="variable-name">{{ variable.name }}</span>
                    <div class="variable-actions">
                      <a-tooltip title="插入到编辑器" placement="top">
                        <button @click="insertVariableToEditor(variable.name)" class="action-btn">
                          <Plus :size="12" />
                        </button>
                      </a-tooltip>
                      <a-tooltip title="删除变量" placement="top">
                        <button @click="removeVariable(variable.name)" class="action-btn delete">
                          <Trash :size="12" />
                        </button>
                      </a-tooltip>
                    </div>
                  </div>
                  <a-input
                    :value="variableInputValues[variable.name]"
                    @update:value="(val) => updateVariableValue(variable.name, val)"
                    placeholder="变量值"
                    size="small"
                  />
                </div>
                <a-empty
                  v-if="variableList.length === 0"
                  description="暂无变量"
                  class="variable-empty"
                />
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>

    <!-- 弹窗 -->
    <a-modal
      v-model:open="createModalVisible"
      :title="createForm.isDir ? '新建目录' : '新建文件'"
      @ok="handleCreateNode"
      :confirm-loading="creatingNode"
      width="400px"
    >
      <a-form layout="vertical" class="pt-12">
        <a-form-item label="路径 (相对于根目录)" required>
          <a-input v-model:value="createForm.path" placeholder="src/main.py" />
        </a-form-item>
        <a-form-item v-if="!createForm.isDir" label="内容">
          <a-textarea v-model:value="createForm.content" :rows="5" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { message, Modal } from 'ant-design-vue'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'
import { MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/preview.css'
import { useThemeStore } from '@/stores/theme'
import {
  Upload,
  RotateCw,
  Download,
  Copy,
  Trash2,
  Save,
  FileText,
  Layers,
  FilePlus,
  FolderPlus,
  File,
  Search,
  Box,
  FileCode,
  Eye,
  Edit3,
  Plus,
  X,
  Variable,
  Trash
} from 'lucide-vue-next'
import { promptApi } from '@/apis/prompt_api'
import FileTreeComponent from '@/components/FileTreeComponent.vue'

dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

const themeStore = useThemeStore()
const theme = computed(() => (themeStore.isDark ? 'dark' : 'light'))

const previewContent = computed(() => {
  let content = fileContent.value
  variableList.value.forEach(variable => {
    const value = variableInputValues.value[variable.name]
    if (value !== undefined && value !== '') {
      const regex = new RegExp(`\\{\\{${variable.name}\\}\\}`, 'g')
      content = content.replace(regex, value)
    }
  })
  return content
})

const loading = ref(false)
const importing = ref(false)
const savingFile = ref(false)
const creatingNode = ref(false)
const savingDependencies = ref(false)
const searchQuery = ref('')
const viewMode = ref('edit') // 'edit' | 'preview'

const prompts = ref([])
const currentPrompt= ref(null)
const treeData = ref([])
const selectedTreeKeys = ref([])
const expandedKeys = ref([])
const selectedPath = ref('')
const selectedIsDir = ref(false)
const fileContent = ref('')
const originalFileContent = ref('')
const editorTextarea = ref(null)

const createModalVisible = ref(false)
const createForm = reactive({ path: '', isDir: false, content: '' })
const dependencyOptions = reactive({ tools: [], mcps: [], skills: [] })
const dependencyForm = reactive({
  tool_dependencies: [],
  mcp_dependencies: [],
  skill_dependencies: []
})

const variablePanelVisible = ref(false)
const variableList = ref([])
const newVariableName = ref('')
const editingVariable = ref(null)
const variableInputValues = ref({})

const filteredPrompts = computed(() => {
  if (!searchQuery.value) return prompts.value
  const q = searchQuery.value.toLowerCase()
  return prompts.value.filter(
    (s) => s.name.toLowerCase().includes(q) || s.slug.toLowerCase().includes(q)
  )
})

const canSave = computed(() => {
  if (!selectedPath.value || selectedIsDir.value) return false
  return fileContent.value !== originalFileContent.value
})

const canCopy = computed(() => {
  if (!selectedPath.value || selectedIsDir.value) return false
  return true
})

const isMarkdownFile = computed(() => {
  if (!selectedPath.value) return false
  return selectedPath.value.toLowerCase().endsWith('.md')
})

// 切换到非markdown文件时重置为编辑模式
watch(selectedPath, (newPath) => {
  if (newPath && !newPath.toLowerCase().endsWith('.md')) {
    viewMode.value = 'edit'
  }
})

const parseVariablesFromContent = (content) => {
  const found = new Set()
  const regex = /\{\{([^}]+)\}\}/g
  const matches = content.matchAll(regex)
  for (const match of matches) {
    const name = match[1].trim()
    if (name) {
      found.add(name)
    }
  }
  return Array.from(found)
}

const parseVariablesOnBlur = () => {
  const content = fileContent.value
  if (!content) {
    variableList.value = []
    variableInputValues.value = {}
    return
  }
  const parsedVars = parseVariablesFromContent(content)
  
  variableList.value = parsedVars.map(name => {
    const existing = variableList.value.find(v => v.name === name)
    return existing || { name, value: '' }
  })
  
  const newInputValues = {}
  variableList.value.forEach(v => {
    newInputValues[v.name] = variableInputValues.value[v.name] || ''
  })
  variableInputValues.value = newInputValues
}

const formatRelativeTime = (time) => (time ? dayjs(time).fromNow() : '-')

const toolDependencyOptions = computed(() =>
  (dependencyOptions.tools || []).map((i) =>
    typeof i === 'object' ? { label: i.name, value: i.id } : { label: i, value: i }
  )
)
const mcpDependencyOptions = computed(() =>
  (dependencyOptions.mcps || []).map((i) => ({ label: i, value: i }))
)
const skillDependencyOptions = computed(() =>
  (dependencyOptions.skills || [])
    .filter((s) => s !== currentPrompt.value?.slug)
    .map((i) => ({ label: i, value: i }))
)

const normalizeTree = (nodes) =>
  (nodes || []).map((node) => ({
    title: node.name,
    key: node.path,
    isLeaf: !node.is_dir,
    path: node.path,
    is_dir: node.is_dir,
    children: node.is_dir ? normalizeTree(node.children || []) : undefined
  }))

const resetFileState = () => {
  selectedPath.value = ''
  selectedIsDir.value = false
  selectedTreeKeys.value = []
  expandedKeys.value = []
  fileContent.value = ''
  originalFileContent.value = ''
  viewMode.value = 'edit'
}

const expandAllKeys = (nodes) =>
  nodes.flatMap((node) => (node.is_dir ? [node.key, ...expandAllKeys(node.children || [])] : []))

const reloadTree = async () => {
  loading.value = true
  try {
    const result = await promptApi.getPromptTree()
    const normalized = normalizeTree(result?.data || [])
    treeData.value = normalized
    expandedKeys.value = expandAllKeys(normalized)
  } catch {
    message.error('加载目录树失败')
  } finally {
    loading.value = false
  }
}

const handleTreeSelect = async (keys, info) => {
  if (!keys?.length) {
    resetFileState()
    return
  }
  const node = info?.node || {}
  const path = node.path || node.key
  const isDir = !!node.is_dir
  selectedTreeKeys.value = [path]
  selectedPath.value = path
  selectedIsDir.value = isDir
  if (isDir) {
    fileContent.value = ''
    originalFileContent.value = ''
    return
  }
  try {
    const result = await promptApi.getPromptFile(path)
    const content = result?.data?.content || ''
    fileContent.value = content
    originalFileContent.value = content
    parseVariablesOnBlur()
  } catch {
    message.error('文件读取失败')
  }
}

const addVariable = () => {
  if (!newVariableName.value.trim()) {
    message.warning('请输入变量名')
    return
  }
  const name = newVariableName.value.trim()
  if (variableList.value.some(v => v.name === name)) {
    message.warning('变量名已存在')
    return
  }
  variableList.value.push({ name, value: '' })
  variableInputValues.value[name] = ''
  newVariableName.value = ''
}

const removeVariable = (name) => {
  variableList.value = variableList.value.filter(v => v.name !== name)
  delete variableInputValues.value[name]
}

const updateVariableValue = (name, value) => {
  variableInputValues.value[name] = value
  const variable = variableList.value.find(v => v.name === name)
  if (variable) {
    variable.value = value
  }
}

const insertVariableToEditor = async (name) => {
  const textarea = editorTextarea.value?.$el || editorTextarea.value
  if (textarea && textarea instanceof HTMLTextAreaElement) {
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const text = fileContent.value
    const variableMarker = `{{${name}}}`
    fileContent.value = text.substring(0, start) + variableMarker + text.substring(end)
    await nextTick()
    textarea.focus()
    const newPos = start + variableMarker.length
    textarea.setSelectionRange(newPos, newPos)
  } else {
    fileContent.value += `{{${name}}}`
  }
}

const copyCurrentFile = async () => {
  if (!selectedPath.value || selectedIsDir.value) return
  try {
    await navigator.clipboard.writeText(fileContent.value)
    message.success('已复制')
    if (selectedPath.value === 'SKILL.md') await fetchPrompts()
  } catch {
    message.error('复制失败')
  }
}

const copyRenderedContent = async () => {
  if (!selectedPath.value || selectedIsDir.value) return
  
  const unassignedVars = variableList.value.filter(
    v => !variableInputValues.value[v.name] || variableInputValues.value[v.name] === ''
  )
  
  if (unassignedVars.length > 0) {
    Modal.confirm({
      title: '存在未赋值的变量',
      content: `以下变量尚未赋值：${unassignedVars.map(v => v.name).join('、')}。是否继续复制？`,
      okText: '继续复制',
      cancelText: '取消',
      onOk: async () => {
        try {
          await navigator.clipboard.writeText(previewContent.value)
          message.success('已复制渲染后的内容')
        } catch {
          message.error('复制失败')
        }
      }
    })
    return
  }
  
  try {
    await navigator.clipboard.writeText(previewContent.value)
    message.success('已复制渲染后的内容')
  } catch {
    message.error('复制失败')
  }
}

const saveCurrentFile = async () => {
  if (!selectedPath.value || selectedIsDir.value) return
  savingFile.value = true
  try {
    await promptApi.updatePromptFile({
      path: selectedPath.value,
      content: fileContent.value
    })
    originalFileContent.value = fileContent.value
    message.success('已保存')
    if (selectedPath.value === 'SKILL.md') await fetchPrompts()
  } catch {
    message.error('保存失败')
  } finally {
    savingFile.value = false
  }
}

const openCreateModal = (isDir) => {
  createForm.path = ''
  createForm.content = ''
  createForm.isDir = isDir
  createModalVisible.value = true
}

const handleCreateNode = async () => {
  creatingNode.value = true
  try {
    await promptApi.createPromptFile({
      path: createForm.path.trim(),
      is_dir: createForm.isDir,
      content: createForm.content
    })
    createModalVisible.value = false
    await reloadTree()
    message.success('创建成功')
  } catch {
    message.error('创建失败')
  } finally {
    creatingNode.value = false
  }
}

const confirmDeleteNode = () => {
  if (!selectedPath.value) return
  Modal.confirm({
    title: '确认删除？',
    content: `将永久删除: ${selectedPath.value}`,
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      try {
        await promptApi.deletePromptFile(selectedPath.value)
        resetFileState()
        await reloadTree()
        message.success('已删除')
      } catch {
        message.error('删除失败')
      }
    }
  })
}

const handleImportUpload = async ({ file, onSuccess, onError }) => {
  importing.value = true
  try {
    const result = await skillApi.importSkillZip(file)
    message.success('导入完成')
    await fetchPrompts()
    const imported = result?.data
    if (imported?.slug) {
      const record = prompts.value.find((i) => i.slug === imported.slug)
      if (record) await selectSkill(record)
    }
    onSuccess?.(result)
  } catch (e) {
    message.error('导入失败')
    onError?.(e)
  } finally {
    importing.value = false
  }
}

onMounted(reloadTree)

// 暴露方法给父组件
defineExpose({
  reloadTree,
  handleImportUpload
})
</script>

<style scoped lang="less">
@import '@/assets/css/extensions.less';

.list-item {
  .item-details {
    display: flex;
    justify-content: space-between;
    align-items: center;
    .item-slug {
      font-size: 12px;
      color: var(--gray-400);
      font-family: monospace;
    }
    .item-badges {
      display: flex;
      gap: 4px;
      .dot-badge {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        &.blue {
          background-color: #3b82f6;
        }
        &.green {
          background-color: #22c55e;
        }
      }
    }
  }
}

/* 右侧面板 */
.main-panel {
  .panel-top-bar {
    .skill-summary {
      min-height: 32px;
      display: flex;
      flex-direction: column;
      justify-content: center;
      code {
        font-size: 12px;
        color: var(--gray-500);
        background: @bg-secondary;
        padding: 2px 6px;
        border-radius: 4px;
        margin-top: 4px;
        display: inline-block;
      }
    }
  }
}

.workspace {
  display: flex;
  flex: 1;
  min-height: 0;
  height: 100%;
  overflow: hidden;
}

/* 变量管理面板 */
.variable-panel {
  width: 200px;
  border-right: 1px solid @border-color;
  background-color: @bg-secondary;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;

  .variable-header {
    padding: 10px 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid @border-color;
    background-color: var(--gray-50);

    .variable-title {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      font-weight: 600;
      color: var(--gray-500);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
  }

  .variable-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    padding: 8px;
  }

  .variable-add {
    display: flex;
    gap: 6px;
    margin-bottom: 12px;

    .ant-input {
      flex: 1;
    }
  }

  .variable-list {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .variable-item {
    background-color: var(--gray-0);
    border: 1px solid @border-color;
    border-radius: 4px;
    padding: 8px;
    display: flex;
    flex-direction: column;
    gap: 6px;

    .variable-info {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .variable-name {
        font-size: 12px;
        font-weight: 500;
        color: var(--gray-700);
        font-family: monospace;
      }

      .variable-actions {
        display: flex;
        gap: 4px;

        .action-btn {
          background: none;
          border: none;
          padding: 2px;
          cursor: pointer;
          color: var(--gray-500);
          display: flex;
          align-items: center;
          border-radius: 2px;

          &:hover {
            color: var(--gray-700);
            background-color: var(--gray-100);
          }

          &.delete:hover {
            color: #ef4444;
          }
        }
      }
    }
  }

  .variable-empty {
    padding: 20px 0;
    :deep(.ant-empty-description) {
      font-size: 12px;
      color: var(--gray-400);
    }
  }
}

/* 文件 tree */
.tree-container {
  width: 240px;
  border-right: 1px solid @border-color;
  background-color: @bg-secondary;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;

  .tree-header {
    padding: 10px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid @border-color;
    background-color: var(--gray-50);
    .label {
      font-size: 11px;
      font-weight: 600;
      color: var(--gray-500);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .tree-actions {
      display: flex;
      gap: 4px;
      button {
        background: none;
        border: none;
        padding: 2px;
        cursor: pointer;
        color: var(--gray-500);
        display: flex;
        align-items: center;
        &:hover {
          color: var(--gray-900);
        }
      }
    }
  }

  .tree-content {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
  }
}

/* 编辑器 */
.editor-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;

  .editor-header {
    padding: 8px 16px;
    border-bottom: 1px solid @border-color;
    display: flex;
    justify-content: space-between;
    align-items: center;
    background-color: var(--gray-0);
    flex-shrink: 0;

    .current-path {
      display: flex;
      align-items: center;
      gap: 8px;
      font-family: monospace;
      font-size: 12px;
      color: var(--gray-500);
      .save-hint {
        color: #f59e0b;
        font-size: 10px;
        margin-left: 4px;
      }
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .view-toggle-btn {
      background-color: var(--gray-100);
      border-color: var(--gray-300);
      &:hover {
        background-color: var(--gray-200);
        border-color: var(--gray-400);
      }
    }
  }

  .editor-main {
    flex: 1;
    min-height: 0;
    background-color: var(--gray-0);
    display: flex;
    flex-direction: column;
  }

  .editor-main :deep(.ant-empty) {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .editor-main :deep(textarea) {
    flex: 1;
    min-height: 0;
  }

  .pure-editor {
    width: 100%;
    height: 100%;
    border: none;
    resize: none;
    padding: 20px;
    font-family: 'Fira Code', 'Monaco', monospace;
    font-size: 16px;
    line-height: 1.6;
    &:focus {
      outline: none;
    }
  }

  .markdown-preview {
    flex: 1;
    height: 100%;
    overflow-y: auto;
    :deep(.md-editor) {
      height: 100%;
      background: var(--gray-0);
    }
    :deep(.md-editor-preview-wrapper) {
      padding: 16px 20px;
    }
  }
}

/* 依赖配置 */
.config-view {
  padding: 16px;
  flex: 1;
  overflow-y: auto;
  .config-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 32px;
    flex-shrink: 0;
    .text {
      h3 {
        margin: 0 0 4px 0;
        font-size: 16px;
        font-weight: 600;
      }
      p {
        margin: 0;
        color: var(--gray-500);
        font-size: 13px;
      }
    }
  }
  .config-form {
    max-width: 600px;
    :deep(.ant-form-item-label label) {
      font-weight: 500;
      font-size: 13px;
    }
  }
}

.mt-40 {
  margin-top: 40px;
}
.pt-12 {
  padding-top: 12px;
}

@media (max-width: 1000px) {
  .sidebar-list {
    width: 220px;
  }
  .tree-container {
    width: 180px;
  }
}
</style>
