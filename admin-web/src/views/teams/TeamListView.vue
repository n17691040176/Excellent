<template>
  <div class="team-view">
    <!-- 统一页面头部 -->
    <PageHeader title="团队管理" :description="scopeHint">
      <template #actions>
        <el-button type="primary" @click="loadCurrentTeam">刷新团队</el-button>
      </template>
    </PageHeader>

    <!-- 团队信息卡片 -->
    <div class="panel-card data-card">
      <el-descriptions title="当前团队信息" :column="2" border>
        <el-descriptions-item label="团队 ID">{{ team?.id || '--' }}</el-descriptions-item>
        <el-descriptions-item label="团队名称">{{ team?.name || '--' }}</el-descriptions-item>
        <el-descriptions-item label="负责人">{{ team?.owner_user_id || '--' }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ team?.status || '--' }}</el-descriptions-item>
        <el-descriptions-item label="团队简介" :span="2">{{ team?.description || '暂无说明' }}</el-descriptions-item>
      </el-descriptions>
    </div>

    <!-- 成员列表卡片 -->
    <div class="panel-card data-card">
      <div class="section-title-lite">
        <h3>成员列表</h3>
        <p>支持查看当前团队成员及角色。</p>
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
import { computed, onMounted, ref } from 'vue'

import { teamApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'
import { PageHeader } from '@/components/common'

const userStore = useUserStore()
const team = ref(null)
const members = ref([])

const scopeHint = computed(() =>
  userStore.role === 'TEAM_ADMIN'
    ? '聚焦当前团队详情与成员权限分工。'
    : '查看所有团队详情与成员权限分工。'
)

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

<style scoped>
@import '@/styles/variables.css';

.team-view {
  display: grid;
  gap: var(--space-4);
}

.section-title-lite {
  margin-bottom: var(--space-4);
}

.section-title-lite h3 {
  margin: 0;
  font-size: var(--text-xl);
  color: var(--text-primary);
}

.section-title-lite p {
  margin: var(--space-2) 0 0;
  color: var(--text-muted);
  line-height: var(--leading-relaxed);
}
</style>
