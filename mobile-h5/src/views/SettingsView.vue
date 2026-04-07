<template>
  <div class="page safe-bottom">
    <van-nav-bar title="设置" fixed placeholder left-arrow @click-left="$router.back()" />

    <div class="page-card hero-soft">
      <div class="hero-badge">Account Settings</div>
      <h2 class="page-title">密码重置放在独立设置页处理</h2>
      <p class="page-desc">当前 H5 版以轻量交付为主，先提供直接通过手机号重置密码的入口。</p>
    </div>

    <div class="page-card">
      <div class="section-head">
        <h3 class="cell-group-title" style="margin: 0;">密码重置</h3>
        <span class="section-link-text">手机号直改</span>
      </div>
      <van-form @submit="submitForm">
        <van-field v-model="form.phone" label="手机号" placeholder="请输入手机号" />
        <van-field v-model="form.new_password" label="新密码" type="password" placeholder="请输入新密码" />
        <div class="submit-bar">
          <van-button round block type="primary" native-type="submit">{{ resetting ? '重置中...' : '重置密码' }}</van-button>
        </div>
      </van-form>
    </div>

    <AppTabbar />
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { showSuccessToast } from 'vant'

import AppTabbar from '@/components/AppTabbar.vue'
import { authApi } from '@/api/modules'

const form = reactive({
  phone: '',
  new_password: ''
})
const resetting = ref(false)

async function submitForm() {
  resetting.value = true
  try {
    await authApi.resetPassword(form)
    form.new_password = ''
    showSuccessToast('密码已重置')
  } finally {
    resetting.value = false
  }
}
</script>
