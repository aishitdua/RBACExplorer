import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import HomePage from './HomePage'
import * as projectsApi from '../api/projects'

vi.mock('../api/projects')

describe('HomePage', () => {
  it('renders create project form', () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    )
    expect(screen.getByPlaceholderText(/project name/i)).toBeInTheDocument()
  })

  it('creates a project and redirects', async () => {
    projectsApi.createProject.mockResolvedValue({ slug: 'my-app', name: 'My App' })
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    )
    fireEvent.change(screen.getByPlaceholderText(/project name/i), { target: { value: 'My App' } })
    fireEvent.click(screen.getByRole('button', { name: /create/i }))
    await waitFor(() =>
      expect(projectsApi.createProject).toHaveBeenCalledWith({ name: 'My App', description: '' })
    )
  })
})
