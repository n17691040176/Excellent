<template>
  <view class="page">
    <view class="card">
      <view class="title">团队信息</view>
      <view class="desc">支持创建团队、编辑资料、邀请成员加入，并在负责人权限下管理成员角色。</view>
      <view v-if="team && team.id" class="info-list">
        <view class="info-row">团队名称：{{ team.name }}</view>
        <view class="info-row">团队 ID：{{ team.id }}</view>
        <view class="info-row">负责人：{{ team.owner_user_id || '--' }}</view>
        <view class="info-row">状态：{{ team.status || '--' }}</view>
        <view class="info-row">简介：{{ team.description || '暂无简介' }}</view>
      </view>
      <view v-else class="empty-text">当前尚未加入团队</view>
    </view>

    <view class="card" v-if="!team || !team.id">
      <view class="section-title">创建团队 / 加入团队</view>
      <input v-model="createForm.name" class="input" placeholder="请输入团队名称" />
      <input v-model="createForm.description" class="input" placeholder="请输入团队简介" />
      <button class="primary-btn" @click="handleCreate">创建团队</button>
      <view class="divider">或</view>
      <input v-model="joinTeamId" class="input" type="number" placeholder="输入团队 ID 加入" />
      <button class="secondary-btn" @click="handleJoin">申请加入团队</button>
    </view>

    <view class="card" v-else>
      <view class="section-title">团队维护</view>
      <input v-model="editForm.name" class="input" placeholder="请输入团队名称" />
      <input v-model="editForm.description" class="input" placeholder="请输入团队简介" />
      <view class="action-row">
        <button class="secondary-btn" @click="handleUpdate">保存团队</button>
        <button class="danger-btn" @click="handleDissolve">解散团队</button>
      </view>
    </view>

    <view class="card" v-if="team && team.id">
      <view class="section-title">成员列表</view>
      <view v-if="members.length">
        <view class="member-card" v-for="member in members" :key="member.id">
          <view class="member-title">用户 {{ member.user_id }}</view>
          <view class="member-meta">加入时间 {{ formatDate(member.joined_at) }}</view>
          <view class="member-meta">角色 {{ member.team_role }}</view>
          <view class="action-row" style="margin-top: 16rpx;">
            <button class="minor-btn" @click="switchRole(member)">切换角色</button>
            <button class="danger-btn" @click="removeMember(member)">移除</button>
          </view>
        </view>
      </view>
      <view v-else class="empty-text">当前团队暂无成员</view>
    </view>
  </view>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'

import { teamApi } from '../../api/modules'
import { ensureLogin } from '../../utils/guard'

const team = ref(null)
const members = ref([])
const joinTeamId = ref('')
const createForm = reactive({ name: '', description: '' })
const editForm = reactive({ name: '', description: '' })

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
}

async function handleCreate() {
  if (!createForm.name) {
    uni.showToast({ title: '请输入团队名称', icon: 'none' })
    return
  }
  await teamApi.create(createForm)
  uni.showToast({ title: '团队已创建', icon: 'success' })
  createForm.name = ''
  createForm.description = ''
  loadData()
}

async function handleJoin() {
  if (!joinTeamId.value) {
    uni.showToast({ title: '请输入团队 ID', icon: 'none' })
    return
  }
  await teamApi.join(joinTeamId.value)
  uni.showToast({ title: '加入成功', icon: 'success' })
  joinTeamId.value = ''
  loadData()
}

async function handleUpdate() {
  await teamApi.update(team.value.id, editForm)
  uni.showToast({ title: '团队已更新', icon: 'success' })
  loadData()
}

async function handleDissolve() {
  if (!(await confirmAction('确认解散当前团队吗？'))) {
    return
  }
  await teamApi.dissolve(team.value.id)
  uni.showToast({ title: '团队已解散', icon: 'success' })
  loadData()
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
.page { min-height: 100vh; padding: 32rpx; }
.card { background: #ffffff; border-radius: 24rpx; padding: 32rpx; margin-bottom: 24rpx; }
.title { font-size: 40rpx; font-weight: 600; margin-bottom: 16rpx; }
.desc { font-size: 28rpx; color: #6b7280; line-height: 1.6; margin-bottom: 20rpx; }
.section-title { font-size: 34rpx; font-weight: 600; margin-bottom: 20rpx; }
.info-list { display: grid; gap: 12rpx; }
.info-row, .member-meta, .empty-text { font-size: 26rpx; color: #4b5563; line-height: 1.6; }
.input {
  width: 100%;
  height: 88rpx;
  background: #f5f7fb;
  border-radius: 18rpx;
  padding: 0 24rpx;
  font-size: 28rpx;
  margin-bottom: 20rpx;
  box-sizing: border-box;
}
.divider { text-align: center; color: #9ca3af; font-size: 26rpx; margin: 12rpx 0 24rpx; }
.member-card {
  background: #f5f7fb;
  border-radius: 20rpx;
  padding: 24rpx;
  margin-bottom: 16rpx;
}
.member-title { font-size: 30rpx; font-weight: 600; margin-bottom: 8rpx; }
.action-row { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16rpx; }
.primary-btn,
.secondary-btn,
.danger-btn,
.minor-btn {
  height: 88rpx;
  line-height: 88rpx;
  border-radius: 18rpx;
  font-size: 30rpx;
}
.primary-btn { background: #0d6efd; color: #ffffff; }
.secondary-btn { background: #eef4ff; color: #0d6efd; }
.danger-btn { background: #fef2f2; color: #dc2626; }
.minor-btn { background: #f3f4f6; color: #374151; }
</style>
