<template>
  <view class="page">
    <view class="card hero-card">
      <view class="badge">Account Settings</view>
      <view class="title">密码重置与运行时配置放在同一页维护</view>
      <view class="desc">真机联调时可直接在这里修改接口地址和邀请链接域名，不必每次改源码重新打包。</view>
      <view class="info-list">
        <view class="info-row">当前接口地址：{{ currentApiBaseUrl }}</view>
        <view class="info-row">当前邀请域名：{{ currentInviteWebBaseUrl }}</view>
      </view>
    </view>

    <view class="card">
      <view class="section-head">
        <view class="section-title">密码重置</view>
        <view class="section-link">手机号直接重置</view>
      </view>
      <input v-model="form.phone" class="input" type="number" placeholder="请输入手机号" />
      <input v-model="form.new_password" class="input" password placeholder="请输入新密码" />
      <button class="primary-btn" @click="submitForm">{{ resetting ? '重置中...' : '重置密码' }}</button>
    </view>

    <view class="card">
      <view class="section-head">
        <view class="section-title">运行时配置</view>
        <view class="section-link">真机联调</view>
      </view>
      <input v-model="configForm.api_base_url" class="input" placeholder="例如 http://192.168.1.10:8001" />
      <input v-model="configForm.invite_web_base_url" class="input" placeholder="例如 http://192.168.1.10:5174" />
      <view class="helper-box">
        <view class="helper-text">当前接口地址：{{ currentApiBaseUrl }}</view>
        <view class="helper-text">当前邀请域名：{{ currentInviteWebBaseUrl }}</view>
      </view>
      <view class="action-row settings-actions">
        <button class="secondary-btn" @click="resetConfig">恢复默认值</button>
        <button class="primary-btn" @click="saveConfig">{{ savingConfig ? '保存中...' : '保存配置' }}</button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'

import { authApi } from '../../api/modules'
import {
  DEFAULT_INVITE_WEB_BASE_URL,
  DEFAULT_NATIVE_API_BASE_URL,
  clearApiBaseUrl,
  clearInviteWebBaseUrl,
  getApiBaseUrl,
  getInviteWebBaseUrl,
  setApiBaseUrl,
  setInviteWebBaseUrl
} from '../../config/index'
import { getUserCache } from '../../utils/auth'
import { ensureLogin } from '../../utils/guard'

const form = reactive({
  phone: '',
  new_password: ''
})
const configForm = reactive({
  api_base_url: '',
  invite_web_base_url: ''
})
const resetting = ref(false)
const savingConfig = ref(false)

const currentApiBaseUrl = computed(() => normalizeUrl(configForm.api_base_url) || DEFAULT_NATIVE_API_BASE_URL)
const currentInviteWebBaseUrl = computed(() => normalizeUrl(configForm.invite_web_base_url) || DEFAULT_INVITE_WEB_BASE_URL)

function normalizeUrl(value) {
  return String(value || '').trim().replace(/\/$/, '')
}

async function submitForm() {
  if (!form.phone || !form.new_password) {
    uni.showToast({ title: '请填写完整信息', icon: 'none' })
    return
  }
  resetting.value = true
  try {
    await authApi.resetPassword(form)
    form.new_password = ''
    uni.showToast({ title: '密码已重置', icon: 'success' })
  } finally {
    resetting.value = false
  }
}

function loadConfig() {
  configForm.api_base_url = getApiBaseUrl()
  configForm.invite_web_base_url = getInviteWebBaseUrl()
}

function saveConfig() {
  const apiBaseUrl = normalizeUrl(configForm.api_base_url)
  const inviteWebBaseUrl = normalizeUrl(configForm.invite_web_base_url)
  if (!apiBaseUrl || !inviteWebBaseUrl) {
    uni.showToast({ title: '请填写完整配置', icon: 'none' })
    return
  }
  savingConfig.value = true
  try {
    setApiBaseUrl(apiBaseUrl)
    setInviteWebBaseUrl(inviteWebBaseUrl)
    loadConfig()
    uni.showToast({ title: '配置已保存', icon: 'success' })
  } finally {
    savingConfig.value = false
  }
}

function resetConfig() {
  clearApiBaseUrl()
  clearInviteWebBaseUrl()
  configForm.api_base_url = DEFAULT_NATIVE_API_BASE_URL
  configForm.invite_web_base_url = DEFAULT_INVITE_WEB_BASE_URL
  uni.showToast({ title: '已恢复默认值', icon: 'success' })
}

onLoad(() => {
  if (!ensureLogin()) {
    return
  }
  const user = getUserCache()
  form.phone = user?.phone || ''
  loadConfig()
})
</script>

<style scoped>
.hero-card {
  background:
    radial-gradient(circle at 100% 0%, rgba(232, 192, 149, 0.24), transparent 34%),
    radial-gradient(circle at 0% 12%, rgba(208, 220, 244, 0.28), transparent 28%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(250, 247, 241, 0.98) 100%);
}

.helper-box,
.settings-actions {
  margin-top: 12rpx;
}

.helper-text {
  margin-bottom: 12rpx;
  word-break: break-all;
}
</style>
