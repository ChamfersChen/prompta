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

const BASE_URL = '/api/system/skills'

export const listSkills = async () => {
  return apiGet(BASE_URL)
}

export const importSkillZip = async (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return apiPost(`${BASE_URL}/import`, formData)
}

export const getSkillDependencyOptions = async () => {
  return apiGet(`${BASE_URL}/dependency-options`)
}

export const getSkillTree = async (slug) => {
  return apiGet(`${BASE_URL}/${encodeURIComponent(slug)}/tree`)
}


export const getSkillFile = async (slug, path) => {
  return apiGet(
    `${BASE_URL}/${encodeURIComponent(slug)}/file?path=${encodeURIComponent(path)}`
  )
}

export const createSkillFile = async (slug, payload) => {
  return apiPost(`${BASE_URL}/${encodeURIComponent(slug)}/file`, payload)
}

export const updateSkillFile = async (slug, payload) => {
  return apiPut(`${BASE_URL}/${encodeURIComponent(slug)}/file`, payload)
}

export const updateSkillDependencies = async (slug, payload) => {
  return apiPut(`${BASE_URL}/${encodeURIComponent(slug)}/dependencies`, payload)
}

export const deleteSkillFile = async (slug, path) => {
  return apiDelete(
    `${BASE_URL}/${encodeURIComponent(slug)}/file?path=${encodeURIComponent(path)}`
  )
}

export const exportSkill = async (slug) => {
  return apiGet(`${BASE_URL}/${encodeURIComponent(slug)}/export`, {}, 'blob')
}

export const deleteSkill = async (slug) => {
  return apiDelete(`${BASE_URL}/${encodeURIComponent(slug)}`)
}

export const skillApi = {
  listSkills,
  importSkillZip,
  getSkillDependencyOptions,
  getSkillTree,
  getSkillFile,
  createSkillFile,
  updateSkillFile,
  updateSkillDependencies,
  deleteSkillFile,
  exportSkill,
  deleteSkill
}

export default skillApi