<template>
  <div class="page safe-bottom">
    <van-nav-bar title="我的团队" fixed placeholder />

    <div class="page-card hero-soft">
      <div class="hero-badge">Team Center</div>
      <h2 class="page-title">{{ team && team.id ? '团队关系和成员管理' : '还没有团队，先创建或加入' }}</h2>
      <p class="page-desc">支持创建团队、编辑资料、邀请成员加入，并在负责人权限下管理成员角色。</p>
      <div v-if="team && team.id" class="metric-grid">
        <div class="metric-card" v-for="item in teamMetrics" :key="item.label">
          <div class="metric-label">{{ item.label }}</div>
          <div class="metric-value">{{ item.value }}</div>
          <div class="metric-meta">{{ item.meta }}</div>
        </div>
      </div>
      <div v-else class="state-desc">创建团队后，成员关系、角色和邀请链路都会统一落在这里管理。</div>
    </div>

    <div v-if="loadError" class="page-card">
      <div class="state-card">
        <div class="state-title">团队数据加载失败</div>
        <div class="state-desc">{{ loadError }}</div>
        <van-button block round plain type="primary" style="margin-top: 0.18rem;" @click="loadData">重新加载</van-button>
      </div>
    </div>

    <div class="page-card" v-else-if="!team || !team.id">
      <div class="section-head">
        <h3 class="cell-group-title" style="margin: 0;">创建团队 / 加入团队</h3>
        <span class="section-link-text">二选一</span>
      </div>
      <van-form @submit="handleCreate">
        <van-field v-model="createForm.name" label="团队名称" placeholder="请输入团队名称" />
        <van-field v-model="createForm.description" label="团队简介" placeholder="请输入团队简介" />
        <div class="submit-bar">
          <van-button block round type="primary" native-type="submit">{{ submittingCreate ? '创建中...' : '创建团队' }}</van-button>
        </div>
      </van-form>
      <van-divider>或</van-divider>
      <van-field v-model="joinTeamId" label="团队 ID" type="digit" placeholder="输入团队 ID 加入" />
      <div class="submit-bar">
        <van-button block round plain type="primary" @click="handleJoin">{{ submittingJoin ? '加入中...' : '申请加入团队' }}</van-button>
      </div>
    </div>

    <template v-else>
      <div class="page-card">
        <div class="section-head">
          <h3 class="cell-group-title" style="margin: 0;">团队概览</h3>
          <span class="section-link-text">团队 #{{ team.id }}</span>
        </div>
        <div class="soft-section">
          <div class="product-meta">团队名称 {{ team.name }}</div>
          <div class="product-meta">负责人 {{ team.owner_user_id || '--' }}</div>
          <div class="product-meta">状态 {{ team.status || '--' }}</div>
          <div class="product-meta">简介 {{ team.description || '暂无简介' }}</div>
        </div>
      </div>

      <div class="page-card">
        <div class="section-head">
          <h3 class="cell-group-title" style="margin: 0;">团队维护</h3>
          <span class="section-link-text">资料更新</span>
        </div>
        <van-form @submit="handleUpdate">
          <van-field v-model="editForm.name" label="团队名称" placeholder="请输入团队名称" />
          <van-field v-model="editForm.description" label="团队简介" placeholder="请输入团队简介" />
          <div class="inline-actions submit-bar">
            <van-button block round plain type="primary" native-type="submit">{{ submittingUpdate ? '保存中...' : '保存团队' }}</van-button>
            <van-button block round type="danger" @click="handleDissolve">{{ dissolving ? '处理中...' : '解散团队' }}</van-button>
          </div>
        </van-form>
      </div>

      <div class="page-card">
        <div class="section-head">
          <h3 class="cell-group-title" style="margin: 0;">成员列表</h3>
          <span class="section-link-text">{{ members.length }} 人</span>
        </div>
        <div v-if="loading" class="card-stack">
          <div class="skeleton-card short"></div>
        </div>
        <div v-else-if="members.length" class="card-stack">
          <div class="soft-section" v-for="member in members" :key="member.id">
            <div class="top-row">
              <div class="product-name">用户 {{ member.user_id }}</div>
              <div class="status-capsule" :class="teamRoleClass(member.team_role)">{{ teamRoleLabel(member.team_role) }}</div>
            </div>
            <div class="product-meta">加入时间 {{ formatDate(member.joined_at) }}</div>
            <div class="inline-actions" style="margin-top: 0.14rem; justify-content: flex-end; flex-wrap: wrap;">
              <van-button size="small" plain type="primary" @click="switchRole(member)">切换角色</van-button>
              <van-button size="small" plain type="danger" @click="removeMember(member)">移除</van-button>
            </div>
          </div>
        </div>
        <van-empty v-else image="search" description="当前团队暂无成员" />
      </div>
    </template>

    <AppTabbar />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import dayjs from 'dayjs'
import { showConfirmDialog, showSuccessToast } from 'vant'

import AppTabbar from '@/components/AppTabbar.vue'
import { teamApi } from '@/api/modules'
import { normalizeLoadError, teamRoleClass, teamRoleLabel } from '@/utils/ui'

const team = ref(null)
const members = ref([])
const joinTeamId = ref('')
const createForm = reactive({ name: '', description: '' })
const editForm = reactive({ name: '', description: '' })
const loading = ref(false)
const loadError = ref('')
const submittingCreate = ref(false)
const submittingJoin = ref(false)
const submittingUpdate = ref(false)
const dissolving = ref(false)

const teamMetrics = computed(() => [
  { label: '团队成员', value: members.value.length, meta: '当前团队已加入人数' },
  { label: '团队状态', value: team.value?.status || '--', meta: '团队可用状态' },
  { label: '负责人', value: team.value?.owner_user_id || '--', meta: '当前拥有者账号' },
  { label: '团队编号', value: team.value?.id || '--', meta: '用于邀请和加入团队' }
])

function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '--'
}

async function loadData() {
  loading.value = true
  loadError.value = ''
  try {
    try {
      team.value = await teamApi.current()
    } catch {
      team.value = null
    }
    if (team.value?.id) {
      members.value = await teamApi.members(team.value.id)
      editForm.name = team.value.name || ''
      editForm.description = team.value.description || ''
    } else {
      members.value = []
    }
  } catch (error) {
    loadError.value = normalizeLoadError(error)
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  submittingCreate.value = true
  try {
    await teamApi.create(createForm)
    showSuccessToast('团队已创建')
    createForm.name = ''
    createForm.description = ''
    await loadData()
  } finally {
    submittingCreate.value = false
  }
}

async function handleJoin() {
  if (!joinTeamId.value) return
  submittingJoin.value = true
  try {
    await teamApi.join(joinTeamId.value)
    showSuccessToast('加入成功')
    joinTeamId.value = ''
    await loadData()
  } finally {
    submittingJoin.value = false
  }
}

async function handleUpdate() {
  submittingUpdate.value = true
  try {
    await teamApi.update(team.value.id, editForm)
    showSuccessToast('团队已更新')
    await loadData()
  } finally {
    submittingUpdate.value = false
  }
}

async function handleDissolve() {
  await showConfirmDialog({ title: '提示', message: '确认解散当前团队吗？' })
  dissolving.value = true
  try {
    await teamApi.dissolve(team.value.id)
    showSuccessToast('团队已解散')
    await loadData()
  } finally {
    dissolving.value = false
  }
}

async function switchRole(member) {
  const nextRole = member.team_role === 'OWNER' ? 'MEMBER' : 'OWNER'
  await teamApi.updateRole(team.value.id, member.user_id, { team_role: nextRole })
  showSuccessToast('成员角色已更新')
  await loadData()
}

async function removeMember(member) {
  await showConfirmDialog({ title: '提示', message: `确认移除用户 ${member.user_id} 吗？` })
  await teamApi.removeMember(team.value.id, member.user_id)
  showSuccessToast('成员已移除')
  await loadData()
}

onMounted(loadData)
</script>
