import client from './client'

export const listPermissions = async (slug) => (await client.get(`/api/v1/projects/${slug}/permissions`)).data
export const createPermission = async (slug, data) => (await client.post(`/api/v1/projects/${slug}/permissions`, data)).data
export const updatePermission = async (slug, id, data) => (await client.patch(`/api/v1/projects/${slug}/permissions/${id}`, data)).data
export const deletePermission = async (slug, id) => client.delete(`/api/v1/projects/${slug}/permissions/${id}`)
export const assignPermissionToRole = async (slug, roleId, permId) =>
  client.post(`/api/v1/projects/${slug}/roles/${roleId}/permissions/${permId}`)
export const unassignPermissionFromRole = async (slug, roleId, permId) =>
  client.delete(`/api/v1/projects/${slug}/roles/${roleId}/permissions/${permId}`)
export const mapPermissionToResource = async (slug, permId, resId) =>
  client.post(`/api/v1/projects/${slug}/permissions/${permId}/resources/${resId}`)
export const unmapPermissionFromResource = async (slug, permId, resId) =>
  client.delete(`/api/v1/projects/${slug}/permissions/${permId}/resources/${resId}`)
