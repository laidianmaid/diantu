import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import './style.css'
import App from './App.vue'
import Home from './views/Home.vue'
import Auth from './views/Auth.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: Home },
    { path: '/auth', component: Auth },
  ],
})

createApp(App).use(createPinia()).use(router).mount('#app')
