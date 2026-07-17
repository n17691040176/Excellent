<template>
  <div class="login-shell">
    <div class="login-backdrop"></div>
    <div class="login-panel">
      <!-- 左侧品牌区域 -->
      <div class="login-brand">
        <div class="brand-content">
          <div class="brand-logo">
            <svg width="56" height="56" viewBox="0 0 28 28" fill="none">
              <rect x="2" y="2" width="24" height="24" rx="6" fill="url(#loginLogoGradient)"/>
              <path d="M8 14h12M14 8v12" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/>
              <defs>
                <linearGradient id="loginLogoGradient" x1="2" y1="2" x2="26" y2="26" gradientUnits="userSpaceOnUse">
                  <stop stop-color="#D4A853"/>
                  <stop offset="1" stop-color="#B8923F"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <div class="brand-text">
            <span class="brand-name">Excellent</span>
            <span class="brand-tagline">运营中枢</span>
          </div>

          <div class="brand-headline">
            <h1>把招商、返现、资产和本地生活，<br>放进一个清晰后台。</h1>
          </div>

          <p class="brand-description">
            聚焦单人团队可维护的管理体验，所有关键动作都围绕权限、审核、结算与追踪展开。
          </p>

          <div class="brand-features">
            <div class="feature-item">
              <span class="feature-dot"></span>
              <span>权限分级管理</span>
            </div>
            <div class="feature-item">
              <span class="feature-dot"></span>
              <span>审核流程透明</span>
            </div>
            <div class="feature-item">
              <span class="feature-dot"></span>
              <span>数据实时追踪</span>
            </div>
          </div>
        </div>

        <div class="brand-decoration">
          <div class="decoration-circle circle-1"></div>
          <div class="decoration-circle circle-2"></div>
        </div>
      </div>

      <!-- 右侧登录表单 -->
      <div class="login-form-wrapper">
        <div class="login-form-inner panel-card">
          <div class="form-header">
            <h2>管理员登录</h2>
            <p>请使用已分配的管理员账号登录</p>
          </div>

          <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="login-form" @keyup.enter="handleSubmit">
            <el-form-item label="手机号" prop="phone">
              <el-input
                v-model="form.phone"
                placeholder="请输入管理员手机号"
                size="large"
                :prefix-icon="Phone"
              />
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input
                v-model="form.password"
                type="password"
                show-password
                placeholder="请输入密码"
                size="large"
                :prefix-icon="Lock"
              />
            </el-form-item>
            <el-button
              type="primary"
              size="large"
              class="submit-btn"
              :loading="loading"
              @click="handleSubmit"
            >
              {{ loading ? '登录中...' : '进入后台' }}
            </el-button>
          </el-form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Phone, Lock } from '@element-plus/icons-vue'

import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref()
const loading = ref(false)
const form = reactive({
  phone: '',
  password: ''
})

const rules = {
  phone: [{ required: true, message: '请输入手机号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function handleSubmit() {
  await formRef.value.validate()
  loading.value = true
  try {
    await userStore.login(form)
    const prefix = window.location.pathname.startsWith('/admin/') ? '/admin' : ''
    router.replace(`${prefix}/dashboard`)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
@import '@/styles/variables.css';

.login-shell {
  position: relative;
  display: grid;
  place-items: center;
  min-height: 100vh;
  padding: var(--space-6);
  overflow: hidden;
}

.login-backdrop {
  position: absolute;
  inset: 0;
  background: var(--bg-base);
}

.login-panel {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  width: min(1100px, 100%);
  min-height: 640px;
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-2xl);
}

/* ===== 左侧品牌区域 ===== */
.login-brand {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-10);
  background: var(--bg-sidebar);
  overflow: hidden;
}

.brand-content {
  position: relative;
  z-index: 1;
  color: #fff;
}

.brand-logo {
  margin-bottom: var(--space-4);
}

.brand-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.brand-name {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: #ffffff;
  letter-spacing: 0.02em;
}

.brand-tagline {
  font-size: var(--text-xs);
  color: rgba(255, 255, 255, 0.5);
  letter-spacing: 0.15em;
}

.brand-headline {
  margin-top: var(--space-8);
}

.brand-headline h1 {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  line-height: 1.4;
  color: #ffffff;
}

.brand-description {
  margin-top: var(--space-4);
  max-width: 400px;
  font-size: var(--text-base);
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.7);
}

.brand-features {
  margin-top: var(--space-8);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.feature-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--text-sm);
  color: rgba(255, 255, 255, 0.8);
}

.feature-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
}

/* 装饰圆圈 */
.brand-decoration {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.decoration-circle {
  position: absolute;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(212, 168, 83, 0.15), transparent);
}

.circle-1 {
  width: 400px;
  height: 400px;
  top: -100px;
  right: -100px;
}

.circle-2 {
  width: 300px;
  height: 300px;
  bottom: -80px;
  left: -60px;
}

/* ===== 右侧登录表单 ===== */
.login-form-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-10);
  background: var(--bg-surface);
}

.login-form-inner {
  width: 100%;
  max-width: 380px;
  padding: var(--space-8);
}

.form-header {
  margin-bottom: var(--space-6);
  text-align: center;
}

.form-header h2 {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}

.form-header p {
  margin: var(--space-2) 0 0;
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.login-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.login-form :deep(.el-form-item__label) {
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

.submit-btn {
  width: 100%;
  margin-top: var(--space-4);
  height: 48px;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
}

/* ===== 响应式 ===== */
@media (max-width: 960px) {
  .login-panel {
    grid-template-columns: 1fr;
  }

  .login-brand {
    display: none;
  }

  .login-form-wrapper {
    padding: var(--space-6);
  }

  .login-form-inner {
    padding: var(--space-6);
  }
}

@media (max-width: 480px) {
  .login-shell {
    padding: var(--space-4);
  }

  .login-form-inner {
    padding: var(--space-4);
  }
}
</style>
