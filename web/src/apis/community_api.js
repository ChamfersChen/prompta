import {
  apiGet,
  apiPost,
  apiPut,
  apiDelete
} from './base'

const BASE_URL = '/api/community'

export const getPromptTemplates = async (params) => {
  return apiGet(`${BASE_URL}/prompts`, params)
}

export const getMyTemplates = async (params) => {
  return apiGet(`${BASE_URL}/mine`, params)
}

export const getTemplateDetail = async (templateId) => {
  return apiGet(`${BASE_URL}/${templateId}`)
}

export const publishPrompt = async (payload) => {
  return apiPost(`${BASE_URL}/publish/prompt`, payload)
}

export const updateTemplate = async (templateId, payload) => {
  return apiPut(`${BASE_URL}/${templateId}`, payload)
}

export const deleteTemplate = async (templateId) => {
  return apiDelete(`${BASE_URL}/${templateId}`)
}

export const unpublishTemplate = async (templateId) => {
  return apiPost(`${BASE_URL}/${templateId}/unpublish`)
}

export const forkTemplate = async (templateId) => {
  return apiPost(`${BASE_URL}/${templateId}/fork`)
}

export const exportTemplate = async (templateId) => {
  return apiGet(`${BASE_URL}/${templateId}/export`)
}

export const getFavorites = async (params) => {
  return apiGet(`${BASE_URL}/favorites`, params)
}

export const getFavoriteFolders = async (params) => {
  return apiGet(`${BASE_URL}/favorites/folders`, params)
}

export const renameFavoriteFolder = async (payload) => {
  return apiPut(`${BASE_URL}/favorites/folders/rename`, payload)
}

export const createFavoriteFolder = async (payload) => {
  return apiPost(`${BASE_URL}/favorites/folders`, payload)
}

export const deleteFavoriteFolder = async (payload) => {
  return apiDelete(`${BASE_URL}/favorites/folders`, {
    body: JSON.stringify(payload),
    headers: { 'Content-Type': 'application/json' }
  })
}

export const addFavorite = async (payload) => {
  return apiPost(`${BASE_URL}/favorites`, payload)
}

export const removeFavorite = async (templateId) => {
  return apiDelete(`${BASE_URL}/favorites/${templateId}`)
}

export const rateTemplate = async (templateId, rating) => {
  return apiPost(`${BASE_URL}/rate`, { template_id: templateId, rating })
}

export const getMyRating = async (templateId) => {
  return apiGet(`${BASE_URL}/rate/${templateId}`)
}

export const commentTemplate = async (templateId, content) => {
  return apiPost(`${BASE_URL}/${templateId}/comments`, { content })
}

export const getTemplateComments = async (templateId) => {
  return apiGet(`${BASE_URL}/${templateId}/comments`)
}

export const deleteComment = async (templateId, commentId) => {
  return apiDelete(`${BASE_URL}/${templateId}/comments/${commentId}`)
}

export const importTemplate = async (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return apiPost(`${BASE_URL}/import`, formData)
}

export const communityApi = {
  getPromptTemplates,
  getMyTemplates,
  getTemplateDetail,
  publishPrompt,
  updateTemplate,
  deleteTemplate,
  unpublishTemplate,
  forkTemplate,
  exportTemplate,
  getFavorites,
  getFavoriteFolders,
  createFavoriteFolder,
  deleteFavoriteFolder,
  renameFavoriteFolder,
  addFavorite,
  removeFavorite,
  rateTemplate,
  getMyRating,
  commentTemplate,
  getTemplateComments,
  deleteComment,
  importTemplate
}

export default communityApi
