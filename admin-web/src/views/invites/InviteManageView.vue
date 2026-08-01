<template>
  <div class="page-shell">
    <div class="page-header">
      <h2>邀请裂变</h2>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">邀请码总数</div>
        <div class="stat-value">{{ summary.total_invite_codes || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">已邀请用户</div>
        <div class="stat-value">{{ summary.total_invited_users || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">一级邀请</div>
        <div class="stat-value">{{ summary.level1_count || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">二级邀请</div>
        <div class="stat-value">{{ summary.level2_count || 0 }}</div>
      </div>
    </div>

    <!-- 标签页 -->
    <el-tabs v-model="activeTab" class="page-tabs">
      <el-tab-pane label="用户邀请统计" name="users">
        <!-- 用户邀请列表 -->
        <div class="panel-card">
          <div class="panel-toolbar">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索用户名/手机/邀请码"
              clearable
              style="width: 240px"
              @clear="loadUsers"
              @keyup.enter="loadUsers"
            >
              <template #append>
                <el-button :icon="Search" @click="loadUsers" />
              </template>
            </el-input>
          </div>

          <el-table :data="users" v-loading="loading" stripe>
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="username" label="用户名" min-width="120" />
            <el-table-column prop="phone" label="手机号" width="130" />
            <el-table-column prop="invite_code" label="邀请码" min-width="120">
              <template #default="{ row }">
                <span class="invite-code">{{ row.invite_code || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="一级邀请" width="100" align="center">
              <template #default="{ row }">
                <el-tag type="primary" size="small">{{ row.level1_count }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="二级邀请" width="100" align="center">
              <template #default="{ row }">
                <el-tag type="info" size="small">{{ row.level2_count }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="邀请人" min-width="120">
              <template #default="{ row }">
                <span v-if="row.inviter">{{ row.inviter.username }}</span>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            <el-table-column label="注册时间" width="170">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="viewTree(row)">
                  查看下线
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-wrap">
            <el-pagination
              v-model:current-page="usersPage"
              v-model:page-size="usersPageSize"
              :total="usersTotal"
              :page-sizes="[10, 20, 50]"
              layout="total, sizes, prev, pager, next"
              @size-change="loadUsers"
              @current-change="loadUsers"
            />
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="邀请记录" name="records">
        <!-- 邀请记录列表 -->
        <div class="panel-card">
          <div class="panel-toolbar">
            <el-input
              v-model="recordKeyword"
              placeholder="搜索用户名/手机号"
              clearable
              style="width: 240px"
              @clear="loadRecords"
              @keyup.enter="loadRecords"
            >
              <template #append>
                <el-button :icon="Search" @click="loadRecords" />
              </template>
            </el-input>
            <el-select v-model="recordLevel" placeholder="邀请层级" clearable style="width: 120px; margin-left: 12px" @change="loadRecords">
              <el-option :value="1" label="一级邀请" />
              <el-option :value="2" label="二级邀请" />
            </el-select>
          </div>

          <el-table :data="records" v-loading="loading" stripe>
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="username" label="被邀请用户" min-width="120" />
            <el-table-column prop="phone" label="手机号" width="130" />
            <el-table-column label="邀请层级" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.invite_level === 1 ? 'primary' : 'success'" size="small">
                  {{ row.invite_level === 1 ? '一级' : '二级' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="邀请人" min-width="120">
              <template #default="{ row }">
                <span v-if="row.inviter">{{ row.inviter.username }}</span>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            <el-table-column label="二级邀请人" min-width="120">
              <template #default="{ row }">
                <span v-if="row.grand_inviter">{{ row.grand_inviter.username }}</span>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            <el-table-column label="注册时间" width="170">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>

          <div class="pagination-wrap">
            <el-pagination
              v-model:current-page="recordsPage"
              v-model:page-size="recordsPageSize"
              :total="recordsTotal"
              :page-sizes="[10, 20, 50]"
              layout="total, sizes, prev, pager, next"
              @size-change="loadRecords"
              @current-change="loadRecords"
            />
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 邀请树弹窗 -->
    <el-dialog v-model="treeDialogVisible" title="邀请下线" width="640px">
      <div v-if="treeData.user" class="tree-user-info">
        <span class="tree-user-label">当前用户：</span>
        <span class="tree-user-name">{{ treeData.user.username }}</span>
        <span class="tree-user-phone">{{ treeData.user.phone }}</span>
      </div>
      <el-divider />
      <div class="tree-section">
        <div class="tree-title">一级下线 ({{ treeData.level1?.length || 0 }}人)</div>
        <div v-if="treeData.level1?.length" class="tree-list">
          <div v-for="u in treeData.level1" :key="u.id" class="tree-item">
            <span class="tree-item-name">{{ u.username }}</span>
            <span class="tree-item-phone">{{ u.phone }}</span>
            <span class="tree-item-time">{{ formatDateTime(u.created_at) }}</span>
          </div>
        </div>
        <el-empty v-else description="暂无一级下线" :image-size="60" />
      </div>
      <el-divider />
      <div class="tree-section">
        <div class="tree-title">二级下线 ({{ treeData.level2?.length || 0 }}人)</div>
        <div v-if="treeData.level2?.length" class="tree-list">
          <div v-for="u in treeData.level2" :key="u.id" class="tree-item">
            <span class="tree-item-name">{{ u.username }}</span>
            <span class="tree-item-phone">{{ u.phone }}</span>
            <span class="tree-item-time">{{ formatDateTime(u.created_at) }}</span>
          </div>
        </div>
        <el-empty v-else description="暂无二级下线" :image-size="60" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { inviteApi } from '@/api/modules'
import { formatDateTime } from '@/utils/datetime'

const activeTab = ref('users')
const loading = ref(false)

// 统计数据
const summary = ref({})
const loadSummary = async () => {
  try {
    const res = await inviteApi.summary()
    if (res.code === 0) {
      summary.value = res.data || {}
    }
  } catch (e) {
    console.error('加载邀请统计失败', e)
  }
}

// 用户邀请列表
const searchKeyword = ref('')
const users = ref([])
const usersPage = ref(1)
const usersPageSize = ref(20)
const usersTotal = ref(0)

const loadUsers = async () => {
  loading.value = true
  try {
    const res = await inviteApi.users({
      page: usersPage.value,
      page_size: usersPageSize.value,
      keyword: searchKeyword.value || undefined
    })
    if (res.code === 0) {
      users.value = res.data?.items || []
      usersTotal.value = res.data?.total || 0
    }
  } catch (e) {
    console.error('加载用户邀请列表失败', e)
  } finally {
    loading.value = false
  }
}

// 邀请记录列表
const recordKeyword = ref('')
const recordLevel = ref(null)
const records = ref([])
const recordsPage = ref(1)
const recordsPageSize = ref(20)
const recordsTotal = ref(0)

const loadRecords = async () => {
  loading.value = true
  try {
    const res = await inviteApi.records({
      page: recordsPage.value,
      page_size: recordsPageSize.value,
      keyword: recordKeyword.value || undefined,
      level: recordLevel.value || undefined
    })
    if (res.code === 0) {
      records.value = res.data?.items || []
      recordsTotal.value = res.data?.total || 0
    }
  } catch (e) {
    console.error('加载邀请记录失败', e)
  } finally {
    loading.value = false
  }
}

// 邀请树弹窗
const treeDialogVisible = ref(false)
const treeData = ref({ user: null, level1: [], level2: [] })

const viewTree = async (row) => {
  try {
    const res = await inviteApi.tree(row.id)
    if (res.code === 0) {
      treeData.value = res.data || { user: null, level1: [], level2: [] }
      treeDialogVisible.value = true
    }
  } catch (e) {
    console.error('加载邀请树失败', e)
  }
}

onMounted(() => {
  loadSummary()
  loadUsers()
})
</script>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-light);
  border-radius: 12px;
  padding: 20px;
  text-align: center;
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--primary-deep);
}

.page-tabs {
  margin-top: 0;
}

.invite-code {
  font-family: 'Courier New', monospace;
  color: var(--accent);
  letter-spacing: 1px;
}

.text-muted {
  color: var(--text-secondary);
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.tree-user-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tree-user-label {
  color: var(--text-secondary);
}

.tree-user-name {
  font-weight: 600;
  color: var(--text-primary);
}

.tree-user-phone {
  color: var(--text-secondary);
  font-size: 13px;
}

.tree-section {
  margin: 0;
}

.tree-title {
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.tree-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tree-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border-radius: 6px;
}

.tree-item-name {
  font-weight: 500;
  color: var(--text-primary);
  min-width: 100px;
}

.tree-item-phone {
  color: var(--text-secondary);
  font-size: 13px;
}

.tree-item-time {
  margin-left: auto;
  color: var(--text-secondary);
  font-size: 12px;
}
</style>
