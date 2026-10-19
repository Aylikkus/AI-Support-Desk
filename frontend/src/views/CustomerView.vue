<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { createTicket, type CreatedTicket } from '../api'
import { CATEGORY_LABELS, PRIORITY_LABELS } from '../labels'

const router = useRouter()

const form = reactive({ customer_name: '', customer_email: '', message: '' })
const loading = ref(false)
const error = ref('')
const ticket = ref<CreatedTicket | null>(null)

async function submit() {
  loading.value = true
  error.value = ''
  ticket.value = null
  try {
    ticket.value = await createTicket({ ...form })
    if (ticket.value.status === 'pending_operator' && ticket.value.access_token) {
      form.message = ''
      router.push({
        name: 'status',
        params: { id: String(ticket.value.id), token: ticket.value.access_token },
      })
    } else if (ticket.value.status === 'processed') {
      form.message = ''
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Что-то пошло не так'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section>
    <h1>Служба поддержки</h1>
    <p class="hint">Опишите проблему — наш ИИ-ассистент разберёт обращение по базе знаний и при необходимости передаст его оператору.</p>

    <form @submit.prevent="submit">
      <label>
        Имя
        <input v-model.trim="form.customer_name" required maxlength="200" />
      </label>
      <label>
        Электронная почта
        <input v-model.trim="form.customer_email" type="email" required />
      </label>
      <label>
        Сообщение
        <textarea v-model.trim="form.message" required minlength="5" maxlength="5000" rows="6" />
      </label>
      <button :disabled="loading">{{ loading ? 'Анализируем…' : 'Отправить обращение' }}</button>
    </form>

    <p v-if="error" class="error">{{ error }}</p>

    <section v-if="ticket" class="result">
      <h2>Обращение №{{ ticket.id }} принято</h2>

      <template v-if="ticket.status === 'processed'">
        <div class="badges">
          <span class="badge" v-if="ticket.category">{{ CATEGORY_LABELS[ticket.category] ?? ticket.category }}</span>
          <span class="badge" :class="`p-${ticket.priority}`" v-if="ticket.priority">{{ PRIORITY_LABELS[ticket.priority] }}</span>
        </div>
        <h3>Краткое описание</h3>
        <p>{{ ticket.summary }}</p>
        <h3>Наш ответ</h3>
        <p class="reply">{{ ticket.reply_draft }}</p>
      </template>

      <template v-else-if="ticket.status === 'pending_operator'">
        <div class="badges">
          <span class="badge" v-if="ticket.category">{{ CATEGORY_LABELS[ticket.category] ?? ticket.category }}</span>
          <span class="badge" :class="`p-${ticket.priority}`" v-if="ticket.priority">{{ PRIORITY_LABELS[ticket.priority] }}</span>
        </div>
        <p class="reply">Вопрос требует уточнения человеком: мы передали обращение оператору и ответим вам вручную.</p>
      </template>

      <p v-else class="error">Обращение сохранено, но автоматический анализ не удался: {{ ticket.error }}</p>
    </section>
  </section>
</template>
