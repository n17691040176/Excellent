<template>
  <div>
    <div class="page-heading">
      <div>
        <h2>用户管理</h2>
        <p>{{ scopeHint }}</p>
      </div>
      <el-button type="primary" @click="fetchUsers">刷新列表</el-button>
    </div>

    <div class="panel-card data-card">
      <div class="toolbar-row">
        <el-input v-model="keyword" placeholder="搜索手机号或昵称" clearable style="max-width: 280px;" />
        <el-select v-model="roleFilter" placeholder="角色筛选" clearable style="width: 180px;">
          <el-option label="超级管理员" value="SUPER_ADMIN" />
          <el-option label="团队管理员" value="TEAM_ADMIN" />
          <el-option label="普通用户" value="USER" />
        </el-select>
      </div>

      <el-table :data="filteredUsers" border>
        <el-table-column prop="id" label="ID" width="90" />
        <el-table-column prop="phone" label="手机号" min-width="150" />
        <el-table-column prop="nickname" label="昵称" min-width="140" />
        <el-table-column prop="global_role" label="系统角色" min-width="130" />
        <el-table-column prop="business_identity" label="业务身份" min-width="140" />
        <el-table-column label="状态" width="120">
          <template #default="scope">
            <el-tag :type="scope.row.status === 'ENABLED' ? 'success' : 'danger'">{{ scope.row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="team_id" label="团队归属" width="110" />
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="scope">
            <el-button link type="primary" @click="openInviteTree(scope.row)">邀请关系</el-button>
            <el-button v-permission="'users:status'" link type="warning" @click="toggleStatus(scope.row)">
              {{ scope.row.status === 'ENABLED' ? '禁用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-drawer v-model="drawerVisible" title="邀请关系" size="520px">
      <div class="panel-card data-card">
        <div class="soft-tag">用户 {{ inviteTree.user_id || '--' }}</div>
        <p style="margin: 14px 0 10px;">手机号：{{ inviteTree.phone || '--' }}</p>
        <el-divider content-position="left">一级邀请</el-divider>
        <el-table :data="inviteTree.level1 || []" size="small" border>
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="phone" label="手机号" />
          <el-table-column prop="nickname" label="昵称" />
        </el-table>
        <el-divider content-position="left">二级邀请</el-divider>
        <el-table :data="inviteTree.level2 || []" size="small" border>
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="phone" label="手机号" />
          <el-table-column prop="nickname" label="昵称" />
        </el-table>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessageBox } from 'element-plus'

import { userApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const users = ref([])
const keyword = ref('')
const roleFilter = ref('')
const drawerVisible = ref(false)
const inviteTree = ref({})

const scopeHint = computed(() =>
  userStore.role === 'TEAM_ADMIN'
    ? '仅查看当前团队用户、团队归属与该团队内可见的邀请码关系。'
    : '查看全平台用户状态、团队归属、邀请关系和后台可见范围。'
)

const filteredUsers = computed(() => {
  return users.value.filter((item) => {
    const hitKeyword = !keyword.value || item.phone?.includes(keyword.value) || item.nickname?.includes(keyword.value)
    const hitRole = !roleFilter.value || item.global_role === roleFilter.value
    return hitKeyword && hitRole
  })
})

async function fetchUsers() {
  users.value = await userApi.list()
}

async function openInviteTree(row) {
  inviteTree.value = await userApi.inviteTree(row.id)
  drawerVisible.value = true
}

async function toggleStatus(row) {
  const nextStatus = row.status === 'ENABLED' ? 'DISABLED' : 'ENABLED'
  await ElMessageBox.confirm(`确认将该用户状态调整为 ${nextStatus} 吗？`, '状态变更', { type: 'warning' })
  await userApi.updateStatus(row.id, { status: nextStatus })
  await fetchUsers()
}

onMounted(fetchUsers)
</script>
