<template>
  <div class="login-shell">
    <div class="login-backdrop"></div>
    <div class="login-panel panel-card">
      <div class="login-copy">
        <div class="copy-badge">Excellent Operations</div>
        <h1>把招商、返现、资产和本地生活，放进一个清晰后台。</h1>
        <p>聚焦单人团队可维护的管理体验，所有关键动作都围绕权限、审核、结算与追踪展开。</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="login-form" @keyup.enter="handleSubmit">
        <div class="form-title">管理员登录</div>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="form.phone" placeholder="请输入管理员手机号" size="large" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" size="large" />
        </el-form-item>
        <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="handleSubmit">进入后台</el-button>
        <div class="hint-text">默认超级管理员：18800000000 / Admin@123</div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref()
const loading = ref(false)
const form = reactive({
  phone: '18800000000',
  password: 'Admin@123'
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
    router.replace('/dashboard')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-shell {
  position: relative;
  display: grid;
  place-items: center;
  min-height: 100vh;
  padding: 24px;
  overflow: hidden;
}

.login-backdrop {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 15% 20%, rgba(216, 155, 43, 0.26), transparent 22%),
    radial-gradient(circle at 85% 18%, rgba(28, 143, 132, 0.2), transparent 26%),
    linear-gradient(135deg, #fcfaf4, #eef5f2 48%, #f3ead9 100%);
}

.login-panel {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  width: min(1100px, 100%);
  overflow: hidden;
}

.login-copy {
  padding: 56px;
  color: #fff;
  background:
    linear-gradient(145deg, rgba(15, 47, 47, 0.98), rgba(28, 143, 132, 0.88)),
    linear-gradient(90deg, rgba(216, 155, 43, 0.18), transparent 55%);
}

.copy-badge {
  display: inline-flex;
  padding: 8px 14px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 999px;
  font-size: 12px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.login-copy h1 {
  margin: 22px 0 18px;
  font-size: 42px;
  line-height: 1.16;
}

.login-copy p {
  max-width: 460px;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.78);
}

.login-form {
  padding: 48px;
  background: rgba(255, 255, 255, 0.95);
}

.form-title {
  margin-bottom: 24px;
  font-size: 30px;
  font-weight: 700;
  color: var(--brand-deep);
}

.submit-btn {
  width: 100%;
  margin-top: 10px;
}

.hint-text {
  margin-top: 14px;
  color: rgba(15, 47, 47, 0.58);
  font-size: 13px;
}

@media (max-width: 960px) {
  .login-panel {
    grid-template-columns: 1fr;
  }

  .login-copy,
  .login-form {
    padding: 32px 26px;
  }

  .login-copy h1 {
    font-size: 30px;
  }
}
</style>
