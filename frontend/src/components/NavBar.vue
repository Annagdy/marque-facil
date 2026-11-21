<template>
  <header class="nav">
    <div class="nav-inner">
      <RouterLink to="/" class="marca">
        <svg viewBox="0 0 32 32" width="26" height="26" aria-hidden="true">
          <rect x="3" y="6" width="26" height="23" rx="4" fill="currentColor" />
          <path d="M10 20.5l4 4 8-8.5" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        Marque Fácil
      </RouterLink>

      <nav v-if="auth.token" class="links">
        <template v-if="auth.usuario?.papel === 'paciente'">
          <RouterLink to="/medicos">Médicos</RouterLink>
          <RouterLink to="/consultas">Minhas consultas</RouterLink>
        </template>
        <template v-else>
          <RouterLink to="/calendario">Minha agenda</RouterLink>
          <RouterLink to="/consultas">Consultas marcadas</RouterLink>
        </template>
      </nav>

      <div v-if="auth.token" class="usuario">
        <span class="nome">{{ auth.usuario?.nome }}</span>
        <button class="btn ghost small" @click="deslogar">Sair</button>
      </div>
    </div>
  </header>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { auth, sair } from '../auth'

const router = useRouter()

function deslogar() {
  sair()
  router.push('/login')
}
</script>

<style scoped>
.nav {
  background: var(--card);
  border-bottom: 1px solid var(--borda);
  position: sticky;
  top: 0;
  z-index: 10;
}
.nav-inner {
  max-width: 1100px;
  margin: 0 auto;
  padding: 10px 16px;
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}
.marca {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  font-size: 1.15rem;
  color: var(--primaria);
  text-decoration: none;
}
.links {
  display: flex;
  gap: 4px;
  flex: 1;
}
.links a {
  padding: 6px 12px;
  border-radius: 8px;
  color: var(--texto);
  text-decoration: none;
  font-weight: 500;
}
.links a:hover {
  background: var(--fundo);
}
.links a.router-link-active {
  background: var(--primaria-clara);
  color: var(--primaria);
}
.usuario {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
}
.nome {
  font-size: 0.9rem;
  color: var(--suave);
}
@media (max-width: 640px) {
  .nome {
    display: none;
  }
  .links {
    order: 3;
    flex-basis: 100%;
  }
}
</style>
