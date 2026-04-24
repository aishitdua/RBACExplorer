import client from './client'

export const createProject = async (data) => (await client.post('/api/v1/projects', data)).data
export const getProject = async (slug) => (await client.get(`/api/v1/projects/${slug}`)).data
export const deleteProject = async (slug) => client.delete(`/api/v1/projects/${slug}`)
