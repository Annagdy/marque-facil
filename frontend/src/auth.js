import { reactive } from 'vue'

// Sessão do usuário logado (token + dados), guardada no navegador.
const CHAVE = 'marquefacil_sessao'

function lerSalva() {
  try {
    return JSON.parse(localStorage.getItem(CHAVE)) || {}
  } catch {
    return {}
  }
}

const salva = lerSalva()

export const auth = reactive({
  token: salva.token ?? null,
  usuario: salva.usuario ?? null,
})

export function entrar({ access_token, usuario }) {
  auth.token = access_token
  auth.usuario = usuario
  try {
    localStorage.setItem(CHAVE, JSON.stringify({ token: access_token, usuario }))
  } catch {
    /* sem localStorage: a sessão vale só até recarregar a página */
  }
}

export function sair() {
  auth.token = null
  auth.usuario = null
  try {
    localStorage.removeItem(CHAVE)
  } catch {
    /* ignora */
  }
}

// Médico começa na própria agenda; paciente começa buscando médicos.
export function paginaInicial(papel) {
  return papel === 'medico' ? '/calendario' : '/medicos'
}
