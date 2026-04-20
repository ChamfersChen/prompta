import { apiAdminDelete, apiAdminGet, apiAdminPost, apiAdminPut } from './base'

const BASE_URL = '/api/system/api-keys'

export const listApiKeys = async () => {
  return apiAdminGet(BASE_URL)
}

export const createApiKey = async (payload) => {
  return apiAdminPost(BASE_URL, payload)
}

export const setApiKeyEnabled = async (keyId, is_enabled) => {
  return apiAdminPut(`${BASE_URL}/${keyId}/enabled`, { is_enabled })
}

export const deleteApiKey = async (keyId) => {
  return apiAdminDelete(`${BASE_URL}/${keyId}`)
}

export const apiKeyApi = {
  listApiKeys,
  createApiKey,
  setApiKeyEnabled,
  deleteApiKey
}

export default apiKeyApi
