import client from './client'

export const listResources = async (slug) => (await client.get(`/api/v1/projects/${slug}/resources`)).data
export const createResource = async (slug, data) => (await client.post(`/api/v1/projects/${slug}/resources`, data)).data
export const updateResource = async (slug, id, data) => (await client.patch(`/api/v1/projects/${slug}/resources/${id}`, data)).data
export const deleteResource = async (slug, id) => client.delete(`/api/v1/projects/${slug}/resources/${id}`)
