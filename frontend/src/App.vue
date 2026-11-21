<template>
  <NavBar />
  <main class="container">
    <RouterView :key="$route.fullPath" />
  </main>
</template>

<script setup>
import NavBar from './components/NavBar.vue'
</script>
