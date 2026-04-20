import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { apiGet, apiPost, apiPut, apiDelete } from '@/apis/base'

const BASE = '/api/community'

export const useCommunityStore = defineStore('community', () => {
  const promptTemplates = ref([])
  const favorites = ref([])
  const myTemplates = ref([])
  const favoriteFolders = ref([])
  const currentCategory = ref('all')
  const searchKeyword = ref('')
  const loading = ref(false)
  const pagination = ref({
    current: 1,
    pageSize: 20,
    total: 0
  })

  const categories = ref([
    { key: 'all', name: '全部', type: 'both' },
    { key: 'writing', name: '写作', type: 'both' },
    { key: 'programming', name: '编程', type: 'both' },
    { key: 'analysis', name: '分析', type: 'both' },
    { key: 'translation', name: '翻译', type: 'both' },
    { key: 'office', name: '办公', type: 'both' },
    { key: 'education', name: '教育', type: 'both' },
    { key: 'marketing', name: '营销', type: 'both' }
  ])

  const filteredPromptTemplates = computed(() => {
    let result = promptTemplates.value
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

  async function fetchPromptTemplates(params = {}) {
    loading.value = true
    try {
      const data = await apiGet(`${BASE}/prompts`, {
        category: currentCategory.value !== 'all' ? currentCategory.value : undefined,
        keyword: searchKeyword.value || undefined,
        page: pagination.value.current,
        pageSize: pagination.value.pageSize,
        ...params
      })
      promptTemplates.value = data.list || []
      pagination.value.total = data.total || 0
    } catch (error) {
      console.error('获取提示词社区失败:', error)
    } finally {
      loading.value = false
    }
  }

  async function fetchFavorites(itemType) {
    try {
      const params = itemType ? { item_type: itemType } : {}
      const data = await apiGet(`${BASE}/favorites`, params)
      favorites.value = data.list || []
    } catch (error) {
      console.error('获取收藏失败:', error)
    }
  }

  async function fetchFavoriteFolders(itemType) {
    try {
      const params = itemType ? { item_type: itemType } : {}
      const data = await apiGet(`${BASE}/favorites/folders`, params)
      favoriteFolders.value = data.folders || []
    } catch (error) {
      console.error('获取收藏夹失败:', error)
    }
  }

  async function fetchMyTemplates(communityType) {
    try {
      const params = communityType ? { community_type: communityType } : {}
      const data = await apiGet(`${BASE}/mine`, params)
      myTemplates.value = data.list || []
    } catch (error) {
      console.error('获取我的模板失败:', error)
    }
  }

  function isFavorited(templateId) {
    return favorites.value.some(f => f.id === templateId)
  }

  function setCategory(category) {
    currentCategory.value = category
  }

  function setSearchKeyword(keyword) {
    searchKeyword.value = keyword
  }

  function resetFilters() {
    currentCategory.value = 'all'
    searchKeyword.value = ''
    pagination.value.current = 1
  }

  return {
    promptTemplates,
    favorites,
    myTemplates,
    favoriteFolders,
    currentCategory,
    searchKeyword,
    loading,
    pagination,
    categories,
    filteredPromptTemplates,
    fetchPromptTemplates,
    fetchFavorites,
    fetchFavoriteFolders,
    fetchMyTemplates,
    isFavorited,
    setCategory,
    setSearchKeyword,
    resetFilters
  }
})