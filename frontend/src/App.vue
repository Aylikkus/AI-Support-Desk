<script setup lang="ts">
import { reactive, ref } from 'vue'
import { createTicket, type Ticket } from './api'

const form = reactive({ customer_name: '', customer_email: '', message: '' })
const loading = ref(false)
const error = ref('')
const ticket = ref<Ticket | null>(null)

async function submit() {
  loading.value = true
  error.value = ''
  ticket.value = null
  try {
    ticket.value = await createTicket({ ...form })
    if (ticket.value.status === 'processed') form.message = ''
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Something went wrong'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main>
    <h1>Support Desk</h1>
    <p class="hint">Describe your problem and our AI assistant will triage it.</p>

    <form @submit.prevent="submit">
      <label>
        Name
        <input v-model.trim="form.customer_name" required maxlength="200" />
      </label>
      <label>
        Email
        <input v-model.trim="form.customer_email" type="email" required />
      </label>
      <label>
        Message
        <textarea v-model.trim="form.message" required minlength="5" maxlength="5000" rows="6" />
      </label>
      <button :disabled="loading">{{ loading ? 'Analyzing…' : 'Submit feedback' }}</button>
    </form>

    <p v-if="error" class="error">{{ error }}</p>

    <section v-if="ticket" class="result">
      <h2>Ticket #{{ ticket.id }} received</h2>
      <template v-if="ticket.status === 'processed'">
        <div class="badges">
          <span class="badge">{{ ticket.category }}</span>
          <span class="badge" :class="`p-${ticket.priority}`">{{ ticket.priority }} priority</span>
        </div>
        <h3>Summary</h3>
        <p>{{ ticket.summary }}</p>
        <h3>Reply draft</h3>
        <p class="reply">{{ ticket.reply_draft }}</p>
      </template>
      <p v-else class="error">Saved, but automatic analysis failed: {{ ticket.error }}</p>
    </section>
  </main>
</template>

<style>
body { font-family: system-ui, sans-serif; background: #f5f6f8; margin: 0; color: #1c1e21; }
main { max-width: 640px; margin: 2rem auto; padding: 0 1rem; }
h1 { margin-bottom: 0.25rem; }
.hint { color: #666; margin-top: 0; }
form { display: grid; gap: 1rem; background: #fff; padding: 1.25rem; border-radius: 8px; box-shadow: 0 1px 3px #0001; }
label { display: grid; gap: 0.35rem; font-weight: 600; font-size: 0.9rem; }
input, textarea { font: inherit; padding: 0.55rem; border: 1px solid #ccd0d5; border-radius: 6px; }
button { font: inherit; padding: 0.65rem; border: 0; border-radius: 6px; background: #2563eb; color: #fff; cursor: pointer; }
button:disabled { opacity: 0.6; cursor: wait; }
.error { color: #b91c1c; }
.result { margin-top: 1.5rem; background: #fff; padding: 1.25rem; border-radius: 8px; box-shadow: 0 1px 3px #0001; }
.result h2 { margin-top: 0; }
.result h3 { margin-bottom: 0.25rem; font-size: 0.95rem; color: #555; }
.badges { display: flex; gap: 0.5rem; margin-bottom: 0.5rem; }
.badge { padding: 0.15rem 0.6rem; border-radius: 999px; background: #e5e7eb; font-size: 0.85rem; text-transform: capitalize; }
.p-low { background: #dcfce7; }
.p-medium { background: #fef9c3; }
.p-high { background: #fed7aa; }
.p-urgent { background: #fecaca; }
.reply { white-space: pre-wrap; background: #f8fafc; border-left: 3px solid #2563eb; padding: 0.75rem; margin: 0; }
</style>
