import {
  apiGet,
  apiPost,
  apiPut,
  apiDelete,
  apiAdminGet,
  apiAdminPost
} from './base'

const BASE_URL = '/api/market'

// 获取官方模板列表
export const getOfficialTemplates = async (params) => {
  return apiGet(`${BASE_URL}/official`, params)
}

// 获取社区模板列表
export const getCommunityTemplates = async (params) => {
  return apiGet(`${BASE_URL}/community`, params)
}

// 获取模板详情
export const getTemplateDetail = async (templateId) => {
  return apiGet(`${BASE_URL}/${templateId}`)
}

// 获取我的收藏
export const getFavorites = async () => {
  return apiGet(`${BASE_URL}/favorites`)
}

// 收藏模板
export const addFavorite = async (templateId, folderPath = '') => {
  return apiPost(`${BASE_URL}/favorites`, { template_id: templateId, folder_path: folderPath })
}

// 取消收藏
export const removeFavorite = async (templateId) => {
  return apiDelete(`${BASE_URL}/favorites/${templateId}`)
}

// 评分模板
export const rateTemplate = async (templateId, rating) => {
  return apiPost(`${BASE_URL}/rate`, { template_id:templateId, rating: rating })
}

// 获取我的评分
export const getMyRating = async (templateId) => {
  return apiGet(`${BASE_URL}/rate/${templateId}`)
}

// 获取我的模板
export const getMyTemplates = async () => {
  return apiGet(`${BASE_URL}/mine`)
}

// 发布模板到社区
export const publishTemplate = async (template) => {
  return apiPost(`${BASE_URL}/publish`, template)
}

// 更新模板
export const updateTemplate = async (templateId, template) => {
  return apiPut(`${BASE_URL}/${templateId}`, template)
}

// 删除模板
export const deleteTemplate = async (templateId) => {
  return apiDelete(`${BASE_URL}/${templateId}`)
}

// Fork模板
export const forkTemplate = async (templateId) => {
  return apiPost(`${BASE_URL}/${templateId}/fork`)
}

// 导出模板
export const exportTemplate = async (templateId, format = 'json') => {
  return apiGet(`${BASE_URL}/${templateId}/export`, { format }, true, 'text')
}

// 导入模板
export const importTemplate = async (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return apiPost(`${BASE_URL}/import`, formData)
}

// 获取排行榜
export const getLeaderboard = async (type = 'popular', limit = 10) => {
  return apiGet(`${BASE_URL}/leaderboard`, { type, limit })
}

// 获取推荐模板
export const getRecommendedTemplates = async (limit = 10) => {
  return apiGet(`${BASE_URL}/recommended`, { limit })
}

// 评论模板
export const commentTemplate = async (templateId, content) => {
  return apiPost(`${BASE_URL}/${templateId}/comments`, { content })
}

// 获取模板评论
export const getTemplateComments = async (templateId) => {
  return apiGet(`${BASE_URL}/${templateId}/comments`)
}

// 删除评论
export const deleteComment = async (templateId, commentId) => {
  return apiDelete(`${BASE_URL}/${templateId}/comments/${commentId}`)
}