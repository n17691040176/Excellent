<template>
  <view class="page">
    <view class="card">
      <view class="title">密码重置</view>
      <view class="desc">当前版本直接通过手机号重置密码，适合单节点轻量应用快速交付。</view>
      <input v-model="form.phone" class="input" type="number" placeholder="请输入手机号" />
      <input v-model="form.new_password" class="input" password placeholder="请输入新密码" />
      <button class="primary-btn" @click="submitForm">重置密码</button>
    </view>

    <view class="card">
      <view class="title">运行时配置</view>
      <view class="desc">真机联调时可直接在这里修改接口地址和邀请链接域名，不必每次改源码重新打包。</view>
      <input v-model="configForm.api_base_url" class="input" placeholder="例如 http://192.168.1.10:8001" />
      <input v-model="configForm.invite_web_base_url" class="input" placeholder="例如 http://192.168.1.10:5174" />
      <view class="helper-text">当前接口地址：{{ currentApiBaseUrl }}</view>
      <view class="helper-text">当前邀请域名：{{ currentInviteWebBaseUrl }}</view>
      <view class="action-row">
        <button class="secondary-btn" @click="resetConfig">恢复默认值</button>
        <button class="primary-btn" @click="saveConfig">保存配置</button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, reactive } from 'vue'
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
  await authApi.resetPassword(form)
  form.new_password = ''
  uni.showToast({ title: '密码已重置', icon: 'success' })
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
  setApiBaseUrl(apiBaseUrl)
  setInviteWebBaseUrl(inviteWebBaseUrl)
  loadConfig()
  uni.showToast({ title: '配置已保存', icon: 'success' })
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
.helper-text {
  margin-bottom: 12rpx;
  word-break: break-all;
}

.action-row {
  margin-top: 8rpx;
}
</style>
