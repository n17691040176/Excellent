<template>
  <view class="page">
    <view class="card hero-card">
      <view class="badge">Team Center</view>
      <view class="title">{{ team && team.id ? '团队关系和成员管理' : '还没有团队，先创建或加入' }}</view>
      <view class="desc">
        支持创建团队、编辑资料、邀请成员加入，并在负责人权限下管理成员角色。
      </view>
      <view v-if="team && team.id" class="metric-grid">
        <view class="metric-card" v-for="item in teamMetrics" :key="item.label">
          <view class="metric-label">{{ item.label }}</view>
          <view class="metric-value">{{ item.value }}</view>
          <view class="metric-meta">{{ item.meta }}</view>
        </view>
      </view>
      <view v-else class="empty-tip">创建团队后，成员关系、角色和邀请链路都会统一落在这里管理。</view>
    </view>

    <view v-if="loadError" class="card">
      <view class="status-card">
        <view class="status-title">团队数据加载失败</view>
        <view class="status-desc">{{ loadError }}</view>
        <button class="secondary-btn retry-btn" @click="loadData">重新加载</button>
      </view>
    </view>

    <view v-else-if="!team || !team.id" class="card">
      <view class="section-head">
        <view class="section-title">创建团队 / 加入团队</view>
        <view class="section-link">二选一</view>
      </view>
      <input v-model="createForm.name" class="input" placeholder="请输入团队名称" />
      <input v-model="createForm.description" class="input" placeholder="请输入团队简介" />
      <button class="primary-btn" @click="handleCreate">{{ submittingCreate ? '创建中...' : '创建团队' }}</button>
      <view class="divider">或</view>
      <input v-model="joinTeamId" class="input" type="number" placeholder="输入团队 ID 加入" />
      <button class="secondary-btn" @click="handleJoin">{{ submittingJoin ? '加入中...' : '申请加入团队' }}</button>
    </view>

    <template v-else>
      <view class="card">
        <view class="section-head">
          <view class="section-title">团队概览</view>
          <view class="section-link">团队 #{{ team.id }}</view>
        </view>
        <view class="info-list">
          <view class="info-row">团队名称：{{ team.name }}</view>
          <view class="info-row">负责人：{{ team.owner_user_id || '--' }}</view>
          <view class="info-row">状态：{{ team.status || '--' }}</view>
          <view class="info-row">简介：{{ team.description || '暂无简介' }}</view>
        </view>
      </view>

      <view class="card">
        <view class="section-head">
          <view class="section-title">团队维护</view>
          <view class="section-link">资料更新</view>
        </view>
        <input v-model="editForm.name" class="input" placeholder="请输入团队名称" />
        <input v-model="editForm.description" class="input" placeholder="请输入团队简介" />
        <view class="action-row">
          <button class="secondary-btn" @click="handleUpdate">{{ submittingUpdate ? '保存中...' : '保存团队' }}</button>
          <button class="danger-btn" @click="handleDissolve">{{ dissolving ? '处理中...' : '解散团队' }}</button>
        </view>
      </view>

      <view class="card">
        <view class="section-head">
          <view class="section-title">成员列表</view>
          <view class="section-link">{{ members.length }} 人</view>
        </view>
        <view v-if="loading">
          <view class="skeleton-block short"></view>
        </view>
        <view v-else-if="members.length" class="member-list">
          <view class="member-card" v-for="member in members" :key="member.id">
            <view class="member-top">
              <view class="member-title">用户 {{ member.user_id }}</view>
              <view class="role-pill">{{ teamRoleLabel(member.team_role) }}</view>
            </view>
            <view class="member-meta">加入时间 {{ formatDate(member.joined_at) }}</view>
            <view class="action-row action-pad">
              <button class="minor-btn" @click="switchRole(member)">切换角色</button>
              <button class="danger-btn" @click="removeMember(member)">移除</button>
            </view>
          </view>
        </view>
        <view v-else class="empty-text">当前团队暂无成员</view>
      </view>
    </template>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'

import { teamApi } from '../../api/modules'
import { ensureLogin } from '../../utils/guard'
import { normalizeLoadError, teamRoleLabel } from '../../utils/ui'

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
  return value ? String(value).replace('T', ' ').slice(0, 16) : '--'
}

function confirmAction(content) {
  return new Promise((resolve) => {
    uni.showModal({
      title: '提示',
      content,
      success(result) {
        resolve(result.confirm)
      }
    })
  })
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
  if (!createForm.name) {
    uni.showToast({ title: '请输入团队名称', icon: 'none' })
    return
  }
  submittingCreate.value = true
  try {
    await teamApi.create(createForm)
    uni.showToast({ title: '团队已创建', icon: 'success' })
    createForm.name = ''
    createForm.description = ''
    loadData()
  } finally {
    submittingCreate.value = false
  }
}

async function handleJoin() {
  if (!joinTeamId.value) {
    uni.showToast({ title: '请输入团队 ID', icon: 'none' })
    return
  }
  submittingJoin.value = true
  try {
    await teamApi.join(joinTeamId.value)
    uni.showToast({ title: '加入成功', icon: 'success' })
    joinTeamId.value = ''
    loadData()
  } finally {
    submittingJoin.value = false
  }
}

async function handleUpdate() {
  submittingUpdate.value = true
  try {
    await teamApi.update(team.value.id, editForm)
    uni.showToast({ title: '团队已更新', icon: 'success' })
    loadData()
  } finally {
    submittingUpdate.value = false
  }
}

async function handleDissolve() {
  if (!(await confirmAction('确认解散当前团队吗？'))) {
    return
  }
  dissolving.value = true
  try {
    await teamApi.dissolve(team.value.id)
    uni.showToast({ title: '团队已解散', icon: 'success' })
    loadData()
  } finally {
    dissolving.value = false
  }
}

async function switchRole(member) {
  const nextRole = member.team_role === 'OWNER' ? 'MEMBER' : 'OWNER'
  await teamApi.updateRole(team.value.id, member.user_id, { team_role: nextRole })
  uni.showToast({ title: '成员角色已更新', icon: 'success' })
  loadData()
}

async function removeMember(member) {
  if (!(await confirmAction(`确认移除用户 ${member.user_id} 吗？`))) {
    return
  }
  await teamApi.removeMember(team.value.id, member.user_id)
  uni.showToast({ title: '成员已移除', icon: 'success' })
  loadData()
}

onShow(() => {
  if (!ensureLogin()) {
    return
  }
  loadData()
})
</script>

<style scoped>
.hero-card {
  background:
    radial-gradient(circle at top right, rgba(62, 152, 108, 0.22), transparent 36%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(246, 250, 246, 0.98) 100%);
}

.empty-tip {
  font-size: 25rpx;
  line-height: 1.7;
  color: #66756f;
  margin-top: 10rpx;
}

.divider {
  text-align: center;
  color: #9ca3af;
  font-size: 26rpx;
  margin: 16rpx 0 24rpx;
}

.member-list {
  display: grid;
  gap: 16rpx;
}

.member-card {
  background: linear-gradient(180deg, #fcfdfa 0%, #f4f8f3 100%);
  border-radius: 24rpx;
  padding: 24rpx;
  border: 1rpx solid rgba(21, 55, 45, 0.05);
  margin-bottom: 0;
}

.member-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  margin-bottom: 10rpx;
}

.member-meta {
  font-size: 24rpx;
  color: #66756f;
  line-height: 1.7;
}

.role-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10rpx 18rpx;
  border-radius: 999rpx;
  background: #e7f6ef;
  color: #1e8f64;
  font-size: 22rpx;
}

.action-pad,
.retry-btn {
  margin-top: 16rpx;
}

.short {
  height: 112rpx;
}
</style>
