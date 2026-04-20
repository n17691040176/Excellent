<template>
  <div class="user-list-view">
    <div class="page-heading">
      <div>
        <h2>用户管理</h2>
        <p>{{ scopeHint }}</p>
      </div>
      <el-button type="primary" @click="fetchUsers">刷新列表</el-button>
    </div>

    <div class="panel-card data-card">
      <div class="toolbar-row toolbar-wrap">
        <el-input
          v-model="keyword"
          clearable
          placeholder="搜索手机号、昵称、邀请码、历史 ID"
          style="max-width: 360px;"
          @keyup.enter="fetchUsers"
          @clear="fetchUsers"
        />
        <el-select
          v-model="sourceFilter"
          clearable
          placeholder="来源筛选"
          style="width: 160px;"
          @change="fetchUsers"
        >
          <el-option label="仅历史导入" value="legacy" />
          <el-option label="仅当前用户" value="native" />
        </el-select>
        <el-select
          v-model="roleFilter"
          clearable
          placeholder="角色筛选"
          style="width: 180px;"
          @change="fetchUsers"
        >
          <el-option label="超级管理员" value="SUPER_ADMIN" />
          <el-option label="团队管理员" value="TEAM_ADMIN" />
          <el-option label="普通用户" value="USER" />
        </el-select>
        <el-button @click="fetchUsers">查询</el-button>
      </div>

      <el-table :data="users" border>
        <el-table-column prop="id" label="ID" width="90" />
        <el-table-column label="来源" width="130">
          <template #default="{ row }">
            <el-tag :type="row.is_legacy_imported ? 'warning' : 'info'">
              {{ row.is_legacy_imported ? '历史导入' : '当前用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="legacy_user_id" label="历史 ID" width="110" />
        <el-table-column prop="phone" label="手机号" min-width="150" />
        <el-table-column prop="nickname" label="昵称" min-width="160" />
        <el-table-column prop="invite_code" label="邀请码" min-width="120" />
        <el-table-column prop="global_role" label="系统角色" min-width="120" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.status === 'ENABLED' ? 'success' : 'danger'">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="380" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openUserDetail(row)">详情</el-button>
            <el-button link type="primary" @click="openInviteTree(row)">邀请关系</el-button>
            <el-button link type="info" :disabled="!row.is_legacy_imported" @click="openLegacyProfile(row)">
              历史资料
            </el-button>
            <el-button v-permission="'users:status'" link type="warning" @click="toggleStatus(row)">
              {{ row.status === 'ENABLED' ? '禁用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-drawer v-model="detailDrawerVisible" title="用户详情" size="960px">
      <div class="panel-card data-card legacy-card" v-loading="detailLoading">
        <template v-if="userDetail">
          <div class="legacy-section">
            <div class="soft-tag">基础信息</div>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="用户 ID">{{ userDetail.id }}</el-descriptions-item>
              <el-descriptions-item label="来源">{{ userDetail.is_legacy_imported ? '历史导入' : '当前用户' }}</el-descriptions-item>
              <el-descriptions-item label="历史 ID">{{ userDetail.legacy_user_id ?? '--' }}</el-descriptions-item>
              <el-descriptions-item label="手机号">{{ userDetail.phone || '--' }}</el-descriptions-item>
              <el-descriptions-item label="昵称">{{ userDetail.nickname || '--' }}</el-descriptions-item>
              <el-descriptions-item label="邀请码">{{ userDetail.invite_code || '--' }}</el-descriptions-item>
              <el-descriptions-item label="系统角色">{{ userDetail.global_role }}</el-descriptions-item>
              <el-descriptions-item label="业务身份">{{ userDetail.business_identity }}</el-descriptions-item>
              <el-descriptions-item label="状态">{{ userDetail.status }}</el-descriptions-item>
              <el-descriptions-item label="团队">{{ userDetail.team_id ?? '--' }}</el-descriptions-item>
              <el-descriptions-item label="上级">{{ userDetail.parent_id ?? '--' }}</el-descriptions-item>
              <el-descriptions-item label="上上级">{{ userDetail.grandparent_id ?? '--' }}</el-descriptions-item>
            </el-descriptions>
          </div>

          <div class="legacy-section">
            <div class="soft-tag">邀请统计</div>
            <div class="tiny-stat-grid">
              <div class="tiny-stat">
                <div class="title">一级邀请</div>
                <div class="number">{{ userDetail.invite_summary?.level1_count ?? 0 }}</div>
              </div>
              <div class="tiny-stat">
                <div class="title">二级邀请</div>
                <div class="number">{{ userDetail.invite_summary?.level2_count ?? 0 }}</div>
              </div>
              <div class="tiny-stat">
                <div class="title">邀请总数</div>
                <div class="number">{{ userDetail.invite_summary?.total_count ?? 0 }}</div>
              </div>
            </div>
          </div>

          <div class="legacy-section">
            <div class="soft-tag">资产摘要</div>
            <el-table :data="assetRows" size="small" border>
              <el-table-column prop="assetType" label="资产类型" min-width="120" />
              <el-table-column prop="availableAmount" label="可用" min-width="100" />
              <el-table-column prop="totalAmount" label="累计" min-width="100" />
              <el-table-column prop="frozenAmount" label="冻结" min-width="100" />
              <el-table-column prop="consumedAmount" label="已消耗" min-width="100" />
              <el-table-column prop="withdrawnAmount" label="已提现" min-width="100" />
            </el-table>
          </div>

          <div class="legacy-section">
            <div class="soft-tag">充电宝绑定</div>
            <div class="toolbar-row toolbar-wrap">
              <el-input v-model="powerBankForm.device_code" placeholder="设备编号" style="max-width: 220px;" />
              <el-input v-model="powerBankForm.device_name" placeholder="设备名称，可选" style="max-width: 220px;" />
              <el-input v-model="powerBankForm.remark" placeholder="备注，可选" style="max-width: 260px;" />
              <el-button type="primary" :loading="powerBankSubmitting" @click="submitPowerBank">添加充电宝</el-button>
            </div>
            <el-table :data="powerBankRows" size="small" border>
              <el-table-column prop="device_code" label="设备编号" min-width="160" />
              <el-table-column prop="device_name" label="设备名称" min-width="140" />
              <el-table-column label="状态" width="110">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'ACTIVE' ? 'success' : 'info'">
                    {{ row.status === 'ACTIVE' ? '生效中' : '已停用' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="累计收益" min-width="110">
                <template #default="{ row }">{{ formatAmount(row.total_income_amount) }}</template>
              </el-table-column>
              <el-table-column label="推荐奖累计" min-width="110">
                <template #default="{ row }">{{ formatAmount(row.total_referral_income_amount) }}</template>
              </el-table-column>
              <el-table-column label="最近结算日" min-width="120">
                <template #default="{ row }">{{ row.last_income_date || '--' }}</template>
              </el-table-column>
              <el-table-column prop="remark" label="备注" min-width="160" />
              <el-table-column label="操作" width="100" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" @click="togglePowerBankStatus(row)">
                    {{ row.status === 'ACTIVE' ? '停用' : '启用' }}
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <div class="legacy-section">
            <div class="soft-tag">最近资产流水</div>
            <el-table :data="userDetail.recent_asset_ledgers || []" size="small" border>
              <el-table-column prop="id" label="ID" width="90" />
              <el-table-column prop="asset_type" label="资产类型" min-width="110" />
              <el-table-column prop="direction" label="方向" width="90" />
              <el-table-column label="变动" min-width="100">
                <template #default="{ row }">{{ formatAmount(row.change_amount) }}</template>
              </el-table-column>
              <el-table-column prop="business_type" label="业务类型" min-width="160" />
              <el-table-column label="变动后" min-width="100">
                <template #default="{ row }">{{ formatAmount(row.after_amount) }}</template>
              </el-table-column>
              <el-table-column label="时间" min-width="160">
                <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
              </el-table-column>
            </el-table>
          </div>

          <div class="legacy-section">
            <div class="soft-tag">最近订单</div>
            <el-table :data="userDetail.recent_orders || []" size="small" border>
              <el-table-column prop="id" label="ID" width="90" />
              <el-table-column prop="order_no" label="订单号" min-width="180" />
              <el-table-column prop="order_type" label="订单类型" min-width="140" />
              <el-table-column prop="order_status" label="订单状态" min-width="110" />
              <el-table-column prop="pay_status" label="支付状态" min-width="110" />
              <el-table-column label="应付金额" min-width="100">
                <template #default="{ row }">{{ formatAmount(row.payable_amount) }}</template>
              </el-table-column>
              <el-table-column label="创建时间" min-width="160">
                <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
              </el-table-column>
            </el-table>
          </div>
        </template>
      </div>
    </el-drawer>

    <el-drawer v-model="drawerVisible" title="邀请关系" size="520px">
      <div class="panel-card data-card">
        <div class="soft-tag">用户 {{ inviteTree.user_id || '--' }}</div>
        <p class="drawer-meta">手机号：{{ inviteTree.phone || '--' }}</p>
        <el-divider content-position="left">一级邀请</el-divider>
        <el-table :data="inviteTree.level1 || []" size="small" border>
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="phone" label="手机号" />
          <el-table-column prop="nickname" label="昵称" />
        </el-table>
        <el-divider content-position="left">二级邀请</el-divider>
        <el-table :data="inviteTree.level2 || []" size="small" border>
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="phone" label="手机号" />
          <el-table-column prop="nickname" label="昵称" />
        </el-table>
      </div>
    </el-drawer>

    <el-drawer v-model="legacyDrawerVisible" title="历史资料" size="720px">
      <div class="panel-card data-card legacy-card" v-loading="legacyLoading">
        <template v-if="legacyProfile">
          <div class="legacy-section">
            <div class="soft-tag">当前用户</div>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="用户 ID">{{ legacyProfile.user.id }}</el-descriptions-item>
              <el-descriptions-item label="来源">{{ legacyProfile.user.is_legacy_imported ? '历史导入' : '当前用户' }}</el-descriptions-item>
              <el-descriptions-item label="历史 ID">{{ legacyProfile.user.legacy_user_id ?? '--' }}</el-descriptions-item>
              <el-descriptions-item label="手机号">{{ legacyProfile.user.phone || '--' }}</el-descriptions-item>
              <el-descriptions-item label="昵称">{{ legacyProfile.user.nickname || '--' }}</el-descriptions-item>
              <el-descriptions-item label="邀请码">{{ legacyProfile.user.invite_code || '--' }}</el-descriptions-item>
            </el-descriptions>
          </div>

          <div class="legacy-section">
            <div class="soft-tag">历史原始字段</div>
            <el-descriptions :column="2" border>
              <el-descriptions-item v-for="item in legacyFields" :key="item.key" :label="item.key">
                {{ item.value }}
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { userApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const users = ref([])
const keyword = ref('')
const roleFilter = ref('')
const sourceFilter = ref('')
const drawerVisible = ref(false)
const inviteTree = ref({})
const legacyDrawerVisible = ref(false)
const legacyLoading = ref(false)
const legacyProfile = ref(null)
const detailDrawerVisible = ref(false)
const detailLoading = ref(false)
const userDetail = ref(null)
const powerBankSubmitting = ref(false)
const powerBankForm = ref({
  device_code: '',
  device_name: '',
  remark: ''
})

const scopeHint = computed(() =>
  userStore.role === 'TEAM_ADMIN'
    ? '仅查看当前团队用户，支持按来源和角色筛选。'
    : '查看全平台用户，支持筛选历史导入与当前注册用户。'
)

const legacyFields = computed(() => {
  const payload = legacyProfile.value?.legacy_profile || {}
  return Object.entries(payload).map(([key, value]) => ({
    key,
    value: value === null || value === '' ? '--' : String(value)
  }))
})

const assetRows = computed(() => {
  const summary = userDetail.value?.asset_summary || {}
  return Object.entries(summary).map(([assetType, item]) => ({
    assetType,
    availableAmount: formatAmount(item.available_amount),
    totalAmount: formatAmount(item.total_amount),
    frozenAmount: formatAmount(item.frozen_amount),
    consumedAmount: formatAmount(item.consumed_amount),
    withdrawnAmount: formatAmount(item.withdrawn_amount)
  }))
})

const powerBankRows = computed(() => userDetail.value?.power_banks || [])

function formatAmount(value) {
  return value == null ? '--' : Number(value).toFixed(2)
}

function formatDate(value) {
  if (!value) return '--'
  return String(value).replace('T', ' ').slice(0, 19)
}

function resetPowerBankForm() {
  powerBankForm.value = {
    device_code: '',
    device_name: '',
    remark: ''
  }
}

async function fetchUsers() {
  users.value = await userApi.list({
    keyword: keyword.value || undefined,
    role: roleFilter.value || undefined,
    source: sourceFilter.value || undefined
  })
}

async function loadUserDetail(userId) {
  userDetail.value = await userApi.detail(userId)
}

async function openUserDetail(row) {
  detailLoading.value = true
  detailDrawerVisible.value = true
  try {
    await loadUserDetail(row.id)
  } finally {
    detailLoading.value = false
  }
}

async function openInviteTree(row) {
  inviteTree.value = await userApi.inviteTree(row.id)
  drawerVisible.value = true
}

async function openLegacyProfile(row) {
  if (!row.is_legacy_imported) return
  legacyLoading.value = true
  legacyDrawerVisible.value = true
  try {
    legacyProfile.value = await userApi.legacyProfile(row.id)
  } finally {
    legacyLoading.value = false
  }
}

async function submitPowerBank() {
  if (!userDetail.value?.id) return
  if (!String(powerBankForm.value.device_code || '').trim()) {
    ElMessage.warning('请输入设备编号')
    return
  }
  powerBankSubmitting.value = true
  try {
    await userApi.bindPowerBank(userDetail.value.id, powerBankForm.value)
    ElMessage.success('充电宝已绑定')
    resetPowerBankForm()
    await loadUserDetail(userDetail.value.id)
  } finally {
    powerBankSubmitting.value = false
  }
}

async function togglePowerBankStatus(row) {
  if (!userDetail.value?.id || !row?.id) return
  const nextStatus = row.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE'
  await ElMessageBox.confirm(`确认将该充电宝状态调整为 ${nextStatus} 吗？`, '充电宝状态变更', {
    type: 'warning'
  })
  await userApi.updatePowerBank(userDetail.value.id, row.id, { status: nextStatus })
  ElMessage.success('充电宝状态已更新')
  await loadUserDetail(userDetail.value.id)
}

async function toggleStatus(row) {
  const nextStatus = row.status === 'ENABLED' ? 'DISABLED' : 'ENABLED'
  await ElMessageBox.confirm(`确认将该用户状态调整为 ${nextStatus} 吗？`, '状态变更', {
    type: 'warning'
  })
  await userApi.updateStatus(row.id, { status: nextStatus })
  await fetchUsers()
}

onMounted(fetchUsers)
</script>

<style scoped>
.user-list-view {
  display: grid;
  gap: 18px;
}

.toolbar-wrap {
  flex-wrap: wrap;
}

.drawer-meta {
  margin: 14px 0 10px;
}

.legacy-card {
  display: grid;
  gap: 18px;
}

.legacy-section {
  display: grid;
  gap: 12px;
}

:deep(.el-table .el-button.is-link) {
  padding: 0;
}

:deep(.el-drawer__header) {
  margin-bottom: 0;
}
</style>
