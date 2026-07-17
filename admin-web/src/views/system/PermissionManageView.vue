<template>
  <div class="permission-view">
    <div class="page-heading">
      <div>
        <h2>权限管理</h2>
        <p>为后台团队管理员配置可访问菜单和可执行操作，超级管理员默认拥有全部权限。</p>
      </div>
      <div class="toolbar-row">
        <el-button @click="loadData">刷新</el-button>
        <el-button type="primary" :disabled="!selectedAdmin || selectedAdmin.global_role === 'SUPER_ADMIN'" :loading="saving" @click="savePermissions">
          保存权限
        </el-button>
      </div>
    </div>

    <div class="permission-layout">
      <div class="panel-card admin-panel">
        <div class="panel-title">后台管理员</div>
        <el-input v-model.trim="keyword" placeholder="搜索手机号 / 昵称" clearable />
        <div v-loading="loading" class="admin-list">
          <button
            v-for="item in filteredAdmins"
            :key="item.id"
            class="admin-item"
            :class="{ active: selectedAdmin?.id === item.id }"
            @click="selectAdmin(item)"
          >
            <span class="admin-name">{{ item.nickname || `ID ${item.id}` }}</span>
            <span class="admin-meta">{{ item.phone || '--' }}</span>
            <el-tag size="small" :type="item.global_role === 'SUPER_ADMIN' ? 'danger' : 'success'">{{ roleLabel(item.global_role) }}</el-tag>
          </button>
        </div>
      </div>

      <div class="panel-card permission-panel" v-loading="detailLoading">
        <template v-if="selectedAdmin">
          <div class="permission-head">
            <div>
              <h3>{{ selectedAdmin.nickname || `ID ${selectedAdmin.id}` }}</h3>
              <p>{{ selectedAdmin.phone || '--' }} / {{ roleLabel(selectedAdmin.global_role) }}</p>
            </div>
            <el-tag :type="selectedAdmin.global_role === 'SUPER_ADMIN' ? 'danger' : 'success'">
              {{ selectedAdmin.global_role === 'SUPER_ADMIN' ? '全部权限' : `${checkedPermissions.length} 项权限` }}
            </el-tag>
          </div>

          <el-alert
            v-if="selectedAdmin.global_role === 'SUPER_ADMIN'"
            title="超级管理员固定拥有全部权限，不能在这里降权。"
            type="info"
            show-icon
            :closable="false"
          />

          <div class="permission-actions">
            <el-button size="small" :disabled="selectedAdmin.global_role === 'SUPER_ADMIN'" @click="checkAll">全选</el-button>
            <el-button size="small" :disabled="selectedAdmin.global_role === 'SUPER_ADMIN'" @click="clearAll">清空</el-button>
          </div>

          <div class="permission-groups">
            <section v-for="group in permissionGroups" :key="group.label" class="permission-group">
              <div class="group-title">{{ group.label }}</div>
              <el-checkbox-group v-model="checkedPermissions" :disabled="selectedAdmin.global_role === 'SUPER_ADMIN'">
                <el-checkbox
                  v-for="permission in group.permissions"
                  :key="permission.key"
                  :label="permission.key"
                >
                  {{ permission.label }}
                </el-checkbox>
              </el-checkbox-group>
            </section>
          </div>
        </template>
        <el-empty v-else description="请选择一个后台管理员" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { permissionApi } from '@/api/modules'

const loading = ref(false)
const detailLoading = ref(false)
const saving = ref(false)
const keyword = ref('')
const admins = ref([])
const selectedAdmin = ref(null)
const permissionGroups = ref([])
const checkedPermissions = ref([])

const filteredAdmins = computed(() => {
  const key = keyword.value.toLowerCase()
  if (!key) return admins.value
  return admins.value.filter((item) => `${item.nickname || ''}${item.phone || ''}`.toLowerCase().includes(key))
})

const allPermissionKeys = computed(() => permissionGroups.value.flatMap((group) => group.permissions.map((item) => item.key)))

function roleLabel(role) {
  return {
    SUPER_ADMIN: '超级管理员',
    TEAM_ADMIN: '团队管理员'
  }[role] || role
}

async function loadData() {
  loading.value = true
  try {
    const [options, adminRows] = await Promise.all([permissionApi.options(), permissionApi.admins()])
    permissionGroups.value = options?.groups || []
    admins.value = adminRows || []
    if (!selectedAdmin.value && admins.value.length) {
      await selectAdmin(admins.value[0])
    } else if (selectedAdmin.value) {
      const latest = admins.value.find((item) => item.id === selectedAdmin.value.id)
      if (latest) await selectAdmin(latest)
    }
  } finally {
    loading.value = false
  }
}

async function selectAdmin(item) {
  selectedAdmin.value = item
  detailLoading.value = true
  try {
    const detail = await permissionApi.detail(item.id)
    selectedAdmin.value = detail
    checkedPermissions.value = detail.permissions?.includes('*') ? allPermissionKeys.value : [...(detail.permissions || [])]
  } finally {
    detailLoading.value = false
  }
}

function checkAll() {
  checkedPermissions.value = [...allPermissionKeys.value]
}

function clearAll() {
  checkedPermissions.value = []
}

async function savePermissions() {
  if (!selectedAdmin.value || selectedAdmin.value.global_role === 'SUPER_ADMIN') return
  saving.value = true
  try {
    const detail = await permissionApi.update(selectedAdmin.value.id, { permissions: checkedPermissions.value })
    selectedAdmin.value = detail
    checkedPermissions.value = [...(detail.permissions || [])]
    ElMessage.success('权限已保存')
    await loadData()
  } finally {
    saving.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.permission-view {
  display: grid;
  gap: 18px;
}

.permission-layout {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.admin-panel,
.permission-panel {
  padding: 18px;
}

.panel-title {
  margin-bottom: 14px;
  font-weight: 700;
  color: var(--brand-deep);
}

.admin-list {
  display: grid;
  gap: 10px;
  margin-top: 14px;
  max-height: calc(100vh - 260px);
  overflow: auto;
}

.admin-item {
  display: grid;
  gap: 6px;
  width: 100%;
  padding: 14px;
  text-align: left;
  border: 1px solid var(--brand-line);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.82);
  cursor: pointer;
}

.admin-item.active {
  border-color: rgba(198, 132, 79, 0.58);
  box-shadow: 0 10px 28px rgba(166, 110, 62, 0.12);
}

.admin-name {
  font-weight: 700;
  color: var(--brand-deep);
}

.admin-meta {
  font-size: 12px;
  color: rgba(58, 45, 36, 0.62);
}

.permission-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.permission-head h3 {
  margin: 0;
  color: var(--brand-deep);
}

.permission-head p {
  margin: 8px 0 0;
  color: rgba(58, 45, 36, 0.62);
}

.permission-actions {
  display: flex;
  gap: 10px;
  margin: 16px 0;
}

.permission-groups {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.permission-group {
  padding: 16px;
  border: 1px solid var(--brand-line);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.7);
}

.group-title {
  margin-bottom: 12px;
  font-weight: 700;
  color: var(--brand-deep);
}

.permission-group :deep(.el-checkbox-group) {
  display: grid;
  gap: 8px;
}

.permission-group :deep(.el-checkbox) {
  margin-right: 0;
}

@media (max-width: 1180px) {
  .permission-layout {
    grid-template-columns: 1fr;
  }

  .permission-groups {
    grid-template-columns: 1fr;
  }
}
</style>
