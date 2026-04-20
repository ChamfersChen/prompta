import {
  apiAdminGet,
  apiSuperAdminDelete,
  apiSuperAdminGet,
  apiSuperAdminPost,
  apiSuperAdminPut,
  apiGet,
  apiPost,
  apiPut,
  apiDelete
} from './base'

const BASE_URL = '/api/system/prompts'

export const listPrompts = async () => {
  return apiAdminGet(BASE_URL)
}

export const getPromptTree = async () => {
  return apiGet(`${BASE_URL}/tree`)
}

export const getPromptFile = async (path) => {
  return apiGet(`${BASE_URL}/file?path=${encodeURIComponent(path)}`)
}

export const createPromptFile = async (payload) => {
  return apiPost(`${BASE_URL}/file`, payload)
}

export const updatePromptFile = async (payload) => {
  return apiPut(`${BASE_URL}/file`, payload)
}

export const deletePromptFile = async (path) => {
  return apiDelete(`${BASE_URL}/file?path=${encodeURIComponent(path)}`)
}

export const renamePromptNode = async (payload) => {
  return apiPut(`${BASE_URL}/rename`, payload)
}

export const getPromptTestCapability = async () => {
  return apiGet(`${BASE_URL}/test-capability`)
}

export const testPrompt = async (payload) => {
  return apiPost(`${BASE_URL}/test`, payload)
}

export const promptApi = {
  listPrompts,
  getPromptTree,
  getPromptFile,
  createPromptFile,
  updatePromptFile,
  deletePromptFile,
  renamePromptNode,
  getPromptTestCapability,
  testPrompt
}

export default promptApi