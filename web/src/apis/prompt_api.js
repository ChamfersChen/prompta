import {
  apiAdminGet,
  apiSuperAdminDelete,
  apiSuperAdminGet,
  apiSuperAdminPost,
  apiSuperAdminPut
} from './base'

const BASE_URL = '/api/system/prompts'

export const listPrompts = async () => {
  return apiAdminGet(BASE_URL)
}

export const importSkillZip = async (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return apiSuperAdminPost(`${BASE_URL}/import`, formData)
}

export const getSkillDependencyOptions = async () => {
  return apiSuperAdminGet(`${BASE_URL}/dependency-options`)
}

export const getSkillTree = async (slug) => {
  return apiSuperAdminGet(`${BASE_URL}/${encodeURIComponent(slug)}/tree`)
}

export const getPromptTree = async () => {
  return apiSuperAdminGet(`${BASE_URL}/tree`)
}

export const createPromptFile = async (payload) => {
  return apiSuperAdminPost(`${BASE_URL}/file`, payload)
}

export const getSkillFile = async (slug, path) => {
  return apiSuperAdminGet(
    `${BASE_URL}/${encodeURIComponent(slug)}/file?path=${encodeURIComponent(path)}`
  )
}

export const getPromptFile = async (path) => {
  return apiSuperAdminGet(
    `${BASE_URL}/file?path=${encodeURIComponent(path)}`
  )
}

export const createSkillFile = async (slug, payload) => {
  return apiSuperAdminPost(`${BASE_URL}/${encodeURIComponent(slug)}/file`, payload)
}


export const updateSkillFile = async (slug, payload) => {
  return apiSuperAdminPut(`${BASE_URL}/${encodeURIComponent(slug)}/file`, payload)
}

export const updatePromptFile = async (payload) => {
  return apiSuperAdminPut(`${BASE_URL}/file`, payload)
}

export const updateSkillDependencies = async (slug, payload) => {
  return apiSuperAdminPut(`${BASE_URL}/${encodeURIComponent(slug)}/dependencies`, payload)
}

export const deleteSkillFile = async (slug, path) => {
  return apiSuperAdminDelete(
    `${BASE_URL}/${encodeURIComponent(slug)}/file?path=${encodeURIComponent(path)}`
  )
}

export const deletePromptFile = async (path) => {
  return apiSuperAdminDelete(
    `${BASE_URL}/file?path=${encodeURIComponent(path)}`
  )
}

export const exportSkill = async (slug) => {
  return apiSuperAdminGet(`${BASE_URL}/${encodeURIComponent(slug)}/export`, {}, 'blob')
}

export const deleteSkill = async (slug) => {
  return apiSuperAdminDelete(`${BASE_URL}/${encodeURIComponent(slug)}`)
}

export const promptApi = {
  importSkillZip,
  getSkillDependencyOptions,
  getSkillTree,
  getSkillFile,
  getPromptFile,
  createSkillFile,
  getPromptTree,
  createPromptFile,
  updateSkillFile,
  updatePromptFile,
  updateSkillDependencies,
  deleteSkillFile,
  deletePromptFile,
  exportSkill,
  deleteSkill
}

export default promptApi
