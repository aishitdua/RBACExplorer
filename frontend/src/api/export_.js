import client from './client'

export const exportFastapi = async (slug) =>
  (await client.get(`/api/v1/projects/${slug}/export/fastapi`)).data
