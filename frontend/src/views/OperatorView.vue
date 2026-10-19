<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

import {
  answerOperatorRequest,
  getOperatorRequest,
  listOperatorRequests,
  type OperatorRequest,
  type OperatorRequestDetail,
} from '../api'

const pending = ref<OperatorRequest[]>([])
const answered = ref<OperatorRequest[]>([])
const selected = ref<OperatorRequestDetail | null>(null)
const answerText = ref('')
const loading = ref(false)
const error = ref('')
const info = ref('')
let timer: number | undefined

async function refresh() {
  try {
    const [pendingItems, answeredItems] = await Promise.all([
      listOperatorRequests('pending'),
      listOperatorRequests('answered'),
    ])
    pending.value = pendingItems
    answered.value = answeredItems
  } catch {
    /* queue refresh is best-effort */
  }
}

async function open(item: OperatorRequest) {
  error.value = ''
  info.value = ''
  try {
    selected.value = await getOperatorRequest(item.id)
    answerText.value = ''
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Не удалось открыть запрос'
  }
}

async function submit() {
  if (!selected.value || !answerText.value.trim()) return
  loading.value = true
  error.value = ''
  info.value = ''
  try {
    const detail = await answerOperatorRequest(selected.value.id, answerText.value.trim())
    info.value = `Готово: обращение №${detail.ticket.id} обработано.`
    selected.value = null
    answerText.value = ''
    await refresh()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Не удалось отправить ответ'
  } finally {
    loading.value = false
  }
}

function formatTime(value: string): string {
  return new Date(value).toLocaleString('ru-RU')
}

onMounted(() => {
  refresh()
  timer = window.setInterval(refresh, 5000)
})

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <section>
    <h1>Панель оператора</h1>
    <p class="hint">Очередь вопросов, которые ИИ-ассистент не смог решить автоматически. Ваш ответ возвращается в LangGraph-конвейер, и клиент получает финальный ответ.</p>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="info" class="info">{{ info }}</p>

    <div class="queue-layout">
      <div class="queue">
        <h2>Ожидают ответа ({{ pending.length }})</h2>
        <p v-if="pending.length === 0" class="hint">Очередь пуста.</p>
        <ul v-else>
          <li v-for="item in pending" :key="item.id" :class="{ active: selected?.id === item.id }">
            <button class="queue-item" @click="open(item)">
              <span class="question">{{ item.question }}</span>
              <span class="meta">Обращение №{{ item.ticket_id }} · {{ formatTime(item.created_at) }}</span>
            </button>
          </li>
        </ul>

        <h2>Обработанные ({{ answered.length }})</h2>
        <p v-if="answered.length === 0" class="hint">Пока ничего.</p>
        <ul v-else>
          <li v-for="item in answered" :key="item.id">
            <div class="queue-item done">
              <span class="question">{{ item.question }}</span>
              <span class="meta">Обращение №{{ item.ticket_id }} · {{ formatTime(item.created_at) }}</span>
              <span class="meta answer" v-if="item.answer">Ответ: {{ item.answer }}</span>
            </div>
          </li>
        </ul>
      </div>

      <div v-if="selected" class="detail result">
        <h2>Вопрос ассистента</h2>
        <p class="reply">{{ selected.question }}</p>

        <h2>Обращение №{{ selected.ticket.id }}</h2>
        <p><strong>{{ selected.ticket.customer_name }}</strong> · {{ selected.ticket.customer_email }}</p>
        <p class="reply">{{ selected.ticket.message }}</p>

        <h3>Ваш ответ оператора</h3>
        <textarea v-model="answerText" rows="5" maxlength="10000" placeholder="Например: заказ №123, возврат оформлен…" />
        <button :disabled="loading || !answerText.trim()" @click="submit">
          {{ loading ? 'Отправляем…' : 'Отправить ответ' }}
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.info { color: #15803d; }
.queue-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; align-items: start; }
.queue h2 { font-size: 1.05rem; margin-bottom: 0.5rem; }
.queue ul { list-style: none; padding: 0; margin: 0 0 1.5rem; display: grid; gap: 0.5rem; }
.queue-item { display: grid; gap: 0.25rem; width: 100%; text-align: left; background: #fff; padding: 0.75rem; border-radius: 8px; border: 1px solid #e5e7eb; cursor: pointer; font: inherit; color: inherit; }
.queue-item:hover { border-color: #2563eb; }
.queue-item.done { cursor: default; opacity: 0.75; }
li.active .queue-item { border-color: #2563eb; }
.question { font-weight: 600; }
.meta { color: #666; font-size: 0.85rem; }
.meta.answer { color: #15803d; }
.detail textarea { width: 100%; box-sizing: border-box; margin-bottom: 0.75rem; }
@media (max-width: 720px) { .queue-layout { grid-template-columns: 1fr; } }
</style>
