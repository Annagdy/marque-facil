<template>
  <form class="card auth-card" @submit.prevent="enviar">
    <h1>Criar conta</h1>

    <p v-if="erro" class="alert erro">{{ erro }}</p>

    <div class="papeis">
      <label :class="{ on: form.papel === 'paciente' }">
        <input v-model="form.papel" type="radio" value="paciente" />
        Sou paciente
      </label>
      <label :class="{ on: form.papel === 'medico' }">
        <input v-model="form.papel" type="radio" value="medico" />
        Sou médico
      </label>
    </div>

    <label class="campo">
      Nome completo
      <input v-model="form.nome" type="text" autocomplete="name" required minlength="2" />
    </label>
    <label class="campo">
      E-mail
      <input v-model="form.email" type="email" autocomplete="email" required />
    </label>
    <label v-if="form.papel === 'medico'" class="campo">
      Especialidade
      <input v-model="form.especialidade" type="text" placeholder="Ex.: Cardiologia" required />
    </label>
    <label class="campo">
      Senha (mínimo 6 caracteres)
      <input v-model="form.senha" type="password" autocomplete="new-password" required minlength="6" maxlength="72" />
    </label>

    <button class="btn" :disabled="carregando">{{ carregando ? 'Criando…' : 'Criar conta' }}</button>

    <p class="rodape">Já tem conta? <RouterLink to="/login">Entrar</RouterLink></p>
  </form>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { entrar, paginaInicial } from '../auth'

const router = useRouter()
const erro = ref('')
const carregando = ref(false)
const form = reactive({ papel: 'paciente', nome: '', email: '', especialidade: '', senha: '' })

async function enviar() {
  erro.value = ''
  carregando.value = true
  try {
    const resposta = await api('/auth/cadastro', {
      method: 'POST',
      body: {
        papel: form.papel,
        nome: form.nome,
        email: form.email,
        senha: form.senha,
        especialidade: form.papel === 'medico' ? form.especialidade : null,
      },
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

<style scoped>
.papeis {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 18px;
}
.papeis label {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid var(--borda);
  border-radius: 9px;
  cursor: pointer;
  font-weight: 600;
}
.papeis label.on {
  border-color: var(--primaria);
  background: var(--primaria-clara);
  color: var(--primaria);
}
.papeis input {
  width: auto;
}
</style>
