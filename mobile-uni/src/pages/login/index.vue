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
    radial-gradient(circle at 0% 0%, rgba(233, 176, 120, 0.22), transparent 24%),
    radial-gradient(circle at 100% 8%, rgba(208, 220, 244, 0.64), transparent 24%),
    linear-gradient(180deg, #fbf8f3 0%, #f6f4ef 42%, #f3f1ec 100%);
  box-sizing: border-box;
}

.hero-card {
  background:
    radial-gradient(circle at 100% 0%, rgba(232, 192, 149, 0.24), transparent 34%),
    radial-gradient(circle at 0% 12%, rgba(208, 220, 244, 0.32), transparent 28%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(250, 247, 241, 0.98) 100%);
  border-radius: 32rpx;
  padding: 36rpx 30rpx;
  margin-bottom: 24rpx;
  box-shadow: 0 20rpx 48rpx rgba(136, 124, 107, 0.1);
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 48rpx;
  padding: 0 18rpx;
  border-radius: 999rpx;
  background: rgba(210, 108, 50, 0.08);
  color: #c96a32;
  font-size: 22rpx;
  font-weight: 600;
  margin-bottom: 18rpx;
  border: 1rpx solid rgba(210, 108, 50, 0.14);
}

.hero-title {
  font-size: 54rpx;
  line-height: 1.18;
  font-weight: 700;
  color: #191613;
  margin-bottom: 16rpx;
}

.hero-desc {
  font-size: 28rpx;
  color: #7a726a;
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
  color: #7d5633;
  background: #f5ede4;
  border: 1rpx solid rgba(230, 215, 198, 0.9);
}

.tabs {
  display: flex;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 24rpx;
  padding: 8rpx;
  margin-bottom: 24rpx;
  box-shadow: 0 18rpx 40rpx rgba(136, 124, 107, 0.08);
  border: 1rpx solid rgba(232, 223, 214, 0.9);
}

.tab {
  flex: 1;
  text-align: center;
  font-size: 28rpx;
  color: #7a726a;
  padding: 18rpx 0;
  border-radius: 18rpx;
}

.tab.active {
  background: linear-gradient(180deg, #d7793e 0%, #c96a32 100%);
  color: #ffffff;
}

.card {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.94) 0%, rgba(252, 250, 246, 0.96) 100%);
  border: 1rpx solid rgba(238, 229, 219, 0.9);
  border-radius: 30rpx;
  padding: 30rpx;
  margin-bottom: 24rpx;
  box-shadow:
    0 18rpx 42rpx rgba(136, 124, 107, 0.1),
    inset 0 1rpx 0 rgba(255, 255, 255, 0.75);
}

.section-title {
  font-size: 40rpx;
  font-weight: 700;
  color: #191613;
  margin-bottom: 24rpx;
}

.input {
  width: 100%;
  height: 92rpx;
  background: #fbfaf7;
  border: 2rpx solid rgba(232, 223, 214, 0.76);
  border-radius: 20rpx;
  padding: 0 26rpx;
  font-size: 28rpx;
  margin-bottom: 20rpx;
  box-sizing: border-box;
  color: #191613;
}

.primary-btn {
  height: 88rpx;
  line-height: 88rpx;
  border-radius: 20rpx;
  background: linear-gradient(180deg, #d7793e 0%, #c96a32 100%);
  color: #ffffff;
  font-size: 29rpx;
  font-weight: 600;
  box-shadow: 0 16rpx 32rpx rgba(201, 106, 50, 0.22);
}

.demo-card {
  background: linear-gradient(150deg, #2a241f 0%, #513d2f 56%, #8a6448 100%);
  color: #ffffff;
  border-radius: 30rpx;
  padding: 28rpx 30rpx;
  box-shadow: 0 20rpx 42rpx rgba(111, 84, 58, 0.18);
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
