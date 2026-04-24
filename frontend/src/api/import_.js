import client from './client'

export const importOpenapi = async (slug, openapiJson) =>
  (await client.post(`/api/v1/projects/${slug}/import/openapi`, openapiJson)).data
