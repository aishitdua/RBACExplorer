import { describe, it, expect, vi, beforeEach } from 'vitest'
import client from './client'
import { createProject, getProject } from './projects'

vi.mock('./client')

describe('projects API', () => {
  beforeEach(() => vi.clearAllMocks())

  it('createProject posts to /api/v1/projects', async () => {
    client.post = vi.fn().mockResolvedValue({ data: { slug: 'my-app', name: 'My App' } })
    const result = await createProject({ name: 'My App' })
    expect(client.post).toHaveBeenCalledWith('/api/v1/projects', { name: 'My App' })
    expect(result.slug).toBe('my-app')
  })

  it('getProject fetches by slug', async () => {
    client.get = vi.fn().mockResolvedValue({ data: { slug: 'my-app' } })
    const result = await getProject('my-app')
    expect(client.get).toHaveBeenCalledWith('/api/v1/projects/my-app')
    expect(result.slug).toBe('my-app')
  })
})
