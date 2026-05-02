import client from './client'

export const exportFastapi = async (slug) =>
  (await client.get(`/api/v1/projects/${slug}/export/fastapi`)).data

export const exportYaml = async (slug) => {
  const response = await client.get(`/api/v1/projects/${slug}/export/yaml`, {
    responseType: 'blob',
  })
  return response.data
}
