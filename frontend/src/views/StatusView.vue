<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { getTicketStatus, type Ticket } from '../api'
import { CATEGORY_LABELS, PRIORITY_LABELS } from '../labels'

const route = useRoute()
const ticketId = Number(route.params.id)
const token = String(route.params.token)

const ticket = ref<Ticket | null>(null)
const invalid = ref(false)
const loading = ref(true)
let timer: number | undefined

function stopPolling() {
  if (timer) {
    window.clearInterval(timer)
    timer = undefined
  }
}

async function poll() {
  try {
    ticket.value = await getTicketStatus(ticketId, token)
    loading.value = false
    if (ticket.value.status !== 'pending_operator') stopPolling()
  } catch {
    loading.value = false
    invalid.value = true
    stopPolling()
  }
}

onMounted(() => {
  poll()
  timer = window.setInterval(poll, 5000)
})

onBeforeUnmount(stopPolling)
</script>

<template>
  <section>
    <h1>Статус обращения №{{ ticketId }}</h1>

    <p v-if="invalid" class="error">
      Ссылка недействительна: обращение не найдено, доступ запрещён или оно не передавалось оператору.
    </p>

    <p v-else-if="loading" class="hint">Загружаем статус…</p>

    <section v-else-if="ticket" class="result">
      <template v-if="ticket.status === 'pending_operator'">
        <div class="badges">
          <span class="badge" v-if="ticket.category">{{ CATEGORY_LABELS[ticket.category] ?? ticket.category }}</span>
          <span class="badge" :class="`p-${ticket.priority}`" v-if="ticket.priority">{{ PRIORITY_LABELS[ticket.priority] }}</span>
        </div>
        <h3>Вопрос передан оператору</h3>
        <p class="reply">Мы уточняем детали у оператора. Страница обновляется автоматически — как только оператор ответит, здесь появится финальный ответ.</p>
      </template>

      <template v-else-if="ticket.status === 'processed'">
        <div class="badges">
          <span class="badge" v-if="ticket.category">{{ CATEGORY_LABELS[ticket.category] ?? ticket.category }}</span>
          <span class="badge" :class="`p-${ticket.priority}`" v-if="ticket.priority">{{ PRIORITY_LABELS[ticket.priority] }}</span>
        </div>
        <h3>Краткое описание</h3>
        <p>{{ ticket.summary }}</p>
        <h3>Наш ответ</h3>
        <p class="reply">{{ ticket.reply_draft }}</p>
      </template>

      <p v-else-if="ticket.status === 'failed'" class="error">
        Обработка не удалась: {{ ticket.error }}. Напишите нам ещё раз, пожалуйста.
      </p>
    </section>
  </section>
</template>
