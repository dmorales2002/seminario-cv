import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError } from '../api'

beforeEach(() => { localStorage.clear(); vi.restoreAllMocks() })

describe('cliente API', () => {
  it('envía el login como formulario OAuth2', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(
      JSON.stringify({ access_token: 'token', token_type: 'bearer' }),
      { status: 200, headers: { 'Content-Type': 'application/json' } },
    ))
    await api.login('user@example.com', 'secret')
    const options = fetchMock.mock.calls[0][1]
    expect(options.headers.get('Content-Type')).toBe('application/x-www-form-urlencoded')
    expect(options.body.toString()).toContain('username=user%40example.com')
  })

  it('incluye el token y propaga errores de negocio', async () => {
    localStorage.setItem('expediente_token', 'abc')
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(
      JSON.stringify({ detail: 'Vacante cerrada.' }),
      { status: 400, headers: { 'Content-Type': 'application/json' } },
    ))
    await expect(api.vacancies()).rejects.toEqual(expect.objectContaining({ message: 'Vacante cerrada.', status: 400 }))
    expect(fetchMock.mock.calls[0][1].headers.get('Authorization')).toBe('Bearer abc')
  })
})
