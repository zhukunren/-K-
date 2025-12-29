import { createRouter, createWebHistory } from 'vue-router'
import ModernView from '@/views/ModernView.vue'
import MainView from '@/views/MainView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: ModernView  // 恢复使用现代化界面作为默认
    },
    {
      path: '/classic',
      name: 'classic',
      component: MainView  // 经典界面
    }
  ]
})

export default router