<template>
  <form class="card auth-card" @submit.prevent="enviar">
    <h1>Entrar</h1>

    <p v-if="erro" class="alert erro">{{ erro }}</p>

    <label class="campo">
      E-mail
      <input v-model="email" type="email" autocomplete="email" required />
    </label>
    <label class="campo">
      Senha
      <input v-model="senha" type="password" autocomplete="current-password" required />
    </label>

    <button class="btn" :disabled="carregando">{{ carregando ? 'Entrando…' : 'Entrar' }}</button>

    <p class="rodape">Ainda não tem conta? <RouterLink to="/cadastro">Cadastre-se</RouterLink></p>
  </form>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { entrar, paginaInicial } from '../auth'

const router = useRouter()
const email = ref('')
const senha = ref('')
const erro = ref('')
const carregando = ref(false)

async function enviar() {
  erro.value = ''
  carregando.value = true
  try {
    const resposta = await api('/auth/login', {
      method: 'POST',
      body: { email: email.value, senha: senha.value },
    })
    entrar(resposta)
    router.push(paginaInicial(resposta.usuario.papel))
  } catch (e) {
    erro.value = e.message
  } finally {
    carregando.value = false
  }
}
</script>
