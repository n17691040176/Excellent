<template>
  <div>
    <div class="page-heading">
      <div>
        <h2>账号管理</h2>
        <p>仅超级管理员可查看后台账号、角色分布与启停状态。</p>
      </div>
      <el-button type="primary" @click="loadData">刷新账号</el-button>
    </div>

    <div class="panel-card data-card">
      <div class="toolbar-row">
        <el-input v-model="keyword" placeholder="搜索手机号 / 昵称" clearable style="max-width: 260px;" />
        <el-select v-model="roleFilter" placeholder="账号角色" clearable style="width: 180px;">
          <el-option label="超级管理员" value="SUPER_ADMIN" />
          <el-option label="团队管理员" value="TEAM_ADMIN" />
        </el-select>
      </div>

      <el-table :data="pagedRows" border>
        <el-table-column prop="id" label="账号 ID" width="90" />
        <el-table-column prop="phone" label="手机号" min-width="150" />
        <el-table-column prop="nickname" label="昵称" min-width="140" />
        <el-table-column prop="global_role" label="角色" width="130" />
        <el-table-column prop="business_identity" label="业务身份" min-width="140" />
        <el-table-column label="状态" width="120">
          <template #default="scope">
            <el-tag :type="scope.row.status === 'ENABLED' ? 'success' : 'danger'">{{ scope.row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="team_id" label="团队 ID" width="100" />
        <el-table-column label="最后登录" min-width="170">
          <template #default="scope">{{ formatDate(scope.row.last_login_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="scope">
            <el-button link type="warning" @click="toggleStatus(scope.row)">
              {{ scope.row.status === 'ENABLED' ? '禁用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        layout="total, prev, pager, next"
        :total="filteredRows.length"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import dayjs from 'dayjs'
import { ElMessageBox } from 'element-plus'

import { userApi } from '@/api/modules'

const rows = ref([])
const keyword = ref('')
const roleFilter = ref('')
const page = ref(1)
const pageSize = ref(10)

const filteredRows = computed(() => {
  const term = keyword.value.trim()
  return rows.value.filter((item) => {
    const adminHit = ['SUPER_ADMIN', 'TEAM_ADMIN'].includes(item.global_role)
    const keywordHit = !term || item.phone?.includes(term) || item.nickname?.includes(term)
    const roleHit = !roleFilter.value || item.global_role === roleFilter.value
    return adminHit && keywordHit && roleHit
  })
})

const pagedRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredRows.value.slice(start, start + pageSize.value)
})

function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '--'
}

async function loadData() {
  rows.value = await userApi.list()
}

async function toggleStatus(row) {
  const nextStatus = row.status === 'ENABLED' ? 'DISABLED' : 'ENABLED'
  await ElMessageBox.confirm(`确认将账号调整为 ${nextStatus} 吗？`, '账号状态调整', { type: 'warning' })
  await userApi.updateStatus(row.id, { status: nextStatus })
  await loadData()
}

onMounted(loadData)
</script>
