<template>
  <div class="chat-container">
    <ChatSidebarComponent
      :current-chat-id="currentChatId"
      :chats-list="chatsList"
      :is-sidebar-open="chatUIStore.isSidebarOpen"
      :is-initial-render="localUIState.isInitialRender"
      :single-mode="props.singleMode"
      :selected-agent-id="currentLlmId"
      :is-creating-new-chat="chatUIStore.creatingNewChat"
      :has-more-chats="hasMoreChats"
      :is-loading-more="isLoadingMoreChats"
      @create-chat="createNewChat"
      @select-chat="selectChat"
      @delete-chat="deleteChat"
      @rename-chat="renameChat"
      @toggle-pin="togglePinChat"
      @toggle-sidebar="toggleSidebar"
      @open-agent-modal="openAgentModal"
      @load-more-chats="loadMoreChats"
      :class="{
        'sidebar-open': chatUIStore.isSidebarOpen,
        'no-transition': localUIState.isInitialRender
      }"
    />
    <div class="chat">
      <div class="chat-header">
        <div class="header__left">
          <slot name="header-left" class="nav-btn"></slot>
          <div
            type="button"
            class="llm-nav-btn"
            v-if="!chatUIStore.isSidebarOpen"
            @click="toggleSidebar"
          >
            <PanelLeftOpen class="nav-btn-icon" size="18" />
          </div>
          <div
            type="button"
            class="llm-nav-btn"
            v-if="!chatUIStore.isSidebarOpen"
            :class="{ 'is-disabled': chatUIStore.creatingNewChat }"
            @click="createNewChat"
          >
            <LoaderCircle
              v-if="chatUIStore.creatingNewChat"
              class="nav-btn-icon loading-icon"
              size="18"
            />
            <MessageCirclePlus v-else class="nav-btn-icon" size="16" />
            <span class="text">新对话</span>
          </div>
          <div v-if="!props.singleMode" class="llm-nav-btn model-selector-wrapper">
            <ModelSelectorComponent
              :placeholder="currentModelSpec || '选择模型'"
              :model-spec="currentModelSpec"
              @select-model="handleModelSelect"
            />
          </div>
        </div>
        <div class="header__right">
          <!-- AgentState 显示按钮已移动到输入框底部 -->
          <slot name="header-right"></slot>
        </div>
      </div>

      <div class="chat-content-container">
        <!-- Main Chat Area -->
        <div class="chat-main" ref="chatMainContainer">
          <div class="chat-box" ref="messagesContainer">
            <div class="conv-box" v-for="(conv, index) in conversations" :key="index">
              <LLMMessageComponent
                v-for="(message, msgIndex) in conv.messages"
                :message="message"
                :key="msgIndex"
                :is-processing="
                  isProcessing &&
                  conv.status === 'streaming' &&
                  msgIndex === conv.messages.length - 1
                "
                :show-refs="showMsgRefs(message)"
                @retry="retryMessage(message)"
              >
              </LLMMessageComponent>
              <!-- 显示对话最后一个消息使用的模型 -->
              <RefsComponent
                v-if="shouldShowRefs(conv)"
                :message="getLastMessage(conv)"
                :show-refs="['model', 'copy', 'sources']"
                :is-latest-message="false"
                :sources="getConversationSources(conv)"
              />
            </div>

            <!-- 生成中的加载状态 - 增强条件支持主聊天和resume流程 -->
            <div class="generating-status" v-if="isProcessing && conversations.length > 0">
              <div class="generating-indicator">
                <div class="loading-dots">
                  <div></div>
                  <div></div>
                  <div></div>
                </div>
                <span class="generating-text">正在生成回复...</span>
              </div>
            </div>
          </div>
          <div class="bottom" :class="{ 'start-screen': !conversations.length }">
            <div class="input-main-area">
              <!-- 加载状态：加载消息 -->
              <div v-if="isLoadingMessages" class="chat-loading">
                <div class="loading-spinner"></div>
                <span>正在加载消息...</span>
              </div>

              <!-- 打招呼区域 - 在输入框上方 -->
              <div v-if="!conversations.length" class="chat-examples-input">
                <h1 v-if="currentModelSpec">👋 您好，我是 {{ currentModelSpec }}！</h1>
                <h1 v-else>👋 请先选择一个大模型开始对话</h1>
              </div>

              <LLMInputArea
                ref="messageInputRef"
                v-model="userInput"
                :is-loading="isProcessing"
                :disabled="!currentModelSpec"
                :send-button-disabled="(!userInput || !currentModelSpec || hasUnassignedVariables) && !isProcessing"
                placeholder="输入问题..."
                :supports-file-upload="supportsFileUpload"
                :agent-id="currentLlmId"
                :thread-id="currentChatId"
                :ensure-thread="ensureActiveThread"
                :has-state-content="hasAgentStateContent"
                :is-panel-open="isAgentPanelOpen"
                @send="handleSendOrStop"
                @attachment-changed="handleAgentStateRefresh"
                @toggle-panel="toggleAgentPanel"
              >
                <template #input-actions-right>
                  <a-tooltip title="提示词库">
                    <button class="prompt-toggle-btn" @click="togglePromptPanel">
                      <FolderOpen :size="16" />
                    </button>
                  </a-tooltip>
                </template>
              </LLMInputArea>

              <!-- 示例问题 -->
              <div
                class="example-questions"
                v-if="!conversations.length && exampleQuestions.length > 0"
              >
                <div class="example-chips">
                  <div
                    v-for="question in exampleQuestions"
                    :key="question.id"
                    class="example-chip"
                    @click="handleExampleClick(question.text)"
                  >
                    {{ question.text }}
                  </div>
                </div>
              </div>

              <div class="bottom-actions" v-else>
                <p class="note">请注意辨别内容的可靠性</p>
              </div>
            </div>

          </div>
        </div>
        <div v-if="isPromptPanelOpen" class="prompt-sidebar">
          <div class="prompt-panel-header">
            <span class="prompt-panel-title">提示词库</span>
            <button class="prompt-panel-close" @click="togglePromptPanel">
              <X :size="14" />
            </button>
          </div>
          <div class="prompt-panel-content">
            <div class="prompt-tree-container">
              <a-tree
                v-model:expandedKeys="promptExpandedKeys"
                :tree-data="promptTreeData"
                :selected-keys="selectedPromptPath ? [selectedPromptPath] : []"
                :show-icon="true"
                @select="handlePromptSelect"
              >
                <template #icon="{ isLeaf }">
                  <FileText v-if="isLeaf" :size="14" />
                  <FolderOpen v-else :size="14" />
                </template>
              </a-tree>
            </div>
            <div v-if="promptVariables.length > 0" class="prompt-variables">
              <div class="prompt-variables-header">
                <span>变量</span>
                <div class="prompt-variables-actions">
                  <a-button size="small" @click="copyRenderedPrompt">
                    渲染并复制
                  </a-button>
                  <a-button size="small" type="primary" :disabled="hasUnassignedVariables" @click="usePromptWithVariables">
                    应用
                  </a-button>
                </div>
              </div>
              <div class="prompt-variable-list">
                <div
                  v-for="variable in promptVariables"
                  :key="variable.name"
                  class="prompt-variable-item"
                >
                  <div class="prompt-variable-info">
                    <span class="prompt-variable-name">{{ variable.name }}</span>
                    <div class="prompt-variable-actions">
                      <a-tooltip title="插入到输入框" placement="top">
                        <button @click="insertPromptVariableToInput(variable.name)" class="action-btn">
                          <Plus :size="12" />
                        </button>
                      </a-tooltip>
                      <a-tooltip title="删除变量" placement="top">
                        <button @click="removePromptVariable(variable.name)" class="action-btn delete">
                          <Trash :size="12" />
                        </button>
                      </a-tooltip>
                    </div>
                  </div>
                  <a-input
                    :value="promptVariableValues[variable.name]"
                    @update:value="(val) => updatePromptVariableValue(variable.name, val)"
                    placeholder="变量值"
                    size="small"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch, nextTick, computed, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'
import LLMInputArea from '@/components/LLMInputArea.vue'
import LLMMessageComponent from '@/components/LLMMessageComponent.vue'
import ChatSidebarComponent from '@/components/ChatSidebarComponent.vue'
import RefsComponent from '@/components/RefsComponent.vue'
import ModelSelectorComponent from '@/components/ModelSelectorComponent.vue'
import { PanelLeftOpen, MessageCirclePlus, LoaderCircle, ChevronDown, Bot, FolderOpen, FileText, Plus, Trash, X } from 'lucide-vue-next'
import { handleChatError, handleValidationError } from '@/utils/errorHandler'
import { ScrollController } from '@/utils/scrollController'
import { AgentValidator } from '@/utils/agentValidator'
// import { useAgentStore } from '@/stores/agent'
import { useChatUIStore } from '@/stores/chatUI'
import { storeToRefs } from 'pinia'
import { MessageProcessor } from '@/utils/messageProcessor'
import { threadApi, llmThreadApi, llmApi, promptApi } from '@/apis'
import { useApproval } from '@/composables/useApproval'
import { useLLMStreamHandler } from '@/composables/useLLMStreamHandler'

// ==================== PROPS & EMITS ====================
const props = defineProps({
  agentId: { type: String, default: '' },
  modelSpec: { type: String, default: '' },
  singleMode: { type: Boolean, default: true }
})
const emit = defineEmits(['open-config', 'open-agent-modal', 'select-model'])

// ==================== STORE MANAGEMENT ====================
// const agentStore = useAgentStore()
const chatUIStore = useChatUIStore()
// const {
//   agents,
//   selectedAgentId,
//   defaultAgentId,
//   selectedAgentConfigId,
//   agentConfig,
//   configurableItems,
//   availableKnowledgeBases,
//   availableMcps
// } = storeToRefs(agentStore)

// ==================== LOCAL CHAT & UI STATE ====================
const userInput = ref('')

const promptTreeData = ref([])
const promptExpandedKeys = ref([])
const selectedPromptPath = ref('')
const promptVariables = ref([])
const promptVariableValues = ref({})
const isPromptPanelOpen = ref(false)

const hasUnassignedVariables = computed(() => {
  if (promptVariables.value.length === 0) return false
  return promptVariables.value.some(
    v => !promptVariableValues.value[v.name] || promptVariableValues.value[v.name].trim() === ''
  )
})

const normalizePromptTree = (nodes) =>
  (nodes || []).map((node) => ({
    title: node.name,
    key: node.path,
    isLeaf: !node.is_dir,
    path: node.path,
    is_dir: node.is_dir,
    children: node.is_dir ? normalizePromptTree(node.children || []) : undefined
  }))

const loadPromptTree = async () => {
  try {
    const result = await promptApi.getPromptTree()
    promptTreeData.value = normalizePromptTree(result?.data || [])
    const expandKeys = (nodes) =>
      nodes.flatMap((node) => (node.is_dir ? [node.key, ...expandKeys(node.children || [])] : []))
    promptExpandedKeys.value = expandKeys(promptTreeData.value)
  } catch (error) {
    console.error('加载提示词目录失败:', error)
  }
}

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

const handlePromptSelect = async (keys, info) => {
  if (!keys?.length) {
    selectedPromptPath.value = ''
    promptVariables.value = []
    promptVariableValues.value = {}
    return
  }
  const node = info?.node || {}
  const path = node.path || node.key
  if (node.is_dir) {
    selectedPromptPath.value = ''
    promptVariables.value = []
    promptVariableValues.value = {}
    return
  }
  selectedPromptPath.value = path
  try {
    const result = await promptApi.getPromptFile(path)
    const content = result?.data?.content || ''
    userInput.value = content
    const vars = parseVariablesFromContent(content)
    promptVariables.value = vars.map(name => ({ name, value: '' }))
    promptVariableValues.value = {}
    vars.forEach(name => {
      promptVariableValues.value[name] = ''
    })
  } catch (error) {
    console.error('读取文件失败:', error)
    message.error('读取文件失败')
  }
}

const updatePromptVariableValue = (name, value) => {
  promptVariableValues.value[name] = value
}

const insertPromptVariableToInput = (name) => {
  userInput.value += `{{${name}}}`
}

const removePromptVariable = (name) => {
  promptVariables.value = promptVariables.value.filter(v => v.name !== name)
  delete promptVariableValues.value[name]
}

const togglePromptPanel = () => {
  isPromptPanelOpen.value = !isPromptPanelOpen.value
  if (isPromptPanelOpen.value && promptTreeData.value.length === 0) {
    loadPromptTree()
  }
}

const usePromptWithVariables = () => {
  const unassignedVars = promptVariables.value.filter(
    v => !promptVariableValues.value[v.name] || promptVariableValues.value[v.name].trim() === ''
  )
  
  if (unassignedVars.length > 0) {
    message.warning(`以下变量未赋值: ${unassignedVars.map(v => v.name).join(', ')}`)
  }

  let content = userInput.value
  promptVariables.value.forEach(variable => {
    const value = promptVariableValues.value[variable.name]
    if (value !== undefined && value !== '') {
      const regex = new RegExp(`\\{\\{${variable.name}\\}\\}`, 'g')
      content = content.replace(regex, value)
    }
  })
  
  userInput.value = content
  promptVariables.value = []
  promptVariableValues.value = {}
  message.success('已应用变量')
}

const renderPromptWithVariables = () => {
  let content = userInput.value
  promptVariables.value.forEach(variable => {
    const value = promptVariableValues.value[variable.name]
    if (value !== undefined && value !== '') {
      const regex = new RegExp(`\\{\\{${variable.name}\\}\\}`, 'g')
      content = content.replace(regex, value)
    }
  })
  return content
}

const copyRenderedPrompt = async () => {
  const unassignedVars = promptVariables.value.filter(
    v => !promptVariableValues.value[v.name] || promptVariableValues.value[v.name].trim() === ''
  )
  
  if (unassignedVars.length > 0) {
    message.warning(`以下变量未赋值: ${unassignedVars.map(v => v.name).join(', ')}`)
  }
  
  const renderedContent = renderPromptWithVariables()
  try {
    await navigator.clipboard.writeText(renderedContent)
    message.success('已复制渲染后的内容')
  } catch (error) {
    message.error('复制失败')
  }
}

const useRunsApi =
  import.meta.env.VITE_USE_RUNS_API === 'true' &&
  localStorage.getItem('force_legacy_stream') !== 'true'

const ACTIVE_RUN_STORAGE_TTL_MS = 60 * 60 * 1000
const ACTIVE_RUN_CLIENT_ID = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
const typingChunkQueue = []
let typingAnimationFrameId = null
let typingLastFrameTs = 0
let pendingTypingChars = 0
const MIN_TYPING_CPS = 32
const MAX_TYPING_CPS = 320
const TYPING_BACKLOG_HIGH_WATERMARK = 500

// 从智能体元数据获取示例问题
const exampleQuestions = computed(() => {
  let examples = []
  return examples.map((text, index) => ({
    id: index + 1,
    text: text
  }))
})

// Keep per-thread streaming scratch data in a consistent shape.
const createOnGoingConvState = () => ({
  msgChunks: {},
  currentRequestKey: null,
  currentAssistantKey: null,
  toolCallBuffers: {}
})

// 业务状态（保留在组件本地）
const chatState = reactive({
  currentThreadId: null,
  // 以threadId为键的线程状态
  threadStates: {}
})

// 组件级别的线程和消息状态
const threads = ref([])
const threadMessages = ref({})
const hasMoreChats = ref(true) // 是否还有更多对话可加载
const isLoadingMoreChats = ref(false) // 加载更多对话中

// 本地 UI 状态（仅在本组件使用）
const localUIState = reactive({
  isInitialRender: true
})

// 当前选中的模型
const currentModelSpec = ref(props.modelSpec || '')

// Agent Panel State
const isAgentPanelOpen = ref(false)
const isResizing = ref(false)
const panelRatio = ref(0.4) // 面板宽度比例 (0-1)
const panelWrapperRef = ref(null) // 直接操作 DOM
const minPanelRatio = 0.3 // 最小比例 30%
const maxPanelRatio = 0.6 // 最大比例 60%
let panelContainerWidth = 0

// ==================== COMPUTED PROPERTIES ====================
const currentLlmId = computed(() => {
  if (props.modelSpec) {
    return props.modelSpec.split('/').pop()
  } else {
    return 'gpt-3.5-turbo'
  }
})

const currentLlmName = computed(() => {
  const llm = currentLlm.value
  return llm ? llm.modelSpec: '智能体'
})

const currentLlm= computed(() => {
  if (!currentLlmId.value) return null
  return props
})
const chatsList = computed(() => threads.value || [])
const currentChatId = computed(() => chatState.currentThreadId)
const currentThread = computed(() => {
  if (!currentChatId.value) return null
  return threads.value.find((thread) => thread.id === currentChatId.value) || null
})

// 检查当前智能体是否支持文件上传
const supportsFileUpload = computed(() => {
  if (!currentLlm.value.modelSpec) return false
  const capabilities = currentLlm.value.capabilities || []
  return capabilities.includes('file_upload')
})
const supportsTodo = computed(() => {
  if (!currentLlm.value) return false
  const capabilities = currentLlm.value.capabilities || []
  return capabilities.includes('todo')
})

const supportsFiles = computed(() => {
  if (!currentLlm.value) return false
  const capabilities = currentLlm.value.capabilities || []
  return capabilities.includes('files')
})

// AgentState 相关计算属性
const currentAgentState = computed(() => {
  return currentChatId.value ? getThreadState(currentChatId.value)?.agentState || null : null
})

const countFiles = (files) => {
  if (!files) return 0
  if (Array.isArray(files)) {
    return files.reduce(
      (c, item) => c + (item && typeof item === 'object' ? Object.keys(item).length : 0),
      0
    )
  }
  return typeof files === 'object' ? Object.keys(files).length : 0
}

const hasAgentStateContent = computed(() => {
  const s = currentAgentState.value
  if (!s) return false
  const todoCount = Array.isArray(s.todos) ? s.todos.length : 0
  const fileCount = countFiles(s.files)
  return todoCount > 0 || fileCount > 0
})

// 监听 hasAgentStateContent 从 false → true 时，自动展开面板
watch(hasAgentStateContent, (newVal, oldVal) => {
  if (newVal && !oldVal) {
    // 从无状态变为有状态时，自动展开面板
    isAgentPanelOpen.value = true
  }
})

// const mentionConfig = computed(() => {
//   const rawFiles = currentAgentState.value?.files || {}
//   const files = []

//   // 处理 files - 兼容字典格式 {"/path/file": {content: [...]}} 和旧数组格式
//   if (typeof rawFiles === 'object' && !Array.isArray(rawFiles) && rawFiles !== null) {
//     // 新格式：字典格式 {"/attachments/xxx/file.md": {...}}
//     Object.entries(rawFiles).forEach(([filePath, fileData]) => {
//       files.push({
//         path: filePath,
//         ...fileData
//       })
//     })
//   } else if (Array.isArray(rawFiles)) {
//     // 旧格式：数组格式
//     rawFiles.forEach((item) => {
//       if (typeof item === 'object' && item !== null) {
//         Object.entries(item).forEach(([filePath, fileData]) => {
//           files.push({
//             path: filePath,
//             ...fileData
//           })
//         })
//       }
//     })
//   }

  // Filter KBs and MCPs based on agent config
  // const configItems = configurableItems.value || {}
  // const currentConfig = agentConfig.value || {}
  // const allowedKbNames = new Set()
  // const allowedMcpNames = new Set()

  // Object.entries(configItems).forEach(([key, item]) => {
  //   const kind = item?.template_metadata?.kind
  //   const val = currentConfig[key]

  //   if (Array.isArray(val)) {
  //     if (kind === 'knowledges') {
  //       val.forEach((v) => allowedKbNames.add(v))
  //     } else if (kind === 'mcps') {
  //       val.forEach((v) => allowedMcpNames.add(v))
  //     }
  //   }
  // })

  // const knowledgeBases = availableKnowledgeBases.value.filter((kb) => allowedKbNames.has(kb.name))
  // const mcps = availableMcps.value.filter((mcp) => allowedMcpNames.has(mcp.name))

  // if (!files.length && !knowledgeBases.length && !mcps.length) return null

//   return {
//     files,
//     knowledgeBases,
//     mcps
//   }
// })

const currentThreadMessages = computed(() => threadMessages.value[currentChatId.value] || [])

// 计算是否显示Refs组件的条件
const shouldShowRefs = computed(() => {
  return (conv) => {
    return (
      getLastMessage(conv) &&
      conv.status !== 'streaming' &&
      !approvalState.showModal &&
      !(
        approvalState.threadId &&
        chatState.currentThreadId === approvalState.threadId &&
        isProcessing.value
      )
    )
  }
})

// 当前线程状态的computed属性
const currentThreadState = computed(() => {
  return getThreadState(currentChatId.value)
})

const onGoingConvMessages = computed(() => {
  const threadState = currentThreadState.value
  if (!threadState || !threadState.onGoingConv) return []

  const msgs = Object.values(threadState.onGoingConv.msgChunks).map(
    MessageProcessor.mergeMessageChunk
  )
  return msgs.length > 0
    ? MessageProcessor.convertToolResultToMessages(msgs).filter((msg) => msg.type !== 'tool')
    : []
})

const historyConversations = computed(() => {
  return MessageProcessor.convertServerHistoryToMessages(currentThreadMessages.value)
})

const conversations = computed(() => {
  const historyConvs = historyConversations.value

  // 如果有进行中的消息且线程状态显示正在流式处理，添加进行中的对话
  if (onGoingConvMessages.value.length > 0) {
    const onGoingConv = {
      messages: onGoingConvMessages.value,
      status: 'streaming'
    }
    return [...historyConvs, onGoingConv]
  }
  return historyConvs
})

const isLoadingMessages = computed(() => chatUIStore.isLoadingMessages)
const isStreaming = computed(() => {
  const threadState = currentThreadState.value
  return threadState ? threadState.isStreaming : false
})
const isProcessing = computed(() => isStreaming.value)

// ==================== SCROLL & RESIZE HANDLING ====================
// Update scroll controller to target .chat-main
const scrollController = new ScrollController('.chat-main')

onMounted(() => {
  nextTick(() => {
    // Update event listener to target .chat-main
    const chatMainContainer = document.querySelector('.chat-main')
    if (chatMainContainer) {
      chatMainContainer.addEventListener('scroll', scrollController.handleScroll, { passive: true })
    }
  })
  setTimeout(() => {
    localUIState.isInitialRender = false
  }, 300)
})

onUnmounted(() => {
  stopTypingRenderLoop()
  typingChunkQueue.length = 0
  pendingTypingChars = 0
  scrollController.cleanup()
  // 清理所有线程状态
  resetOnGoingConv()
})

// ==================== THREAD STATE MANAGEMENT ====================
// 获取指定线程的状态，如果不存在则创建
const getThreadState = (threadId) => {
  if (!threadId) return null
  if (!chatState.threadStates[threadId]) {
    chatState.threadStates[threadId] = {
      isStreaming: false,
      streamAbortController: null,
      runStreamAbortController: null,
      activeRunId: null,
      runLastSeq: '0',
      lastRetryableJobTry: null,
      onGoingConv: createOnGoingConvState(),
      agentState: null // 添加 agentState 字段
    }
  }
  return chatState.threadStates[threadId]
}

// 清理指定线程的状态
const cleanupThreadState = (threadId) => {
  if (!threadId) return
  const threadState = chatState.threadStates[threadId]
  if (threadState) {
    clearTypingQueueForThread(threadId)
    if (threadState.streamAbortController) {
      threadState.streamAbortController.abort()
    }
    if (threadState.runStreamAbortController) {
      threadState.runStreamAbortController.abort()
    }
    delete chatState.threadStates[threadId]
  }
}

// ==================== STREAM HANDLING LOGIC ====================
const resetOnGoingConv = (threadId = null) => {
  const targetThreadId = threadId || currentChatId.value

  if (targetThreadId) {
    // 清理指定线程的状态
    const threadState = getThreadState(targetThreadId)
    if (threadState) {
      clearTypingQueueForThread(targetThreadId)
      if (threadState.streamAbortController) {
        threadState.streamAbortController.abort()
        threadState.streamAbortController = null
      }
      if (threadState.runStreamAbortController) {
        threadState.runStreamAbortController.abort()
        threadState.runStreamAbortController = null
      }

      // 直接重置对话状态
      threadState.onGoingConv = createOnGoingConvState()
    }
  } else {
    // 如果没有当前线程，清理所有线程状态
    Object.keys(chatState.threadStates).forEach((tid) => {
      cleanupThreadState(tid)
    })
  }
}

// ==================== 线程管理方法 ====================
// 获取当前智能体的线程列表
const fetchThreads = async (agentId = null) => {
  const targetAgentId = agentId
  if (!targetAgentId) return

  chatUIStore.isLoadingThreads = true
  try {
    const fetchedThreads = await llmThreadApi.getThreads(targetAgentId, 100, 0)
    threads.value = fetchedThreads || []
    // 如果返回的数量小于limit，说明没有更多了
    hasMoreChats.value = fetchedThreads && fetchedThreads.length >= 100
  } catch (error) {
    console.error('Failed to fetch threads:', error)
    handleChatError(error, 'fetch')
    throw error
  } finally {
    chatUIStore.isLoadingThreads = false
  }
}

// 加载更多对话
const loadMoreChats = async () => {
  if (isLoadingMoreChats.value || !hasMoreChats.value) return

  const targetAgentId = currentLlmId.value
  if (!targetAgentId) return

  isLoadingMoreChats.value = true
  try {
    const offset = threads.value.length
    const fetchedThreads = await threadApi.getThreads(targetAgentId, 100, offset)
    if (fetchedThreads && fetchedThreads.length > 0) {
      // 去除重复的置顶对话（后端每次都返回所有置顶对话）
      const existingIds = new Set(threads.value.map((t) => t.id))
      const newThreads = fetchedThreads.filter((t) => !existingIds.has(t.id))

      threads.value = [...threads.value, ...newThreads]
      hasMoreChats.value = newThreads.length >= 100
    } else {
      hasMoreChats.value = false
    }
  } catch (error) {
    console.error('Failed to load more chats:', error)
    handleChatError(error, 'fetch')
  } finally {
    isLoadingMoreChats.value = false
  }
}

// 创建新线程
const createThread = async (llmId, title = '新的对话') => {
  if (!llmId) return null

  chatState.isCreatingThread = true
  try {
    const thread = await llmThreadApi.createThread(llmId, title)
    if (thread) {
      threads.value.unshift(thread)
      threadMessages.value[thread.id] = []
    }
    return thread
  } catch (error) {
    console.error('Failed to create thread:', error)
    handleChatError(error, 'create')
    throw error
  } finally {
    chatState.isCreatingThread = false
  }
}

// 删除线程
const deleteThread = async (threadId) => {
  if (!threadId) return

  chatState.isDeletingThread = true
  try {
    await llmThreadApi.deleteThread(threadId)
    threads.value = threads.value.filter((thread) => thread.id !== threadId)
    delete threadMessages.value[threadId]

    if (chatState.currentThreadId === threadId) {
      chatState.currentThreadId = null
    }
  } catch (error) {
    console.error('Failed to delete thread:', error)
    handleChatError(error, 'delete')
    throw error
  } finally {
    chatState.isDeletingThread = false
  }
}

// 更新线程标题
const updateThread = async (threadId, title, is_pinned) => {
  if (!threadId) return

  if (title) {
    const normalizedTitle = String(title).replace(/\s+/g, ' ').trim().slice(0, 255)
    if (!normalizedTitle) return

    chatState.isRenamingThread = true
    try {
      await llmThreadApi.updateThread(threadId, normalizedTitle, is_pinned)
      const thread = threads.value.find((t) => t.id === threadId)
      if (thread) {
        thread.title = normalizedTitle
        if (is_pinned !== undefined) {
          thread.is_pinned = is_pinned
        }
      }
    } catch (error) {
      console.error('Failed to update thread:', error)
      handleChatError(error, 'update')
      throw error
    } finally {
      chatState.isRenamingThread = false
    }
  } else if (is_pinned !== undefined) {
    // 只更新置顶状态
    try {
      await threadApi.updateThread(threadId, null, is_pinned)
      const thread = threads.value.find((t) => t.id === threadId)
      if (thread) {
        thread.is_pinned = is_pinned
      }
    } catch (error) {
      console.error('Failed to update thread pin status:', error)
      handleChatError(error, 'update')
      throw error
    }
  }
}

// 获取线程消息
const fetchThreadMessages = async ({ agentId, threadId, delay = 0 }) => {
  if (!threadId || !agentId) return

  // 如果指定了延迟，等待指定时间（用于确保后端数据库事务提交）
  if (delay > 0) {
    await new Promise((resolve) => setTimeout(resolve, delay))
  }
  console.log('agentId', agentId, 'threadId', threadId)
  try {
    const response = await llmApi.getLlmHistory(threadId)
    threadMessages.value[threadId] = response.history || []
  } catch (error) {
    handleChatError(error, 'load')
    throw error
  }
}

const RUN_TERMINAL_STATUSES = new Set(['completed', 'failed', 'cancelled', 'interrupted'])

const getActiveRunStorageKey = (threadId) => `active_run:${threadId}`

const normalizeRunSeq = (value) => {
  if (value === undefined || value === null) return '0'
  const text = String(value).trim()
  return text || '0'
}

const parseRunSeq = (value) => {
  const text = normalizeRunSeq(value)
  if (text.includes('-')) {
    const [majorRaw, minorRaw] = text.split('-', 2)
    let major = 0n
    let minor = 0n
    try {
      major = BigInt(majorRaw || '0')
      minor = BigInt(minorRaw || '0')
    } catch {
      return { kind: 'legacy', value: 0 }
    }
    return { kind: 'stream', major, minor }
  }
  const numberValue = Number.parseInt(text, 10)
  if (!Number.isNaN(numberValue)) {
    return { kind: 'legacy', value: numberValue }
  }
  return { kind: 'legacy', value: 0 }
}

const compareRunSeq = (incoming, current) => {
  const left = parseRunSeq(incoming)
  const right = parseRunSeq(current)

  if (left.kind === 'stream' && right.kind === 'stream') {
    if (left.major > right.major) return 1
    if (left.major < right.major) return -1
    if (left.minor > right.minor) return 1
    if (left.minor < right.minor) return -1
    return 0
  }

  if (left.kind === 'legacy' && right.kind === 'legacy') {
    return left.value - right.value
  }

  if (left.kind === 'stream' && right.kind === 'legacy') return 1
  return -1
}

const saveActiveRunSnapshot = (threadId, runId, lastSeq = '0') => {
  if (!threadId || !runId) return
  localStorage.setItem(
    getActiveRunStorageKey(threadId),
    JSON.stringify({
      run_id: runId,
      last_seq: normalizeRunSeq(lastSeq),
      created_at: Date.now(),
      client_id: ACTIVE_RUN_CLIENT_ID
    })
  )
}

const loadActiveRunSnapshot = (threadId) => {
  if (!threadId) return null
  try {
    const raw = localStorage.getItem(getActiveRunStorageKey(threadId))
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

const clearActiveRunSnapshot = (threadId) => {
  if (!threadId) return
  localStorage.removeItem(getActiveRunStorageKey(threadId))
}

const splitChars = (text) => {
  if (typeof text !== 'string' || !text) return []
  return Array.from(text)
}

const calcTypingCps = () => {
  if (pendingTypingChars <= 0) return MIN_TYPING_CPS
  const ratio = Math.min(1, pendingTypingChars / TYPING_BACKLOG_HIGH_WATERMARK)
  return Math.round(MIN_TYPING_CPS + ratio * (MAX_TYPING_CPS - MIN_TYPING_CPS))
}

const scheduleTypingRender = () => {
  if (typingAnimationFrameId !== null) return
  if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
    typingAnimationFrameId = window.requestAnimationFrame(drainTypingQueue)
  } else {
    typingAnimationFrameId = setTimeout(() => {
      typingAnimationFrameId = null
      drainTypingQueue(Date.now())
    }, 16)
  }
}

const stopTypingRenderLoop = () => {
  if (typingAnimationFrameId === null) return
  if (typeof window !== 'undefined' && typeof window.cancelAnimationFrame === 'function') {
    window.cancelAnimationFrame(typingAnimationFrameId)
  } else {
    clearTimeout(typingAnimationFrameId)
  }
  typingAnimationFrameId = null
  typingLastFrameTs = 0
}

const enqueueLoadingChunkForTyping = (threadId, chunk) => {
  if (!threadId || !chunk) return
  if (chunk.status !== 'loading') {
    typingChunkQueue.push({ threadId, chunk, isChar: false })
    scheduleTypingRender()
    return
  }

  const msg = chunk.msg || {}
  const msgType = String(msg.type || '').toLowerCase()
  const isToolMessage = msgType === 'tool' || msgType.includes('tool')
  const streamText = typeof chunk.response === 'string' ? chunk.response : ''
  const contentChars = !isToolMessage ? splitChars(streamText) : []
  if (contentChars.length === 0) {
    typingChunkQueue.push({ threadId, chunk, isChar: false })
    scheduleTypingRender()
    return
  }

  for (const char of contentChars) {
    typingChunkQueue.push({
      threadId,
      isChar: true,
      chunk: {
        ...chunk,
        response: char,
        msg: {
          ...msg,
          content: char
        }
      }
    })
  }
  pendingTypingChars += contentChars.length
  scheduleTypingRender()
}

// 将队列按 threadId 分区，对匹配项执行回调，返回移除的字符数
const partitionTypingQueue = (threadId, onMatch = null) => {
  const remaining = []
  let charCount = 0
  for (const item of typingChunkQueue) {
    if (item.threadId === threadId) {
      if (onMatch) onMatch(item)
      if (item.isChar) charCount += 1
    } else {
      remaining.push(item)
    }
  }
  typingChunkQueue.length = 0
  typingChunkQueue.push(...remaining)
  pendingTypingChars = Math.max(0, pendingTypingChars - charCount)
  typingChunkQueue.length === 0 ? stopTypingRenderLoop() : scheduleTypingRender()
}

const clearTypingQueueForThread = (threadId) => {
  if (!threadId || typingChunkQueue.length === 0) return
  partitionTypingQueue(threadId)
}

const flushTypingQueueForThread = (threadId) => {
  if (!threadId || typingChunkQueue.length === 0) return
  partitionTypingQueue(threadId, (item) => handleStreamChunk(item.chunk, threadId))
}

function drainTypingQueue(frameTs = Date.now()) {
  typingAnimationFrameId = null
  if (typingChunkQueue.length === 0) {
    typingLastFrameTs = 0
    return
  }

  if (!typingLastFrameTs) {
    typingLastFrameTs = frameTs
  }

  const elapsedSeconds = Math.max(0.001, (frameTs - typingLastFrameTs) / 1000)
  typingLastFrameTs = frameTs
  const cps = calcTypingCps()
  let budget = Math.max(1, Math.floor(elapsedSeconds * cps))

  while (budget > 0 && typingChunkQueue.length > 0) {
    const item = typingChunkQueue.shift()
    if (!item) break
    handleStreamChunk(item.chunk, item.threadId)
    if (item.isChar) {
      pendingTypingChars = Math.max(0, pendingTypingChars - 1)
    }
    budget -= 1
  }

  if (typingChunkQueue.length > 0) {
    scheduleTypingRender()
  } else {
    typingLastFrameTs = 0
  }
}

const processRunSseResponse = async (response, onEvent) => {
  if (!response || !response.body) return
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let eventType = 'message'
  let dataLines = []

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const rawLine of lines) {
        const line = rawLine.replace(/\r$/, '')
        if (!line) {
          if (dataLines.length > 0) {
            const dataText = dataLines.join('\n')
            try {
              const parsed = JSON.parse(dataText)
              onEvent(eventType, parsed)
            } catch (e) {
              console.warn('Failed to parse run SSE data:', e, dataText)
            }
          }
          eventType = 'message'
          dataLines = []
          continue
        }
        if (line.startsWith('event:')) {
          eventType = line.slice(6).trim() || 'message'
        } else if (line.startsWith('data:')) {
          dataLines.push(line.slice(5).trim())
        }
      }
    }
    if (dataLines.length > 0) {
      const dataText = dataLines.join('\n')
      try {
        const parsed = JSON.parse(dataText)
        onEvent(eventType, parsed)
      } catch (e) {
        console.warn('Failed to parse trailing run SSE data:', e, dataText)
      }
    }
  } finally {
    try {
      reader.releaseLock()
    } catch {
      // ignore
    }
  }
}

const stopRunStreamSubscription = (threadId) => {
  const ts = getThreadState(threadId)
  if (!ts) return
  if (ts.runStreamAbortController) {
    ts.runStreamAbortController.abort()
    ts.runStreamAbortController = null
  }
}

const startRunStream = async (threadId, runId, afterSeq = '0') => {
  if (!threadId || !runId || !useRunsApi) return
  const ts = getThreadState(threadId)
  if (!ts) return

  stopRunStreamSubscription(threadId)
  const runController = new AbortController()
  ts.runStreamAbortController = runController
  ts.activeRunId = runId
  ts.runLastSeq = normalizeRunSeq(afterSeq)
  ts.lastRetryableJobTry = null
  ts.isStreaming = true
  saveActiveRunSnapshot(threadId, runId, ts.runLastSeq)

  try {
    const response = await agentApi.streamAgentRunEvents(runId, ts.runLastSeq, {
      signal: runController.signal
    })
    if (!response.ok) {
      throw new Error(`SSE response not ok: ${response.status}`)
    }

    await processRunSseResponse(response, (event, data) => {
      if (!data || ts.activeRunId !== runId) return

      if (data.seq !== undefined && data.seq !== null) {
        const incomingSeq = normalizeRunSeq(data.seq)
        if (compareRunSeq(incomingSeq, ts.runLastSeq) <= 0) return
        ts.runLastSeq = incomingSeq
        saveActiveRunSnapshot(threadId, runId, incomingSeq)
      }

      if (event === 'heartbeat') return

      const payload = data.payload || {}
      const isRetryableError = event === 'error' && payload?.chunk?.retryable === true
      if (isRetryableError) {
        const parsedJobTry = Number.parseInt(payload?.chunk?.job_try, 10)
        const retryJobTry = Number.isNaN(parsedJobTry) ? null : parsedJobTry
        if (retryJobTry !== null && ts.lastRetryableJobTry === retryJobTry) {
          return
        }
        ts.lastRetryableJobTry = retryJobTry
        console.warn('Run encountered retryable error, waiting for worker retry', {
          threadId,
          runId,
          retryJobTry,
          errorType: payload?.chunk?.error_type
        })
        return
      }

      if (Array.isArray(payload.items)) {
        payload.items.forEach((chunk) => {
          enqueueLoadingChunkForTyping(threadId, chunk)
        })
      } else if (payload.chunk) {
        enqueueLoadingChunkForTyping(threadId, payload.chunk)
      }

      if (event === 'close') {
        flushTypingQueueForThread(threadId)
        ts.isStreaming = false
        if (RUN_TERMINAL_STATUSES.has(data.status)) {
          ts.activeRunId = null
          ts.lastRetryableJobTry = null
          clearActiveRunSnapshot(threadId)
        } else if (ts.activeRunId === runId) {
          window.setTimeout(() => {
            if (ts.activeRunId === runId && !ts.runStreamAbortController) {
              void startRunStream(threadId, runId, ts.runLastSeq)
            }
          }, 300)
        }
      }

      if (
        event === 'finished' ||
        event === 'error' ||
        event === 'interrupted' ||
        event === 'ask_user_question_required'
      ) {
        flushTypingQueueForThread(threadId)
        ts.isStreaming = false
        ts.activeRunId = null
        ts.lastRetryableJobTry = null
        clearActiveRunSnapshot(threadId)
        fetchThreadMessages({ agentId: currentLlmId.value, threadId, delay: 300 }).finally(() => {
          resetOnGoingConv(threadId)
          scrollController.scrollToBottom()
        })
      }
    })
  } catch (error) {
    if (error?.name !== 'AbortError') {
      console.error('Run SSE stream error:', error)
      handleChatError(error, 'stream')
      if (ts.activeRunId === runId) {
        window.setTimeout(() => {
          if (ts.activeRunId === runId && !ts.runStreamAbortController) {
            void startRunStream(threadId, runId, ts.runLastSeq)
          }
        }, 500)
      }
    }
  } finally {
    if (ts.runStreamAbortController === runController) {
      ts.runStreamAbortController = null
    }
    if (!ts.activeRunId) {
      ts.isStreaming = false
    }
  }
}

const resumeActiveRunForThread = async (threadId) => {
  if (!useRunsApi || !threadId) return
  const ts = getThreadState(threadId)
  if (!ts || ts.runStreamAbortController) return

  const snapshot = loadActiveRunSnapshot(threadId)
  if (snapshot?.run_id) {
    if (Date.now() - Number(snapshot.created_at || 0) > ACTIVE_RUN_STORAGE_TTL_MS) {
      clearActiveRunSnapshot(threadId)
    } else {
      try {
        const runRes = await agentApi.getAgentRun(snapshot.run_id)
        const run = runRes?.run
        if (run && !RUN_TERMINAL_STATUSES.has(run.status)) {
          await startRunStream(threadId, run.id, snapshot.last_seq || '0')
          return
        }
      } catch {
        // ignore
      }
      clearActiveRunSnapshot(threadId)
    }
  }

  try {
    const active = await agentApi.getThreadActiveRun(threadId)
    const run = active?.run
    if (run && !RUN_TERMINAL_STATUSES.has(run.status)) {
      await startRunStream(threadId, run.id, 0)
      return
    }
  } catch (e) {
    console.warn('Failed to load active run for thread:', threadId, e)
  }

  ts.activeRunId = null
  ts.runLastSeq = '0'
  ts.isStreaming = false
  clearActiveRunSnapshot(threadId)
}

const ensureActiveThread = async (title = '新的对话') => {
  console.log('currentChahatId', currentChatId.value)
  if (currentChatId.value) return currentChatId.value
  try {
    const newThread = await createThread(currentLlmId.value, title || '新的对话')
    if (newThread) {
      chatState.currentThreadId = newThread.id
      return newThread.id
    }
  } catch {
    // createThread 已处理错误提示
    console.error('createThread 失败')
  }
  return null
}

// ==================== 审批功能管理 ====================
const { approvalState, handleApproval, processApprovalInStream } = useApproval({
  getThreadState,
  resetOnGoingConv,
  fetchThreadMessages
})

const { handleLLMResponse, handleStreamChunk } = useLLMStreamHandler({
  getThreadState,
  processApprovalInStream,
  currentLlmId,
  supportsTodo,
  supportsFiles
})

// 发送消息并处理流式响应
const sendMessage = async ({
  llmId,
  threadId,
  text,
  signal = undefined,
  imageData = undefined
}) => {
  if (!llmId || !threadId || !text) {
    const error = new Error('Missing agent, thread, or message text')
    handleChatError(error, 'send')
    return Promise.reject(error)
  }

  // 如果是新对话，用消息内容作为标题
  if ((threadMessages.value[threadId] || []).length === 0) {
    const autoTitle = text.replace(/\s+/g, ' ').trim().slice(0, 255)
    if (autoTitle) {
      void updateThread(threadId, autoTitle).catch(() => {})
    }
  }

  const requestData = {
    query: text,
    config: {
      thread_id: threadId,
      ...({})
    },
    meta: {
      model_spec: props.modelSpec
    }
  }

  // 如果有图片，添加到请求中
  if (imageData && imageData.imageContent) {
    requestData.image_content = imageData.imageContent
  }

  try {
    return await llmApi.sendLlmMessage(llmId, requestData, signal ? { signal } : undefined)
  } catch (error) {
    handleChatError(error, 'send')
    throw error
  }
}

// ==================== CHAT ACTIONS ====================
// 检查第一个对话是否为空
const isFirstChatEmpty = () => {
  if (threads.value.length === 0) return false
  const chatToReuse = getFirstNonPinnedChat(threads.value)
  const messages = threadMessages.value[chatToReuse.id]
  // 只有当消息已加载且为空时才返回 true
  return messages !== undefined && messages.length === 0
}

// 获取第一个非置顶的对话
const getFirstNonPinnedChat = (chatList) => {
  if (!chatList || chatList.length === 0) return null
  return chatList.find((chat) => !chat.is_pinned) || chatList[0]
}

// 如果第一个对话为空，直接切换到第一个非置顶对话
const switchToFirstChatIfEmpty = async () => {
  if (threads.value.length > 0 && isFirstChatEmpty()) {
    const chatToReuse = getFirstNonPinnedChat(threads.value)
    if (chatState.currentThreadId !== chatToReuse.id) {
      await selectChat(chatToReuse.id)
    }
    return true
  }
  return false
}

const createNewChat = async () => {
  // 如果第一个对话为空，直接切换到第一个对话而不是创建新对话
  if (await switchToFirstChatIfEmpty()) return

  chatUIStore.creatingNewChat = true
  try {
    const newThread = await createThread(currentLlmId.value, '新的对话')
    if (newThread) {
      // 中断之前线程的流式输出（如果存在）
      const previousThreadId = chatState.currentThreadId
      if (previousThreadId) {
        const previousThreadState = getThreadState(previousThreadId)
        if (previousThreadState?.isStreaming && previousThreadState.streamAbortController) {
          previousThreadState.streamAbortController.abort()
          previousThreadState.isStreaming = false
          previousThreadState.streamAbortController = null
        }
      }

      chatState.currentThreadId = newThread.id
    }
  } catch (error) {
    handleChatError(error, 'create')
  } finally {
    chatUIStore.creatingNewChat = false
  }
}

const selectChat = async (chatId) => {
  // 中断之前线程的流式输出（如果存在）
  const previousThreadId = chatState.currentThreadId
  if (previousThreadId && previousThreadId !== chatId) {
    const previousThreadState = getThreadState(previousThreadId)
    if (previousThreadState?.isStreaming && previousThreadState.streamAbortController) {
      previousThreadState.streamAbortController.abort()
      previousThreadState.isStreaming = false
      previousThreadState.streamAbortController = null
    }
    // run 模式下仅断开 SSE 订阅，不取消后台运行任务
    stopRunStreamSubscription(previousThreadId)
  }

  chatState.currentThreadId = chatId
  chatUIStore.isLoadingMessages = true
  try {
    // await fetchThreadMessages({ agentId: currentAgentId.value, threadId: chatId })
    await fetchThreadMessages({ agentId: currentLlmId.value, threadId: chatId })
  } catch (error) {
    handleChatError(error, 'load')
  } finally {
    chatUIStore.isLoadingMessages = false
  }

  await nextTick()
  scrollController.scrollToBottomStaticForce()
  await resumeActiveRunForThread(chatId)
}

const deleteChat = async (chatId) => {
  try {
    await deleteThread(chatId)
    if (chatState.currentThreadId === chatId) {
      chatState.currentThreadId = null
      // 如果删除的是当前对话，自动创建新对话
      await createNewChat()
    } else if (chatsList.value.length > 0) {
      // 如果删除的不是当前对话，选择第一个非置顶可用对话
      await selectChat(getFirstNonPinnedChat(chatsList.value).id)
    }
  } catch (error) {
    handleChatError(error, 'delete')
  }
}

const renameChat = async (data) => {
  let { chatId, title } = data
  if (
    !AgentValidator.validateRenameOperation(
      chatId,
      title,
      // currentAgentId.value,
      currentLlmId.value,
      handleValidationError
    )
  )
    return
  if (title.length > 30) title = title.slice(0, 30)
  try {
    await updateThread(chatId, title)
  } catch (error) {
    handleChatError(error, 'rename')
  }
}

const togglePinChat = async (chatId) => {
  const chat = chatsList.value.find((c) => c.id === chatId)
  if (!chat) return
  try {
    // 保存当前选中的对话ID
    const prevChatId = currentChatId.value

    await updateThread(chatId, null, !chat.is_pinned)

    // 刷新对话列表
    await loadChatsList()

    // 恢复当前选中的对话
    if (prevChatId) {
      chatState.currentThreadId = prevChatId
    }
  } catch (error) {
    handleChatError(error, 'pin')
  }
}

const handleSendMessage = async ({ image } = {}) => {
  const text = userInput.value.trim()
  if ((!text && !image) || !currentModelSpec.value || isProcessing.value) return
  let threadId = currentChatId.value
  if (!threadId) {
    threadId = await ensureActiveThread(text)
    if (!threadId) {
      message.error('创建对话失败，请重试')
      return
    }
  }

  userInput.value = ''

  await nextTick()
  scrollController.scrollToBottom(true)

  const threadState = getThreadState(threadId)
  if (!threadState) return
  threadState.isStreaming = true
  resetOnGoingConv(threadId)
  threadState.streamAbortController = new AbortController()
  console.log('threadId', threadId)

  try {
    const response = await sendMessage({
      llmId: currentLlmId.value,
      threadId: threadId,
      text: text,
      signal: threadState.streamAbortController?.signal,
      imageData: image
    })
    await handleLLMResponse(response, threadId)
  } catch (error) {
    if (error.name !== 'AbortError') {
      console.error('Stream error:', error)
      handleChatError(error, 'send')
    } else {
      console.warn('[Interrupted] Catch')
    }
    threadState.isStreaming = false
  } finally {
    threadState.streamAbortController = null
    // 异步加载历史记录，保持当前消息显示直到历史记录加载完成
    fetchThreadMessages({ agentId: currentLlmId.value, threadId: threadId }).finally(() => {
      // 历史记录加载完成后，安全地清空当前进行中的对话
      resetOnGoingConv(threadId)
      scrollController.scrollToBottom()
    })
  }
}

// 发送或中断
const handleSendOrStop = async (payload) => {
  const threadId = currentChatId.value
  const threadState = getThreadState(threadId)
  if (isProcessing.value && threadState) {
    if (useRunsApi && threadState.activeRunId) {
      try {
        await agentApi.cancelAgentRun(threadState.activeRunId)
        message.info('已发送取消请求')
      } catch (error) {
        handleChatError(error, 'stop')
      }
      return
    }

    if (threadState.streamAbortController) {
      // 中断生成
      threadState.streamAbortController.abort()

      // 中断后刷新消息历史，确保显示最新的状态
      try {
        await fetchThreadMessages({ agentId: currentLlmId.value, threadId: threadId, delay: 500 })
        message.info('已中断对话生成')
      } catch (error) {
        console.error('刷新消息历史失败:', error)
        message.info('已中断对话生成')
      }
      return
    }
  }
  await handleSendMessage(payload)
}

// ==================== 人工审批处理 ====================
const handleApprovalWithStream = async (answer) => {
  const threadId = approvalState.threadId
  if (!threadId) {
    message.error('无效的提问请求')
    approvalState.showModal = false
    return
  }

  const threadState = getThreadState(threadId)
  if (!threadState) {
    message.error('无法找到对应的对话线程')
    approvalState.showModal = false
    return
  }

  try {
    // 使用审批 composable 处理审批
    const response = await handleApproval(answer, currentLlmId.value)

    if (!response) return // 如果 handleApproval 抛出错误，这里不会执行

    // 处理流式响应
    await handleLLMResponse(response, threadId)
  } catch (error) {
    if (error.name !== 'AbortError') {
      console.error('Resume approval error:', error)
    }
  } finally {
    if (threadState) {
      threadState.isStreaming = false
      threadState.streamAbortController = null
    }

    // 异步加载历史记录，保持当前消息显示直到历史记录加载完成
    fetchThreadMessages({ agentId: currentLlmId.value, threadId: threadId }).finally(() => {
      resetOnGoingConv(threadId)
      scrollController.scrollToBottom()
    })
  }
}

// 处理示例问题点击
const handleExampleClick = (questionText) => {
  userInput.value = questionText
  nextTick(() => {
    handleSendMessage()
  })
}

const buildExportPayload = () => {
  let llmDescription = ''

  const payload = {
    chatTitle: currentThread.value?.title || '新对话',
    agentName: currentLlmName.value || currentLlm.value?.modelSpec|| '智能助手',
    agentDescription: llmDescription || currentLlm.value?.modelSpec|| '',
    messages: conversations.value ? JSON.parse(JSON.stringify(conversations.value)) : [],
    onGoingMessages: onGoingConvMessages.value
      ? JSON.parse(JSON.stringify(onGoingConvMessages.value))
      : []
  }

  return payload
}

defineExpose({
  getExportPayload: buildExportPayload
})

const toggleSidebar = () => {
  chatUIStore.toggleSidebar()
}
const openAgentModal = () => emit('open-agent-modal')

const handleModelSelect = (modelSpec) => {
  currentModelSpec.value = modelSpec
  emit('select-model', modelSpec)
}

const handleAgentStateRefresh = async (threadId = null) => {
  if (!currentLlmId.value) return
  const chatId = threadId || currentChatId.value
  if (!chatId) return
}

const toggleAgentPanel = () => {
  isAgentPanelOpen.value = !isAgentPanelOpen.value
}

// 处理面板宽度调整（使用比例）
// 向右拖动(deltaX > 0)让面板变窄，向左拖动(deltaX < 0)让面板变宽
const handlePanelResize = (deltaX) => {
  if (!panelWrapperRef.value) return

  // 初始化容器宽度
  if (!panelContainerWidth) {
    const container = document.querySelector('.chat-content-container')
    panelContainerWidth = container ? container.clientWidth : window.innerWidth
  }

  const currentWidth = panelWrapperRef.value.offsetWidth
  // 反转 deltaX：向右拖(deltaX > 0)让面板变窄
  const newWidth = currentWidth - deltaX
  const newRatio = newWidth / panelContainerWidth

  // 限制在合理范围内
  if (newRatio >= minPanelRatio && newRatio <= maxPanelRatio) {
    // 直接操作 DOM，不触发 Vue 响应式，使用 !important 确保不被覆盖
    panelWrapperRef.value.style.setProperty('flex', `0 0 ${newWidth}px`, 'important')
  }
}

// 拖拽状态变化时，同步最终状态到 Vue 响应式数据
const handleResizingChange = (isResizingState) => {
  isResizing.value = isResizingState

  // 拖拽结束时，同步 DOM 宽度到响应式数据
  if (!isResizingState && panelWrapperRef.value && panelContainerWidth) {
    const finalWidth = panelWrapperRef.value.offsetWidth
    panelRatio.value = finalWidth / panelContainerWidth
    panelContainerWidth = 0 // 重置，供下次使用
  }
}

// ==================== HELPER FUNCTIONS ====================
const getLastMessage = (conv) => {
  if (!conv?.messages?.length) return null
  for (let i = conv.messages.length - 1; i >= 0; i--) {
    if (conv.messages[i].type === 'ai') return conv.messages[i]
  }
  return null
}

const showMsgRefs = (msg) => {
  // 如果正在审批中，不显示 refs
  if (approvalState.showModal) {
    return false
  }

  // 如果当前线程ID与审批线程ID匹配，但审批框已关闭（说明刚刚处理完审批）
  // 且当前有新的流式处理正在进行，则不显示之前被中断的消息的 refs
  if (
    approvalState.threadId &&
    chatState.currentThreadId === approvalState.threadId &&
    !approvalState.showModal &&
    isProcessing
  ) {
    return false
  }

  // 只有真正完成的消息才显示 refs
  if (msg.isLast && msg.status === 'finished') {
    return ['copy', 'sources']
  }
  return false
}

const getConversationSources = (conv) => {
  return MessageProcessor.extractSourcesFromConversation(conv)
}

// ==================== LIFECYCLE & WATCHERS ====================
const loadChatsList = async () => {
  // const agentId = currentAgentId.value
  const agentId = currentLlmId.value
  if (!agentId) {
    console.warn('No agent selected, cannot load chats list')
    threads.value = []
    chatState.currentThreadId = null
    return
  }

  try {
    await fetchThreads(agentId)
    if (currentLlmId.value !== agentId) return

    // 如果当前线程不在线程列表中，清空当前线程
    if (
      chatState.currentThreadId &&
      !threads.value.find((t) => t.id === chatState.currentThreadId)
    ) {
      chatState.currentThreadId = null
    }

    // 如果有线程但没有选中任何线程，自动选择第一个非置顶对话
    if (threads.value.length > 0 && !chatState.currentThreadId) {
      await selectChat(getFirstNonPinnedChat(threads.value).id)
    }
  } catch (error) {
    handleChatError(error, 'load')
  }
}

// const initAll = async () => {
//   try {
//     if (!agentStore.isInitialized) {
//       await agentStore.initialize()
//     }
//   } catch (error) {
//     handleChatError(error, 'load')
//   }
// }

onMounted(async () => {
  // await initAll()
  scrollController.enableAutoScroll()
})

watch(
  currentLlmId,
  async (newAgentId, oldAgentId) => {
    if (newAgentId !== oldAgentId) {
      // 清理当前线程状态
      chatState.currentThreadId = null
      threadMessages.value = {}
      // 清理所有线程状态
      resetOnGoingConv()

      if (newAgentId) {
        await loadChatsList()
      } else {
        threads.value = []
      }
    }
  },
  { immediate: true }
)

watch(
  conversations,
  () => {
    if (isProcessing.value) {
      scrollController.scrollToBottom()
    }
  },
  { deep: true, flush: 'post' }
)
</script>

<style lang="less" scoped>
@import '@/assets/css/main.css';
@import '@/assets/css/animations.less';

.chat-container {
  display: flex;
  width: 100%;
  height: 100%;
  position: relative;
}

.chat {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden; /* Changed from overflow-x: hidden to overflow: hidden */
  position: relative;
  box-sizing: border-box;
  transition: all 0.3s ease;

  .chat-header {
    user-select: none;
    // position: sticky; // Not needed if .chat is flex col and header is fixed height item
    // top: 0;
    z-index: 10;
    height: var(--header-height);
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 8px;
    flex-shrink: 0; /* Prevent header from shrinking */

    .header__left,
    .header__right {
      display: flex;
      align-items: center;
    }

    .switch-icon {
      color: var(--gray-500);
      transition: all 0.2s ease;
    }

    .llm-nav-btn:hover .switch-icon {
      color: var(--main-500);
    }
  }
}

.chat-content-container {
  flex: 1;
  display: flex;
  flex-direction: row;
  overflow: hidden;
  position: relative;
  width: 100%;
  contain: layout;
}

.chat-main {
  flex: 1 1 0;
  display: flex;
  flex-direction: column;
  overflow-y: auto; /* Scroll is here now */
  position: relative;
  transition:
    flex-basis 0.3s cubic-bezier(0.4, 0, 0.2, 1),
    width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  min-width: 0; /* Prevent flex item from overflowing */

  scrollbar-width: none;
}

.agent-panel-wrapper {
  flex: 0 0 auto;
  height: calc(100% - 56px);
  overflow: hidden;
  z-index: 20;
  margin: 28px 8px;
  margin-left: 0;
  background: var(--gray-0);
  border-radius: 12px;
  box-shadow: 0 4px 20px var(--shadow-1);
  border: 1px solid var(--gray-150);
  min-width: 0;
  will-change: flex-basis;
}

/* Workbench transition animations */
.agent-panel-wrapper {
  transition: flex-basis 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  opacity: 0;
  transform: translateX(10px);
  margin-left: -16px;
}

.agent-panel-wrapper.is-visible {
  opacity: 1;
  transform: translateX(0);
  margin-left: 0;
}

.agent-panel-wrapper.no-transition {
  transition: none !important;
}

.chat-examples-input {
  padding: 32px 0;
  text-align: center;

  h1 {
    font-size: 1.2rem;
    color: var(--gray-1000);
    margin: 0;
  }
}

.example-questions {
  margin-top: 16px;
  text-align: center;

  .example-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
  }

  .example-chip {
    padding: 6px 12px;
    background: var(--gray-25);
    // border: 1px solid var(--gray-100);
    border-radius: 16px;
    cursor: pointer;
    font-size: 0.8rem;
    color: var(--gray-700);
    transition: all 0.15s ease;
    white-space: nowrap;
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;

    &:hover {
      // background: var(--main-25);
      border-color: var(--main-200);
      color: var(--main-700);
      box-shadow: 0 0px 4px rgba(0, 0, 0, 0.03);
    }

    &:active {
      transform: translateY(0);
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }
  }
}

.chat-loading {
  padding: 0 50px;
  text-align: center;
  position: absolute;
  top: 20%;
  width: 100%;
  z-index: 9;
  animation: slideInUp 0.5s ease-out;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;

  span {
    color: var(--gray-700);
    font-size: 14px;
  }

  .loading-spinner {
    width: 20px;
    height: 20px;
    border: 2px solid var(--gray-200);
    border-top-color: var(--main-color);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
}

.prompt-actions-bar {
  display: flex;
  justify-content: flex-end;
  padding: 4px 0;
}

.prompt-toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: var(--gray-600);
  cursor: pointer;
  border-radius: 4px;
  &:hover {
    background: var(--gray-100);
    color: var(--gray-800);
  }
}

.prompt-sidebar {
  width: 300px;
  flex-shrink: 0;
  background: var(--gray-0);
  border: 1px solid var(--gray-200);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  max-height: 500px;
  overflow: hidden;

  .prompt-panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px;
    border-bottom: 1px solid var(--gray-200);

    .prompt-panel-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--gray-800);
    }

    .prompt-panel-close {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      border: none;
      background: transparent;
      color: var(--gray-500);
      cursor: pointer;
      border-radius: 4px;
      &:hover {
        background: var(--gray-100);
        color: var(--gray-700);
      }
    }
  }

  .prompt-panel-content {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .prompt-tree-container {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
    max-height: 250px;
  }

  .prompt-variables {
    border-top: 1px solid var(--gray-200);
    padding: 8px;
    max-height: 200px;
    overflow-y: auto;

    .prompt-variables-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
      font-size: 12px;
      font-weight: 600;
      color: var(--gray-600);

      .prompt-variables-actions {
        display: flex;
        gap: 6px;
      }
    }

    .prompt-variable-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .prompt-variable-item {
      background: var(--gray-50);
      border: 1px solid var(--gray-200);
      border-radius: 4px;
      padding: 8px;

      .prompt-variable-info {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;

        .prompt-variable-name {
          font-size: 12px;
          font-weight: 500;
          color: var(--gray-700);
          font-family: monospace;
        }

        .prompt-variable-actions {
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
  }
}

.chat-box {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
  flex-grow: 1;
  padding: 1rem 1.25rem;
  display: flex;
  flex-direction: column;
}

.conv-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.bottom {
  position: sticky;
  bottom: 0;
  width: 100%;
  margin: 0 auto;
  padding: 4px 1rem 0 1rem;
  background: var(--gray-0);
  z-index: 1000;
  display: flex;
  gap: 12px;

  .message-input-wrapper {
    flex: 1;
    width: 100%;
    max-width: 800px;
    margin: 0 auto;

    .bottom-actions {
      display: flex;
      justify-content: center;
      align-items: center;
    }

    .note {
      font-size: small;
      color: var(--gray-300);
      margin: 4px 0;
      user-select: none;
    }
  }

  .input-main-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    max-width: 800px;
    margin: 0 auto;
    width: 100%;

    .bottom-actions {
      display: flex;
      justify-content: center;
      align-items: center;
    }

    .note {
      font-size: small;
      color: var(--gray-300);
      margin: 4px 0;
      user-select: none;
    }
  }

  &.start-screen {
    position: absolute;
    top: 45%;
    left: 50%;
    transform: translate(-50%, -50%);
    bottom: auto;
    max-width: 800px;
    width: 90%;
    background: transparent;
    padding: 0;
    border-top: none;
    z-index: 100; /* Ensure it's above other elements */
  }
}

.loading-dots {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
}

.loading-dots div {
  width: 6px;
  height: 6px;
  background: linear-gradient(135deg, var(--main-color), var(--main-700));
  border-radius: 50%;
  animation: dotPulse 1.4s infinite ease-in-out both;
}

.loading-dots div:nth-child(1) {
  animation-delay: -0.32s;
}

.loading-dots div:nth-child(2) {
  animation-delay: -0.16s;
}

.loading-dots div:nth-child(3) {
  animation-delay: 0s;
}

.generating-status {
  display: flex;
  justify-content: flex-start;
  padding: 1rem 0;
  animation: fadeInUp 0.4s ease-out;
  transition: all 0.2s;
}

.generating-indicator {
  display: flex;
  align-items: center;
  padding: 0.75rem 0rem;

  .generating-text {
    margin-left: 12px;
    font-size: 14px;
    font-weight: 500;
    letter-spacing: 0.025em;
    /* 恢复灰色调：深灰 -> 亮灰(高光) -> 深灰 */
    background: linear-gradient(
      90deg,
      var(--gray-700) 0%,
      var(--gray-700) 40%,
      var(--gray-300) 45%,
      var(--gray-200) 50%,
      var(--gray-300) 55%,
      var(--gray-700) 60%,
      var(--gray-700) 100%
    );
    background-size: 200% auto;
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    animation: waveFlash 2s linear infinite;
  }
}

@keyframes waveFlash {
  0% {
    background-position: 200% center;
  }
  100% {
    background-position: -200% center;
  }
}

@media (max-width: 1800px) {
  .chat-header {
    background-color: var(--gray-0);
    border-bottom: 1px solid var(--gray-100);
  }
}

@media (max-width: 768px) {
  .chat-header {
    .header__left {
      .text {
        display: none;
      }
    }
  }
}
</style>

<style lang="less">
.llm-nav-btn {
  display: flex;
  gap: 6px;
  padding: 6px 8px;
  height: 32px;
  justify-content: center;
  align-items: center;
  border-radius: 6px;
  color: var(--gray-900);
  cursor: pointer;
  width: auto;
  font-size: 15px;
  transition: background-color 0.3s;
  border: none;
  background: transparent;

  &:hover:not(.is-disabled) {
    background-color: var(--gray-100);
  }

  &.is-disabled {
    cursor: not-allowed;
    opacity: 0.7;
    pointer-events: none;
  }

  &.model-selector-wrapper {
    padding: 0;
    height: auto;
    background: transparent;

    &:hover:not(.is-disabled) {
      background-color: transparent;
    }
  }

  .nav-btn-icon {
    height: 18px;
  }

  .loading-icon {
    animation: spin 1s linear infinite;
  }
}

.hide-text {
  display: none;
}

@media (min-width: 769px) {
  .hide-text {
    display: inline;
  }
}

/* AgentState 按钮有内容时的样式 */
.llm-nav-btn.agent-state-btn.has-content:hover:not(.is-disabled) {
  color: var(--main-700);
  background-color: var(--main-20);
}

.llm-nav-btn.agent-state-btn.active {
  color: var(--main-700);
  background-color: var(--main-20);
}
</style>
