<template>
  <div class="template-market-view">
    <div class="market-header">
      <div class="header-right">
        <a-input-search
          v-model:value="searchKeyword"
          placeholder="搜索模板..."
          style="width: 280px"
          @search="handleSearch"
          @change="handleSearchChange"
          allowClear
        />
      </div>
    </div>

    <div class="market-content">
      <div class="sidebar">
        <div class="sidebar-section">
          <div class="section-title">模板类型</div>
          <a-menu
            v-model:selectedKeys="selectedTab"
            mode="inline"
            class="template-menu"
          >
            <a-menu-item key="official">
              <Store :size="16" />
              <span> 官方模板</span>
            </a-menu-item>
            <a-menu-item key="community">
              <Users :size="16" />
              <span> 社区模板</span>
            </a-menu-item>
            <a-menu-item key="mine" v-if="userStore.isAdmin">
              <Folder :size="16" />
              <span> 我的模板</span>
            </a-menu-item>
            <a-menu-item key="favorites">
              <Heart :size="16" />
              <span> 我的收藏</span>
            </a-menu-item>
          </a-menu>
        </div>

        <div class="sidebar-section" v-if="selectedTab[0] !== 'favorites' && selectedTab[0] !== 'mine'">
          <div class="section-title">分类筛选</div>
          <div class="category-list">
            <div
              v-for="cat in categories"
              :key="cat.key"
              class="category-item"
              :class="{ active: currentCategory === cat.key }"
              @click="handleCategoryChange(cat.key)"
            >
              <component :is="cat.icon" :size="14" />
              <span>{{ cat.name }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="main-content">
        <div class="content-header" v-if="selectedTab[0] !== 'favorites' && selectedTab[0] !== 'mine'">
          <div class="sort-options">
            <a-radio-group v-model:value="sortBy" size="small" @change="handleSortChange">
              <a-radio-button value="popular">热门</a-radio-button>
              <a-radio-button value="latest">最新</a-radio-button>
              <a-radio-button value="rating">评分</a-radio-button>
            </a-radio-group>
          </div>
          <div class="template-count">
            共 {{ totalCount }} 个模板
          </div>
        </div>

        <div class="template-grid" v-if="!loading && currentList.length > 0">
          <template-card
            v-for="template in currentList"
            :key="template.id"
            :template="template"
            :favorited="isFavorited(template.id)"
            :mode="selectedTab[0]"
            @click="handleTemplateClick(template)"
            @favorite="handleFavoriteClick(template)"
            @fork="handleFork(template)"
            @use="handleUseTemplate(template)"
          />
        </div>

        <div class="empty-state" v-else-if="!loading">
          <Inbox :size="48" />
          <p>暂无模板</p>
          <!-- <a-button type="primary" @click="showCreateModal = true">创建第一个模板</a-button> -->
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

    <!-- 模板详情弹窗 -->
    <a-modal
      v-model:open="showDetailModal"
      :title="selectedTemplate?.name"
      width="900px"
      :footer="null"
      class="template-detail-modal"
    >
      <div class="detail-content">
        <div class="detail-layout">
          <!-- 左侧：预览内容 -->
          <div class="detail-preview">
            <h4>预览</h4>
            <div class="preview-content">
              <pre>{{ selectedTemplate?.content }}</pre>
            </div>
          </div>

          <!-- 右侧：其他信息 -->
          <div class="detail-info">
            <div class="detail-header">
              <div class="detail-meta">
                <a-tag :color="getCategoryColor(selectedTemplate?.category)">
                  {{ getCategoryName(selectedTemplate?.category) }}
                </a-tag>
                <span class="author">作者: {{ selectedTemplate?.author }}</span>
                <div class="detail-actions" v-if="selectedTab[0] !== 'mine'">
                  <a-button
                    :type="isFavorited(selectedTemplate?.id) ? 'default' : 'primary'"
                    @click="handleFavoriteClick(selectedTemplate)"
                  >
                    <Heart :size="14" :fill="isFavorited(selectedTemplate?.id) ? 'currentColor' : 'none'" />
                    {{ isFavorited(selectedTemplate?.id) ? '已收藏' : '收藏' }}
                  </a-button>
                </div>
              </div>
            </div>

            <div class="detail-description">
              <h4>描述</h4>
              <p>{{ selectedTemplate?.description || '暂无描述' }}</p>
            </div>

            <div class="detail-rating" v-if="selectedTab[0] !== 'mine'">
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

            <div class="detail-comments" v-if="selectedTab[0] !== 'mine'">
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
                <a-button type="primary" size="small" @click="handleComment">评论</a-button>
              </div>
            </div>

            <!-- 我的模板：显示使用和评论统计 -->
            <div class="detail-stats" v-if="selectedTab[0] === 'mine'">
              <h4>使用统计</h4>
              <div class="stats-row">
                <div class="stat-item">
                  <span class="stat-label">评分</span>
                  <span class="stat-value">{{ selectedTemplate?.rating?.toFixed(1) || '0.0' }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">评论数</span>
                  <span class="stat-value">{{ comments.length }}</span>
                </div>
              </div>
            </div>

            <!-- 我的模板：发布设置 -->
            <div class="detail-publish-settings" v-if="selectedTab[0] === 'mine'">
              <h4>发布设置</h4>
              <div class="publish-setting-item">
                <div class="setting-label">
                  <span>公开到社区</span>
                  <a-tooltip title="公开后其他用户可以在社区模板中查看和使用此模板">
                    <Info :size="14" class="info-icon" />
                  </a-tooltip>
                </div>
                <a-switch
                  :checked="editForm.isPublic"
                  @change="(val) => editForm.isPublic = val"
                />
              </div>
              <div class="publish-setting-item" v-if="userStore.isSuperAdmin && editForm.isPublic">
                <div class="setting-label">
                  <span>设为官方模板</span>
                  <a-tooltip title="官方模板会同时在官方模板和社区模板列表中展示">
                    <Info :size="14" class="info-icon" />
                  </a-tooltip>
                </div>
                <a-switch
                  :checked="editForm.isOfficial"
                  @change="(val) => editForm.isOfficial = val"
                />
              </div>
              <a-button
                type="primary"
                size="small"
                :loading="savingSettings"
                :disabled="!hasSettingsChanged"
                @click="handleSaveSettings"
                style="margin-top: 12px;"
              >
                保存设置
              </a-button>
            </div>
          </div>
        </div>
      </div>
    </a-modal>

    <!-- 收藏弹窗（选择文件夹路径） -->
    <a-modal
      v-model:open="showFavoriteModal"
      title="收藏到提示词管理"
      @ok="confirmFavorite"
      :confirm-loading="favoriting"
    >
      <p>选择收藏后，该模板将保存到提示词管理的指定文件夹中。</p>
      <a-form layout="vertical">
        <a-form-item label="文件夹路径" required>
          <a-tree-select
            v-model:value="favoriteForm.folderPath"
            :tree-data="promptTreeData"
            placeholder="选择文件夹路径"
            tree-default-expand-all
            allow-clear
            style="width: 100%"
          />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 创建模板弹窗 -->
    <!-- <a-modal
      v-model:open="showCreateModal"
      title="创建模板"
      width="600px"
      @ok="handleCreateTemplate"
      :confirm-loading="creating"
    >
      <a-form :model="createForm" layout="vertical">
        <a-form-item label="模板名称" required>
          <a-input v-model:value="createForm.name" placeholder="输入模板名称" />
        </a-form-item>
        <a-form-item label="分类" required>
          <a-select v-model:value="createForm.category" placeholder="选择分类">
            <a-select-option v-for="cat in categories" :key="cat.key" :value="cat.key">
              {{ cat.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea
            v-model:value="createForm.description"
            placeholder="简要描述这个模板的用途"
            :rows="3"
          />
        </a-form-item>
        <a-form-item label="标签">
          <a-select
            v-model:value="createForm.tags"
            mode="tags"
            placeholder="添加标签"
            style="width: 100%"
          />
        </a-form-item>
        <a-form-item label="Prompt 内容" required>
          <a-textarea
            v-model:value="createForm.content"
            placeholder="输入 Prompt 内容，可以使用 {{variable}} 定义变量"
            :rows="8"
          />
        </a-form-item>
        <a-form-item label="变量定义">
          <div class="variable-definitions">
            <div
              v-for="(v, idx) in createForm.variables"
              :key="idx"
              class="variable-row"
            >
              <a-input v-model:value="v.name" placeholder="变量名" style="width: 120px" />
              <a-select v-model:value="v.type" style="width: 100px">
                <a-select-option value="string">字符串</a-select-option>
                <a-select-option value="number">数字</a-select-option>
                <a-select-option value="boolean">布尔</a-select-option>
                <a-select-option value="select">选择</a-select-option>
              </a-select>
              <a-input v-model:value="v.default" placeholder="默认值" style="width: 120px" />
              <a-input v-model:value="v.description" placeholder="说明" style="flex: 1" />
              <a-button type="text" danger @click="removeVariable(idx)">
                <Trash2 :size="14" />
              </a-button>
            </div>
            <a-button type="dashed" block @click="addVariable">
              <Plus :size="14" />
              添加变量
            </a-button>
          </div>
        </a-form-item>
        <a-form-item label="公开状态">
          <a-switch v-model:checked="createForm.isPublic" />
          <span class="switch-hint">公开后可分享到社区市场</span>
        </a-form-item>
        <a-form-item label="设为官方模板" v-if="userStore.isSuperAdmin && createForm.isPublic">
          <a-switch v-model:checked="createForm.isOfficial" />
          <span class="switch-hint">设为官方模板后，所有用户可见并可收藏</span>
        </a-form-item>
      </a-form>
    </a-modal> -->
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  Store,
  Users,
  Heart,
  Folder,
  Plus,
  Inbox,
  Play,
  Trash2,
  FileText,
  Code,
  BarChart,
  Globe,
  Briefcase,
  GraduationCap,
  Megaphone,
  Info
} from 'lucide-vue-next'
import TemplateCard from '@/components/TemplateCard.vue'
import { useTemplateStore } from '@/stores/templateStore'
import { useUserStore } from '@/stores/user'
import * as templateApi from '@/apis/template_api'
import { promptApi } from '@/apis/prompt_api'
import { useThemeStore } from '@/stores/theme'

const router = useRouter()
const store = useTemplateStore()
const userStore = useUserStore()
const themeStore = useThemeStore()
const theme = computed(() => (themeStore.isDark ? 'dark' : 'light'))

const selectedTab = ref(['official'])
const currentCategory = ref('all')
const searchKeyword = ref('')
const sortBy = ref('popular')
const currentPage = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)
const loading = ref(false)
const showDetailModal = ref(false)
// const showCreateModal = ref(false)
const showFavoriteModal = ref(false)
const selectedTemplate = ref(null)
const creating = ref(false)
const favoriting = ref(false)
const comments = ref([])
const newComment = ref('')
const myRating = ref(0)
const userRatings = ref({})
const promptTreeData = ref([])

const favoriteForm = ref({
  folderPath: ''
})

const createForm = ref({
  name: '',
  category: 'writing',
  description: '',
  tags: [],
  content: '',
  variables: [],
  is_public: false,
  is_official: false
})

const editForm = ref({
  isPublic: false,
  isOfficial: false
})

const editFormOriginal = ref({
  isPublic: false,
  isOfficial: false
})

const savingSettings = ref(false)

const hasSettingsChanged = computed(() => {
  return editForm.value.isPublic !== editFormOriginal.value.isPublic ||
         editForm.value.isOfficial !== editFormOriginal.value.isOfficial
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
  switch (selectedTab.value[0]) {
    case 'official':
      return store.officialTemplates
    case 'community':
      return store.communityTemplates
    case 'favorites':
      return store.favorites
    case 'mine':
      return store.myTemplates
    default:
      return []
  }
})

onMounted(() => {
  loadData()
  loadPromptTree()
})

watch([selectedTab, currentCategory, sortBy], () => {
  currentPage.value = 1
  loadData()
})

const loadPromptTree = async () => {
  try {
    const result = await promptApi.getPromptTree()
    const normalizeTree = (nodes) =>
      (nodes || [])
        .filter((node) => node.is_dir)
        .map((node) => ({
          title: node.name,
          value: node.path,
          key: node.path,
          isLeaf: false,
          children: normalizeTree(node.children || [])
        }))
    promptTreeData.value = normalizeTree(result?.data || [])
  } catch (error) {
    console.error('加载提示词树失败:', error)
  }
}

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

    const currentTab = selectedTab.value[0]
    
    if (currentTab === 'official' || currentTab === 'community') {
      await templateApi.getFavorites().then(data => {
        store.favorites = data.list || []
      })
    }

    switch (currentTab) {
      case 'official':
        const officialData = await templateApi.getOfficialTemplates(params)
        store.officialTemplates = officialData.list || []
        totalCount.value = officialData.total || 0
        break
      case 'community':
        const communityData = await templateApi.getCommunityTemplates(params)
        store.communityTemplates = communityData.list || []
        totalCount.value = communityData.total || 0
        break
      case 'favorites':
        const favData = await templateApi.getFavorites()
        store.favorites = favData.list || []
        totalCount.value = store.favorites.length
        break
      case 'mine':
        const mineData = await templateApi.getMyTemplates()
        store.myTemplates = mineData.list || []
        totalCount.value = mineData.list?.length || 0
        break
    }
  } catch (error) {
    message.error('加载模板失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  loadData()
}

const handleSearchChange = () => {
  if (!searchKeyword.value) {
    loadData()
  }
}

const handleCategoryChange = (category) => {
  currentCategory.value = category
}

const handleSortChange = () => {
  loadData()
}

const handlePageChange = (page) => {
  currentPage.value = page
  loadData()
}

const handleTemplateClick = async (template) => {
  try {
    const detail = await templateApi.getTemplateDetail(template.id)
    selectedTemplate.value = detail
    showDetailModal.value = true

    editForm.value.isPublic = detail.is_public || false
    editForm.value.isOfficial = detail.is_official || false
    editFormOriginal.value.isPublic = detail.is_public || false
    editFormOriginal.value.isOfficial = detail.is_official || false

    try {
      const commentData = await templateApi.getTemplateComments(template.id)
      comments.value = commentData.list || []
    } catch {
      comments.value = []
    }

    try {
      const myRatingData = await templateApi.getMyRating(template.id)
      if (myRatingData) {
        userRatings.value[template.id] = myRatingData.rating
        myRating.value = myRatingData.rating
      } else {
        userRatings.value[template.id] = 0
        myRating.value = 0
      }
    } catch {
      userRatings.value[template.id] = 0
      myRating.value = 0
    }
  } catch {
    message.error('获取模板详情失败')
  }
}

const handleSaveSettings = async () => {
  if (!selectedTemplate.value) return
  
  savingSettings.value = true
  try {
    await templateApi.updateTemplate(selectedTemplate.value.id, {
      is_public: editForm.value.isPublic,
      is_official: editForm.value.isOfficial
    })
    
    selectedTemplate.value.is_public = editForm.value.isPublic
    selectedTemplate.value.is_official = editForm.value.isOfficial
    editFormOriginal.value.isPublic = editForm.value.isPublic
    editFormOriginal.value.isOfficial = editForm.value.isOfficial
    
    const newData = await templateApi.getMyTemplates()
    store.myTemplates = newData.list || []
    
    message.success('设置已保存')
  } catch {
    message.error('保存失败')
  } finally {
    savingSettings.value = false
  }
}

const handleFavoriteClick = (template) => {
  if (store.isFavorited(template.id)) {
    handleUnfavorite(template)
    return
  }
  if (userStore.isAdmin) {
    selectedTemplate.value = template
    favoriteForm.value.folderPath = ''
    showFavoriteModal.value = true
  } else {
    handleQuickFavorite(template)
  }
}

const handleQuickFavorite = async (template) => {
  try {
    await templateApi.addFavorite(template.id)
    message.success('收藏成功')
    await store.fetchFavorites()
  } catch {
    message.error('收藏失败')
  }
}

const confirmFavorite = async () => {
  if (!favoriteForm.value.folderPath) {
    message.error('请选择文件夹路径')
    return
  }
  favoriting.value = true
  try {
    await templateApi.addFavorite(selectedTemplate.value.id, favoriteForm.value.folderPath)
    message.success('收藏成功，已保存到提示词管理')
    showFavoriteModal.value = false
    await store.fetchFavorites()
  } catch (error) {
    message.error('收藏失败')
  } finally {
    favoriting.value = false
  }
}

const handleUnfavorite = async (template) => {
  try {
    await templateApi.removeFavorite(template.id)
    message.success('已取消收藏')
    await store.fetchFavorites()
  } catch (error) {
    message.error('操作失败')
  }
}

const handleFork = async (template) => {
  try {
    const forked = await templateApi.forkTemplate(template.id)
    message.success('Fork 成功')
    await loadData()
  } catch (error) {
    message.error('Fork 失败')
  }
}

const handleUseTemplate = (template) => {
  router.push({
    path: '/extensions/prompts',
    query: {
      template: template.id
    }
  })
}

const handleRate = async (template) => {
  try {
    await templateApi.rateTemplate(template.id, myRating.value)
    message.success('评分成功')
    userRatings.value[template.id] = myRating.value
    await loadData()
    const detail = await templateApi.getTemplateDetail(template.id)
    selectedTemplate.value = detail
  } catch (error) {
    message.error('评分失败')
  }
}

const handleComment = async () => {
  if (!newComment.value.trim()) return
  try {
    await templateApi.commentTemplate(selectedTemplate.value.id, newComment.value)
    message.success('评论成功')
    newComment.value = ''
    const commentData = await templateApi.getTemplateComments(selectedTemplate.value.id)
    comments.value = commentData.list || []
  } catch (error) {
    message.error('评论失败')
  }
}

const addVariable = () => {
  createForm.value.variables.push({
    name: '',
    type: 'string',
    default: '',
    description: ''
  })
}

const removeVariable = (idx) => {
  createForm.value.variables.splice(idx, 1)
}

const handleCreateTemplate = async () => {
  if (!createForm.value.name || !createForm.value.content) {
    message.error('请填写必填项')
    return
  }
  creating.value = true
  try {
    await templateApi.publishTemplate(createForm.value)
    message.success('创建成功')
    // showCreateModal.value = false
    createForm.value = {
      name: '',
      category: 'writing',
      description: '',
      tags: [],
      content: '',
      variables: [],
      is_public: false,
      is_pfficial: false
    }
    loadData()
  } catch (error) {
    message.error('创建失败')
  } finally {
    creating.value = false
  }
}

const getCategoryColor = (category) => {
  const colors = {
    writing: 'blue',
    programming: 'green',
    analysis: 'purple',
    translation: 'orange',
    office: 'cyan',
    education: 'gold',
    marketing: 'red'
  }
  return colors[category] || 'default'
}

const getCategoryName = (category) => {
  const cat = categories.find(c => c.key === category)
  return cat ? cat.name : category
}

const isFavorited = (templateId) => {
  return store.isFavorited(templateId)
}
</script>

<style scoped>
.template-market-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px;
  background: var(--bg-color, #f5f5f5);
}

.market-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left .page-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
}

.header-right {
  display: flex;
  gap: 12px;
  align-items: center;
}

.market-content {
  display: flex;
  flex: 1;
  gap: 20px;
  overflow: hidden;
}

.sidebar {
  width: 200px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 8px;
  padding: 16px;
}

.sidebar-section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 12px;
  color: #999;
  margin-bottom: 12px;
  text-transform: uppercase;
}

.template-menu {
  border: none;
}

.template-menu :deep(.ant-menu-item) {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  padding: 8px 12px;
  border-radius: 6px;
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
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  color: #666;
  transition: all 0.2s;
}

.category-item:hover {
  background: #f5f5f5;
}

.category-item.active {
  background: #e6f7ff;
  color: #1890ff;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  overflow: hidden;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.template-count {
  color: #999;
  font-size: 14px;
}

.template-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
  overflow-y: auto;
}

.empty-state,
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: #999;
  gap: 16px;
}

.pagination {
  display: flex;
  justify-content: center;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.template-detail-modal :deep(.ant-modal-body) {
  padding: 20px;
  max-height: 70vh;
  overflow: hidden;
}

.detail-content {
  height: 100%;
}

.detail-layout {
  display: flex;
  gap: 20px;
  height: 60vh;
}

.detail-preview {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.detail-preview h4 {
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.preview-content {
  flex: 1;
  background: #f5f5f5;
  border-radius: 6px;
  padding: 12px;
  overflow: auto;
  font-size: 13px;
  line-height: 1.6;
}

.preview-content pre {
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  font-family: 'Consolas', 'Monaco', monospace;
}

.detail-info {
  width: 300px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.detail-header {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detail-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  justify-content: space-between;
}

.author {
  font-size: 13px;
  color: #666;
}

.detail-actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

.detail-description h4,
.detail-rating h4,
.detail-variables h4,
.detail-comments h4,
.detail-stats h4 {
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 600;
}

.detail-description p {
  color: #666;
  font-size: 13px;
  margin: 0;
}

.rating-display {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rating-count {
  color: #999;
  font-size: 13px;
}

.my-rating {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.variable-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.comment-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 10px;
  max-height: 200px;
  overflow-y: auto;
}

.comment-item {
  display: flex;
  gap: 10px;
}

.comment-content {
  flex: 1;
  min-width: 0;
}

.comment-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.comment-author {
  font-weight: 500;
  font-size: 13px;
}

.comment-time {
  font-size: 11px;
  color: #999;
}

.comment-text {
  font-size: 13px;
  color: #666;
  margin: 0;
}

.comment-input {
  display: flex;
  gap: 8px;
}

.stats-row {
  display: flex;
  gap: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 16px;
  background: #f5f5f5;
  border-radius: 8px;
  flex: 1;
}

.stat-label {
  font-size: 11px;
  color: #999;
}

.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.detail-publish-settings {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.detail-publish-settings h4 {
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 600;
}

.publish-setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.setting-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #333;
}

.info-icon {
  color: #999;
  cursor: help;
}

.variable-definitions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.variable-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.switch-hint {
  margin-left: 8px;
  font-size: 12px;
  color: #999;
}

.lucide-icon-btn {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* Dark mode styles */
:global(.dark) .template-market-view {
  background: var(--bg-color, #141414);
}

:global(.dark) .sidebar {
  background: #1f1f1f;
}

:global(.dark) .section-title {
  color: #666;
}

:global(.dark) .category-item {
  color: #999;
}

:global(.dark) .category-item:hover {
  background: #2a2a2a;
}

:global(.dark) .category-item.active {
  background: #1f3a5f;
  color: #1890ff;
}

:global(.dark) .main-content {
  background: #1f1f1f;
}

:global(.dark) .template-count {
  color: #666;
}

:global(.dark) .empty-state,
:global(.dark) .loading-state {
  color: #666;
}

:global(.dark) .pagination {
  border-top-color: #303030;
}

:global(.dark) .preview-content {
  background: #2a2a2a;
}

:global(.dark) .detail-info h4 {
  color: #999;
}

:global(.dark) .info-row {
  color: #999;
}

:global(.dark) .info-value {
  color: #e5e5e5;
}

:global(.dark) .rating-stats {
  color: #999;
}

:global(.dark) .rating-value {
  color: #faad14;
}

:global(.dark) .detail-actions {
  border-top-color: #303030;
}

:global(.dark) .comment-item {
  border-bottom-color: #303030;
}

:global(.dark) .comment-author {
  color: #e5e5e5;
}

:global(.dark) .comment-time {
  color: #666;
}

:global(.dark) .comment-content {
  color: #ccc;
}

:global(.dark) .comment-form textarea {
  background: #2a2a2a;
  border-color: #434343;
  color: #e5e5e5;
}

:global(.dark) .create-modal :deep(.ant-modal-content) {
  background: #1f1f1f;
}

:global(.dark) .create-modal :deep(.ant-modal-header) {
  background: #1f1f1f;
}

:global(.dark) .create-modal :deep(.ant-modal-title) {
  color: #e5e5e5;
}

:global(.dark) .form-label {
  color: #999;
}

:global(.dark) .modal-actions {
  border-top-color: #303030;
}

:global(.dark) .favorite-folder-info {
  color: #999;
}
</style>
