<template>
  <header class="titulo">
    <div>
      <h1 v-if="ehMedico">Minha agenda</h1>
      <h1 v-else>Agenda {{ medico ? `de ${medico.nome}` : '' }}</h1>
      <p v-if="ehMedico" class="sub">
        {{ auth.usuario.especialidade }} · cadastre seus horários e acompanhe as consultas marcadas.
      </p>
      <p v-else-if="medico" class="sub">{{ medico.especialidade }} · escolha um dia e clique em um horário livre.</p>
    </div>
    <RouterLink v-if="!ehMedico" to="/medicos" class="btn ghost">← Voltar à busca</RouterLink>
  </header>

  <p v-if="erro" class="alert erro">{{ erro }}</p>
  <p v-if="aviso" class="alert ok">{{ aviso }}</p>

  <div class="layout">
    <!-- ───────── Calendário do mês ───────── -->
    <section class="card">
      <div class="mes-nav">
        <button class="icone" :disabled="!podeVoltar" aria-label="Mês anterior" @click="mudarMes(-1)">‹</button>
        <h2>{{ tituloMes }}</h2>
        <button class="icone" :disabled="!podeAvancar" aria-label="Próximo mês" @click="mudarMes(1)">›</button>
      </div>

      <div class="grade">
        <div v-for="n in SEMANA_CURTA" :key="n" class="cab">{{ n }}</div>

        <template v-for="(c, i) in celulas" :key="i">
          <div v-if="!c" class="cel vazia"></div>
          <button
            v-else
            type="button"
            class="cel dia"
            :class="{ sel: c.k === diaSel, passado: c.passado, hoje: c.k === hojeChave }"
            @click="diaSel = c.k"
          >
            <span class="num">{{ c.d }}</span>
            <span class="pills">
              <span v-if="c.livres" class="pill livre" title="Horários livres">{{ c.livres }}</span>
              <span v-if="ehMedico && c.ocupados" class="pill ocup" title="Consultas marcadas">{{ c.ocupados }}</span>
              <span v-if="!ehMedico && c.minhas" class="pill ocup" title="Suas consultas">{{ c.minhas }}</span>
            </span>
          </button>
        </template>
      </div>

      <div class="legenda">
        <span><i class="pill livre">n</i> horários livres</span>
        <span v-if="ehMedico"><i class="pill ocup">n</i> consultas marcadas</span>
        <span v-else><i class="pill ocup">n</i> suas consultas</span>
      </div>
    </section>

    <!-- ───────── Horários do dia selecionado ───────── -->
    <aside class="card">
      <h2>{{ tituloDia }}</h2>

      <p v-if="carregando" class="muted vazio">Carregando…</p>
      <p v-else-if="!slotsDoDia.length" class="muted vazio">
        {{ ehMedico ? 'Nenhum horário cadastrado neste dia.' : 'O médico não tem horários neste dia.' }}
      </p>

      <ul v-else class="slots">
        <li v-for="s in slotsDoDia" :key="s.id" class="slot" :class="estado(s)">
          <span class="hora">{{ hora(s.inicio) }} – {{ hora(s.fim) }}</span>

          <!-- médico -->
          <template v-if="ehMedico">
            <span class="situacao">{{ s.livre ? 'Livre' : s.paciente_nome }}</span>
            <button v-if="s.livre && !passado(s)" class="btn perigo small" @click="remover(s)">Remover</button>
            <button v-else-if="!s.livre && !passado(s)" class="btn perigo small" @click="cancelar(s)">Cancelar</button>
          </template>

          <!-- paciente -->
          <template v-else>
            <span class="situacao">{{ rotuloPaciente(s) }}</span>
            <button v-if="s.livre && !passado(s)" class="btn small" @click="marcar(s)">Marcar</button>
            <button v-else-if="s.minha && !passado(s)" class="btn perigo small" @click="cancelar(s)">Cancelar</button>
          </template>
        </li>
      </ul>
    </aside>
  </div>

  <!-- ───────── Médico: cadastrar horários em lote ───────── -->
  <section v-if="ehMedico" class="card cadastro">
    <div class="cab-cadastro">
      <div>
        <h2>Cadastrar horários</h2>
        <p class="sub">Defina o período (pode ser o ano inteiro), os dias da semana e os turnos de atendimento.</p>
      </div>
      <button class="btn ghost small" type="button" @click="mostrarForm = !mostrarForm">
        {{ mostrarForm ? 'Ocultar' : 'Mostrar' }}
      </button>
    </div>

    <form v-if="mostrarForm" class="form-lote" @submit.prevent="gerar">
      <div class="linha">
        <label class="campo">
          De
          <input v-model="form.de" type="date" required />
        </label>
        <label class="campo">
          Até
          <input v-model="form.ate" type="date" required />
        </label>
        <label class="campo">
          Duração da consulta
          <select v-model.number="form.duracao">
            <option v-for="d in DURACOES" :key="d" :value="d">{{ d }} min</option>
          </select>
        </label>
      </div>

      <div class="campo">
        Dias da semana
        <div class="chips">
          <label v-for="d in DIAS" :key="d.v" class="chip" :class="{ on: form.dias.includes(d.v) }">
            <input v-model="form.dias" type="checkbox" :value="d.v" />
            {{ d.rotulo }}
          </label>
        </div>
      </div>

      <div class="campo">
        Turnos de atendimento
        <div v-for="(f, i) in form.faixas" :key="i" class="faixa">
          <input v-model="f.inicio" type="time" required aria-label="Início do turno" />
          <span>até</span>
          <input v-model="f.fim" type="time" required aria-label="Fim do turno" />
          <button v-if="form.faixas.length > 1" type="button" class="btn ghost small" @click="form.faixas.splice(i, 1)">
            Remover
          </button>
        </div>
        <button
          v-if="form.faixas.length < 6"
          type="button"
          class="btn ghost small"
          @click="form.faixas.push({ inicio: '', fim: '' })"
        >
          + Adicionar turno
        </button>
      </div>

      <div class="acoes-form">
        <button class="btn" :disabled="gerando">{{ gerando ? 'Gerando…' : 'Gerar horários' }}</button>
        <button class="btn ghost" type="button" @click="proximos12Meses">Próximos 12 meses</button>
        <button class="btn ghost" type="button" @click="usarDia">Usar só o dia selecionado</button>
      </div>
    </form>
  </section>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import { auth } from '../auth'

const route = useRoute()
const ehMedico = computed(() => auth.usuario?.papel === 'medico')
const medicoId = computed(() => (ehMedico.value ? auth.usuario.id : Number(route.params.medicoId)))

// ───────── utilidades de data (tudo em horário local, sem toISOString) ─────────
const MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
const SEMANA_CURTA = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']
const SEMANA_LONGA = ['Domingo', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']
// valor = dia da semana no padrão do backend (0 = segunda ... 6 = domingo)
const DIAS = [
  { v: 0, rotulo: 'Seg' },
  { v: 1, rotulo: 'Ter' },
  { v: 2, rotulo: 'Qua' },
  { v: 3, rotulo: 'Qui' },
  { v: 4, rotulo: 'Sex' },
  { v: 5, rotulo: 'Sáb' },
  { v: 6, rotulo: 'Dom' },
]
const DURACOES = [15, 20, 30, 40, 45, 60]

const pad = (n) => String(n).padStart(2, '0')
const chave = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
const hora = (iso) => iso.slice(11, 16)
// "agora" no mesmo formato dos horários da API (AAAA-MM-DDTHH:MM:SS) para comparar como texto
function agoraTexto() {
  const n = new Date()
  return `${chave(n)}T${pad(n.getHours())}:${pad(n.getMinutes())}:${pad(n.getSeconds())}`
}
const passado = (s) => s.inicio <= agoraTexto()

// ───────── estado ─────────
const hoje = new Date()
const hojeChave = chave(hoje)
const mes = ref(new Date(hoje.getFullYear(), hoje.getMonth(), 1))
const diaSel = ref(hojeChave)
const medico = ref(null)
const slots = ref([])
const carregando = ref(false)
const gerando = ref(false)
const erro = ref('')
const aviso = ref('')
const mostrarForm = ref(false)

const form = reactive({
  de: hojeChave,
  ate: `${hoje.getFullYear()}-12-31`,
  duracao: 30,
  dias: [0, 1, 2, 3, 4],
  faixas: [
    { inicio: '08:00', fim: '12:00' },
    { inicio: '14:00', fim: '18:00' },
  ],
})

// ───────── calendário ─────────
const tituloMes = computed(() => `${MESES[mes.value.getMonth()]} ${mes.value.getFullYear()}`)
const mesesAfrente = computed(
  () => (mes.value.getFullYear() - hoje.getFullYear()) * 12 + mes.value.getMonth() - hoje.getMonth(),
)
const podeVoltar = computed(() => mesesAfrente.value > 0)
const podeAvancar = computed(() => mesesAfrente.value < 24)

const porDia = computed(() => {
  const mapa = {}
  for (const s of slots.value) {
    const k = s.inicio.slice(0, 10)
    if (!mapa[k]) mapa[k] = []
    mapa[k].push(s)
  }
  return mapa
})

const celulas = computed(() => {
  const ano = mes.value.getFullYear()
  const m = mes.value.getMonth()
  const lista = Array(new Date(ano, m, 1).getDay()).fill(null) // espaços antes do dia 1
  const total = new Date(ano, m + 1, 0).getDate()
  for (let d = 1; d <= total; d++) {
    const k = chave(new Date(ano, m, d))
    const dia = porDia.value[k] ?? []
    lista.push({
      d,
      k,
      passado: k < hojeChave,
      livres: dia.filter((s) => s.livre && !passado(s)).length,
      ocupados: dia.filter((s) => !s.livre).length,
      minhas: dia.filter((s) => s.minha).length,
    })
  }
  return lista
})

const slotsDoDia = computed(() => porDia.value[diaSel.value] ?? [])

const tituloDia = computed(() => {
  const [a, m, d] = diaSel.value.split('-').map(Number)
  return `${SEMANA_LONGA[new Date(a, m - 1, d).getDay()]}, ${pad(d)}/${pad(m)}/${a}`
})

function mudarMes(delta) {
  const novo = new Date(mes.value.getFullYear(), mes.value.getMonth() + delta, 1)
  mes.value = novo
  const ehMesAtual = novo.getFullYear() === hoje.getFullYear() && novo.getMonth() === hoje.getMonth()
  diaSel.value = ehMesAtual ? hojeChave : chave(novo)
}

// ───────── horários do dia ─────────
function estado(s) {
  if (passado(s)) return 'passado'
  if (s.livre) return 'livre'
  return s.minha ? 'minha' : 'ocupado'
}

function rotuloPaciente(s) {
  if (passado(s)) return s.minha ? 'Sua consulta' : '—'
  if (s.livre) return 'Livre'
  return s.minha ? 'Sua consulta' : 'Ocupado'
}

// ───────── carregar dados ─────────
async function carregar() {
  carregando.value = true
  const ano = mes.value.getFullYear()
  const m = mes.value.getMonth()
  try {
    slots.value = await api(`/medicos/${medicoId.value}/slots`, {
      params: { inicio: chave(new Date(ano, m, 1)), fim: chave(new Date(ano, m + 1, 0)) },
    })
  } catch (e) {
    erro.value = e.message
  } finally {
    carregando.value = false
  }
}

watch(mes, carregar)

onMounted(async () => {
  if (!ehMedico.value) {
    try {
      medico.value = await api(`/medicos/${medicoId.value}`)
    } catch (e) {
      erro.value = e.message
      return
    }
  }
  await carregar()
  // Médico sem nenhum horário no mês: já abre o formulário de cadastro
  if (ehMedico.value && !slots.value.length) mostrarForm.value = true
})

// ───────── ações ─────────
async function executar(acao, mensagemOk) {
  erro.value = ''
  aviso.value = ''
  try {
    await acao()
    aviso.value = mensagemOk
  } catch (e) {
    erro.value = e.message
  }
  await carregar() // sempre recarrega: mostra o estado real (ex.: alguém marcou antes)
}

const marcar = (s) =>
  executar(() => api(`/slots/${s.id}/marcar`, { method: 'POST' }), 'Consulta marcada com sucesso!')

function cancelar(s) {
  if (!window.confirm('Cancelar esta consulta? O horário voltará a ficar livre.')) return
  return executar(() => api(`/slots/${s.id}/cancelar`, { method: 'POST' }), 'Consulta cancelada.')
}

const remover = (s) => executar(() => api(`/slots/${s.id}`, { method: 'DELETE' }), 'Horário removido.')

function proximos12Meses() {
  const fim = new Date()
  fim.setDate(fim.getDate() + 365) // o backend aceita até 366 dias de período
  form.de = hojeChave
  form.ate = chave(fim)
}

function usarDia() {
  const [a, m, d] = diaSel.value.split('-').map(Number)
  const diaSemana = (new Date(a, m - 1, d).getDay() + 6) % 7 // converte para 0 = segunda
  form.de = diaSel.value
  form.ate = diaSel.value
  form.dias = [diaSemana]
}

async function gerar() {
  erro.value = ''
  aviso.value = ''
  if (!form.dias.length) {
    erro.value = 'Escolha ao menos um dia da semana.'
    return
  }
  if (form.faixas.some((f) => !f.inicio || !f.fim)) {
    erro.value = 'Preencha o início e o fim de todos os turnos.'
    return
  }
  gerando.value = true
  try {
    const r = await api('/slots/gerar', {
      method: 'POST',
      body: {
        data_inicio: form.de,
        data_fim: form.ate,
        dias_semana: form.dias,
        faixas: form.faixas,
        duracao_min: form.duracao,
      },
    })
    aviso.value =
      `${r.criados} horário(s) criado(s)` +
      (r.ignorados ? `; ${r.ignorados} ignorado(s) (já existiam, se sobrepunham ou estavam no passado).` : '.')
    await carregar()
  } catch (e) {
    erro.value = e.message
  } finally {
    gerando.value = false
  }
}
</script>

<style scoped>
.titulo {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 18px;
}
.layout {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

/* mês */
.mes-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.icone {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 1px solid var(--borda);
  background: #fff;
  font-size: 1.4rem;
  line-height: 1;
  cursor: pointer;
  color: var(--texto);
}
.icone:hover:not(:disabled) {
  background: var(--primaria-clara);
  border-color: var(--primaria);
}
.icone:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

/* grade */
.grade {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 6px;
}
.cab {
  text-align: center;
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--suave);
  padding-bottom: 4px;
}
.cel {
  min-height: 64px;
}
.dia {
  appearance: none;
  font: inherit;
  color: inherit;
  background: #fff;
  border: 1px solid var(--borda);
  border-radius: 9px;
  padding: 6px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: space-between;
  cursor: pointer;
  text-align: left;
}
.dia:hover {
  border-color: var(--primaria);
}
.dia.passado {
  background: var(--fundo);
  color: var(--suave);
}
.dia.hoje .num {
  background: var(--primaria);
  color: #fff;
  border-radius: 50%;
  padding: 0 6px;
}
.dia.sel {
  outline: 2px solid var(--primaria);
  border-color: var(--primaria);
}
.num {
  font-weight: 700;
  font-size: 0.9rem;
}
.pills {
  display: flex;
  gap: 3px;
  flex-wrap: wrap;
}
.pill {
  font-size: 0.7rem;
  font-weight: 700;
  font-style: normal;
  padding: 0 6px;
  border-radius: 999px;
  line-height: 1.5;
}
.pill.livre {
  background: var(--livre-bg);
  color: var(--livre-tx);
}
.pill.ocup {
  background: var(--ocupado-bg);
  color: var(--ocupado-tx);
}
.legenda {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--borda);
  font-size: 0.85rem;
  color: var(--suave);
}

/* horários do dia */
.vazio {
  margin-top: 12px;
}
.slots {
  list-style: none;
  padding: 0;
  margin: 12px 0 0;
  display: grid;
  gap: 8px;
}
.slot {
  display: grid;
  grid-template-columns: 110px 1fr auto;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 9px;
  border: 1px solid var(--borda);
}
.slot .hora {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.slot .situacao {
  font-size: 0.9rem;
}
.slot.livre {
  background: var(--livre-bg);
  border-color: transparent;
}
.slot.livre .situacao {
  color: var(--livre-tx);
}
.slot.minha,
.slot.ocupado {
  background: var(--ocupado-bg);
  border-color: transparent;
}
.slot.minha .situacao,
.slot.ocupado .situacao {
  color: var(--ocupado-tx);
}
.slot.passado {
  background: var(--fundo);
  color: var(--suave);
}

/* cadastro em lote */
.cadastro {
  margin-top: 18px;
}
.cab-cadastro {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}
.form-lote {
  margin-top: 16px;
}
.linha {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}
.chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 6px;
}
.chip {
  display: inline-flex;
  align-items: center;
  padding: 6px 14px;
  border: 1px solid var(--borda);
  border-radius: 999px;
  cursor: pointer;
  font-weight: 600;
}
.chip input {
  display: none;
}
.chip.on {
  background: var(--primaria-clara);
  border-color: var(--primaria);
  color: var(--primaria);
}
.faixa {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 6px 0;
  max-width: 420px;
}
.faixa input {
  width: 130px;
}
.acoes-form {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 8px;
}
.campo {
  font-weight: 600;
  font-size: 0.9rem;
  margin-bottom: 14px;
}

@media (max-width: 860px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 480px) {
  .cel {
    min-height: 52px;
  }
  .slot {
    grid-template-columns: 1fr auto;
  }
  .slot .hora {
    grid-column: 1 / -1;
  }
}
</style>
