import client from './client'

export const simulateRole = async (slug, roleId) =>
  (await client.get(`/api/v1/projects/${slug}/simulate/${roleId}`)).data
