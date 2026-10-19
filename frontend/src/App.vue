<script setup lang="ts">
</script>

<template>
  <main>
    <nav class="nav">
      <router-link to="/">Обращение в поддержку</router-link>
      <router-link to="/operator">Панель оператора</router-link>
    </nav>
    <router-view />
  </main>
</template>

<style>
body { font-family: system-ui, sans-serif; background: #f5f6f8; margin: 0; color: #1c1e21; }
main { max-width: 960px; margin: 2rem auto; padding: 0 1rem; }
.nav { display: flex; gap: 1rem; margin-bottom: 1.5rem; }
.nav a { color: #2563eb; text-decoration: none; font-weight: 600; }
.nav a.router-link-active { color: #1c1e21; }
h1 { margin-bottom: 0.25rem; }
.hint { color: #666; margin-top: 0; }
form { display: grid; gap: 1rem; background: #fff; padding: 1.25rem; border-radius: 8px; box-shadow: 0 1px 3px #0001; }
label { display: grid; gap: 0.35rem; font-weight: 600; font-size: 0.9rem; }
input, textarea { font: inherit; padding: 0.55rem; border: 1px solid #ccd0d5; border-radius: 6px; }
button { font: inherit; padding: 0.65rem; border: 0; border-radius: 6px; background: #2563eb; color: #fff; cursor: pointer; }
button:disabled { opacity: 0.6; cursor: wait; }
button.secondary { background: #e5e7eb; color: #1c1e21; }
.error { color: #b91c1c; }
.result { margin-top: 1.5rem; background: #fff; padding: 1.25rem; border-radius: 8px; box-shadow: 0 1px 3px #0001; }
.result h2 { margin-top: 0; }
.result h3 { margin-bottom: 0.25rem; font-size: 0.95rem; color: #555; }
.badges { display: flex; gap: 0.5rem; margin-bottom: 0.5rem; }
.badge { padding: 0.15rem 0.6rem; border-radius: 999px; background: #e5e7eb; font-size: 0.85rem; }
.p-low { background: #dcfce7; }
.p-medium { background: #fef9c3; }
.p-high { background: #fed7aa; }
.p-urgent { background: #fecaca; }
.reply { white-space: pre-wrap; background: #f8fafc; border-left: 3px solid #2563eb; padding: 0.75rem; margin: 0; }
</style>
