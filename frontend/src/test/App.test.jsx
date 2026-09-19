import React from 'react'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App, { EvidenceCard } from '../App'
import { api } from '../api'

vi.mock('../api', () => ({
  api: {
    me: vi.fn(),
    myVacancies: vi.fn(),
  },
}))

beforeEach(() => localStorage.clear())
afterEach(cleanup)

describe('autenticación', () => {
  it('muestra el acceso con el principio de decisión humana', () => {
    render(<MemoryRouter initialEntries={['/login']}><App /></MemoryRouter>)
    expect(screen.getByRole('heading', { name: /Talento visible/i })).toBeInTheDocument()
    expect(screen.getByText(/Usted conserva la decisión/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ingresar' })).toBeInTheDocument()
  })

  it('permite elegir el rol durante el registro', () => {
    render(<MemoryRouter initialEntries={['/register']}><App /></MemoryRouter>)
    expect(screen.getByRole('radio', { name: 'Candidato' })).toBeChecked()
    expect(screen.getByRole('radio', { name: 'Reclutador' })).toBeInTheDocument()
  })
})

describe('panel del reclutador', () => {
  it('permanece visible en StrictMode después de restaurar la sesión', async () => {
    localStorage.setItem('expediente_token', 'token-de-prueba')
    api.me.mockResolvedValue({ full_name: 'Reclutadora Demo', role: 'RECRUITER' })
    api.myVacancies.mockResolvedValue([])

    render(
      <React.StrictMode>
        <MemoryRouter initialEntries={['/recruiter']}><App /></MemoryRouter>
      </React.StrictMode>,
    )

    expect(await screen.findByRole('heading', { name: 'Mis vacantes' })).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('Aún no hay vacantes')).toBeInTheDocument())
  })
})

describe('evidencia explicable', () => {
  it('presenta el peso, contribución y cita exacta', () => {
    render(<EvidenceCard factor={{
      criterion: 'Python', kind: 'SKILL', weight: 75, match_strength: 1,
      contribution: 75, evidence_quote: 'Desarrollé servicios con Python.',
      evidence_section: 'Experiencia', rationale: 'Coincidencia directa.',
    }} />)
    expect(screen.getByText('Python')).toBeInTheDocument()
    expect(screen.getByText(/Peso 0.75 · \+75/)).toBeInTheDocument()
    expect(screen.getByText(/Desarrollé servicios con Python/)).toBeInTheDocument()
    expect(screen.getByText('CUBIERTO')).toBeInTheDocument()
  })
})
