<template>
  <div class="login-shell">
    <div class="login-hero">
      <h1>健康商城与本地生活，装进一个轻盈 App。</h1>
      <p>围绕复购区、自营商城、爆款区、本地生活四大专区，串起团队、邀请、佣金和资产体系。</p>
    </div>

    <div class="login-panel">
      <van-tabs v-model:active="activeTab" animated>
        <van-tab title="登录">
          <van-form @submit="handleLogin">
            <van-field v-model="loginForm.phone" name="phone" label="手机号" placeholder="请输入手机号" :rules="rules.phone" />
            <van-field v-model="loginForm.password" name="password" type="password" label="密码" placeholder="请输入密码" :rules="rules.password" />
            <div class="submit-bar">
              <van-button round block type="primary" native-type="submit">立即登录</van-button>
            </div>
          </van-form>
        </van-tab>

        <van-tab title="注册">
          <van-form @submit="handleRegister">
            <van-field v-model="registerForm.phone" name="phone" label="手机号" placeholder="请输入手机号" :rules="rules.phone" />
            <van-field v-model="registerForm.nickname" name="nickname" label="昵称" placeholder="请输入昵称" :rules="rules.nickname" />
            <van-field v-model="registerForm.password" name="password" type="password" label="密码" placeholder="请输入密码" :rules="rules.password" />
            <van-field v-model="registerForm.invite_code" name="invite_code" label="邀请码" placeholder="选填邀请码" />
            <div class="submit-bar">
              <van-button round block type="primary" native-type="submit">注册并进入</van-button>
            </div>
          </van-form>
        </van-tab>
      </van-tabs>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showSuccessToast } from 'vant'

import { authApi } from '@/api/modules'
import { setToken, setUserCache } from '@/utils/auth'

const route = useRoute()
const router = useRouter()
const activeTab = ref(0)
const loginForm = reactive({
  phone: '18800000000',
  password: 'Admin@123'
})
const registerForm = reactive({
  phone: '',
  nickname: '',
  password: '',
  invite_code: ''
})

const rules = {
  phone: [{ required: true, message: '请输入手机号' }],
  password: [{ required: true, message: '请输入密码' }],
  nickname: [{ required: true, message: '请输入昵称' }]
}

function saveAuth(data) {
  setToken(data.access_token)
  setUserCache(data.user)
}

async function handleLogin() {
  const data = await authApi.login(loginForm)
  saveAuth(data)
  showSuccessToast('登录成功')
  router.replace('/home')
}

async function handleRegister() {
  const payload = {
    ...registerForm,
    invite_code: registerForm.invite_code || null
  }
  const data = await authApi.register(payload)
  saveAuth(data)
  showSuccessToast('注册成功')
  router.replace('/home')
}

onMounted(() => {
  if (route.query.invite_code) {
    activeTab.value = 1
    registerForm.invite_code = String(route.query.invite_code)
  }
})
</script>
