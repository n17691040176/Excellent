<template>
  <div class="page safe-bottom">
    <van-nav-bar title="我的团队" fixed placeholder />

    <div class="page-card">
      <h2 class="page-title">团队信息</h2>
      <p class="page-desc">支持创建团队、编辑资料、邀请成员加入，并在负责人权限下管理成员角色。</p>
      <template v-if="team && team.id">
        <van-cell-group inset>
          <van-cell title="团队名称" :value="team.name" />
          <van-cell title="团队 ID" :value="String(team.id)" />
          <van-cell title="负责人" :value="String(team.owner_user_id || '--')" />
          <van-cell title="状态" :value="team.status || '--'" />
          <van-cell title="简介" :label="team.description || '暂无简介'" />
        </van-cell-group>
      </template>
      <van-empty v-else image="search" description="当前尚未加入团队" />
    </div>

    <div class="page-card" v-if="!team || !team.id">
      <h3 class="cell-group-title">创建团队 / 加入团队</h3>
      <van-form @submit="handleCreate">
        <van-field v-model="createForm.name" label="团队名称" placeholder="请输入团队名称" />
        <van-field v-model="createForm.description" label="团队简介" placeholder="请输入团队简介" />
        <div class="submit-bar">
          <van-button block round type="primary" native-type="submit">创建团队</van-button>
        </div>
      </van-form>
      <van-divider>或</van-divider>
      <van-field v-model="joinTeamId" label="团队 ID" type="digit" placeholder="输入团队 ID 加入" />
      <div class="submit-bar">
        <van-button block round plain type="primary" @click="handleJoin">申请加入团队</van-button>
      </div>
    </div>

    <div class="page-card" v-else>
      <h3 class="cell-group-title">团队维护</h3>
      <van-form @submit="handleUpdate">
        <van-field v-model="editForm.name" label="团队名称" placeholder="请输入团队名称" />
        <van-field v-model="editForm.description" label="团队简介" placeholder="请输入团队简介" />
        <div class="inline-actions submit-bar">
          <van-button block round plain type="primary" native-type="submit">保存团队</van-button>
          <van-button block round type="danger" @click="handleDissolve">解散团队</van-button>
        </div>
      </van-form>
    </div>

    <div class="page-card" v-if="team && team.id">
      <h3 class="cell-group-title">成员列表</h3>
      <van-cell-group inset>
        <van-cell v-for="member in members" :key="member.id" :title="`用户 ${member.user_id}`" :label="`加入时间 ${formatDate(member.joined_at)}`">
          <template #value>
            <div>{{ member.team_role }}</div>
            <div class="inline-actions" style="margin-top: 0.12rem; justify-content: flex-end;">
              <van-button size="mini" plain type="primary" @click="switchRole(member)">切换角色</van-button>
              <van-button size="mini" plain type="danger" @click="removeMember(member)">移除</van-button>
            </div>
          </template>
        </van-cell>
      </van-cell-group>
    </div>

    <AppTabbar />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import dayjs from 'dayjs'
import { showConfirmDialog, showSuccessToast } from 'vant'

import AppTabbar from '@/components/AppTabbar.vue'
import { teamApi } from '@/api/modules'

const team = ref(null)
const members = ref([])
const joinTeamId = ref('')
const createForm = reactive({ name: '', description: '' })
const editForm = reactive({ name: '', description: '' })

function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '--'
}

async function loadData() {
  try {
    team.value = await teamApi.current()
  } catch (error) {
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
  await teamApi.create(createForm)
  showSuccessToast('团队已创建')
  createForm.name = ''
  createForm.description = ''
  await loadData()
}

async function handleJoin() {
  if (!joinTeamId.value) return
  await teamApi.join(joinTeamId.value)
  showSuccessToast('加入成功')
  joinTeamId.value = ''
  await loadData()
}

async function handleUpdate() {
  await teamApi.update(team.value.id, editForm)
  showSuccessToast('团队已更新')
  await loadData()
}

async function handleDissolve() {
  await showConfirmDialog({ title: '提示', message: '确认解散当前团队吗？' })
  await teamApi.dissolve(team.value.id)
  showSuccessToast('团队已解散')
  await loadData()
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
