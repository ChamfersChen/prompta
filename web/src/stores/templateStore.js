import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { apiGet, apiPost, apiPut, apiDelete, apiAdminGet } from '@/apis/base'

export const useTemplateStore = defineStore('template', () => {
  // 官方模板库
  const officialTemplates = ref([])
  // 社区模板
  const communityTemplates = ref([])
  // 我的收藏
  const favorites = ref([])
  // 我的模板
  const myTemplates = ref([])
  // 当前分类
  const currentCategory = ref('all')
  // 搜索关键词
  const searchKeyword = ref('')
  // 加载状态
  const loading = ref(false)
  // 分页
  const pagination = ref({
    current: 1,
    pageSize: 20,
    total: 0
  })

  // 分类列表
  const categories = ref([
    { key: 'all', name: '全部', icon: 'AppWindow' },
    { key: 'writing', name: '写作', icon: 'FileText' },
    { key: 'programming', name: '编程', icon: 'Code' },
    { key: 'analysis', name: '分析', icon: 'BarChart' },
    { key: 'translation', name: '翻译', icon: 'Globe' },
    { key: 'office', name: '办公', icon: 'Briefcase' },
    { key: 'education', name: '教育', icon: 'GraduationCap' },
    { key: 'marketing', name: '营销', icon: 'Megaphone' }
  ])

  // 筛选后的官方模板
  const filteredOfficialTemplates = computed(() => {
    let result = officialTemplates.value
    if (currentCategory.value !== 'all') {
      result = result.filter(t => t.category === currentCategory.value)
    }
    if (searchKeyword.value) {
      const keyword = searchKeyword.value.toLowerCase()
      result = result.filter(t => 
        t.name.toLowerCase().includes(keyword) || 
        t.description.toLowerCase().includes(keyword) ||
        t.tags?.some(tag => tag.toLowerCase().includes(keyword))
      )
    }
    return result
  })

  // 筛选后的社区模板
  const filteredCommunityTemplates = computed(() => {
    let result = communityTemplates.value
    if (currentCategory.value !== 'all') {
      result = result.filter(t => t.category === currentCategory.value)
    }
    if (searchKeyword.value) {
      const keyword = searchKeyword.value.toLowerCase()
      result = result.filter(t => 
        t.name.toLowerCase().includes(keyword) || 
        t.description.toLowerCase().includes(keyword) ||
        t.tags?.some(tag => tag.toLowerCase().includes(keyword))
      )
    }
    return result
  })

  // 获取官方模板
  async function fetchOfficialTemplates() {
    loading.value = true
    try {
      const data = await apiGet('/api/market/official', {
        category: currentCategory.value,
        page: pagination.value.current,
        pageSize: pagination.value.pageSize
      })
      officialTemplates.value = data.list || []
      pagination.value.total = data.total || 0
    } catch (error) {
      console.error('获取官方模板失败:', error)
    } finally {
      loading.value = false
    }
  }

  // 获取社区模板
  async function fetchCommunityTemplates() {
    loading.value = true
    try {
      const data = await apiGet('/api/market/community', {
        category: currentCategory.value,
        keyword: searchKeyword.value,
        page: pagination.value.current,
        pageSize: pagination.value.pageSize
      })
      communityTemplates.value = data.list || []
      pagination.value.total = data.total || 0
    } catch (error) {
      console.error('获取社区模板失败:', error)
    } finally {
      loading.value = false
    }
  }

  // 获取我的收藏
  async function fetchFavorites() {
    try {
      const data = await apiGet('/api/market/favorites')
      favorites.value = data.list || []
    } catch (error) {
      console.error('获取收藏失败:', error)
    }
  }

  // 获取我的模板
  async function fetchMyTemplates() {
    try {
      const data = await apiGet('/api/market/mine')
      myTemplates.value = data.list || []
    } catch (error) {
      console.error('获取我的模板失败:', error)
    }
  }

  // 收藏模板
  async function favoriteTemplate(templateId) {
    try {
      await apiPost('/api/market/favorites', { template_id: templateId })
      const template = [...officialTemplates.value, ...communityTemplates.value].find(t => t.id === templateId)
      if (template && !favorites.value.find(f => f.id === templateId)) {
        favorites.value.push(template)
      }
    } catch (error) {
      console.error('收藏失败:', error)
    }
  }

  // 取消收藏
  async function unfavoriteTemplate(templateId) {
    try {
      await apiDelete(`/api/market/favorites/${templateId}`)
      favorites.value = favorites.value.filter(f => f.id !== templateId)
    } catch (error) {
      console.error('取消收藏失败:', error)
    }
  }

  // 检查是否已收藏
  function isFavorited(templateId) {
    return favorites.value.some(f => f.id === templateId)
  }

  // 评分模板
  async function rateTemplate(templateId, rating) {
    try {
      console.log(`评分模板 ${templateId}，评分: ${rating}`)
      await apiPost('/api/market/rate', { template_id: templateId, rating })
      const updateList = list => {
        const idx = list.findIndex(t => t.id === templateId)
        if (idx !== -1) {
          list[idx].userRating = rating
          list[idx].rating = (list[idx].rating * list[idx].ratingCount + rating) / (list[idx].ratingCount + 1)
          list[idx].ratingCount++
        }
      }
      updateList(officialTemplates.value)
      updateList(communityTemplates.value)
    } catch (error) {
      console.error('评分失败:', error)
    }
  }

  // 发布模板到社区
  async function publishTemplate(template) {
    try {
      const data = await apiPost('/api/market/publish', template)
      myTemplates.value.unshift(data)
      return data
    } catch (error) {
      console.error('发布模板失败:', error)
      throw error
    }
  }

  // 导入模板
  async function importTemplate(templateData) {
    try {
      const data = await apiPost('/api/market/import', templateData)
      myTemplates.value.unshift(data)
      return data
    } catch (error) {
      console.error('导入模板失败:', error)
      throw error
    }
  }

  // 导出模板
  async function exportTemplate(templateId) {
    try {
      const data = await apiGet(`/api/market/${templateId}/export`)
      return data
    } catch (error) {
      console.error('导出模板失败:', error)
      throw error
    }
  }

  // Fork模板
  async function forkTemplate(templateId) {
    try {
      const data = await apiPost(`/api/market/${templateId}/fork`)
      myTemplates.value.unshift(data)
      return data
    } catch (error) {
      console.error('Fork模板失败:', error)
      throw error
    }
  }

  // 设置分类
  function setCategory(category) {
    currentCategory.value = category
  }

  // 设置搜索关键词
  function setSearchKeyword(keyword) {
    searchKeyword.value = keyword
  }

  // 重置筛选
  function resetFilters() {
    currentCategory.value = 'all'
    searchKeyword.value = ''
    pagination.value.current = 1
  }

  return {
    officialTemplates,
    communityTemplates,
    favorites,
    myTemplates,
    currentCategory,
    searchKeyword,
    loading,
    pagination,
    categories,
    filteredOfficialTemplates,
    filteredCommunityTemplates,
    fetchOfficialTemplates,
    fetchCommunityTemplates,
    fetchFavorites,
    fetchMyTemplates,
    favoriteTemplate,
    unfavoriteTemplate,
    isFavorited,
    rateTemplate,
    publishTemplate,
    importTemplate,
    exportTemplate,
    forkTemplate,
    setCategory,
    setSearchKeyword,
    resetFilters
  }
})