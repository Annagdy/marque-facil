<template>
  <header class="titulo">
    <h1>{{ ehMedico ? 'Consultas marcadas' : 'Minhas consultas' }}</h1>
    <p class="sub">
      {{ ehMedico ? 'Pacientes que marcaram horário na sua agenda.' : 'Consultas que você marcou.' }}
    </p>
  </header>

  <p v-if="erro" class="alert erro">{{ erro }}</p>
  <p v-if="aviso" class="alert ok">{{ aviso }}</p>
  <p v-if="carregando" class="muted">Carregando…</p>

  <template v-else>
    <h2 class="secao">Próximas</h2>
    <p v-if="!proximas.length" class="muted">Nenhuma consulta futura.</p>
    <ul class="lista">
      <li v-for="c in proximas" :key="c.id" class="card item">
        <div class="quando">
          <strong>{{ dataCurta(c.inicio) }}</strong>
          <span>{{ hora(c.inicio) }} – {{ hora(c.fim) }}</span>
        </div>
        <div class="quem">
          <strong>{{ ehMedico ? c.paciente_nome : c.medico_nome }}</strong>
          <span v-if="!ehMedico" class="sub">{{ c.especialidade }}</span>
        </div>
        <button class="btn perigo small" @click="cancelar(c)">Cancelar</button>
      </li>
    </ul>

    <template v-if="passadas.length">
      <h2 class="secao">Anteriores</h2>
      <ul class="lista passadas">
        <li v-for="c in passadas" :key="c.id" class="card item">
          <div class="quando">
            <strong>{{ dataCurta(c.inicio) }}</strong>
            <span>{{ hora(c.inicio) }} – {{ hora(c.fim) }}</span>
          </div>
          <div class="quem">
            <strong>{{ ehMedico ? c.paciente_nome : c.medico_nome }}</strong>
            <span v-if="!ehMedico" class="sub">{{ c.especialidade }}</span>
          </div>
        </li>
      </ul>
    </template>
  </template>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { auth } from '../auth'

const ehMedico = computed(() => auth.usuario?.papel === 'medico')
const consultas = ref([])
const carregando = ref(true)
const erro = ref('')
const aviso = ref('')

// Próximas em ordem crescente; anteriores da mais recente para a mais antiga
const proximas = computed(() => consultas.value.filter((c) => !c.passada))
const passadas = computed(() => consultas.value.filter((c) => c.passada).reverse())

const SEMANA = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb']

function dataCurta(iso) {
  const [a, m, d] = iso.slice(0, 10).split('-').map(Number)
  const dia = SEMANA[new Date(a, m - 1, d).getDay()]
  return `${dia}, ${String(d).padStart(2, '0')}/${String(m).padStart(2, '0')}/${a}`
}

function hora(iso) {
  return iso.slice(11, 16)
}

async function carregar() {
  try {
    consultas.value = await api('/minhas-consultas')
  } catch (e) {
    erro.value = e.message
  } finally {
    carregando.value = false
  }
}

async function cancelar(c) {
  if (!window.confirm('Cancelar esta consulta? O horário voltará a ficar livre.')) return
  erro.value = ''
  aviso.value = ''
  try {
    await api(`/slots/${c.id}/cancelar`, { method: 'POST' })
    aviso.value = 'Consulta cancelada.'
  } catch (e) {
    erro.value = e.message
  }
  await carregar()
}

onMounted(carregar)
</script>

<style scoped>
.titulo {
  margin-bottom: 18px;
}
.secao {
  margin: 22px 0 10px;
}
.lista {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 10px;
}
.item {
  display: grid;
  grid-template-columns: 190px 1fr auto;
  align-items: center;
  gap: 14px;
  padding: 14px 18px;
}
.quando,
.quem {
  display: flex;
  flex-direction: column;
}
.passadas {
  opacity: 0.7;
}
@media (max-width: 600px) {
  .item {
    grid-template-columns: 1fr auto;
  }
  .quando {
    grid-column: 1 / -1;
  }
}
</style>
