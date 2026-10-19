import { createRouter, createWebHistory } from 'vue-router'

import CustomerView from './views/CustomerView.vue'
import OperatorView from './views/OperatorView.vue'
import StatusView from './views/StatusView.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'customer', component: CustomerView },
    { path: '/operator', name: 'operator', component: OperatorView },
    { path: '/status/:id/:token', name: 'status', component: StatusView },
  ],
})
