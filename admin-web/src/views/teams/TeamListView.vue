<template>
  <div>
    <div class="page-heading">
      <div>
        <h2>团队管理</h2>
        <p>聚焦当前团队详情与成员权限分工，超级管理员可扩展成全量团队视图。</p>
      </div>
      <el-button type="primary" @click="loadCurrentTeam">刷新团队</el-button>
    </div>

    <div class="panel-card data-card" style="margin-bottom: 18px;">
      <el-descriptions title="当前团队信息" :column="2" border>
        <el-descriptions-item label="团队 ID">{{ team?.id || '--' }}</el-descriptions-item>
        <el-descriptions-item label="团队名称">{{ team?.name || '--' }}</el-descriptions-item>
        <el-descriptions-item label="负责人">{{ team?.owner_user_id || '--' }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ team?.status || '--' }}</el-descriptions-item>
        <el-descriptions-item label="团队简介" :span="2">{{ team?.description || '暂无说明' }}</el-descriptions-item>
      </el-descriptions>
    </div>

    <div class="panel-card data-card">
      <div class="page-heading" style="margin-bottom: 14px;">
        <div>
          <h2 style="font-size:22px;">成员列表</h2>
          <p>支持查看当前团队成员及角色。</p>
        </div>
      </div>
      <el-table :data="members" border>
        <el-table-column prop="user_id" label="用户 ID" width="100" />
        <el-table-column prop="team_role" label="团队角色" width="140" />
        <el-table-column prop="joined_at" label="加入时间" min-width="180" />
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

import { teamApi } from '@/api/modules'

const team = ref(null)
const members = ref([])

async function loadCurrentTeam() {
  team.value = await teamApi.current()
  if (team.value?.id) {
    members.value = await teamApi.members(team.value.id)
  } else {
    members.value = []
  }
}

onMounted(loadCurrentTeam)
</script>
