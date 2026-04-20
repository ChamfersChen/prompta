<template>
  <div class="community-view">
    <div class="community-header">
      <div class="header-right">
        <a-input-search
          v-model:value="searchKeyword"
          placeholder="搜索..."
          style="width: 280px"
          @search="handleSearch"
          @change="handleSearchChange"
          allowClear
        />
      </div>
    </div>

    <div class="community-content">
      <div class="sidebar">
        <div class="sidebar-section">
          <div class="section-title">浏览</div>
          <a-menu
            v-model:selectedKeys="selectedTab"
            mode="inline"
            class="community-menu"
          >
            <a-menu-item key="prompts">
              <BookText :size="18" />
              <span> 提示词社区</span>
            </a-menu-item>
            <a-menu-item key="favorites">
              <Heart :size="18" />
              <span> 我的收藏</span>
            </a-menu-item>
          </a-menu>
        </div>

        <div class="sidebar-section" v-if="selectedTab[0] !== 'favorites'">
          <div class="section-title">分类筛选</div>
          <div class="category-list">
            <div
              v-for="cat in categories"
              :key="cat.key"
              class="category-item"
              :class="{ active: currentCategory === cat.key }"
              @click="handleCategoryChange(cat.key)"
            >
              <component :is="cat.icon" :size="16" />
              <span>{{ cat.name }}</span>
            </div>
          </div>
        </div>

        <div class="sidebar-section" v-if="selectedTab[0] === 'favorites'">
          <div class="section-title">收藏夹</div>
          <div class="folder-panel">
            <a-button class="btn-outline-primary" type="dashed" size="small" block @click="openCreateFolderModal">
              新建收藏夹
            </a-button>
            <div class="folder-list">
              <div
                v-for="folder in availableFavoriteFolders"
                :key="folder"
                class="folder-item"
                :class="{ active: favoriteFolder === folder }"
                @click="favoriteFolder = folder"
              >
                <div class="folder-main">
                  <Folder :size="16" />
                  <span class="folder-name" :title="folder">{{ folder }}</span>
                </div>
                <div class="folder-actions">
                  <a-dropdown :trigger="['click']" placement="bottomRight">
                    <button class="folder-more" type="button" @click.stop>
                      <MoreHorizontal :size="13" />
                    </button>
                    <template #overlay>
                      <a-menu @click="({ key }) => handleFolderMenuClick(folder, key)">
                        <a-menu-item key="rename">改名</a-menu-item>
                        <a-menu-item key="delete" danger>删除</a-menu-item>
                      </a-menu>
                    </template>
                  </a-dropdown>
                </div>
              </div>
              <div v-if="availableFavoriteFolders.length === 0" class="folder-empty">
                还没有收藏夹，先新建一个吧
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="main-content">
        <div class="content-header" v-if="selectedTab[0] !== 'favorites'">
          <div class="sort-options">
            <a-radio-group v-model:value="sortBy" size="small" @change="handleSortChange">
              <a-radio-button value="popular">热门</a-radio-button>
              <a-radio-button value="latest">最新</a-radio-button>
              <a-radio-button value="rating">评分</a-radio-button>
            </a-radio-group>
          </div>
          <div class="template-count">共 {{ totalCount }} 个</div>
        </div>

        <div class="template-grid" v-if="!loading && currentList.length > 0">
          <community-card
            v-for="item in currentList"
            :key="item.id"
            :template="item"
            :favorited="isFavorited(item.id)"
            :mode="selectedTab[0]"
            @click="handleTemplateClick(item)"
            @favorite="handleFavoriteClick(item)"
            @fork="handleFork(item)"
          />
        </div>

        <div class="empty-state" v-else-if="!loading">
          <Inbox :size="48" />
          <p>暂无内容</p>
        </div>

        <div class="loading-state" v-if="loading">
          <a-spin size="large" />
        </div>

        <div class="pagination" v-if="totalCount > pageSize">
          <a-pagination
            v-model:current="currentPage"
            :total="totalCount"
            :pageSize="pageSize"
            @change="handlePageChange"
            showQuickJumper
          />
        </div>
      </div>
    </div>

    <a-modal
      v-model:open="showDetailModal"
      :title="selectedTemplate?.name"
      :width="960"
      :footer="null"
      :bodyStyle="{ height: '620px', overflow: 'hidden' }"
      class="template-detail-modal"
    >
      <div class="detail-content">
        <div class="detail-layout">
          <div class="detail-preview">
            <div class="preview-header">
              <h4>预览</h4>
              <a-button class="btn-primary-solid" type="primary" size="small" @click="copyTemplateContent">
                <Copy :size="14" />
                复制提示词
              </a-button>
            </div>
            <div class="preview-content">
              <pre>{{ selectedTemplate?.content }}</pre>
            </div>
          </div>

          <div class="detail-info">
            <div class="detail-header">
              <div class="detail-meta">
                <a-tag :color="getCategoryColor(selectedTemplate?.category)">
                  {{ getCategoryName(selectedTemplate?.category) }}
                </a-tag>
                <a-tag color="blue">提示词</a-tag>
                <span class="author">作者: {{ selectedTemplate?.author }}</span>
                <span v-if="selectedTemplate?.department_name" class="dept-tag">
                  {{ selectedTemplate.department_name }}
                </span>
              </div>
            </div>

            <div class="detail-description">
              <h4>描述</h4>
              <p>{{ selectedTemplate?.description || '暂无描述' }}</p>
            </div>

            <div class="detail-rating" v-if="selectedTab[0] !== 'favorites'">
              <h4>评分</h4>
              <div class="my-rating">
                <a-rate v-model:value="myRating" @change="handleRate(selectedTemplate)" />
              </div>
            </div>

            <div class="detail-variables" v-if="selectedTemplate?.variables?.length">
              <h4>变量</h4>
              <div class="variable-tags">
                <a-tag v-for="v in selectedTemplate.variables" :key="v.name" color="blue">
                  {{ v.name }}
                  <span v-if="v.default">: {{ v.default }}</span>
                </a-tag>
              </div>
            </div>

            <div class="detail-tags" v-if="selectedTemplate?.tags?.length">
              <h4>标签</h4>
              <div class="variable-tags">
                <a-tag v-for="tag in selectedTemplate.tags" :key="tag">{{ tag }}</a-tag>
              </div>
            </div>

            <div class="detail-comments" v-if="selectedTab[0] !== 'favorites'">
              <h4>评论</h4>
              <div class="comment-list">
                <div class="comment-item" v-for="comment in comments" :key="comment.id">
                  <div class="comment-avatar">
                    <a-avatar :size="28">{{ comment.author?.charAt(0) }}</a-avatar>
                  </div>
                  <div class="comment-content">
                    <div class="comment-header">
                      <span class="comment-author">{{ comment.author }}</span>
                      <span class="comment-time">{{ comment.createdAt }}</span>
                    </div>
                    <p class="comment-text">{{ comment.content }}</p>
                  </div>
                </div>
              </div>
              <div class="comment-input">
                <a-input
                  v-model:value="newComment"
                  placeholder="发表你的看法..."
                  @pressEnter="handleComment"
                />
                <a-button class="btn-primary-solid" type="primary" size="small" @click="handleComment">评论</a-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </a-modal>

    <a-modal
      v-model:open="showFavoriteModal"
      title="收藏"
      @ok="confirmFavorite"
      :confirm-loading="favoriting"
    >
      <p>选择收藏夹：</p>
      <a-form layout="vertical">
        <a-form-item label="收藏夹">
          <a-auto-complete
            v-model:value="favoriteForm.folderPath"
            :options="favoriteFolderOptions"
            placeholder="可选择或输入新的收藏夹"
            allow-clear
            style="width: 100%"
          />
          <div class="folder-tip">可直接输入名称创建新收藏夹</div>
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal
      v-model:open="showCreateFolderModal"
      title="新建收藏夹"
      @ok="confirmCreateFolder"
      :confirm-loading="creatingFolder"
    >
      <a-form layout="vertical">
        <a-form-item label="收藏夹名称" required>
          <a-input
            v-model:value="newFolderName"
            placeholder="例如：常用提示词"
            @pressEnter="confirmCreateFolder"
          />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal
      v-model:open="showRenameFolderModal"
      title="重命名收藏夹"
      @ok="confirmRenameFolder"
      :confirm-loading="renamingFolder"
    >
      <a-form layout="vertical">
        <a-form-item label="新名称" required>
          <a-input
            v-model:value="renameFolderName"
            placeholder="请输入新的收藏夹名称"
            @pressEnter="confirmRenameFolder"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { message, Modal } from 'ant-design-vue'
import {
  BookText,
  Heart,
  Folder,
  Copy,
  MoreHorizontal,
  Inbox,
  FileText,
  Code,
  BarChart,
  Globe,
  Briefcase,
  GraduationCap,
  Megaphone
} from 'lucide-vue-next'
import CommunityCard from '@/components/CommunityCard.vue'
import { useCommunityStore } from '@/stores/communityStore'
import * as communityApi from '@/apis/community_api'

const store = useCommunityStore()

const selectedTab = ref(['prompts'])
const currentCategory = ref('all')
const searchKeyword = ref('')
const sortBy = ref('popular')
const currentPage = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)
const loading = ref(false)
const showDetailModal = ref(false)
const showFavoriteModal = ref(false)
const selectedTemplate = ref(null)
const favoriting = ref(false)
const comments = ref([])
const newComment = ref('')
const myRating = ref(0)
const favoriteFolder = ref('')
const showCreateFolderModal = ref(false)
const creatingFolder = ref(false)
const newFolderName = ref('')
const showRenameFolderModal = ref(false)
const renamingFolder = ref(false)
const renameSourceFolder = ref('')
const renameFolderName = ref('')

const favoriteForm = ref({
  folderPath: ''
})

const availableFavoriteFolders = computed(() => {
  const serverFolders = store.favoriteFolders || []
  return Array.from(new Set(serverFolders.filter(Boolean))).sort((a, b) => a.localeCompare(b, 'zh-CN'))
})

const folderCountMap = computed(() => {
  const map = new Map()
  for (const item of store.favorites || []) {
    const key = item._favorite_folder || ''
    map.set(key, (map.get(key) || 0) + 1)
  }
  return map
})

const favoriteFolderOptions = computed(() => {
  return availableFavoriteFolders.value.map(folder => ({ value: folder }))
})

const categories = [
  { key: 'all', name: '全部', icon: FileText },
  { key: 'writing', name: '写作', icon: FileText },
  { key: 'programming', name: '编程', icon: Code },
  { key: 'analysis', name: '分析', icon: BarChart },
  { key: 'translation', name: '翻译', icon: Globe },
  { key: 'office', name: '办公', icon: Briefcase },
  { key: 'education', name: '教育', icon: GraduationCap },
  { key: 'marketing', name: '营销', icon: Megaphone }
]

const currentList = computed(() => {
  const tab = selectedTab.value[0]
  if (tab === 'prompts') return store.promptTemplates
  if (tab === 'favorites') {
    let items = store.favorites
    if (favoriteFolder.value) {
      items = items.filter(t => t._favorite_folder === favoriteFolder.value)
    }
    return items
  }
  return []
})

onMounted(() => {
  loadData()
  store.fetchFavoriteFolders('prompt')
})

watch([selectedTab, currentCategory, sortBy], () => {
  currentPage.value = 1
  loadData()
})

const loadData = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      pageSize: pageSize.value,
      category: currentCategory.value === 'all' ? undefined : currentCategory.value,
      keyword: searchKeyword.value || undefined,
      sort: sortBy.value
    }

    const tab = selectedTab.value[0]

    if (tab === 'prompts') {
      await communityApi.getFavorites().then(data => {
        store.favorites = data.list || []
      })
      const data = await communityApi.getPromptTemplates(params)
      store.promptTemplates = data.list || []
      totalCount.value = data.total || 0
    } else if (tab === 'favorites') {
      await store.fetchFavorites('prompt')
      totalCount.value = store.favorites.length
    }
  } catch {
    message.error('加载失败')
  } finally {
    loading.value = false
  }
}

const openCreateFolderModal = () => {
  showCreateFolderModal.value = true
}

const handleFolderMenuClick = (folder, action) => {
  if (action === 'rename') {
    renameSourceFolder.value = folder
    renameFolderName.value = folder
    showRenameFolderModal.value = true
    return
  }
  if (action === 'delete') {
    handleDeleteFolder(folder)
  }
}

const handleDeleteFolder = (folder) => {
  Modal.confirm({
    title: '删除收藏夹',
    content: `删除收藏夹「${folder}」后，原收藏项会保留但不再归属该收藏夹，是否继续？`,
    okText: '删除',
    cancelText: '取消',
    okType: 'danger',
    async onOk() {
      await communityApi.deleteFavoriteFolder({ folder_name: folder, item_type: 'prompt' })
      await store.fetchFavorites('prompt')
      await store.fetchFavoriteFolders('prompt')
      if (favoriteFolder.value === folder) favoriteFolder.value = ''
      if (selectedTab.value[0] === 'favorites') totalCount.value = store.favorites.length
      message.success('收藏夹已删除')
    }
  })
}

const confirmRenameFolder = async () => {
  const oldName = (renameSourceFolder.value || '').trim()
  const newName = (renameFolderName.value || '').trim()

  if (!oldName) {
    message.warning('未找到要重命名的收藏夹')
    return
  }
  if (!newName) {
    message.warning('请输入新的收藏夹名称')
    return
  }
  if (newName === oldName) {
    showRenameFolderModal.value = false
    return
  }
  if (availableFavoriteFolders.value.includes(newName)) {
    message.warning('收藏夹已存在')
    return
  }

  renamingFolder.value = true
  try {
    await communityApi.renameFavoriteFolder({
      old_folder_path: oldName,
      new_folder_path: newName,
      item_type: 'prompt'
    })

    await store.fetchFavorites('prompt')
    await store.fetchFavoriteFolders('prompt')

    if (favoriteFolder.value === oldName) {
      favoriteFolder.value = newName
    }
    if (selectedTab.value[0] === 'favorites') totalCount.value = store.favorites.length

    showRenameFolderModal.value = false
    renameSourceFolder.value = ''
    renameFolderName.value = ''
    message.success('收藏夹已重命名')
  } catch {
    message.error('重命名失败')
  } finally {
    renamingFolder.value = false
  }
}

const handleSearch = () => { loadData() }
const handleSearchChange = () => { if (!searchKeyword.value) loadData() }
const handleCategoryChange = (cat) => { currentCategory.value = cat }
const handleSortChange = () => { loadData() }
const handlePageChange = (page) => { currentPage.value = page; loadData() }

const handleTemplateClick = async (template) => {
  try {
    const detail = await communityApi.getTemplateDetail(template.id)
    selectedTemplate.value = detail
    showDetailModal.value = true

    try {
      const data = await communityApi.getMyRating(template.id)
      myRating.value = data ? data.rating : 0
    } catch { myRating.value = 0 }

    try {
      const commentData = await communityApi.getTemplateComments(template.id)
      comments.value = commentData.list || []
    } catch { comments.value = [] }
  } catch {
    message.error('获取详情失败')
  }
}

const handleFavoriteClick = (template) => {
  if (store.isFavorited(template.id)) {
    handleUnfavorite(template)
    return
  }
  selectedTemplate.value = template
  favoriteForm.value.folderPath = favoriteFolder.value || ''
  store.fetchFavoriteFolders('prompt')
  showFavoriteModal.value = true
}

const confirmFavorite = async () => {
  favoriting.value = true
  try {
    await communityApi.addFavorite({
      template_id: selectedTemplate.value.id,
      item_type: 'prompt',
      folder_path: favoriteForm.value.folderPath || null
    })
    message.success('收藏成功')
    showFavoriteModal.value = false
    await store.fetchFavorites('prompt')
    await store.fetchFavoriteFolders('prompt')
  } catch {
    message.error('收藏失败')
  } finally {
    favoriting.value = false
  }
}

const handleUnfavorite = async (template) => {
  try {
    await communityApi.removeFavorite(template.id)
    message.success('已取消收藏')
    await store.fetchFavorites('prompt')
    await store.fetchFavoriteFolders('prompt')
    if (selectedTab.value[0] === 'favorites') totalCount.value = store.favorites.length
  } catch {
    message.error('操作失败')
  }
}

const confirmCreateFolder = async () => {
  const folderName = (newFolderName.value || '').trim()
  if (!folderName) {
    message.warning('请输入收藏夹名称')
    return
  }
  if (availableFavoriteFolders.value.includes(folderName)) {
    message.warning('收藏夹已存在')
    return
  }
  creatingFolder.value = true
  try {
    await communityApi.createFavoriteFolder({
      folder_name: folderName,
      item_type: 'prompt'
    })
    await store.fetchFavoriteFolders('prompt')
    favoriteFolder.value = folderName
    favoriteForm.value.folderPath = folderName
    showCreateFolderModal.value = false
    newFolderName.value = ''
    message.success('收藏夹已创建')
  } finally {
    creatingFolder.value = false
  }
}

const handleFork = async (template) => {
  try {
    await communityApi.forkTemplate(template.id)
    message.success('Fork 成功')
    loadData()
  } catch {
    message.error('Fork 失败')
  }
}

const handleRate = async (template) => {
  try {
    await communityApi.rateTemplate(template.id, myRating.value)
    message.success('评分成功')
  } catch {
    message.error('评分失败')
  }
}

const handleComment = async () => {
  if (!newComment.value.trim()) return
  try {
    await communityApi.commentTemplate(selectedTemplate.value.id, newComment.value)
    message.success('评论成功')
    newComment.value = ''
    const commentData = await communityApi.getTemplateComments(selectedTemplate.value.id)
    comments.value = commentData.list || []
  } catch {
    message.error('评论失败')
  }
}

const copyTemplateContent = async () => {
  const content = selectedTemplate.value?.content || ''
  if (!content.trim()) {
    message.warning('暂无可复制内容')
    return
  }

  try {
    await navigator.clipboard.writeText(content)
    message.success('提示词已复制')
  } catch {
    const textarea = document.createElement('textarea')
    textarea.value = content
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.focus()
    textarea.select()
    try {
      const ok = document.execCommand('copy')
      if (ok) {
        message.success('提示词已复制')
      } else {
        message.error('复制失败，请手动复制')
      }
    } finally {
      document.body.removeChild(textarea)
    }
  }
}

const isFavorited = (templateId) => store.isFavorited(templateId)
const getFolderCount = (folder) => folderCountMap.value.get(folder) || 0

const getCategoryColor = (category) => {
  const colors = {
    writing: 'blue', programming: 'green', analysis: 'purple',
    translation: 'orange', office: 'cyan', education: 'gold', marketing: 'red'
  }
  return colors[category] || 'default'
}

const getCategoryName = (category) => {
  const cat = categories.find(c => c.key === category)
  return cat ? cat.name : category
}
</script>

<style scoped lang="less">
.community-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px;
  background: var(--main-20);
}

.community-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-right {
  display: flex;
  gap: 12px;
  align-items: center;
}

.btn-primary-solid {
  background: var(--color-primary-500);
  border-color: var(--color-primary-500);
  color: var(--gray-0);
}

.btn-primary-solid:hover,
.btn-primary-solid:focus {
  background: var(--color-primary-700);
  border-color: var(--color-primary-700);
  color: var(--gray-0);
}

.btn-primary-solid:active {
  background: var(--color-primary-900);
  border-color: var(--color-primary-900);
  color: var(--gray-0);
}

.btn-outline-primary {
  background: var(--main-0);
  border-color: var(--color-primary-100);
  color: var(--color-primary-700);
}

.btn-outline-primary:hover,
.btn-outline-primary:focus {
  background: var(--color-primary-50);
  border-color: var(--color-primary-500);
  color: var(--color-primary-700);
}

.btn-outline-primary:active {
  background: var(--color-primary-100);
  border-color: var(--color-primary-700);
  color: var(--color-primary-900);
}

.community-content {
  display: flex;
  flex: 1;
  gap: 20px;
  overflow: hidden;
}

.sidebar {
  width: 240px;
  flex-shrink: 0;
  background: var(--main-0);
  border-radius: 8px;
  padding: 16px;
  border: 1px solid var(--gray-200);
}

.sidebar-section { margin-bottom: 24px; }

.section-title {
  font-size: 12px;
  color: var(--gray-600);
  margin-bottom: 12px;
  text-transform: uppercase;
}

.community-menu { border: none; }
.community-menu :deep(.ant-menu-item) {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  padding: 8px 12px;
  border-radius: 6px;
  color: var(--color-secondary-700);
}

.community-menu :deep(.ant-menu-item:hover) {
  background: var(--color-primary-50);
  color: var(--color-primary-700);
}

.community-menu :deep(.ant-menu-item-selected) {
  background: var(--color-primary-50);
  color: var(--color-primary-700);
  font-weight: 600;
}

.category-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.category-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid transparent;
  cursor: pointer;
  font-size: 13px;
  color: var(--color-secondary-700);
  transition: all 0.2s;
}

.category-item:hover {
  background: var(--color-primary-50);
  border-color: var(--color-primary-100);
  color: var(--color-primary-700);
}

.category-item.active {
  background: var(--color-primary-50);
  border-color: var(--color-primary-500);
  color: var(--color-primary-700);
  font-weight: 600;
}

.folder-panel {
  margin-top: 6px;
  padding: 10px;
  border-radius: 10px;
  border: 1px solid var(--gray-200);
  background: linear-gradient(180deg, var(--main-5) 0%, var(--main-20) 100%);
}

.folder-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 10px;
}

.folder-tip {
  margin-top: 6px;
  font-size: 12px;
  color: var(--gray-600);
}

.folder-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid transparent;
  cursor: pointer;
  font-size: 13px;
  color: var(--color-secondary-700);
  transition: all 0.2s ease;
}

.folder-main {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.folder-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.folder-actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.folder-more {
  width: 20px;
  height: 20px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--gray-500);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  cursor: pointer;
  transition: all 0.2s ease;
}

.folder-item:hover .folder-more,
.folder-item.active .folder-more {
  opacity: 1;
}

.folder-more:hover {
  background: var(--color-primary-50);
  color: var(--color-primary-700);
}

.folder-item:hover {
  background: var(--color-primary-50);
  border-color: var(--color-primary-100);
  color: var(--color-primary-700);
}

.folder-item.active {
  background: var(--color-primary-50);
  border-color: var(--color-primary-500);
  color: var(--color-primary-700);
  font-weight: 600;
}

.folder-empty {
  padding: 10px;
  border-radius: 8px;
  border: 1px dashed var(--gray-300);
  color: var(--gray-600);
  font-size: 12px;
  text-align: center;
}

.main-content {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.sort-options :deep(.ant-radio-group) {
  display: inline-flex;
  gap: 4px;
  padding: 3px;
  border-radius: 8px;
  border: 1px solid var(--gray-200);
  background: var(--main-10);
}

.sort-options :deep(.ant-radio-button-wrapper) {
  height: 30px;
  line-height: 30px;
  padding: 0 14px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--color-secondary-700);
  font-size: 13px;
  transition: all 0.2s ease;
}

.sort-options :deep(.ant-radio-button-wrapper:not(:first-child)::before) {
  display: none;
}

.sort-options :deep(.ant-radio-button-wrapper:hover) {
  background: var(--color-primary-50);
  color: var(--color-primary-700);
}

.sort-options :deep(.ant-radio-button-wrapper-checked:not(.ant-radio-button-wrapper-disabled)) {
  background: var(--color-primary-500);
  color: var(--gray-0);
  font-weight: 600;
  box-shadow: none;
}

.sort-options :deep(.ant-radio-button-wrapper-checked:not(.ant-radio-button-wrapper-disabled):hover),
.sort-options :deep(.ant-radio-button-wrapper-checked:not(.ant-radio-button-wrapper-disabled):focus) {
  background: var(--color-primary-700);
  color: var(--gray-0);
}

.template-count { font-size: 13px; color: var(--gray-600); }

.template-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--gray-600);
}

.loading-state {
  display: flex;
  justify-content: center;
  padding: 40px;
  border: 1px dashed var(--color-primary-100);
  border-radius: 10px;
  background: linear-gradient(180deg, var(--main-5) 0%, var(--main-20) 100%);
}

.loading-state :deep(.ant-spin) {
  color: var(--color-primary-500);
}

.loading-state :deep(.ant-spin-dot-item) {
  background-color: var(--color-primary-500);
}

.pagination { margin-top: 16px; text-align: center; }

.detail-content { width: 100%; }
.detail-layout { display: flex; gap: 24px; height: 100%; }
.detail-preview { flex: 1; min-width: 0; height: 100%; display: flex; flex-direction: column; }
.detail-info { width: 300px; flex-shrink: 0; height: 100%; overflow-y: auto; }

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.preview-header h4 {
  margin: 0;
}

.preview-content {
  background: var(--main-10);
  border: 1px solid var(--gray-200);
  border-radius: 8px;
  padding: 12px;
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.preview-content pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.6;
  margin: 0;
}

.detail-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.author { font-size: 13px; color: #999; }
.author { font-size: 13px; color: var(--gray-600); }
.dept-tag { font-size: 12px; color: var(--color-primary-700); background: var(--color-primary-50); padding: 1px 6px; border-radius: 4px; }

.detail-description { margin-top: 16px; }
.detail-description h4 { font-size: 14px; margin-bottom: 8px; }
.detail-description p { font-size: 13px; color: var(--color-secondary-700); line-height: 1.6; }

.detail-rating { margin-top: 16px; }
.detail-rating h4 { font-size: 14px; margin-bottom: 8px; }

.detail-variables { margin-top: 16px; }
.detail-variables h4 { font-size: 14px; margin-bottom: 8px; }
.variable-tags { display: flex; flex-wrap: wrap; gap: 6px; }

.detail-tags { margin-top: 16px; }
.detail-tags h4 { font-size: 14px; margin-bottom: 8px; }

.detail-comments { margin-top: 16px; }
.detail-comments h4 { font-size: 14px; margin-bottom: 8px; }

.comment-list { display: flex; flex-direction: column; gap: 12px; margin-bottom: 12px; }
.comment-item { display: flex; gap: 8px; }
.comment-avatar { flex-shrink: 0; }
.comment-content { flex: 1; min-width: 0; }
.comment-header { display: flex; gap: 8px; margin-bottom: 4px; }
.comment-author { font-size: 13px; font-weight: 500; }
.comment-time { font-size: 12px; color: var(--gray-600); }
.comment-text { font-size: 13px; line-height: 1.5; }

.comment-input { display: flex; gap: 8px; }
.comment-input .ant-input { flex: 1; }

:deep(.template-detail-modal .ant-modal-content) {
  height: 680px;
  display: flex;
  flex-direction: column;
}

:deep(.template-detail-modal .ant-modal-body) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

:deep(.ant-modal-footer .ant-btn-primary) {
  background: var(--color-primary-500);
  border-color: var(--color-primary-500);
}

:deep(.ant-modal-footer .ant-btn-primary:hover),
:deep(.ant-modal-footer .ant-btn-primary:focus) {
  background: var(--color-primary-700);
  border-color: var(--color-primary-700);
}

:deep(.ant-modal-footer .ant-btn-primary:active) {
  background: var(--color-primary-900);
  border-color: var(--color-primary-900);
}

:deep(.ant-btn-dangerous) {
  color: var(--color-error-700);
  border-color: var(--color-error-100);
  background: var(--color-error-50);
}

:deep(.ant-btn-dangerous:hover),
:deep(.ant-btn-dangerous:focus) {
  color: var(--gray-0);
  border-color: var(--color-error-700);
  background: var(--color-error-700);
}

:global(.dark) .community-view { background: #141414; }
:global(.dark) .sidebar { background: #1f1f1f; }
:global(.dark) .category-item:hover { background: #2a2a2a; border-color: #334155; color: #9ec3ff; }
:global(.dark) .category-item.active { background: #111d2c; border-color: #3d6bc0; color: #9ec3ff; }
:global(.dark) .community-menu :deep(.ant-menu-item) { color: #c2c8d2; }
:global(.dark) .community-menu :deep(.ant-menu-item:hover) { background: #1f334f; color: #9ec3ff; }
:global(.dark) .community-menu :deep(.ant-menu-item-selected) { background: #1a3557; color: #9ec3ff; }
:global(.dark) .sort-options :deep(.ant-radio-group) {
  background: #1c2434;
  border-color: #2c3a52;
}
:global(.dark) .sort-options :deep(.ant-radio-button-wrapper) {
  color: #c2c8d2;
}
:global(.dark) .sort-options :deep(.ant-radio-button-wrapper:hover) {
  background: #1f334f;
  color: #9ec3ff;
}
:global(.dark) .sort-options :deep(.ant-radio-button-wrapper-checked:not(.ant-radio-button-wrapper-disabled)) {
  background: #2e5ac4;
  color: #f8fafe;
}
:global(.dark) .sort-options :deep(.ant-radio-button-wrapper-checked:not(.ant-radio-button-wrapper-disabled):hover),
:global(.dark) .sort-options :deep(.ant-radio-button-wrapper-checked:not(.ant-radio-button-wrapper-disabled):focus) {
  background: #4a72d6;
  color: #ffffff;
}
:global(.dark) .folder-panel {
  border-color: #30343b;
  background: linear-gradient(180deg, #1d1f24 0%, #181a1f 100%);
}
:global(.dark) .folder-item:hover {
  background: #2a2e36;
  border-color: #3a404a;
  color: #d1d5db;
}
:global(.dark) .folder-item.active {
  background: #1b3552;
  border-color: #2a5d92;
  color: #74b1ff;
}
:global(.dark) .folder-more {
  color: #7d8592;
}
:global(.dark) .folder-more:hover {
  background: #303642;
  color: #c2c8d2;
}
:global(.dark) .folder-empty {
  border-color: #3a3f47;
  color: #9ca3af;
}
:global(.dark) .loading-state {
  border-color: #33445f;
  background: linear-gradient(180deg, #1b2435 0%, #171f2f 100%);
}
:global(.dark) .loading-state :deep(.ant-spin-dot-item) {
  background-color: #8faaea;
}
:global(.dark) .preview-content { background: #1f1f1f; border-color: #303030; }

@media (max-width: 960px) {
  .community-content {
    flex-direction: column;
    overflow: visible;
  }

  .sidebar {
    width: 100%;
  }
}
</style>
