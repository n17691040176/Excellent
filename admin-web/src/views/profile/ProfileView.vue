<template>
  <div>
    <div class="page-heading">
      <div>
        <h2>个人中心</h2>
        <p>维护管理员资料、登录信息与安全设置。</p>
      </div>
      <el-button type="primary" @click="loadData">刷新资料</el-button>
    </div>

    <div class="split-grid">
      <div class="panel-card data-card">
        <div class="section-title">
          <div>
            <h3>基础资料</h3>
            <p>修改昵称、头像、真实姓名等信息，并同步本地缓存。</p>
          </div>
        </div>
        <el-form :model="profileForm" label-position="top">
          <el-form-item label="手机号">
            <el-input v-model="profileForm.phone" disabled />
          </el-form-item>
          <el-form-item label="昵称">
            <el-input v-model="profileForm.nickname" placeholder="请输入昵称" />
          </el-form-item>
          <el-form-item label="真实姓名">
            <el-input v-model="profileForm.real_name" placeholder="请输入真实姓名" />
          </el-form-item>
          <el-form-item label="头像地址">
            <el-input v-model="profileForm.avatar" placeholder="请输入头像 URL" />
          </el-form-item>
          <el-form-item>
            <el-button v-permission="'profile:edit'" type="primary" @click="saveProfile">保存资料</el-button>
          </el-form-item>
        </el-form>
      </div>

      <div class="panel-card data-card">
        <div class="section-title">
          <div>
            <h3>账号安全</h3>
            <p>当前版本使用手机号重置密码，保存后需重新登录验证新密码。</p>
          </div>
        </div>
        <div class="tiny-stat-grid" style="margin-bottom: 18px;">
          <div class="tiny-stat">
            <div class="title">系统角色</div>
            <div class="number">{{ roleLabel }}</div>
            <div class="meta">后台路由与菜单按角色收敛</div>
          </div>
          <div class="tiny-stat">
            <div class="title">业务身份</div>
            <div class="number">{{ profileForm.business_identity || '--' }}</div>
            <div class="meta">可关联团队、招商或本地生活身份</div>
          </div>
        </div>
        <el-form :model="passwordForm" label-position="top">
          <el-form-item label="当前密码">
            <el-input v-model="passwordForm.current_password" type="password" show-password placeholder="请输入当前密码" />
          </el-form-item>
          <el-form-item label="新密码">
            <el-input v-model="passwordForm.new_password" type="password" show-password placeholder="请输入新密码" />
          </el-form-item>
          <el-form-item label="确认新密码">
            <el-input v-model="passwordForm.confirm_password" type="password" show-password placeholder="请再次输入新密码" />
          </el-form-item>
          <el-form-item>
            <el-button v-permission="'profile:password'" type="primary" plain @click="resetPassword">重置密码</el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'

import { adminProfileApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const profileForm = reactive({
  phone: '',
  nickname: '',
  real_name: '',
  avatar: '',
  business_identity: '',
  global_role: ''
})
const passwordForm = reactive({
  current_password: '',
  new_password: '',
  confirm_password: ''
})

const roleLabel = computed(() => ({
  SUPER_ADMIN: '超级管理员',
  TEAM_ADMIN: '团队管理员',
  USER: '普通用户'
}[profileForm.global_role] || '--'))

async function loadData() {
  const profile = await adminProfileApi.get()
  Object.assign(profileForm, profile)
  userStore.userInfo = profile
}

async function saveProfile() {
  const payload = {
    nickname: profileForm.nickname,
    real_name: profileForm.real_name,
    avatar: profileForm.avatar
  }
  const profile = await adminProfileApi.update(payload)
  Object.assign(profileForm, profile)
  userStore.userInfo = profile
  ElMessage.success('资料已更新')
}

async function resetPassword() {
  if (!passwordForm.current_password) {
    ElMessage.warning('请输入当前密码')
    return
  }
  if (!passwordForm.new_password) {
    ElMessage.warning('请输入新密码')
    return
  }
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  await adminProfileApi.changePassword({
    current_password: passwordForm.current_password,
    new_password: passwordForm.new_password
  })
  passwordForm.current_password = ''
  passwordForm.new_password = ''
  passwordForm.confirm_password = ''
  ElMessage.success('密码已重置，请使用新密码重新登录')
}

onMounted(loadData)
</script>
