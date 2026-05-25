<template>
  <view class="container settings-page">
    <view class="card hero-card">
      <view class="hero-tag">账号设置</view>
      <view class="section-title mt-12">管理资料、安全与偏好配置</view>
      <view class="muted">切换环境、查看账号偏好，方便调试和联调</view>

      <view class="setting-list mt-20">
        <view class="setting-item interactive" v-for="item in items" :key="item.title" @click="preview(item.title)">
          <view>
            <view class="item-title">{{ item.title }}</view>
            <view class="item-desc">{{ item.desc }}</view>
          </view>
          <view class="arrow">查看</view>
        </view>
      </view>
    </view>

    <view class="card mt-20 env-card">
      <view class="row-between">
        <view>
          <view class="section-title slim-title">环境切换</view>
          <view class="muted">用于控制移动端打包后访问的 API 地址</view>
        </view>
        <view class="env-current-value">{{ currentEnvLabel }}</view>
      </view>

      <view class="env-grid mt-16">
        <view
          v-for="env in envOptions"
          :key="env.value"
          class="env-item interactive"
          :class="{ active: currentEnv === env.value }"
          @click="applyEnv(env.value)"
        >
          <view class="env-head">
            <view class="env-name">{{ env.label }}</view>
            <view class="env-badge" :class="env.badgeClass">{{ env.tag }}</view>
          </view>
          <view class="env-url">{{ env.apiUrl || '留空，后续补充' }}</view>
          <view class="env-note">{{ env.note }}</view>
        </view>
      </view>

      <view class="env-current">
        <view class="env-current-label">当前环境</view>
        <view class="env-current-value">{{ currentEnvLabel }}</view>
      </view>

      <view class="env-debug">
        <view class="env-debug-title">当前 API 地址</view>
        <view class="env-debug-code">{{ currentApiBaseUrlDisplay }}</view>
      </view>
    </view>

    <button class="btn btn-ghost mt-24 logout-btn" @click="logout">退出登录</button>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { clearAuth } from '@/utils/auth'
import {
  APP_ENV,
  clearApiBaseUrl,
  clearAppEnv,
  clearInviteWebBaseUrl,
  getApiBaseUrl,
  getAppEnv,
  setApiBaseUrl,
  setAppEnv,
  setInviteWebBaseUrl
} from '@/config'

const items = [
  { title: '个人资料', desc: '头像、昵称和联系方式' },
  { title: '账号安全', desc: '修改手机号与登录验证' },
  { title: '隐私设置', desc: '授权范围与数据管理' }
]

const envOptions = [
  {
    value: APP_ENV.LOCAL,
    label: '本地环境',
    tag: 'local',
    apiUrl: 'http://127.0.0.1:8000',
    note: '适合电脑本机启动后调试',
    badgeClass: 'badge-local'
  },
  {
    value: APP_ENV.DEV,
    label: '开发服务器',
    tag: 'dev',
    apiUrl: 'http://156.238.241.213:8000',
    note: '适合真机或打包后联调',
    badgeClass: 'badge-dev'
  },
  {
    value: APP_ENV.PROD,
    label: '部署服务器',
    tag: 'prod',
    apiUrl: '',
    note: '上线前再填写正式地址',
    badgeClass: 'badge-prod'
  }
]

const currentEnv = ref(getAppEnv())
const currentApiBaseUrl = computed(() => getApiBaseUrl())
const currentApiBaseUrlDisplay = computed(() => currentApiBaseUrl.value || '未配置')

const currentEnvLabel = computed(() => {
  const matched = envOptions.find((item) => item.value === currentEnv.value)
  return matched ? `${matched.label}（${matched.tag}）` : currentEnv.value
})

const envRuntimeConfig = {
  [APP_ENV.LOCAL]: {
    apiUrl: 'http://127.0.0.1:8000',
    inviteUrl: 'http://127.0.0.1:5174'
  },
  [APP_ENV.DEV]: {
    apiUrl: 'http://156.238.241.213:8000',
    inviteUrl: 'http://156.238.241.213:5174'
  },
  [APP_ENV.PROD]: {
    apiUrl: '',
    inviteUrl: ''
  }
}

const logout = () => {
  clearAuth()
  uni.reLaunch({ url: '/pages/login/index' })
}

const preview = (title) => {
  uni.showToast({ title: `${title}即将开放`, icon: 'none' })
}

const applyEnv = (env) => {
  if (env === currentEnv.value) {
    uni.showToast({ title: `已是${currentEnvLabel.value}`, icon: 'none' })
    return
  }

  if (env === APP_ENV.PROD) {
    clearAppEnv()
    clearApiBaseUrl()
    clearInviteWebBaseUrl()
  } else {
    setAppEnv(env)
    const runtimeConfig = envRuntimeConfig[env]
    setApiBaseUrl(runtimeConfig?.apiUrl || '')
    setInviteWebBaseUrl(runtimeConfig?.inviteUrl || '')
  }

  currentEnv.value = getAppEnv()
  uni.showToast({ title: `已切换到${currentEnvLabel.value}`, icon: 'none' })
  setTimeout(() => {
    const pages = getCurrentPages()
    const currentPage = pages[pages.length - 1]
    if (!currentPage) {
      uni.reLaunch({ url: '/pages/profile/index' })
      return
    }

    const route = `/${currentPage.route}`
    uni.reLaunch({ url: route })
  }, 300)
}
</script>

<style scoped>
@import '@/styles/common.css';
.settings-page { padding-bottom: 36rpx; }
.hero-card {
  background:
    radial-gradient(circle at 95% 8%, rgba(255, 166, 82, 0.16), transparent 36%),
    linear-gradient(180deg, #fffdf9 0%, #fff6ec 100%);
  border: 1rpx solid rgba(255, 154, 106, 0.16);
}
.hero-tag {
  display: inline-flex;
  align-items: center;
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  background: rgba(255, 138, 43, 0.12);
  color: #ff6a00;
  font-size: 20rpx;
  font-weight: 800;
}
.setting-list {
  display: grid;
  gap: 12rpx;
}
.setting-item {
  padding: 18rpx 0;
  border-bottom: 1rpx solid #ebf2ef;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.setting-item:last-child { border-bottom: none; }
.item-title { font-size: 28rpx; color: #1f4032; }
.item-desc { margin-top: 6rpx; font-size: 22rpx; color: #7a8d84; }
.arrow { font-size: 22rpx; color: #ff6a00; font-weight: 700; }
.env-card { border: 1rpx solid rgba(255, 154, 106, 0.16); }
.env-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12rpx;
}
.env-item {
  padding: 20rpx;
  border-radius: 20rpx;
  border: 1rpx solid #edf0ee;
  background: #fbfcfb;
}
.env-item.active {
  border-color: #ffbf6e;
  background: linear-gradient(180deg, #fff7eb, #fff1de);
  box-shadow: 0 14rpx 24rpx rgba(179, 117, 45, 0.08);
}
.env-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12rpx;
}
.env-name { font-size: 28rpx; font-weight: 700; color: #1f4032; }
.env-badge {
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  font-size: 18rpx;
  font-weight: 700;
  color: #fff;
}
.badge-local { background: linear-gradient(180deg, #60a5fa, #2563eb); }
.badge-dev { background: linear-gradient(180deg, #34d399, #059669); }
.badge-prod { background: linear-gradient(180deg, #fb7185, #e11d48); }
.env-url { margin-top: 10rpx; font-size: 22rpx; color: #6f7f78; }
.env-note { margin-top: 8rpx; font-size: 20rpx; color: #95a39c; }
.env-current {
  margin-top: 16rpx;
  padding: 16rpx 18rpx;
  border-radius: 18rpx;
  background: #f6faf8;
  display: flex;
  justify-content: space-between;
  gap: 12rpx;
}
.env-current-label { font-size: 22rpx; color: #7b8f86; }
.env-current-value { font-size: 22rpx; font-weight: 700; color: #1f4032; }
.env-debug {
  margin-top: 12rpx;
  padding: 16rpx 18rpx;
  border-radius: 18rpx;
  background: #fff9f1;
  border: 1rpx solid #f3ddbe;
}
.env-debug-title { font-size: 22rpx; color: #8a6240; font-weight: 700; }
.env-debug-code {
  margin-top: 8rpx;
  font-size: 20rpx;
  line-height: 1.6;
  color: #5f4a37;
  word-break: break-all;
}
.logout-btn {
  width: 100%;
}
.interactive { transition: transform 180ms ease, opacity 180ms ease; }
.interactive:active { transform: scale(0.99); opacity: 0.92; }
</style>
