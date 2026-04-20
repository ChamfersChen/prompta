<template>
  <div class="extensions-view">
    <div class="extensions-content">
      <PromptsManagerComponent ref="promptsRef" @refresh="handlePromptsRefresh" />
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import PromptsManagerComponent from '@/components/PromptsManagerComponent.vue'

const props = defineProps({
  tab: {
    type: String,
    default: 'prompts'
  }
})

const promptsRef = ref(null)

watch(
  () => props.tab,
  () => {},
  { immediate: true }
)

const handlePromptsRefresh = () => {
  if (promptsRef.value?.reloadTree) {
    promptsRef.value.reloadTree()
  }
}

const handleImportUpload = async ({ file, onSuccess, onError }) => {
  if (promptsRef.value?.handleImportUpload) {
    try {
      await promptsRef.value.handleImportUpload({ file, onSuccess, onError })
    } catch (e) {
      onError?.(e)
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