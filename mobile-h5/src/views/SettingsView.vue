<template>
  <div class="page safe-bottom">
    <van-nav-bar title="设置" fixed placeholder left-arrow @click-left="$router.back()" />

    <div class="page-card">
      <h2 class="page-title">密码重置</h2>
      <p class="page-desc">当前版本直接通过手机号重置密码，适合单节点轻量应用快速交付。</p>
      <van-form @submit="submitForm">
        <van-field v-model="form.phone" label="手机号" placeholder="请输入手机号" />
        <van-field v-model="form.new_password" label="新密码" type="password" placeholder="请输入新密码" />
        <div class="submit-bar">
          <van-button round block type="primary" native-type="submit">重置密码</van-button>
        </div>
      </van-form>
    </div>

    <AppTabbar />
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { showSuccessToast } from 'vant'

import AppTabbar from '@/components/AppTabbar.vue'
import { authApi } from '@/api/modules'

const form = reactive({
  phone: '',
  new_password: ''
})

async function submitForm() {
  await authApi.resetPassword(form)
  form.new_password = ''
  showSuccessToast('密码已重置')
}
</script>
