import { auth, sair } from './auth'

// Todas as chamadas usam o caminho relativo /api (mesmo domínio em produção,
// proxy do Vite em desenvolvimento). Nenhum endereço fixo no código.

export class ApiError extends Error {
  constructor(mensagem, status) {
    super(mensagem)
    this.status = status
  }
}

function textoDoErro(detail) {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) {
    // Erros de validação do FastAPI/Pydantic (422)
    const msg = detail[0]?.msg ?? 'Dados inválidos.'
    return msg.replace(/^Value error, /, '')
  }
  return 'Ocorreu um erro. Tente novamente.'
}

export async function api(caminho, { method = 'GET', body, params } = {}) {
  let url = '/api' + caminho
  if (params) {
    const qs = new URLSearchParams()
    for (const [chave, valor] of Object.entries(params)) {
      if (valor !== '' && valor != null) qs.set(chave, valor)
    }
    const texto = qs.toString()
    if (texto) url += '?' + texto
  }

  const headers = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (auth.token) headers.Authorization = `Bearer ${auth.token}`

  let resposta
  try {
    resposta = await fetch(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError('Não foi possível conectar ao servidor.', 0)
  }

  if (resposta.status === 204) return null

  let dados = null
  try {
    dados = await resposta.json()
  } catch {
    /* resposta sem corpo JSON */
  }

  if (!resposta.ok) {
    // Token expirado: volta para o login (exceto na própria tela de login/cadastro)
    if (resposta.status === 401 && auth.token && !caminho.startsWith('/auth/')) {
      sair()
      window.location.assign('/login')
    }
    throw new ApiError(textoDoErro(dados?.detail), resposta.status)
  }
  return dados
}
