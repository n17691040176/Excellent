<template>
  <div>
    <div class="page-heading">
      <div>
        <h2>管理员管理</h2>
        <p>创建管理员，或将已有用户晋升后分配自定义角色和数据范围。</p>
      </div>
      <div class="toolbar-row">
        <el-button @click="loadData">刷新</el-button>
        <el-button v-if="canManage" @click="openPromote">从用户晋升</el-button>
        <el-button v-if="canManage" type="primary" @click="openCreate">新增管理员</el-button>
      </div>
    </div>

    <div class="panel-card data-card">
      <div class="toolbar-row">
        <el-input v-model.trim="keyword" placeholder="搜索手机号 / 昵称" clearable style="max-width: 260px;" @keyup.enter="loadAdmins" />
        <el-select v-model="roleFilter" placeholder="角色" clearable style="width: 190px;">
          <el-option v-for="role in roles" :key="role.id" :label="role.name" :value="role.id" />
        </el-select>
        <el-button @click="loadAdmins">查询</el-button>
      </div>

      <el-table v-loading="loading" :data="filteredRows" border>
        <el-table-column prop="id" label="账号 ID" width="90" />
        <el-table-column prop="phone" label="手机号" min-width="140" />
        <el-table-column prop="nickname" label="昵称" min-width="120" />
        <el-table-column label="角色" min-width="140">
          <template #default="{ row }">{{ row.role?.name || '--' }}</template>
        </el-table-column>
        <el-table-column label="数据范围" width="110">
          <template #default="{ row }">{{ row.role?.data_scope === 'ALL' ? '全平台' : '所属团队' }}</template>
        </el-table-column>
        <el-table-column label="团队" min-width="130">
          <template #default="{ row }">{{ teamLabel(row.team_id) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'ENABLED' ? 'success' : 'danger'">
              {{ row.status === 'ENABLED' ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最后登录" min-width="160">
          <template #default="{ row }">{{ formatDate(row.last_login_at) }}</template>
        </el-table-column>
        <el-table-column v-if="canManage" label="操作" width="270" fixed="right">
          <template #default="{ row }">
            <template v-if="row.global_role !== 'SUPER_ADMIN'">
              <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
              <el-button link type="warning" @click="toggleStatus(row)">
                {{ row.status === 'ENABLED' ? '禁用' : '启用' }}
              </el-button>
              <el-button link @click="openResetPassword(row)">重置密码</el-button>
              <el-button link type="danger" @click="demote(row)">降为普通用户</el-button>
            </template>
            <span v-else>根账号受保护</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="createVisible" title="新增管理员" width="560px" destroy-on-close>
      <el-form :model="createForm" label-position="top">
        <div class="form-grid">
          <el-form-item label="手机号"><el-input v-model="createForm.phone" maxlength="20" /></el-form-item>
          <el-form-item label="昵称"><el-input v-model="createForm.nickname" maxlength="64" /></el-form-item>
          <el-form-item label="初始密码"><el-input v-model="createForm.password" type="password" show-password /></el-form-item>
          <el-form-item label="角色">
            <el-select v-model="createForm.role_id" style="width: 100%;" @change="syncCreateTeam">
              <el-option v-for="role in enabledRoles" :key="role.id" :label="role.name" :value="role.id" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="roleNeedsTeam(createForm.role_id)" label="所属团队">
            <el-select v-model="createForm.team_id" style="width: 100%;">
              <el-option v-for="team in teams" :key="team.id" :label="`${team.name}（${team.id}）`" :value="team.id" />
            </el-select>
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="createAdmin">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="promoteVisible" title="从现有用户晋升" width="560px" destroy-on-close>
      <el-form :model="promoteForm" label-position="top">
        <el-form-item label="选择用户">
          <el-select v-model="promoteForm.user_id" filterable style="width: 100%;" placeholder="手机号 / 昵称">
            <el-option
              v-for="user in candidates"
              :key="user.id"
              :label="`${user.nickname || '--'} / ${user.phone || '--'} / ID ${user.id}`"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="分配角色">
          <el-select v-model="promoteForm.role_id" style="width: 100%;" @change="syncPromoteTeam">
            <el-option v-for="role in enabledRoles" :key="role.id" :label="role.name" :value="role.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="roleNeedsTeam(promoteForm.role_id)" label="所属团队">
          <el-select v-model="promoteForm.team_id" style="width: 100%;">
            <el-option v-for="team in teams" :key="team.id" :label="`${team.name}（${team.id}）`" :value="team.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="promoteVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="promoteUser">确认晋升</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editVisible" title="编辑管理员" width="520px" destroy-on-close>
      <el-form :model="editForm" label-position="top">
        <el-form-item label="昵称"><el-input v-model="editForm.nickname" maxlength="64" /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="editForm.role_id" style="width: 100%;" @change="syncEditTeam">
            <el-option v-for="role in enabledRoles" :key="role.id" :label="role.name" :value="role.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="roleNeedsTeam(editForm.role_id)" label="所属团队">
          <el-select v-model="editForm.team_id" style="width: 100%;">
            <el-option v-for="team in teams" :key="team.id" :label="`${team.name}（${team.id}）`" :value="team.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="saveAdmin">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="passwordVisible" title="重置管理员密码" width="460px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="新密码">
          <el-input v-model="newPassword" type="password" show-password placeholder="至少 8 位" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="resetPassword">确认重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'

import { adminAccountApi, roleApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'
import { hasPermission } from '@/utils/permission'

const userStore = useUserStore()
const rows = ref([])
const roles = ref([])
const teams = ref([])
const candidates = ref([])
const keyword = ref('')
const roleFilter = ref(null)
const loading = ref(false)
const submitting = ref(false)

const createVisible = ref(false)
const promoteVisible = ref(false)
const editVisible = ref(false)
const passwordVisible = ref(false)
const editingId = ref(null)
const passwordUserId = ref(null)
const newPassword = ref('')

const createForm = reactive({ phone: '', nickname: '', password: '', role_id: null, team_id: null })
const promoteForm = reactive({ user_id: null, role_id: null, team_id: null })
const editForm = reactive({ nickname: '', role_id: null, team_id: null })

const canManage = computed(() => hasPermission(userStore.role, 'admins:manage', userStore.permissions))
const enabledRoles = computed(() => roles.value.filter((role) => role.status === 'ENABLED'))
const filteredRows = computed(() => !roleFilter.value ? rows.value : rows.value.filter((row) => row.role?.id === roleFilter.value))

function roleNeedsTeam(roleId) {
  return roles.value.find((role) => role.id === roleId)?.data_scope === 'TEAM'
}

function teamLabel(teamId) {
  if (!teamId) return '--'
  const team = teams.value.find((item) => item.id === teamId)
  return team ? `${team.name}（${team.id}）` : `团队 ${teamId}`
}

function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '--'
}

function defaultTeamId() {
  return teams.value.length === 1 ? teams.value[0].id : null
}

function syncCreateTeam() {
  createForm.team_id = roleNeedsTeam(createForm.role_id) ? (createForm.team_id || defaultTeamId()) : null
}

function syncPromoteTeam() {
  promoteForm.team_id = roleNeedsTeam(promoteForm.role_id) ? (promoteForm.team_id || defaultTeamId()) : null
}

function syncEditTeam() {
  editForm.team_id = roleNeedsTeam(editForm.role_id) ? (editForm.team_id || defaultTeamId()) : null
}

async function loadAdmins() {
  loading.value = true
  try {
    rows.value = await adminAccountApi.list({ keyword: keyword.value || undefined })
  } finally {
    loading.value = false
  }
}

async function loadData() {
  const [roleRows, teamRows] = await Promise.all([roleApi.list(), adminAccountApi.teams()])
  roles.value = roleRows || []
  teams.value = teamRows || []
  await loadAdmins()
}

function openCreate() {
  Object.assign(createForm, { phone: '', nickname: '', password: '', role_id: enabledRoles.value[0]?.id || null, team_id: defaultTeamId() })
  syncCreateTeam()
  createVisible.value = true
}

async function createAdmin() {
  if (!createForm.phone || !createForm.nickname || !createForm.password || !createForm.role_id) {
    ElMessage.warning('请完整填写管理员信息')
    return
  }
  submitting.value = true
  try {
    await adminAccountApi.create({ ...createForm })
    createVisible.value = false
    ElMessage.success('管理员已创建')
    await loadAdmins()
  } finally {
    submitting.value = false
  }
}

async function openPromote() {
  candidates.value = await adminAccountApi.candidates()
  Object.assign(promoteForm, { user_id: candidates.value[0]?.id || null, role_id: enabledRoles.value[0]?.id || null, team_id: defaultTeamId() })
  const selected = candidates.value.find((item) => item.id === promoteForm.user_id)
  if (selected?.team_id) promoteForm.team_id = selected.team_id
  syncPromoteTeam()
  promoteVisible.value = true
}

async function promoteUser() {
  if (!promoteForm.user_id || !promoteForm.role_id) {
    ElMessage.warning('请选择用户和角色')
    return
  }
  submitting.value = true
  try {
    await adminAccountApi.promote({ ...promoteForm })
    promoteVisible.value = false
    ElMessage.success('用户已晋升为管理员')
    await loadAdmins()
  } finally {
    submitting.value = false
  }
}

function openEdit(row) {
  editingId.value = row.id
  Object.assign(editForm, { nickname: row.nickname, role_id: row.role?.id || null, team_id: row.team_id })
  editVisible.value = true
}

async function saveAdmin() {
  submitting.value = true
  try {
    await adminAccountApi.update(editingId.value, { ...editForm })
    editVisible.value = false
    ElMessage.success('管理员已更新')
    await loadAdmins()
  } finally {
    submitting.value = false
  }
}

async function toggleStatus(row) {
  const status = row.status === 'ENABLED' ? 'DISABLED' : 'ENABLED'
  await ElMessageBox.confirm(`确认${status === 'ENABLED' ? '启用' : '禁用'}该管理员吗？`, '账号状态', { type: 'warning' })
  await adminAccountApi.updateStatus(row.id, { status })
  await loadAdmins()
}

function openResetPassword(row) {
  passwordUserId.value = row.id
  newPassword.value = ''
  passwordVisible.value = true
}

async function resetPassword() {
  if (newPassword.value.length < 8) {
    ElMessage.warning('新密码至少 8 位')
    return
  }
  submitting.value = true
  try {
    await adminAccountApi.resetPassword(passwordUserId.value, { new_password: newPassword.value })
    passwordVisible.value = false
    ElMessage.success('密码已重置')
  } finally {
    submitting.value = false
  }
}

async function demote(row) {
  await ElMessageBox.confirm(`确认将“${row.nickname}”降为普通用户吗？`, '降级管理员', { type: 'warning' })
  await adminAccountApi.demote(row.id)
  ElMessage.success('已降为普通用户')
  await loadAdmins()
}

onMounted(loadData)
</script>

<style scoped>
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
</style>
