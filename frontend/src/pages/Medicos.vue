<template>
  <header class="titulo">
    <h1>Encontre um médico</h1>
    <p class="sub">Busque por nome ou especialidade e veja os horários disponíveis no calendário.</p>
  </header>

  <div class="filtros">
    <input v-model="busca" type="search" placeholder="Buscar por nome…" aria-label="Buscar por nome" />
    <select v-model="especialidade" aria-label="Especialidade">
      <option value="">Todas as especialidades</option>
      <option v-for="e in especialidades" :key="e" :value="e">{{ e }}</option>
    </select>
  </div>

  <p v-if="erro" class="alert erro">{{ erro }}</p>
  <p v-else-if="carregando && !medicos.length" class="muted">Carregando…</p>
  <p v-else-if="!medicos.length" class="muted">Nenhum médico encontrado.</p>

  <ul class="lista">
    <li v-for="m in medicos" :key="m.id" class="card medico">
      <div>
        <h2>{{ m.nome }}</h2>
        <p class="sub">{{ m.especialidade }}</p>
        <p class="livres" :class="{ nenhum: !m.horarios_livres }">
          {{ m.horarios_livres ? `${m.horarios_livres} horário(s) livre(s)` : 'Sem horários livres' }}
        </p>
      </div>
      <RouterLink :to="`/calendario/${m.id}`" class="btn">Ver agenda</RouterLink>
    </li>
  </ul>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { api } from '../api'

const busca = ref('')
const especialidade = ref('')
const medicos = ref([])
const especialidades = ref([])
const carregando = ref(false)
const erro = ref('')

async function carregar() {
  carregando.value = true
  erro.value = ''
  try {
    medicos.value = await api('/medicos', {
      params: { q: busca.value.trim(), especialidade: especialidade.value },
    })
  } catch (e) {
    erro.value = e.message
  } finally {
    carregando.value = false
  }
}

// Espera o usuário parar de digitar antes de buscar
let temporizador
watch([busca, especialidade], () => {
  clearTimeout(temporizador)
  temporizador = setTimeout(carregar, 250)
})

onMounted(async () => {
  try {
    especialidades.value = await api('/especialidades')
  } catch {
    /* o filtro de especialidade só fica vazio */
  }
  carregar()
})
</script>

<style scoped>
.titulo {
  margin-bottom: 18px;
}
.filtros {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 12px;
  margin-bottom: 18px;
}
.lista {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 14px;
}
.medico {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}
.livres {
  margin: 6px 0 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--livre-tx);
}
.livres.nenhum {
  color: var(--suave);
  font-weight: 400;
}
@media (max-width: 560px) {
  .filtros {
    grid-template-columns: 1fr;
  }
}
</style>
