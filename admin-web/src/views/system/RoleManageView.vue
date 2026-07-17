<template>
  <div>
    <div class="page-heading">
      <div>
        <h2>角色管理</h2>
        <p>创建业务角色，配置后台权限和全平台/所属团队数据范围。</p>
      </div>
      <div class="toolbar-row">
        <el-button @click="loadData">刷新</el-button>
        <el-button v-if="canManage" type="primary" @click="openCreate">新增角色</el-button>
      </div>
    </div>

    <div class="split-grid">
      <div class="panel-card data-card">
        <el-table v-loading="loading" :data="roles" border highlight-current-row @row-click="selectRole">
          <el-table-column prop="name" label="角色名称" min-width="130" />
          <el-table-column prop="code" label="角色编码" min-width="150" />
          <el-table-column label="数据范围" width="110">
            <template #default="{ row }">{{ scopeLabel(row.data_scope) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.status === 'ENABLED' ? 'success' : 'info'">
                {{ row.status === 'ENABLED' ? '启用' : '停用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="user_count" label="管理员数" width="100" />
        </el-table>
      </div>

      <div class="panel-card data-card" v-loading="detailLoading">
        <template v-if="selectedRole">
          <div class="section-title">
            <div>
              <h3>{{ selectedRole.name }}</h3>
              <p>角色编码创建后不可修改；系统角色可调整权限，但不能删除。</p>
            </div>
          </div>

          <el-form :model="form" label-position="top" :disabled="!canManage">
            <div class="form-grid">
              <el-form-item label="角色名称">
                <el-input v-model="form.name" maxlength="64" />
              </el-form-item>
              <el-form-item label="数据范围">
                <el-select v-model="form.data_scope" :disabled="selectedRole.is_system" style="width: 100%;">
                  <el-option label="全平台" value="ALL" />
                  <el-option label="所属团队" value="TEAM" />
                </el-select>
              </el-form-item>
              <el-form-item label="状态">
                <el-select v-model="form.status" style="width: 100%;">
                  <el-option label="启用" value="ENABLED" />
                  <el-option label="停用" value="DISABLED" />
                </el-select>
              </el-form-item>
            </div>
            <el-form-item label="角色说明">
              <el-input v-model="form.description" type="textarea" :rows="2" maxlength="500" />
            </el-form-item>
          </el-form>

          <div class="permission-actions">
            <strong>角色权限</strong>
            <el-button v-if="canManage" size="small" @click="checkAll">全选</el-button>
            <el-button v-if="canManage" size="small" @click="checkedPermissions = []">清空</el-button>
          </div>
          <div class="permission-groups">
            <section v-for="group in permissionGroups" :key="group.label" class="permission-group">
              <div class="group-title">{{ group.label }}</div>
              <el-checkbox-group v-model="checkedPermissions" :disabled="!canManage">
                <el-checkbox v-for="item in group.permissions" :key="item.key" :label="item.key">
                  {{ item.label }}
                </el-checkbox>
              </el-checkbox-group>
            </section>
          </div>

          <div v-if="canManage" class="toolbar-row" style="margin-top: 18px;">
            <el-button type="primary" :loading="saving" @click="saveRole">保存角色</el-button>
            <el-button
              v-if="!selectedRole.is_system"
              type="danger"
              plain
              :disabled="selectedRole.user_count > 0"
              @click="removeRole"
            >删除角色</el-button>
          </div>
        </template>
        <el-empty v-else description="请选择一个角色" />
      </div>
    </div>

    <el-dialog v-model="createVisible" title="新增角色" width="520px" destroy-on-close>
      <el-form :model="createForm" label-position="top">
        <el-form-item label="角色编码">
          <el-input v-model="createForm.code" placeholder="例如 FINANCE_ADMIN" maxlength="64" />
        </el-form-item>
        <el-form-item label="角色名称">
          <el-input v-model="createForm.name" placeholder="例如 财务管理员" maxlength="64" />
        </el-form-item>
        <el-form-item label="数据范围">
          <el-select v-model="createForm.data_scope" style="width: 100%;">
            <el-option label="全平台" value="ALL" />
            <el-option label="所属团队" value="TEAM" />
          </el-select>
        </el-form-item>
        <el-form-item label="角色说明">
          <el-input v-model="createForm.description" type="textarea" :rows="2" maxlength="500" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="createRole">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { roleApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'
import { hasPermission } from '@/utils/permission'

const userStore = useUserStore()
const roles = ref([])
const permissionGroups = ref([])
const selectedRole = ref(null)
const checkedPermissions = ref([])
const loading = ref(false)
const detailLoading = ref(false)
const saving = ref(false)
const creating = ref(false)
const createVisible = ref(false)

const form = reactive({ name: '', description: '', data_scope: 'TEAM', status: 'ENABLED' })
const createForm = reactive({ code: '', name: '', description: '', data_scope: 'TEAM' })

const canManage = computed(() => {
  const globalScope = userStore.role === 'SUPER_ADMIN' || userStore.userInfo?.admin_role?.data_scope === 'ALL'
  return globalScope && hasPermission(userStore.role, 'roles:manage', userStore.permissions)
})
const allPermissionKeys = computed(() => permissionGroups.value.flatMap((group) => group.permissions.map((item) => item.key)))

function scopeLabel(scope) {
  return scope === 'ALL' ? '全平台' : '所属团队'
}

function applyRole(role) {
  selectedRole.value = role
  Object.assign(form, {
    name: role.name,
    description: role.description || '',
    data_scope: role.data_scope,
    status: role.status
  })
  checkedPermissions.value = [...(role.permissions || [])]
}

async function loadData() {
  loading.value = true
  try {
    const [options, rows] = await Promise.all([roleApi.options(), roleApi.list()])
    permissionGroups.value = options.groups || []
    roles.value = rows || []
    if (selectedRole.value) {
      const latest = roles.value.find((item) => item.id === selectedRole.value.id)
      if (latest) applyRole(latest)
      else selectedRole.value = null
    } else if (roles.value.length) {
      applyRole(roles.value[0])
    }
  } finally {
    loading.value = false
  }
}

async function selectRole(row) {
  detailLoading.value = true
  try {
    applyRole(await roleApi.detail(row.id))
  } finally {
    detailLoading.value = false
  }
}

function checkAll() {
  checkedPermissions.value = [...allPermissionKeys.value]
}

async function saveRole() {
  if (!selectedRole.value) return
  saving.value = true
  try {
    const role = await roleApi.update(selectedRole.value.id, {
      ...form,
      permissions: checkedPermissions.value
    })
    applyRole(role)
    ElMessage.success('角色已保存')
    await loadData()
  } finally {
    saving.value = false
  }
}

function openCreate() {
  Object.assign(createForm, { code: '', name: '', description: '', data_scope: 'TEAM' })
  createVisible.value = true
}

async function createRole() {
  if (!createForm.code.trim() || !createForm.name.trim()) {
    ElMessage.warning('请填写角色编码和名称')
    return
  }
  creating.value = true
  try {
    const role = await roleApi.create({
      ...createForm,
      code: createForm.code.trim().toUpperCase(),
      permissions: []
    })
    createVisible.value = false
    await loadData()
    await selectRole(role)
    ElMessage.success('角色已创建，请继续配置权限')
  } finally {
    creating.value = false
  }
}

async function removeRole() {
  if (!selectedRole.value) return
  await ElMessageBox.confirm(`确认删除角色“${selectedRole.value.name}”吗？`, '删除角色', { type: 'warning' })
  await roleApi.remove(selectedRole.value.id)
  selectedRole.value = null
  ElMessage.success('角色已删除')
  await loadData()
}

onMounted(loadData)
</script>

<style scoped>
.form-grid,
.permission-groups {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.permission-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 12px 0;
}

.permission-group {
  padding: 14px;
  border: 1px solid var(--brand-line);
  border-radius: 10px;
}

.group-title {
  margin-bottom: 10px;
  font-weight: 700;
}

.permission-group :deep(.el-checkbox-group) {
  display: grid;
  gap: 8px;
}

.permission-group :deep(.el-checkbox) {
  margin-right: 0;
}
</style>
