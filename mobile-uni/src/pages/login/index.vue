<template>
  <view class="page login-page">
    <view class="hero-card">
      <view class="eyebrow">Excellent Mall</view>
      <view class="hero-title">把健康消费、本地生活和团队关系装进一个轻量客户端</view>
      <view class="hero-desc">
        登录后即可进入套餐、订单、资产、团队和本地生活全链路页面。注册时也可以直接带邀请码完成绑定。
      </view>
      <view class="hero-pills">
        <view class="hero-pill">套餐复购</view>
        <view class="hero-pill">本地生活</view>
        <view class="hero-pill">邀请返利</view>
      </view>
    </view>

    <view class="tabs">
      <view
        class="tab"
        :class="{ active: activeTab === 'login' }"
        @click="activeTab = 'login'"
      >
        登录
      </view>
      <view
        class="tab"
        :class="{ active: activeTab === 'register' }"
        @click="activeTab = 'register'"
      >
        注册
      </view>
    </view>

    <view class="card" v-if="activeTab === 'login'">
      <view class="section-title">账号登录</view>
      <input v-model="loginForm.phone" class="input" type="number" placeholder="请输入手机号" />
      <input v-model="loginForm.password" class="input" password placeholder="请输入密码" />
      <button class="primary-btn" @click="handleLogin">{{ loggingIn ? '登录中...' : '立即登录' }}</button>
    </view>

    <view class="card" v-else>
      <view class="section-title">注册并进入</view>
      <input v-model="registerForm.phone" class="input" type="number" placeholder="请输入手机号" />
      <input v-model="registerForm.nickname" class="input" placeholder="请输入昵称" />
      <input v-model="registerForm.password" class="input" password placeholder="请输入密码" />
      <input v-model="registerForm.invite_code" class="input" placeholder="选填邀请码" />
      <button class="primary-btn" @click="handleRegister">{{ registering ? '注册中...' : '注册并进入' }}</button>
    </view>

    <view class="demo-card">
      <view class="demo-title">当前演示账号</view>
      <view class="demo-row">手机号：18800000000</view>
      <view class="demo-row">密码：Admin@123</view>
    </view>
  </view>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'

import { authApi } from '../../api/modules'
import { getToken, setToken, setUserCache } from '../../utils/auth'

const activeTab = ref('login')
const loggingIn = ref(false)
const registering = ref(false)
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

function saveAuth(data) {
  setToken(data.access_token)
  setUserCache(data.user)
}

function toHome() {
  uni.switchTab({ url: '/pages/home/index' })
}

async function handleLogin() {
  if (!loginForm.phone || !loginForm.password) {
    uni.showToast({ title: '请填写手机号和密码', icon: 'none' })
    return
  }
  loggingIn.value = true
  try {
    const data = await authApi.login(loginForm)
    saveAuth(data)
    uni.showToast({ title: '登录成功', icon: 'success' })
    toHome()
  } finally {
    loggingIn.value = false
  }
}

async function handleRegister() {
  if (!registerForm.phone || !registerForm.nickname || !registerForm.password) {
    uni.showToast({ title: '请填写完整注册信息', icon: 'none' })
    return
  }
  registering.value = true
  try {
    const data = await authApi.register({
      ...registerForm,
      invite_code: registerForm.invite_code || null
    })
    saveAuth(data)
    uni.showToast({ title: '注册成功', icon: 'success' })
    toHome()
  } finally {
    registering.value = false
  }
}

onLoad((options) => {
  if (options?.invite_code) {
    activeTab.value = 'register'
    registerForm.invite_code = String(options.invite_code)
  }
})

onShow(() => {
  if (getToken()) {
    toHome()
  }
})
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  padding: 36rpx 24rpx 40rpx;
  background:
    radial-gradient(circle at top, rgba(224, 238, 230, 0.92), transparent 36%),
    linear-gradient(180deg, #f7f2e9 0%, #f2f5ef 48%, #eef3ef 100%);
  box-sizing: border-box;
}

.hero-card {
  background:
    radial-gradient(circle at top right, rgba(62, 152, 108, 0.22), transparent 36%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(246, 250, 246, 0.98) 100%);
  border-radius: 32rpx;
  padding: 36rpx 30rpx;
  margin-bottom: 24rpx;
  box-shadow: 0 20rpx 48rpx rgba(22, 48, 43, 0.08);
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 48rpx;
  padding: 0 18rpx;
  border-radius: 999rpx;
  background: #e8f4ee;
  color: #1e8f64;
  font-size: 22rpx;
  font-weight: 600;
  margin-bottom: 18rpx;
}

.hero-title {
  font-size: 54rpx;
  line-height: 1.18;
  font-weight: 700;
  color: #18342e;
  margin-bottom: 16rpx;
}

.hero-desc {
  font-size: 28rpx;
  color: #66756f;
  line-height: 1.7;
}

.hero-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-top: 22rpx;
}

.hero-pill {
  padding: 10rpx 18rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
  color: #1b6f4f;
  background: rgba(231, 246, 239, 0.9);
}

.tabs {
  display: flex;
  background: #fffdf9;
  border-radius: 24rpx;
  padding: 8rpx;
  margin-bottom: 24rpx;
  box-shadow: 0 18rpx 40rpx rgba(15, 23, 42, 0.06);
}

.tab {
  flex: 1;
  text-align: center;
  font-size: 28rpx;
  color: #66756f;
  padding: 18rpx 0;
  border-radius: 18rpx;
}

.tab.active {
  background: #1e8f64;
  color: #ffffff;
}

.card {
  background: #ffffff;
  border: 1rpx solid rgba(21, 55, 45, 0.06);
  border-radius: 30rpx;
  padding: 30rpx;
  margin-bottom: 24rpx;
  box-shadow: 0 20rpx 48rpx rgba(22, 48, 43, 0.08);
}

.section-title {
  font-size: 40rpx;
  font-weight: 700;
  color: #18342e;
  margin-bottom: 24rpx;
}

.input {
  width: 100%;
  height: 92rpx;
  background: #f5f6f2;
  border: 2rpx solid transparent;
  border-radius: 20rpx;
  padding: 0 26rpx;
  font-size: 28rpx;
  margin-bottom: 20rpx;
  box-sizing: border-box;
  color: #18342e;
}

.primary-btn {
  height: 88rpx;
  line-height: 88rpx;
  border-radius: 20rpx;
  background: #1e8f64;
  color: #ffffff;
  font-size: 29rpx;
  font-weight: 600;
  box-shadow: 0 16rpx 32rpx rgba(30, 143, 100, 0.22);
}

.demo-card {
  background: #18342e;
  color: #ffffff;
  border-radius: 30rpx;
  padding: 28rpx 30rpx;
}

.demo-title {
  font-size: 28rpx;
  font-weight: 700;
  margin-bottom: 12rpx;
}

.demo-row {
  font-size: 28rpx;
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.6;
}
</style>
