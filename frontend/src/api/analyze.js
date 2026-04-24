import client from './client'

export const analyzeProject = async (slug) => (await client.get(`/api/v1/projects/${slug}/analyze`)).data
