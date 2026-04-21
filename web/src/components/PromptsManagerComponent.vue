<template>
  <div class="extension-page-root">
    <div v-if="loading" class="loading-bar-wrapper">
      <div class="loading-bar"></div>
    </div>
    <div class="layout-wrapper" :class="{ 'content-loading': loading }">
      <!-- 详情面板 -->
      <div class="main-panel">
        <div class="panel-top-bar compact-bar">
          <div class="panel-title">
            <h2>提示词管理</h2>
            <span class="panel-subtitle">统一维护目录、内容与变量</span>
          </div>
          <div class="panel-center-metrics">
            <span class="metric-pill">{{ treeStats.folders }} 目录</span>
            <span class="metric-pill">{{ treeStats.files }} 文件</span>
            <span class="metric-pill">{{ recentFiles.length }} 已打开</span>
            <span v-if="canSave" class="metric-pill warning">未保存变更</span>
          </div>
          <!-- <div class="panel-right-hint">
            <span v-if="selectedPath" class="active-file" :title="selectedPath">{{ selectedPath }}</span>
            <span v-else class="active-file muted">未选择文件</span>
          </div> -->
        </div>
        <div class="workspace">
          <div class="tree-container">
            <div class="tree-header">
              <div class="tree-title-wrap">
                <div class="label-row">
                  <Layers :size="14" />
                  <span class="label">提示词目录</span>
                </div>
                <span class="tree-meta">{{ treeStats.folders }} 个目录 · {{ treeStats.files }} 个文件</span>
              </div>
              <div class="tree-actions">
                <a-tooltip title="新建文件"
                  ><button class="tree-action-btn" @click="openCreateModal(false)"><FilePlus :size="14" /></button
                ></a-tooltip>
                <a-tooltip title="新建目录"
                  ><button class="tree-action-btn" @click="openCreateModal(true)"><FolderPlus :size="14" /></button
                ></a-tooltip>
                <a-tooltip title="刷新"
                  ><button class="tree-action-btn" @click="reloadTree"><RotateCw :size="14" /></button
                ></a-tooltip>
              </div>
            </div>
            <div class="tree-search">
              <a-input v-model:value="treeSearchQuery" allow-clear placeholder="搜索目录或文件" size="small">
                <template #prefix>
                  <Search :size="14" />
                </template>
              </a-input>
            </div>
            <div class="tree-content">
              <div class="tree-surface">
                <FileTreeComponent
                  tree-class="prompt-tree"
                  v-model:selectedKeys="selectedTreeKeys"
                  v-model:expandedKeys="expandedKeys"
                  :tree-data="treeDataForRender"
                  @select="handleTreeSelect"
                >
                  <template #title="{ node }">
                    <a-dropdown :trigger="['contextmenu']">
                      <span class="tree-node-title" :title="node.title">{{ node.title }}</span>
                      <template #overlay>
                        <a-menu @click="({ key }) => handleTreeContextAction(key, node)">
                          <a-menu-item key="new-file">新建文件</a-menu-item>
                          <a-menu-item key="new-dir">新建目录</a-menu-item>
                          <a-menu-divider />
                          <a-menu-item key="rename">重命名</a-menu-item>
                          <a-menu-item key="delete" danger>删除</a-menu-item>
                        </a-menu>
                      </template>
                    </a-dropdown>
                  </template>
                </FileTreeComponent>
                <a-empty v-if="!treeDataForRender.length" :description="treeSearchQuery ? '未找到匹配项' : '暂无文件'" class="tree-empty" />
              </div>
            </div>
          </div>

          <div class="editor-container">
            <div class="editor-header">
              <div class="header-main">
                <div class="current-path">
                  <File :size="14" />
                  <template v-if="selectedPath">
                    <button
                      v-for="(segment, index) in selectedPathSegments"
                      :key="segment.path"
                      type="button"
                      class="breadcrumb-segment"
                      :class="{ active: index === selectedPathSegments.length - 1 }"
                      @click="openPath(segment.path)"
                    >
                      <span>{{ segment.name }}</span>
                    </button>
                  </template>
                  <span v-else>未选择文件</span>
                  <span v-if="canSave" class="save-hint">●</span>
                </div>
              </div>
              <div class="header-top-row">
                <div class="header-actions">
                  <div v-if="selectedExternalId && !selectedIsDir" class="external-id-inline">
                    <span class="external-id-label">External ID</span>
                    <code class="external-id-value" :title="selectedExternalId">{{ selectedExternalId }}</code>
                    <button
                      type="button"
                      class="external-id-copy-btn"
                      @click="copyExternalId"
                      title="复制 external_id"
                    >
                      <Copy :size="12" />
                    </button>
                  </div>
                  <a-button
                    v-if="isMarkdownFile && selectedPath"
                    size="small"
                    @click="viewMode = viewMode === 'edit' ? 'preview' : 'edit'"
                    class="lucide-icon-btn toolbar-btn toolbar-btn-secondary view-toggle-btn"
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
                    class="lucide-icon-btn toolbar-btn toolbar-btn-secondary"
                  >
                    <Copy :size="14" />
                    <span>复制</span>
                  </a-button>
                  <a-button
                    size="small"
                    @click="copyRenderedContent"
                    :disabled="!canCopy"
                    class="lucide-icon-btn toolbar-btn toolbar-btn-secondary"
                  >
                    <FileText :size="14" />
                    <span>渲染并复制</span>
                  </a-button>
                  <a-button
                    type="primary"
                    size="small"
                    @click="saveCurrentFile"
                    :disabled="!canSave"
                    :loading="savingFile"
                    class="lucide-icon-btn toolbar-btn toolbar-btn-primary"
                  >
                    <Save :size="14" />
                    <span>保存</span>
                  </a-button>
                  <a-dropdown overlayClassName="prompt-manager-more-menu">
                    <a-button size="small" class="lucide-icon-btn toolbar-btn toolbar-btn-secondary">
                      <MoreHorizontal :size="14" />
                      <span>更多</span>
                    </a-button>
                    <template #overlay>
                      <a-menu @click="({ key }) => handleMoreAction(key)">
                        <a-menu-item key="publish" :disabled="!selectedPath || selectedIsDir">
                          {{ isPublicToCommunity ? '重新发布到社区' : '发布到社区' }}
                        </a-menu-item>
                        <a-menu-item key="unpublish" :disabled="!isPublicToCommunity || unpublishing">
                          {{ unpublishing ? '取消发布中...' : '取消发布' }}
                        </a-menu-item>
                        <a-menu-divider />
                        <a-menu-item key="rename" :disabled="!selectedPath">重命名</a-menu-item>
                        <a-menu-item key="delete" danger :disabled="!selectedPath">删除</a-menu-item>
                      </a-menu>
                    </template>
                  </a-dropdown>
                </div>
              </div>
              <div v-if="recentFiles.length" class="opened-files-row">
                <span class="recent-title">已打开文件</span>
                <div class="recent-files-scroll">
                  <a-dropdown
                    v-for="item in visibleRecentFiles"
                    :key="item.path"
                    :trigger="['contextmenu']"
                  >
                    <div
                      class="recent-item"
                      :class="{ active: item.path === selectedPath }"
                      :title="item.path"
                      @click="openPath(item.path)"
                    >
                      <span class="name">{{ getPathName(item.path) }}</span>
                      <button
                        type="button"
                        class="recent-close"
                        title="关闭"
                        @click.stop="closeRecentByPath(item.path)"
                      >
                        ×
                      </button>
                    </div>
                    <template #overlay>
                      <a-menu @click="({ key }) => handleRecentContextAction(key, item.path)">
                        <a-menu-item key="close-current">关闭当前</a-menu-item>
                        <a-menu-item key="close-all">关闭所有</a-menu-item>
                        <a-menu-divider />
                        <a-menu-item key="save-close-current">保存并关闭</a-menu-item>
                        <a-menu-item key="save-close-all">保存并关闭所有</a-menu-item>
                        <a-menu-divider />
                        <a-menu-item key="close-right">关闭右侧</a-menu-item>
                        <a-menu-item key="save-close-right">保存并关闭右侧</a-menu-item>
                      </a-menu>
                    </template>
                  </a-dropdown>
                  <a-dropdown v-if="overflowRecentFiles.length">
                    <button type="button" class="recent-overflow-trigger">+{{ overflowRecentFiles.length }}</button>
                    <template #overlay>
                      <a-menu @click="({ key }) => handleOverflowMenuAction(key)">
                        <a-menu-item
                          v-for="item in overflowRecentFiles"
                          :key="`open::${item.path}`"
                          :title="item.path"
                        >
                          打开 {{ getPathName(item.path) }}
                        </a-menu-item>
                        <a-menu-divider />
                        <a-menu-item key="close-all">关闭所有</a-menu-item>
                        <a-menu-item key="save-close-all">保存并关闭所有</a-menu-item>
                      </a-menu>
                    </template>
                  </a-dropdown>
                </div>
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
            <div
              v-if="selectedPath && !selectedIsDir"
              class="editor-test-panel"
              :class="{ empty: !promptTestResult }"
            >
              <div class="editor-test-panel-header">
                <span>测试结果</span>
                <div class="editor-test-panel-header-actions">
                  <code v-if="promptTestResult?.model_spec">{{ promptTestResult.model_spec }}</code>
                  <button
                    type="button"
                    class="editor-test-copy-btn"
                    :disabled="!promptTestResult?.response"
                    @click="copyPromptTestResult"
                    title="复制测试结果"
                  >
                    <Copy :size="13" />
                    <span>复制</span>
                  </button>
                </div>
              </div>
              <div v-if="promptTestResult" class="editor-test-panel-body">
                <pre>{{ promptTestResult.response }}</pre>
              </div>
              <div v-else class="editor-test-panel-empty">运行“测试提示词”后，这里会展示模型回复</div>
            </div>
          </div>
          <!-- 变量管理面板 -->
          <div class="variable-panel">
            <div class="variable-header">
              <div class="variable-header-main">
                <div class="variable-title">
                  <Variable :size="14" />
                  <span>变量管理</span>
                </div>
                <span class="variable-meta">{{ variableList.length }} 个变量</span>
              </div>
              <div class="variable-header-actions">
                <a-tooltip title="从当前内容重新识别变量" placement="top">
                  <button
                    class="refresh-btn"
                    :disabled="!selectedPath || selectedIsDir"
                    @click="parseVariablesOnBlur"
                  >
                    <RotateCw :size="13" />
                  </button>
                </a-tooltip>
              </div>
            </div>
            <div class="variable-content">
              <div class="variable-tip">
                使用<span v-pre>{{variable}}</span>在文本中插入变量
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
              <div class="prompt-test-card">
                <div class="prompt-test-toolbar">
                  <a-button
                    type="primary"
                    size="small"
                    class="prompt-test-btn"
                    :disabled="!selectedPath || selectedIsDir"
                    @click="openPromptTestModal"
                  >
                    提示词测试
                  </a-button>
                  <span
                    class="prompt-test-status"
                    :class="{ ready: promptTestCapability.ready, error: !promptTestCapability.ready }"
                  >
                    {{ promptTestCapability.ready ? '模型已就绪' : '模型未就绪' }}
                  </span>
                </div>
                <div v-if="!promptTestCapability.ready" class="prompt-test-issues">
                  {{ promptTestCapability.issues.join('；') || '当前无可用模型，请先在系统设置中启用并配置模型提供方' }}
                </div>
                <div
                  v-else-if="promptTestCapability.defaultReady === false && promptTestCapability.defaultIssues.length"
                  class="prompt-test-issues warning"
                >
                  {{ promptTestCapability.defaultIssues.join('；') }}
                </div>
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
        <a-form-item v-if="createForm.parentPath" label="父目录">
          <span class="parent-path-display">{{ createForm.parentPath }}/</span>
        </a-form-item>
        <a-form-item :label="createForm.isDir ? '目录名称' : '文件名称'" required>
          <a-input 
            v-model:value="createFileName" 
            :placeholder="createForm.isDir ? 'my-folder' : 'myfile.md'"
            @pressEnter="handleCreateNode"
          />
          <div v-if="createFileNameError" class="error-text">{{ createFileNameError }}</div>
        </a-form-item>
        <a-form-item v-if="!createForm.isDir" label="内容">
          <a-textarea v-model:value="createForm.content" :rows="5" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal
      v-model:open="renameModalVisible"
      :title="renameForm.isDir ? '重命名目录' : '重命名文件'"
      @ok="handleRenameNode"
      :confirm-loading="renamingNode"
      width="420px"
    >
      <a-form layout="vertical" class="pt-12">
        <a-form-item label="当前路径">
          <span class="parent-path-display">{{ renameForm.path || '-' }}</span>
        </a-form-item>
        <a-form-item label="新名称" required>
          <a-input
            v-model:value="renameFileName"
            :placeholder="renameForm.isDir ? 'new-folder' : 'new-name.md'"
            @pressEnter="handleRenameNode"
          />
          <div v-if="renameFileNameError" class="error-text">{{ renameFileNameError }}</div>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 发布到市场弹窗 -->
    <a-modal
      v-model:open="publishModalVisible"
      title="发布到提示词社区"
      @ok="handlePublishToMarket"
      :confirm-loading="publishing"
      width="520px"
      class="publish-modal"
      wrapClassName="publish-modal-wrap"
      ok-text="发布"
      cancel-text="取消"
    >
      <a-form layout="vertical" class="pt-12 publish-form">
        <a-form-item label="模板名称" required>
          <a-input v-model:value="publishForm.name" placeholder="输入模板名称" />
        </a-form-item>
        <a-form-item label="分类" required>
          <a-select v-model:value="publishForm.category" placeholder="选择分类">
            <a-select-option v-for="cat in templateCategories" :key="cat.key" :value="cat.key">
              {{ cat.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea
            v-model:value="publishForm.description"
            placeholder="简要描述这个模板的用途"
            :rows="3"
          />
        </a-form-item>
        <a-form-item label="标签">
          <a-select
            v-model:value="publishForm.tags"
            mode="tags"
            placeholder="添加标签"
            style="width: 100%"
          />
        </a-form-item>
        <a-form-item label="变量">
          <div class="variable-tags-preview">
            <a-tag v-for="v in variableList" :key="v.name" color="blue">
              {{ v.name }}
            </a-tag>
            <span v-if="variableList.length === 0" style="color: #999; font-size: 12px;">
              当前文件未检测到变量
            </span>
          </div>
        </a-form-item>
        <a-form-item label="设为官方模板" v-if="userStore.isSuperAdmin">
          <a-switch v-model:checked="publishForm.isOfficial" />
          <span class="switch-hint">设为官方模板后，所有用户可见并可收藏</span>
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal
      v-model:open="promptTestModalVisible"
      title="测试提示词"
      @ok="runPromptTest"
      :confirm-loading="testingPrompt"
      :ok-button-props="{ disabled: isPromptTestDisabled }"
      width="560px"
      ok-text="开始测试"
      cancel-text="取消"
      class="prompt-test-modal"
      wrapClassName="prompt-test-modal-wrap"
    >
      <a-form layout="vertical" class="pt-12">
        <a-form-item label="测试模型">
          <a-select
            v-model:value="promptTestForm.model_spec"
            placeholder="请选择模型"
            size="small"
            style="width: 100%"
            :options="promptTestModelOptions"
            :disabled="promptTestModelOptions.length === 0"
            show-search
            popupClassName="prompt-test-model-dropdown"
            :filter-option="(input, option) => String(option?.label || '').toLowerCase().includes(input.toLowerCase())"
          />
          <div class="switch-hint">
            默认使用系统 default_model；也可在此切换测试模型
          </div>
        </a-form-item>
        <a-form-item label="变量赋值检查">
          <div v-if="missingVariableNames.length" class="prompt-test-variable-alert is-warning">
            <div class="alert-title">还有 {{ missingVariableNames.length }} 个变量待填写</div>
            <div class="alert-names">{{ missingVariableNames.join('、') }}</div>
            <div class="alert-tip">请先在变量管理面板补全变量，再开始测试</div>
          </div>
          <div v-else class="prompt-test-variable-alert is-ready">
            <div class="alert-title">变量检查通过</div>
            <div class="alert-tip">变量已全部赋值，可直接开始测试</div>
          </div>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/preview.css'
import { useThemeStore } from '@/stores/theme'
import { useConfigStore } from '@/stores/config'
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
  Eye,
  Edit3,
  MoreHorizontal,
  Plus,
  Variable,
  Trash,
  Store
} from 'lucide-vue-next'
import { promptApi } from '@/apis/prompt_api'
import { publishTemplate, updateTemplate, getMyTemplates, unpublishTemplate, deleteTemplate } from '@/apis/template_api'
import { publishPrompt as communityPublishPrompt, getMyTemplates as communityGetMyTemplates, unpublishTemplate as communityUnpublish, updateTemplate as communityUpdateTemplate } from '@/apis/community_api'
import { useUserStore } from '@/stores/user'
import FileTreeComponent from '@/components/FileTreeComponent.vue'

const themeStore = useThemeStore()
const userStore = useUserStore()
const configStore = useConfigStore()
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
const treeSearchQuery = ref('')
const viewMode = ref('edit') // 'edit' | 'preview'

const prompts = ref([])
const currentPrompt= ref(null)
const treeData = ref([])
const selectedTreeKeys = ref([])
const expandedKeys = ref([])
const selectedPath = ref('')
const selectedIsDir = ref(false)
const selectedExternalId = ref('')
const fileContent = ref('')
const originalFileContent = ref('')
const editorTextarea = ref(null)

const createModalVisible = ref(false)
const createForm = reactive({ parentPath: '', isDir: false, content: '' })
const createFileName = ref('')
const createFileNameError = ref('')
const renameModalVisible = ref(false)
const renamingNode = ref(false)
const renameFileName = ref('')
const renameFileNameError = ref('')
const renameForm = reactive({ path: '', isDir: false })
const expandedKeysBeforeSearch = ref([])
const dependencyOptions = reactive({ tools: [], mcps: [] })
const dependencyForm = reactive({
  tool_dependencies: [],
  mcp_dependencies: []
})

const variablePanelVisible = ref(false)
const variableList = ref([])
const editingVariable = ref(null)
const variableInputValues = ref({})

const publishModalVisible = ref(false)
const publishing = ref(false)
const unpublishing = ref(false)
const publishForm = reactive({
  name: '',
  category: 'writing',
  description: '',
  tags: [],
  isOfficial: false
})
const publishedTemplateId = ref('')
const recentFiles = ref([])
const promptTestModalVisible = ref(false)
const testingPrompt = ref(false)
const promptTestResult = ref(null)
const promptTestCapability = reactive({
  ready: false,
  issues: [],
  default_model: '',
  defaultReady: false,
  defaultIssues: [],
  availableModels: []
})
const promptTestForm = reactive({ model_spec: '' })

const promptTestModelOptions = computed(() =>
  (promptTestCapability.availableModels || []).map((spec) => ({
    label: spec,
    value: spec
  }))
)

const templateCategories = [
  { key: 'writing', name: '写作' },
  { key: 'programming', name: '编程' },
  { key: 'analysis', name: '分析' },
  { key: 'translation', name: '翻译' },
  { key: 'office', name: '办公' },
  { key: 'education', name: '教育' },
  { key: 'marketing', name: '营销' }
]

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

const treeStats = computed(() => {
  let folders = 0
  let files = 0
  const walk = (nodes) => {
    ;(nodes || []).forEach((node) => {
      if (node.is_dir) {
        folders += 1
        walk(node.children || [])
      } else {
        files += 1
      }
    })
  }
  walk(treeData.value)
  return { folders, files }
})

const selectedPathSegments = computed(() => {
  if (!selectedPath.value) return []
  const parts = selectedPath.value.split('/').filter(Boolean)
  return parts.map((name, index) => ({
    name,
    path: parts.slice(0, index + 1).join('/')
  }))
})

const visibleRecentLimit = 6

const visibleRecentFiles = computed(() => {
  const list = recentFiles.value
  if (list.length <= visibleRecentLimit) return list

  const selectedIndex = list.findIndex((item) => item.path === selectedPath.value)
  const visible = [...list.slice(0, visibleRecentLimit)]

  if (selectedIndex >= visibleRecentLimit) {
    visible[visibleRecentLimit - 1] = list[selectedIndex]
  }

  const unique = []
  const seen = new Set()
  for (const item of visible) {
    if (item && !seen.has(item.path)) {
      unique.push(item)
      seen.add(item.path)
    }
  }

  return unique
})

const overflowRecentFiles = computed(() => {
  const visibleSet = new Set(visibleRecentFiles.value.map((item) => item.path))
  return recentFiles.value.filter((item) => !visibleSet.has(item.path))
})

const treeDataForRender = computed(() => {
  const query = treeSearchQuery.value.trim().toLowerCase()
  if (!query) return treeData.value
  return filterTreeWithAncestors(treeData.value, query).nodes
})

const myPublishedTemplates = ref([])

const publishedTemplate = computed(() => {
  if (!selectedPath.value || selectedIsDir.value) return null
  return myPublishedTemplates.value.find(t => t.source_path === selectedPath.value) || null
})

const isPublicToCommunity = computed(() => {
  return publishedTemplate.value?.is_public === true
})

const missingVariableNames = computed(() =>
  variableList.value
    .filter((v) => !String(variableInputValues.value[v.name] || '').trim())
    .map((v) => v.name)
)

const isPromptTestDisabled = computed(() => {
  if (!selectedPath.value || selectedIsDir.value) return true
  return missingVariableNames.value.length > 0
})

// 切换到非markdown文件时重置为编辑模式
watch(selectedPath, (newPath) => {
  if (newPath && !newPath.toLowerCase().endsWith('.md')) {
    viewMode.value = 'edit'
  }
})

watch(treeSearchQuery, (nextQuery, prevQuery) => {
  const next = nextQuery.trim()
  const prev = (prevQuery || '').trim()
  if (next && !prev) {
    expandedKeysBeforeSearch.value = [...expandedKeys.value]
  }
  if (!next && prev) {
    expandedKeys.value = [...expandedKeysBeforeSearch.value]
    expandedKeysBeforeSearch.value = []
    return
  }
  if (next) {
    const filtered = filterTreeWithAncestors(treeData.value, next.toLowerCase())
    expandedKeys.value = filtered.expandedKeys
  }
})

watch(
  () => configStore.config?.default_model,
  (next) => {
    if (!promptTestForm.model_spec && next) {
      promptTestForm.model_spec = next
    }
  },
  { immediate: true }
)

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

const toolDependencyOptions = computed(() =>
  (dependencyOptions.tools || []).map((i) =>
    typeof i === 'object' ? { label: i.name, value: i.id } : { label: i, value: i }
  )
)
const mcpDependencyOptions = computed(() =>
  (dependencyOptions.mcps || []).map((i) => ({ label: i, value: i }))
)

const normalizeTree = (nodes) =>
  (nodes || []).map((node) => ({
    title: node.name,
    key: node.path,
    isLeaf: !node.is_dir,
    path: node.path,
    is_dir: node.is_dir,
    external_id: node.external_id || '',
    children: node.is_dir ? normalizeTree(node.children || []) : undefined
  }))

const filterTreeWithAncestors = (nodes, query) => {
  const expandedSet = new Set()

  const walk = (items) => {
    const result = []
    for (const item of items || []) {
      const title = String(item.title || '').toLowerCase()
      const selfMatch = title.includes(query)
      const children = item.children || []
      const filteredChildren = walk(children)
      const hasChildrenMatch = filteredChildren.length > 0

      if (!selfMatch && !hasChildrenMatch) continue

      if (hasChildrenMatch) {
        expandedSet.add(item.key)
      }

      if (selfMatch && item.is_dir) {
        expandedSet.add(item.key)
      }

      if (item.is_dir && selfMatch) {
        result.push({ ...item })
      } else if (item.is_dir) {
        result.push({ ...item, children: filteredChildren })
      } else {
        result.push({ ...item })
      }
    }
    return result
  }

  return { nodes: walk(nodes), expandedKeys: Array.from(expandedSet) }
}

const getParentPath = (path) => {
  const clean = String(path || '')
  const idx = clean.lastIndexOf('/')
  return idx > 0 ? clean.slice(0, idx) : ''
}

const getPathName = (path) => String(path || '').split('/').pop() || path

const remapPathByRename = (path, oldPath, newPath, isDir) => {
  if (!path) return path
  if (!isDir) {
    return path === oldPath ? newPath : path
  }
  if (path === oldPath) return newPath
  if (path.startsWith(`${oldPath}/`)) {
    return `${newPath}${path.slice(oldPath.length)}`
  }
  return path
}

const findNodeByPath = (nodes, path) => {
  for (const node of nodes || []) {
    if (node.path === path || node.key === path) return node
    if (node.children?.length) {
      const found = findNodeByPath(node.children, path)
      if (found) return found
    }
  }
  return null
}

const getAncestorKeys = (path) => {
  const parts = String(path || '').split('/').filter(Boolean)
  const result = []
  for (let i = 0; i < parts.length - 1; i += 1) {
    result.push(parts.slice(0, i + 1).join('/'))
  }
  return result
}

const resetFileState = () => {
  selectedPath.value = ''
  selectedIsDir.value = false
  selectedExternalId.value = ''
  selectedTreeKeys.value = []
  fileContent.value = ''
  originalFileContent.value = ''
  viewMode.value = 'edit'
  promptTestResult.value = null
}

const expandAllKeys = (nodes) =>
  nodes.flatMap((node) => (node.is_dir ? [node.key, ...expandAllKeys(node.children || [])] : []))

const reloadTree = async () => {
  loading.value = true
  try {
    const result = await promptApi.getPromptTree()
    const normalized = normalizeTree(result?.data || [])
    treeData.value = normalized
    if (treeSearchQuery.value.trim()) {
      const filtered = filterTreeWithAncestors(normalized, treeSearchQuery.value.trim().toLowerCase())
      expandedKeys.value = filtered.expandedKeys
    } else {
      expandedKeys.value = expandAllKeys(normalized)
    }
  } catch {
    message.error('加载目录树失败')
  } finally {
    loading.value = false
  }
}

const loadPromptTestCapability = async () => {
  try {
    const result = await promptApi.getPromptTestCapability()
    const data = result?.data || {}
    promptTestCapability.ready = !!data.ready
    promptTestCapability.issues = Array.isArray(data.issues) ? data.issues : []
    promptTestCapability.default_model = data.default_model || ''
    promptTestCapability.defaultReady = data.default_ready !== false
    promptTestCapability.defaultIssues = Array.isArray(data.default_issues) ? data.default_issues : []
    promptTestCapability.availableModels = Array.isArray(data.available_models) ? data.available_models : []

    const currentModel = String(promptTestForm.model_spec || '').trim()
    const availableSet = new Set(promptTestCapability.availableModels)
    const hasCurrentModel = currentModel && availableSet.has(currentModel)
    const defaultModel = String(data.default_model || configStore.config?.default_model || '').trim()
    const hasDefaultModel = defaultModel && availableSet.has(defaultModel)

    if (!hasCurrentModel) {
      promptTestForm.model_spec = hasDefaultModel ? defaultModel : (promptTestCapability.availableModels[0] || '')
    }
  } catch {
    promptTestCapability.ready = false
    promptTestCapability.issues = ['无法读取测试能力，请稍后重试']
    promptTestCapability.defaultReady = false
    promptTestCapability.defaultIssues = []
    promptTestCapability.availableModels = []
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
  selectedExternalId.value = isDir ? '' : (node.external_id || '')
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
    recentFiles.value = [
      { path },
      ...recentFiles.value.filter((item) => item.path !== path)
    ].slice(0, 10)
  } catch {
    message.error('文件读取失败')
  }
}

const openPath = async (path) => {
  const node = findNodeByPath(treeData.value, path)
  if (!node) return
  const shouldExpand = node.is_dir ? [...getAncestorKeys(path), path] : getAncestorKeys(path)
  expandedKeys.value = Array.from(new Set([...expandedKeys.value, ...shouldExpand]))
  await handleTreeSelect([path], { node })
}

const closePathsDirectly = async (paths) => {
  if (!paths.length) return

  const oldList = [...recentFiles.value]
  const removeSet = new Set(paths)
  const selectedWasClosed = !!selectedPath.value && removeSet.has(selectedPath.value)
  const selectedIndex = oldList.findIndex((item) => item.path === selectedPath.value)
  const nextList = oldList.filter((item) => !removeSet.has(item.path))

  recentFiles.value = nextList

  if (!selectedWasClosed) return
  if (!nextList.length) {
    resetFileState()
    return
  }

  const nextIndex = selectedIndex >= 0 ? Math.min(selectedIndex, nextList.length - 1) : 0
  await openPath(nextList[nextIndex].path)
}

const closeWithUnsavedReminder = async (paths, saveFirst = false) => {
  const uniquePaths = Array.from(new Set(paths)).filter(Boolean)
  if (!uniquePaths.length) return

  const includesCurrent = !!selectedPath.value && uniquePaths.includes(selectedPath.value)

  if (saveFirst && includesCurrent && canSave.value) {
    await saveCurrentFile()
    if (canSave.value) return
  }

  if (!saveFirst && includesCurrent && canSave.value) {
    await new Promise((resolve) => {
      Modal.confirm({
        title: '当前文件未保存',
        content: '是否先保存后再关闭？',
        okText: '保存并关闭',
        cancelText: '直接关闭',
        onOk: async () => {
          await saveCurrentFile()
          if (canSave.value) {
            resolve(false)
            return
          }
          await closePathsDirectly(uniquePaths)
          resolve(true)
        },
        onCancel: async () => {
          await closePathsDirectly(uniquePaths)
          resolve(true)
        }
      })
    })
    return
  }

  await closePathsDirectly(uniquePaths)
}

const closeRecentByPath = async (path) => {
  await closeWithUnsavedReminder([path], false)
}

const getRecentContextTargets = (actionKey, basePath) => {
  const list = recentFiles.value.map((item) => item.path)
  const baseIndex = list.indexOf(basePath)
  if (baseIndex < 0) return []

  if (actionKey === 'close-current' || actionKey === 'save-close-current') {
    return [basePath]
  }
  if (actionKey === 'close-all' || actionKey === 'save-close-all') {
    return list
  }
  if (actionKey === 'close-right' || actionKey === 'save-close-right') {
    return list.slice(baseIndex + 1)
  }
  return []
}

const handleRecentContextAction = async (actionKey, basePath) => {
  const targets = getRecentContextTargets(actionKey, basePath)
  if (!targets.length) return
  const saveFirst = actionKey.startsWith('save-')
  await closeWithUnsavedReminder(targets, saveFirst)
}

const handleOverflowMenuAction = async (actionKey) => {
  const key = String(actionKey || '')
  if (key.startsWith('open::')) {
    const path = key.slice(6)
    if (path) await openPath(path)
    return
  }

  if (key === 'close-all') {
    await closeWithUnsavedReminder(recentFiles.value.map((item) => item.path), false)
    return
  }

  if (key === 'save-close-all') {
    await closeWithUnsavedReminder(recentFiles.value.map((item) => item.path), true)
  }
}

const handleMoreAction = async (actionKey) => {
  if (actionKey === 'publish') {
    await openPublishModal()
    return
  }

  if (actionKey === 'unpublish') {
    await handleUnpublish()
    return
  }

  if (actionKey === 'rename') {
    openRenameModal()
    return
  }

  if (actionKey === 'delete') {
    confirmDeleteNode()
  }
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

const writeClipboardText = async (text) => {
  const value = String(text ?? '')
  if (!value) return

  if (window.isSecureContext && navigator?.clipboard?.writeText) {
    await navigator.clipboard.writeText(value)
    return
  }

  const textArea = document.createElement('textarea')
  textArea.value = value
  textArea.setAttribute('readonly', '')
  textArea.style.position = 'fixed'
  textArea.style.top = '-9999px'
  textArea.style.left = '-9999px'
  document.body.appendChild(textArea)
  textArea.focus()
  textArea.select()

  let copied = false
  try {
    copied = document.execCommand('copy')
  } finally {
    document.body.removeChild(textArea)
  }

  if (!copied) {
    throw new Error('Clipboard copy failed')
  }
}

const copyCurrentFile = async () => {
  if (!selectedPath.value || selectedIsDir.value) return
  try {
    await writeClipboardText(fileContent.value)
    message.success('已复制')
    if (selectedPath.value === 'SKILL.md') await fetchPrompts()
  } catch {
    message.error('复制失败')
  }
}

const copyExternalId = async () => {
  if (!selectedExternalId.value) return
  try {
    await writeClipboardText(selectedExternalId.value)
    message.success('external_id 已复制')
  } catch {
    message.error('复制 external_id 失败')
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
          await writeClipboardText(previewContent.value)
          message.success('已复制渲染后的内容')
        } catch {
          message.error('复制失败')
        }
      }
    })
    return
  }
  
  try {
    await writeClipboardText(previewContent.value)
    message.success('已复制渲染后的内容')
  } catch {
    message.error('复制失败')
  }
}

const openPromptTestModal = async () => {
  if (!selectedPath.value || selectedIsDir.value) return
  await loadPromptTestCapability()
  if (!promptTestForm.model_spec) {
    promptTestForm.model_spec = promptTestCapability.default_model || configStore.config?.default_model || ''
  }
  promptTestModalVisible.value = true
}

const runPromptTest = async () => {
  if (!selectedPath.value || selectedIsDir.value) return
  if (missingVariableNames.value.length > 0) {
    message.warning(`变量尚未填写完整：${missingVariableNames.value.join('、')}`)
    return
  }

  testingPrompt.value = true
  try {
    const payload = {
      path: selectedPath.value,
      content: fileContent.value,
      variables: { ...variableInputValues.value },
      model_spec: promptTestForm.model_spec || promptTestCapability.default_model || configStore.config?.default_model || ''
    }
    const result = await promptApi.testPrompt(payload)
    promptTestResult.value = result?.data || null
    promptTestModalVisible.value = false
    message.success('测试完成')
  } catch (error) {
    const detail = error?.response?.data?.detail
    if (detail?.missing_variables?.length) {
      message.error(`存在未赋值变量：${detail.missing_variables.join('、')}`)
    } else if (detail?.issues?.length) {
      message.error(detail.issues.join('；'))
    } else if (typeof detail === 'string' && detail) {
      message.error(detail)
    } else {
      message.error('测试失败')
    }
  } finally {
    testingPrompt.value = false
  }
}

const copyPromptTestResult = async () => {
  const text = String(promptTestResult.value?.response || '')
  if (!text) return
  try {
    await writeClipboardText(text)
    message.success('测试结果已复制')
  } catch {
    message.error('复制测试结果失败')
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

const openCreateModal = (isDir, targetNode = null) => {
  createFileName.value = ''
  createFileNameError.value = ''
  createForm.content = ''
  createForm.isDir = isDir
  const basePath = targetNode?.path || selectedPath.value
  const baseIsDir = targetNode ? !!targetNode.is_dir : selectedIsDir.value
  if (basePath && baseIsDir) {
    createForm.parentPath = basePath
  } else if (basePath) {
    createForm.parentPath = getParentPath(basePath)
  } else {
    createForm.parentPath = ''
  }
  createModalVisible.value = true
}

const openRenameModal = (targetNode = null) => {
  const path = targetNode?.path || selectedPath.value
  if (!path) return
  const isDir = targetNode ? !!targetNode.is_dir : selectedIsDir.value
  const publishedTemplates = myPublishedTemplates.value.filter((t) => {
    if (isDir) {
      return t.source_path && t.source_path.startsWith(`${path}/`)
    }
    return t.source_path === path
  })
  if (publishedTemplates.length > 0) {
    message.warning('该节点包含已发布模板，请先取消发布后再重命名')
    return
  }
  renameForm.path = path
  renameForm.isDir = isDir
  renameFileName.value = getPathName(path)
  renameFileNameError.value = ''
  renameModalVisible.value = true
}

const handleRenameNode = async () => {
  const newName = renameFileName.value.trim()
  if (!newName) {
    renameFileNameError.value = '请输入新名称'
    return
  }
  if (newName.includes('/')) {
    renameFileNameError.value = '名称不能包含 /'
    return
  }

  const oldPath = renameForm.path
  const parentPath = getParentPath(oldPath)
  const newPath = parentPath ? `${parentPath}/${newName}` : newName
  if (newPath === oldPath) {
    renameModalVisible.value = false
    return
  }

  const allPaths = getAllPaths(treeData.value)
  if (allPaths.includes(newPath)) {
    renameFileNameError.value = '目标名称已存在'
    return
  }

  renameFileNameError.value = ''
  renamingNode.value = true
  try {
    await promptApi.renamePromptNode({
      old_path: oldPath,
      new_path: newPath
    })
    const isDir = !!renameForm.isDir
    const latestSelectedPath = remapPathByRename(selectedPath.value, oldPath, newPath, isDir)
    selectedPath.value = latestSelectedPath
    selectedTreeKeys.value = latestSelectedPath ? [latestSelectedPath] : []
    recentFiles.value = recentFiles.value
      .map((item) => ({ ...item, path: remapPathByRename(item.path, oldPath, newPath, isDir) }))
      .filter((item, index, arr) => arr.findIndex((x) => x.path === item.path) === index)
    myPublishedTemplates.value = myPublishedTemplates.value.map((tpl) => ({
      ...tpl,
      source_path: remapPathByRename(tpl.source_path, oldPath, newPath, isDir)
    }))

    renameModalVisible.value = false
    await reloadTree()
    const targetPath = remapPathByRename(selectedPath.value || newPath, oldPath, newPath, isDir) || newPath
    await openPath(targetPath)
    message.success('重命名成功')
  } catch (error) {
    const detail = error?.response?.data?.detail
    if (typeof detail === 'string' && detail) {
      message.error(detail)
    } else {
      message.error('重命名失败')
    }
  } finally {
    renamingNode.value = false
  }
}

const getAllPaths = (nodes) => {
  const paths = []
  for (const node of nodes) {
    paths.push(node.path || node.key)
    if (node.children) {
      paths.push(...getAllPaths(node.children))
    }
  }
  return paths
}

const handleCreateNode = async () => {
  const fileName = createFileName.value.trim()
  if (!fileName) {
    createFileNameError.value = createForm.isDir ? '请输入目录名称' : '请输入文件名称'
    return
  }
  
  const fullPath = createForm.parentPath ? `${createForm.parentPath}/${fileName}` : fileName
  
  const allPaths = getAllPaths(treeData.value)
  if (allPaths.includes(fullPath)) {
    createFileNameError.value = createForm.isDir ? '该目录名称已存在' : '该文件名称已存在'
    return
  }
  
  createFileNameError.value = ''
  creatingNode.value = true
  try {
    await promptApi.createPromptFile({
      path: fullPath,
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

const confirmDeleteNode = (targetNode = null) => {
  const targetPath = targetNode?.path || selectedPath.value
  if (!targetPath) return

  const isDir = targetNode ? !!targetNode.is_dir : selectedIsDir.value
  const publishedTemplates = myPublishedTemplates.value.filter(t => {
    if (isDir) {
      return t.source_path && t.source_path.startsWith(targetPath + '/')
    }
    return t.source_path === targetPath
  })
  
  let warningContent = `将永久删除: ${targetPath}`
  if (publishedTemplates.length > 0) {
    const templateNames = publishedTemplates.map(t => t.name).join('、')
    if (isDir) {
      warningContent = `将永久删除文件夹: ${targetPath}，同时会删除已发布的社区模板: ${templateNames}`
    } else {
      warningContent = `将永久删除: ${targetPath}，同时会删除已发布的社区模板「${templateNames}」`
    }
  } else if (isDir) {
    warningContent = `将永久删除文件夹: ${targetPath} 及其所有内容`
  }
  
  Modal.confirm({
    title: '确认删除？',
    content: warningContent,
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      try {
        for (const template of publishedTemplates) {
          await deleteTemplate(template.id)
        }
        await promptApi.deletePromptFile(targetPath)
        if (selectedPath.value === targetPath || selectedPath.value.startsWith(`${targetPath}/`)) {
          resetFileState()
        }
        await reloadTree()
        await loadMyTemplates()
        message.success('已删除')
      } catch {
        message.error('删除失败')
      }
    }
  })
}

const handleTreeContextAction = (key, node) => {
  if (key === 'new-file') {
    openCreateModal(false, node)
    return
  }
  if (key === 'new-dir') {
    openCreateModal(true, node)
    return
  }
  if (key === 'rename') {
    openRenameModal(node)
    return
  }
  if (key === 'delete') {
    confirmDeleteNode(node)
  }
}

const openPublishModal = async () => {
  if (!selectedPath.value || selectedIsDir.value) return
  const fileName = selectedPath.value.split('/').pop().replace(/\.[^.]+$/, '')
  publishForm.name = fileName
  publishForm.category = 'writing'
  publishForm.description = ''
  publishForm.tags = []
  publishForm.isOfficial = false
  publishedTemplateId.value = ''

  const existing = publishedTemplate.value
  if (existing) {
    try {
      const data = await communityGetMyTemplates({ community_type: 'prompt' })
      const template = (data.list || []).find(t => t.source_path === selectedPath.value)
      if (template) {
        publishForm.name = template.name
        publishForm.category = template.category
        publishForm.description = template.description || ''
        publishForm.tags = template.tags || []
        publishForm.isOfficial = template.is_official || false
        publishedTemplateId.value = template.id
      }
    } catch (error) {
      console.error('获取模板信息失败:', error)
    }
  }

  publishModalVisible.value = true
}

const handleUnpublish = async () => {
  if (!publishedTemplate.value) return
  
  unpublishing.value = true
  try {
    await communityUnpublish(publishedTemplate.value.id)
    message.success('已取消发布')
    await loadMyTemplates()
  } catch {
    message.error('取消发布失败')
  } finally {
    unpublishing.value = false
  }
}

const handlePublishToMarket = async () => {
  if (!publishForm.name || !fileContent.value) {
    message.error('请填写模板名称')
    return
  }
  publishing.value = true
  try {
    const variables = variableList.value.map(v => ({
      name: v.name,
      type: 'string',
      default: variableInputValues.value[v.name] || '',
      description: ''
    }))

    const payload = {
      name: publishForm.name,
      category: publishForm.category,
      description: publishForm.description,
      tags: publishForm.tags,
      content: fileContent.value,
      variables: variables,
      is_public: true,
      is_official: publishForm.isOfficial,
      source_path: selectedPath.value
    }

    if (publishedTemplateId.value) {
      await communityUpdateTemplate(publishedTemplateId.value, payload)
      message.success('重新发布成功！模板已更新')
    } else {
      await communityPublishPrompt(payload)
      message.success('发布成功！可在社区中查看')
    }
    publishModalVisible.value = false
    await loadMyTemplates()
  } catch (error) {
    message.error('发布失败')
  } finally {
    publishing.value = false
  }
}

const handleImportUpload = async ({ file, onSuccess, onError }) => {
  importing.value = true
  try {
    message.info('暂不支持导入 ZIP 文件')
    onSuccess?.({})
  } catch (e) {
    message.error('导入失败')
    onError?.(e)
  } finally {
    importing.value = false
  }
}

const loadMyTemplates = async () => {
  try {
    const data = await communityGetMyTemplates({ community_type: 'prompt' })
    myPublishedTemplates.value = data.list || []
  } catch (error) {
    console.error('获取我的模板失败:', error)
  }
}

onMounted(async () => {
  await reloadTree()
  await loadMyTemplates()
  await loadPromptTestCapability()
})

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
    &.compact-bar {
      padding: 6px 12px 4px;
      gap: 12px;
      align-items: center;

      .panel-title {
        min-width: 0;
        display: flex;
        align-items: baseline;
        gap: 8px;

        h2 {
          margin: 0;
          font-size: 15px;
          font-weight: 600;
          color: var(--gray-800);
          white-space: nowrap;
        }

        .panel-subtitle {
          font-size: 12px;
          color: var(--gray-500);
          white-space: nowrap;
        }
      }

      .panel-center-metrics {
        flex: 1;
        min-width: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        flex-wrap: wrap;

        .metric-pill {
          height: 22px;
          padding: 0 8px;
          border-radius: 999px;
          border: 1px solid var(--gray-200);
          background: var(--gray-50);
          color: var(--gray-600);
          font-size: 11px;
          display: inline-flex;
          align-items: center;
          line-height: 1;

          &.warning {
            border-color: #fbbf24;
            background: #fffbeb;
            color: #b45309;
          }
        }
      }

      .panel-right-hint {
        width: 280px;
        min-width: 160px;
        display: flex;
        justify-content: flex-end;

        .active-file {
          font-family: monospace;
          font-size: 12px;
          color: var(--gray-500);
          max-width: 100%;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;

          &.muted {
            color: var(--gray-400);
          }
        }
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
  width: 250px;
  border-right: 1px solid @border-color;
  background: linear-gradient(180deg, #f8fbff 0%, #f4f8ff 100%);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;

  .variable-header {
    padding: 10px 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid @border-color;
    background-color: rgba(255, 255, 255, 0.85);

    .variable-header-main {
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 3px;
    }

    .variable-title {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      font-weight: 600;
      color: var(--gray-700);
      line-height: 1;
    }

    .variable-meta {
      font-size: 11px;
      color: var(--gray-500);
      white-space: nowrap;
    }

    .variable-header-actions {
      flex-shrink: 0;
      display: flex;
      align-items: center;

      .refresh-btn {
        width: 24px;
        height: 24px;
        border: 1px solid var(--gray-200);
        border-radius: 8px;
        background: var(--gray-0);
        color: var(--gray-500);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0;
        cursor: pointer;
        transition: all 0.2s ease;

        &:hover:not(:disabled) {
          color: var(--main-700);
          border-color: var(--main-300);
          background: var(--main-50);
        }

        &:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
      }
    }
  }

  .variable-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    padding: 8px;
  }

  .variable-tip {
    display: flex;
    margin-bottom: 12px;
    padding: 8px;
    border-radius: 10px;
    background: linear-gradient(180deg, #f8fbff 0%, #f5f8ff 100%);
    border: 1px solid #dbe7fb;
    color: var(--gray-500);
    font-size: 12px;
    line-height: 1.5;

    code {
      display: inline;
      white-space: nowrap;
      font-family: 'Fira Code', 'Monaco', monospace;
      padding: 1px 5px;
      border-radius: 6px;
      background: rgba(59, 130, 246, 0.08);
      border: 1px solid rgba(59, 130, 246, 0.18);
      color: #2558a9;
    }
  }

  .variable-list {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding-right: 2px;

    &::-webkit-scrollbar {
      width: 5px;
    }

    &::-webkit-scrollbar-thumb {
      background: rgba(148, 163, 184, 0.5);
      border-radius: 999px;
    }
  }

  .variable-item {
    background-color: var(--gray-0);
    border: 1px solid @border-color;
    border-radius: 10px;
    padding: 9px;
    display: flex;
    flex-direction: column;
    gap: 7px;
    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
    transition: border-color 0.2s ease, box-shadow 0.2s ease;

    &:hover {
      border-color: var(--main-200);
      box-shadow: 0 8px 22px rgba(59, 130, 246, 0.08);
    }

    .variable-info {
      display: flex;
      justify-content: space-between;
      align-items: center;

        .variable-name {
          font-size: 12px;
          font-weight: 600;
          color: var(--gray-700);
          font-family: monospace;
          max-width: 130px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
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
            background-color: #eef3ff;
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

  .prompt-test-card {
    margin-top: 10px;
    padding: 10px;
    border: 1px solid #d8e6f8;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.8);
    display: flex;
    flex-direction: column;
    gap: 8px;

    .prompt-test-toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }

    .prompt-test-status {
      font-size: 11px;
      padding: 1px 7px;
      border-radius: 999px;
      border: 1px solid #cfd8e3;
      color: var(--gray-500);
      background: #f7f9fc;

      &.ready {
        border-color: #bfe7cf;
        color: #1f7a4a;
        background: #effbf3;
      }

      &.error {
        border-color: #f2c9c9;
        color: #b73b3b;
        background: #fff3f3;
      }
    }

    .prompt-test-issues {
      color: #b45309;
      font-size: 12px;
      line-height: 1.45;
    }

    .prompt-test-btn {
      min-width: 92px;
      border-radius: 8px;
      border-color: var(--color-primary-500);
      background: var(--color-primary-500);
      color: var(--gray-0);
      box-shadow: none;
      font-weight: 500;
      transition: all 0.2s ease;

      &:hover,
      &:focus {
        border-color: var(--color-primary-700);
        background: var(--color-primary-700);
        color: var(--gray-0);
      }

      &:active {
        border-color: var(--color-primary-900);
        background: var(--color-primary-900);
        color: var(--gray-0);
      }

      &[disabled],
      &[disabled]:hover {
        border-color: var(--gray-200);
        background: var(--gray-100);
        color: var(--gray-400);
      }
    }
  }

}

/* 文件 tree */
.tree-container {
  width: 280px;
  border-right: 1px solid @border-color;
  background: linear-gradient(180deg, #f8fafc 0%, #f5f7fb 100%);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;

  .tree-header {
    padding: 12px 14px;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    border-bottom: 1px solid @border-color;
    background-color: rgba(255, 255, 255, 0.72);

    .tree-title-wrap {
      display: flex;
      flex-direction: column;
      gap: 4px;
      min-width: 0;
    }

    .label-row {
      display: flex;
      align-items: center;
      gap: 6px;
      color: var(--main-800);
    }

    .label {
      font-size: 13px;
      font-weight: 700;
      color: var(--gray-800);
    }

    .tree-meta {
      font-size: 11px;
      color: var(--gray-500);
    }

    .tree-actions {
      display: flex;
      gap: 6px;
      padding-top: 1px;

      .tree-action-btn {
        width: 26px;
        height: 26px;
        border: 1px solid var(--gray-200);
        background: var(--gray-0);
        border-radius: 8px;
        padding: 0;
        cursor: pointer;
        color: var(--gray-500);
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s ease;

        &:hover {
          color: var(--main-800);
          border-color: var(--main-300);
          background: var(--main-50);
        }
      }
    }
  }

  .tree-search {
    padding: 10px 12px 0;

    :deep(.ant-input-affix-wrapper) {
      border-radius: 9px;
      border-color: var(--gray-200);
      background: var(--gray-0);
      box-shadow: none;

      &:focus,
      &-focused {
        border-color: var(--main-300);
      }
    }

    :deep(.ant-input-prefix) {
      color: var(--gray-400);
      margin-right: 6px;
      display: flex;
      align-items: center;
    }
  }

  .tree-content {
    flex: 1;
    overflow-y: auto;
    padding: 10px;

    .tree-surface {
      background: var(--gray-0);
      border: 1px solid var(--gray-200);
      border-radius: 12px;
      padding: 8px 6px;
      min-height: 100%;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
    }

    .tree-empty {
      padding: 22px 0 10px;
    }
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
    padding: 8px 12px;
    border-bottom: 1px solid @border-color;
    display: flex;
    flex-direction: column;
    gap: 8px;
    background-color: var(--gray-0);
    flex-shrink: 0;

    .header-main {
      display: flex;
      align-items: center;
      width: 100%;
      min-width: 0;
    }

    .current-path {
      display: flex;
      align-items: center;
      gap: 8px;
      font-family: monospace;
      font-size: 12px;
      color: var(--gray-500);
      min-width: 0;
      width: 100%;
      overflow: hidden;

      > svg {
        flex-shrink: 0;
      }

      > span {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .breadcrumb-segment {
        border: none;
        background: transparent;
        color: var(--gray-500);
        font-size: 12px;
        cursor: pointer;
        padding: 0;
        font-family: inherit;
        max-width: 220px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;

        &::after {
          content: '/';
          margin-left: 8px;
          color: var(--gray-300);
        }

        &:hover {
          color: var(--main-700);
        }

        &.active {
          color: var(--gray-700);
          font-weight: 600;
        }

        &:last-child::after {
          display: none;
        }
      }

      .save-hint {
        color: #f59e0b;
        font-size: 10px;
        margin-left: 4px;
        flex-shrink: 0;
      }
    }

    .header-top-row {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      width: 100%;
    }

    .external-id-inline {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      max-width: min(44vw, 460px);
      margin-right: auto;
      border: 1px solid #dbe8f8;
      background: linear-gradient(90deg, #f8fbff 0%, #f4f8ff 100%);
      border-radius: 999px;
      padding: 0 6px;
      height: 24px;

      .external-id-label {
        font-size: 10px;
        color: #4f6f93;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        flex-shrink: 0;
      }

      .external-id-value {
        display: inline-block;
        max-width: 100%;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-family: 'Fira Code', 'Monaco', monospace;
        font-size: 11px;
        color: #1f4e7b;
        background: rgba(255, 255, 255, 0.7);
        border-radius: 999px;
        padding: 1px 7px;
      }

      .external-id-copy-btn {
        border: none;
        background: transparent;
        color: #2c5d8f;
        width: 20px;
        height: 20px;
        border-radius: 999px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0;
        cursor: pointer;
        flex-shrink: 0;

        &:hover {
          background: rgba(59, 130, 246, 0.1);
          color: #174978;
        }
      }
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 6px;
      min-width: 0;
      flex-wrap: wrap;
      justify-content: flex-end;

      :deep(.ant-btn) {
        flex-shrink: 0;
      }

      :deep(.toolbar-btn) {
        height: 28px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 500;
        border-width: 1px;
        box-shadow: none;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        transition: all 0.2s ease;
      }

      :deep(.toolbar-btn.toolbar-btn-secondary) {
        background: var(--main-0);
        border-color: var(--color-primary-100);
        color: var(--color-primary-700);
      }

      :deep(.toolbar-btn.toolbar-btn-secondary:hover),
      :deep(.toolbar-btn.toolbar-btn-secondary:focus) {
        background: var(--color-primary-50);
        border-color: var(--color-primary-500);
        color: var(--color-primary-700);
      }

      :deep(.toolbar-btn.toolbar-btn-secondary:active) {
        background: var(--color-primary-100);
        border-color: var(--color-primary-700);
        color: var(--color-primary-900);
      }

      :deep(.toolbar-btn.toolbar-btn-primary) {
        background: var(--color-primary-500);
        border-color: var(--color-primary-500);
        color: var(--gray-0);
      }

      :deep(.toolbar-btn.toolbar-btn-primary:hover),
      :deep(.toolbar-btn.toolbar-btn-primary:focus) {
        background: var(--color-primary-700);
        border-color: var(--color-primary-700);
        color: var(--gray-0);
      }

      :deep(.toolbar-btn.toolbar-btn-primary:active) {
        background: var(--color-primary-900);
        border-color: var(--color-primary-900);
        color: var(--gray-0);
      }

      :deep(.toolbar-btn.ant-btn[disabled]),
      :deep(.toolbar-btn.ant-btn[disabled]:hover) {
        background: var(--gray-100);
        border-color: var(--gray-200);
        color: var(--gray-400);
      }
    }

    .opened-files-row {
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      min-width: 0;

      .recent-title {
        color: var(--gray-400);
        font-size: 12px;
        white-space: nowrap;
        flex-shrink: 0;
      }

      .recent-files-scroll {
        display: flex;
        align-items: center;
        gap: 6px;
        min-width: 0;
        flex: 1;
        overflow-x: auto;
        overflow-y: hidden;
        padding-bottom: 2px;

        &::-webkit-scrollbar {
          height: 4px;
        }

        &::-webkit-scrollbar-thumb {
          background: rgba(148, 163, 184, 0.55);
          border-radius: 999px;
        }
      }
    }

    .recent-item {
      border: 1px solid var(--gray-200);
      background: #f8fafc;
      color: var(--gray-600);
      border-radius: 999px;
      height: 24px;
      padding: 0 6px 0 10px;
      font-size: 12px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
      max-width: 200px;
      flex-shrink: 0;

      .name {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .recent-close {
        width: 16px;
        height: 16px;
        border: none;
        background: transparent;
        color: var(--gray-400);
        border-radius: 999px;
        font-size: 12px;
        line-height: 1;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        flex-shrink: 0;

        &:hover {
          color: var(--gray-700);
          background: rgba(15, 23, 42, 0.08);
        }
      }

      &:hover {
        border-color: var(--main-200);
        color: var(--main-700);
        background: #eff6ff;
      }

      &.active {
        border-color: var(--main-300);
        color: var(--main-800);
        background: #eaf4ff;
      }
    }

    .recent-overflow-trigger {
      height: 24px;
      border-radius: 999px;
      border: 1px solid var(--gray-300);
      background: var(--gray-0);
      color: var(--gray-500);
      padding: 0 10px;
      font-size: 12px;
      cursor: pointer;
      flex-shrink: 0;

      &:hover {
        border-color: var(--main-300);
        color: var(--main-700);
      }
    }

    .view-toggle-btn {
      min-width: 72px;
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

.variable-tags-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.switch-hint {
  margin-left: 8px;
  font-size: 12px;
  color: var(--gray-600);
}

.parent-path-display {
  font-family: monospace;
  font-size: 13px;
  color: #666;
  background: #f5f5f5;
  padding: 4px 8px;
  border-radius: 4px;
}

.error-text {
  color: var(--color-error-700);
  font-size: 12px;
  margin-top: 4px;
}

.prompt-test-variable-alert {
  border-radius: 10px;
  padding: 10px 12px;
  border: 1px solid transparent;

  .alert-title {
    font-size: 13px;
    font-weight: 600;
    line-height: 1.35;
  }

  .alert-names {
    margin-top: 4px;
    font-size: 12px;
    line-height: 1.5;
    word-break: break-word;
  }

  .alert-tip {
    margin-top: 4px;
    font-size: 12px;
    line-height: 1.4;
  }

  &.is-warning {
    background: var(--color-warning-50);
    border-color: var(--color-warning-100);

    .alert-title {
      color: var(--color-warning-900);
    }

    .alert-names,
    .alert-tip {
      color: var(--color-warning-700);
    }
  }

  &.is-ready {
    background: var(--color-success-50);
    border-color: color-mix(in srgb, var(--color-success-100) 75%, var(--main-0));

    .alert-title {
      color: var(--color-success-900);
    }

    .alert-tip {
      color: var(--color-success-700);
    }
  }
}

  .editor-test-panel {
  border-top: 1px solid @border-color;
  background: linear-gradient(180deg, #f9fbff 0%, #f5f8ff 100%);
  min-height: 150px;
  max-height: 240px;
  display: flex;
  flex-direction: column;

  &.empty {
    min-height: 92px;
    max-height: 92px;
  }

  .editor-test-panel-header {
    height: 32px;
    padding: 0 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid #dfe8f4;
    font-size: 13px;
    font-weight: 600;
    color: var(--gray-700);
    flex-shrink: 0;

    .editor-test-panel-header-actions {
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }

    code {
      font-family: 'Fira Code', 'Monaco', monospace;
      font-size: 12px;
      color: #1f4e7b;
      background: #f3f8ff;
      border: 1px solid #dce9f9;
      border-radius: 999px;
      padding: 1px 8px;
      font-weight: 500;
      max-width: 58%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .editor-test-copy-btn {
      border: 1px solid #cfdceb;
      background: #ffffff;
      color: #2b5f92;
      height: 22px;
      border-radius: 999px;
      padding: 0 8px;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      cursor: pointer;
      flex-shrink: 0;

      &:hover:not(:disabled) {
        border-color: #aac7e8;
        background: #f3f8ff;
        color: #1f4e7b;
      }

      &:disabled {
        opacity: 0.55;
        cursor: not-allowed;
      }
    }
  }

  .editor-test-panel-body {
    flex: 1;
    min-height: 0;
    overflow: auto;
    display: flex;
    align-items: flex-start;
    justify-content: flex-start;

    pre {
      margin: 0;
      width: 100%;
      padding: 8px 14px 12px;
      font-size: 14px;
      line-height: 1.65;
      white-space: pre-wrap;
      word-break: break-word;
      color: var(--gray-800);
      font-family: 'Fira Code', 'Monaco', monospace;
    }
  }

  .editor-test-panel-empty {
    flex: 1;
    display: flex;
    align-items: center;
    padding: 0 12px;
    font-size: 13px;
    color: var(--gray-500);
  }
}

.tree-node-title {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:global(.publish-modal-wrap .ant-modal-content) {
  border: 1px solid var(--color-primary-100);
  border-radius: 12px;
  box-shadow: 0 14px 30px var(--shadow-2);
  overflow: hidden;
}

:global(.publish-modal-wrap .ant-modal-header) {
  border-bottom: 1px solid var(--gray-200);
  background: linear-gradient(180deg, var(--main-5) 0%, var(--main-20) 100%);
  padding: 14px 20px;
}

:global(.publish-modal-wrap .ant-modal-title) {
  color: var(--color-secondary-900);
  font-weight: 600;
}

:global(.publish-modal-wrap .ant-modal-body) {
  padding: 16px 20px 8px;
}

:global(.publish-modal-wrap .publish-form .ant-form-item-label > label) {
  color: var(--color-secondary-700);
  font-weight: 500;
}

:global(.publish-modal-wrap .publish-form .ant-input),
:global(.publish-modal-wrap .publish-form .ant-input-affix-wrapper),
:global(.publish-modal-wrap .publish-form .ant-select-selector) {
  border-radius: 8px;
  border-color: var(--gray-200) !important;
  box-shadow: none !important;
}

:global(.publish-modal-wrap .publish-form .ant-input:hover),
:global(.publish-modal-wrap .publish-form .ant-input-affix-wrapper:hover),
:global(.publish-modal-wrap .publish-form .ant-select:not(.ant-select-disabled):hover .ant-select-selector) {
  border-color: var(--color-primary-500) !important;
}

:global(.publish-modal-wrap .publish-form .ant-input:focus),
:global(.publish-modal-wrap .publish-form .ant-input-affix-wrapper-focused),
:global(.publish-modal-wrap .publish-form .ant-select-focused .ant-select-selector) {
  border-color: var(--color-primary-500) !important;
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-primary-500) 20%, transparent) !important;
}

:global(.publish-modal-wrap .publish-form .ant-switch-checked) {
  background: var(--color-primary-500);
}

:global(.publish-modal-wrap .publish-form .ant-tag) {
  border-radius: 999px;
}

:global(.publish-modal-wrap .ant-modal-footer) {
  border-top: 1px solid var(--gray-200);
  padding: 10px 20px 14px;
}

:global(.publish-modal-wrap .ant-modal-footer .ant-btn) {
  border-radius: 8px;
  box-shadow: none;
}

:global(.publish-modal-wrap .ant-modal-footer .ant-btn-default) {
  background: var(--main-0);
  border-color: var(--color-primary-100);
  color: var(--color-primary-700);
}

:global(.publish-modal-wrap .ant-modal-footer .ant-btn-default:hover),
:global(.publish-modal-wrap .ant-modal-footer .ant-btn-default:focus) {
  background: var(--color-primary-50);
  border-color: var(--color-primary-500);
  color: var(--color-primary-700);
}

:global(.publish-modal-wrap .ant-modal-footer .ant-btn-default:active) {
  background: var(--color-primary-100);
  border-color: var(--color-primary-700);
  color: var(--color-primary-900);
}

:global(.publish-modal-wrap .ant-modal-footer .ant-btn-primary) {
  background: var(--color-primary-500);
  border-color: var(--color-primary-500);
  color: var(--gray-0);
}

:global(.publish-modal-wrap .ant-modal-footer .ant-btn-primary:hover),
:global(.publish-modal-wrap .ant-modal-footer .ant-btn-primary:focus) {
  background: var(--color-primary-700);
  border-color: var(--color-primary-700);
  color: var(--gray-0);
}

:global(.publish-modal-wrap .ant-modal-footer .ant-btn-primary:active) {
  background: var(--color-primary-900);
  border-color: var(--color-primary-900);
  color: var(--gray-0);
}

:global(.publish-modal-wrap .ant-modal-footer .ant-btn[disabled]),
:global(.publish-modal-wrap .ant-modal-footer .ant-btn[disabled]:hover) {
  background: var(--gray-100);
  border-color: var(--gray-200);
  color: var(--gray-400);
}

:global(.prompt-test-modal-wrap .ant-modal-content) {
  border: 1px solid var(--color-primary-100);
  border-radius: 12px;
  box-shadow: 0 14px 30px var(--shadow-2);
  overflow: hidden;
}

:global(.prompt-test-modal-wrap .ant-modal-header) {
  border-bottom: 1px solid var(--gray-200);
  background: linear-gradient(180deg, var(--main-5) 0%, var(--main-20) 100%);
  padding: 14px 20px;
}

:global(.prompt-test-modal-wrap .ant-modal-title) {
  color: var(--color-secondary-900);
  font-weight: 600;
}

:global(.prompt-test-modal-wrap .ant-modal-body) {
  padding: 16px 20px 8px;
}

:global(.prompt-test-modal-wrap .ant-form-item-label > label) {
  color: var(--color-secondary-700);
  font-weight: 500;
}

:global(.prompt-test-modal-wrap .ant-select-selector) {
  border-radius: 8px !important;
  border-color: var(--gray-200) !important;
  box-shadow: none !important;
  transition: all 0.2s ease;
}

:global(.prompt-test-modal-wrap .ant-select:not(.ant-select-disabled):hover .ant-select-selector) {
  border-color: var(--color-primary-500) !important;
}

:global(.prompt-test-modal-wrap .ant-select-focused .ant-select-selector) {
  border-color: var(--color-primary-500) !important;
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-primary-500) 20%, transparent) !important;
}

:global(.prompt-test-modal-wrap .ant-select-selection-placeholder) {
  color: var(--gray-500);
}

:global(.prompt-test-modal-wrap .ant-modal-footer) {
  border-top: 1px solid var(--gray-200);
  padding: 10px 20px 14px;
}

:global(.prompt-test-modal-wrap .ant-modal-footer .ant-btn) {
  border-radius: 8px;
  box-shadow: none;
}

:global(.prompt-test-modal-wrap .ant-modal-footer .ant-btn-default) {
  background: var(--main-0);
  border-color: var(--color-primary-100);
  color: var(--color-primary-700);
}

:global(.prompt-test-modal-wrap .ant-modal-footer .ant-btn-default:hover),
:global(.prompt-test-modal-wrap .ant-modal-footer .ant-btn-default:focus) {
  background: var(--color-primary-50);
  border-color: var(--color-primary-500);
  color: var(--color-primary-700);
}

:global(.prompt-test-modal-wrap .ant-modal-footer .ant-btn-primary) {
  background: var(--color-primary-500);
  border-color: var(--color-primary-500);
  color: var(--gray-0);
}

:global(.prompt-test-modal-wrap .ant-modal-footer .ant-btn-primary:hover),
:global(.prompt-test-modal-wrap .ant-modal-footer .ant-btn-primary:focus) {
  background: var(--color-primary-700);
  border-color: var(--color-primary-700);
  color: var(--gray-0);
}

:global(.prompt-test-modal-wrap .ant-modal-footer .ant-btn-primary:active) {
  background: var(--color-primary-900);
  border-color: var(--color-primary-900);
  color: var(--gray-0);
}

:global(.prompt-test-modal-wrap .ant-modal-footer .ant-btn[disabled]),
:global(.prompt-test-modal-wrap .ant-modal-footer .ant-btn[disabled]:hover) {
  background: var(--gray-100);
  border-color: var(--gray-200);
  color: var(--gray-400);
}

:global(.prompt-test-model-dropdown) {
  border: 1px solid var(--color-primary-100);
  border-radius: 10px;
  box-shadow: 0 8px 20px var(--shadow-2);
  overflow: hidden;
}

:global(.prompt-test-model-dropdown .ant-select-item-option) {
  color: var(--color-secondary-700);
}

:global(.prompt-test-model-dropdown .ant-select-item-option-active:not(.ant-select-item-option-disabled)) {
  background: var(--color-primary-50);
}

:global(.prompt-test-model-dropdown .ant-select-item-option-selected:not(.ant-select-item-option-disabled)) {
  background: color-mix(in srgb, var(--color-primary-50) 65%, var(--main-0));
  color: var(--color-primary-700);
  font-weight: 600;
}

:global(.prompt-manager-more-menu .ant-dropdown-menu) {
  padding: 6px;
  border: 1px solid var(--color-primary-100);
  border-radius: 10px;
  background: var(--main-0);
  box-shadow: 0 8px 20px var(--shadow-2);
}

:global(.prompt-manager-more-menu .ant-dropdown-menu-item) {
  border-radius: 7px;
  color: var(--color-secondary-700);
  transition: all 0.2s ease;
}

:global(.prompt-manager-more-menu .ant-dropdown-menu-item:hover),
:global(.prompt-manager-more-menu .ant-dropdown-menu-item-active) {
  background: var(--color-primary-50);
  color: var(--color-primary-700);
}

:global(.prompt-manager-more-menu .ant-dropdown-menu-item-danger) {
  color: var(--color-error-700);
}

:global(.prompt-manager-more-menu .ant-dropdown-menu-item-danger:hover),
:global(.prompt-manager-more-menu .ant-dropdown-menu-item-danger.ant-dropdown-menu-item-active) {
  background: var(--color-error-50);
  color: var(--color-error-700);
}

:global(.prompt-manager-more-menu .ant-dropdown-menu-item-disabled),
:global(.prompt-manager-more-menu .ant-dropdown-menu-item-disabled:hover) {
  color: var(--gray-400);
  background: transparent;
}

:global(.prompt-manager-more-menu .ant-dropdown-menu-item-divider) {
  margin: 6px 0;
  background: var(--gray-200);
}

@media (max-width: 1000px) {
  .main-panel .panel-top-bar.compact-bar {
    .panel-subtitle,
    .panel-right-hint {
      display: none;
    }

    .panel-center-metrics {
      justify-content: flex-start;
    }
  }

  .sidebar-list {
    width: 220px;
  }
  .tree-container {
    width: 220px;
  }

  .editor-container .editor-header {
    gap: 10px;

    .header-top-row {
      justify-content: flex-start;
    }

    .header-actions {
      width: 100%;
      flex-wrap: wrap;
      justify-content: flex-start;

      .external-id-inline {
        max-width: 100%;
        margin-right: 0;
      }
    }

    .opened-files-row {
      align-items: flex-start;
      flex-direction: column;

      .recent-files-scroll {
        width: 100%;
      }
    }
  }
}
</style>
