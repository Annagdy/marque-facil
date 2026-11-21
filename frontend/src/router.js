import { createRouter, createWebHistory } from 'vue-router'
import { auth, paginaInicial } from './auth'
import Login from './pages/Login.vue'
import Cadastro from './pages/Cadastro.vue'
import Medicos from './pages/Medicos.vue'
import Calendario from './pages/Calendario.vue'
import Consultas from './pages/Consultas.vue'

const routes = [
  { path: '/', redirect: () => (auth.usuario ? paginaInicial(auth.usuario.papel) : '/login') },
  { path: '/login', component: Login, meta: { publica: true } },
  { path: '/cadastro', component: Cadastro, meta: { publica: true } },
  // Paciente: busca médicos
  { path: '/medicos', component: Medicos, meta: { papel: 'paciente' } },
  // Calendário compartilhado: médico (/calendario) e paciente (/calendario/:medicoId)
  { path: '/calendario/:medicoId?', component: Calendario },
  // Consultas marcadas (do paciente ou da agenda do médico)
  { path: '/consultas', component: Consultas },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const papel = auth.usuario?.papel

  if (!to.meta.publica && !auth.token) return '/login'
  if (to.meta.publica && auth.token) return paginaInicial(papel)
  if (to.meta.papel && papel !== to.meta.papel) return paginaInicial(papel)

  if (to.path.startsWith('/calendario')) {
    const medicoId = to.params.medicoId
    if (papel === 'paciente' && !medicoId) return '/medicos'
    if (papel === 'medico' && medicoId && Number(medicoId) !== auth.usuario.id) return '/calendario'
  }
})

export default router
