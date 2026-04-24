import client from './client'

export const listRoles = async (slug) => (await client.get(`/api/v1/projects/${slug}/roles`)).data
export const createRole = async (slug, data) => (await client.post(`/api/v1/projects/${slug}/roles`, data)).data
export const updateRole = async (slug, id, data) => (await client.patch(`/api/v1/projects/${slug}/roles/${id}`, data)).data
export const deleteRole = async (slug, id) => client.delete(`/api/v1/projects/${slug}/roles/${id}`)
export const addParent = async (slug, roleId, parentRoleId) =>
  client.post(`/api/v1/projects/${slug}/roles/${roleId}/parents`, { parent_role_id: parentRoleId })
export const removeParent = async (slug, roleId, parentId) =>
  client.delete(`/api/v1/projects/${slug}/roles/${roleId}/parents/${parentId}`)
