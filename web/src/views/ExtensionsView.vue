<template>
  <div class="extensions-view">
    <div class="extensions-header">
      <a-tabs v-model:activeKey="activeTab" class="extensions-tabs">
        <a-tab-pane key="prompts" tab="提示词管理" />
        <a-tab-pane key="skills" tab="Skills 管理" />
      </a-tabs>
      <div class="header-actions">
        <!-- Skills Tab 的按钮 -->
        <template v-if="activeTab === 'skills'">
          <a-upload
            accept=".zip"
            :show-upload-list="false"
            :custom-request="handleImportUpload"
            :disabled="skillsLoading || skillsImporting"
          >
            <a-button type="primary" :loading="skillsImporting" class="lucide-icon-btn">
              <Upload :size="14" />
              <span>导入 ZIP</span>
            </a-button>
          </a-upload>
          <a-button @click="handleSkillsRefresh" :disabled="skillsLoading" class="lucide-icon-btn">
            <RotateCw :size="14" />
            <span>刷新</span>
          </a-button>
        </template>
        <!-- Prompts Tab 的按钮 -->
        <template v-if="activeTab === 'prompts'">
          <a-button @click="handlePromptsRefresh" :disabled="promptsLoading" class="lucide-icon-btn">
            <RotateCw :size="14" />
            <span>刷新</span>
          </a-button>
        </template>
      </div>
    </div>

    <div class="extensions-content">
      <div v-show="activeTab === 'prompts'" class="tab-panel">
        <PromptsManagerComponent ref="promptsRef" @refresh="handlePromptsRefresh" />
      </div>
      <div v-show="activeTab === 'skills'" class="tab-panel">
        <SkillsManagerComponent
          ref="skillsRef"
          @import="handleSkillsImport"
          @refresh="handleSkillsRefresh"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Upload, RotateCw, Plus } from 'lucide-vue-next'
import PromptsManagerComponent from '@/components/PromptsManagerComponent.vue'
import SkillsManagerComponent from '@/components/SkillsManagerComponent.vue'

const route = useRoute()
const activeTab = ref('prompts')
const skillsRef = ref(null)

// 监听路由 query 参数变化
watch(
  () => route.query,
  (query) => {
    console.log('query', query)
    if (query.tab && ['prompts', 'skills'].includes(query.tab)) {
      activeTab.value = query.tab
    }
  },
  { immediate: true }
)
const skillsLoading = ref(false)
const skillsImporting = ref(false)
const promptsRef = ref(null)
const promptsLoading = ref(false)

const updateSkillsState = (loading, importing) => {
  skillsLoading.value = loading
  skillsImporting.value = importing
}

const updatePromptState = (loading) => {
  promptsLoading.value = loading
}

// Skills 事件处理
const handleSkillsImport = () => {
  // 导入完成后自动刷新
  handleSkillsRefresh()
}

const handleSkillsRefresh = () => {
  if (skillsRef.value?.fetchSkills) {
    updateSkillsState(true, skillsImporting.value)
    skillsRef.value.fetchSkills().finally(() => {
      updateSkillsState(false, skillsImporting.value)
    })
  }
}

// Prompts 事件处理
const handlePromptsRefresh = () => {
  if (promptsRef.value?.reloadTree) {
    updatePromptState(true)
    promptsRef.value.reloadTree().finally(() => {
      updatePromptState(false)
    })
  }
}

// 处理导入上传
const handleImportUpload = async ({ file, onSuccess, onError }) => {
  if (skillsRef.value?.handleImportUpload) {
    updateSkillsState(skillsLoading.value, true)
    try {
      await skillsRef.value.handleImportUpload({ file, onSuccess, onError })
      handleSkillsImport()
    } catch (e) {
      onError?.(e)
    } finally {
      updateSkillsState(skillsLoading.value, false)
    }
  }
}
</script>

<style scoped lang="less">
.extensions-view {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background-color: var(--gray-0);

  .extensions-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 16px;
    border-bottom: 1px solid var(--gray-150);
    background-color: var(--gray-0);

    .extensions-tabs {
      flex: 1;
      height: auto;
      display: flex;
      flex-direction: column;

      :deep(.ant-tabs-nav) {
        margin: 0;
        padding: 0;

        &::before {
          border-bottom: none;
        }
      }

      :deep(.ant-tabs-nav::after) {
        content: none;
      }

      :deep(.ant-tabs-nav-left-bar) {
        display: none;
      }

      :deep(.ant-tabs-items) {
        padding: 0;
      }

      :deep(.ant-tabs-tab) {
        padding: 12px 16px;
        font-size: 14px;
        margin: 0;

        &:hover {
          color: var(--main-600);
        }
      }

      :deep(.ant-tabs-tab-active) {
        .ant-tabs-tab-btn {
          color: var(--main-800) !important;
        }
      }

      :deep(.ant-tabs-ink-bar) {
        display: block;
        background-color: var(--main-800);
      }
    }

    .header-actions {
      display: flex;
      gap: 8px;
      padding: 8px 0;

      :deep(.ant-btn-primary) {
        background-color: var(--main-800);
        border-color: var(--main-800);

        &:hover {
          background-color: var(--main-700);
          border-color: var(--main-700);
        }
      }
    }
  }

  .extensions-content {
    flex: 1;
    min-height: 0;
    overflow: hidden;

    .tab-panel {
      height: 100%;
      min-height: 0;
      overflow: hidden;
    }
  }
}
</style>
