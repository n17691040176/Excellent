<template>
  <div class="page-shell">
    <div class="page-header">
      <h2>足迹管理</h2>
    </div>

    <div class="panel-card">
      <div class="panel-toolbar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索用户名/商品名称"
          clearable
          style="width: 280px"
          @clear="loadFootprints"
          @keyup.enter="loadFootprints"
        >
          <template #append>
            <el-button :icon="Search" @click="loadFootprints" />
          </template>
        </el-input>
        <span class="toolbar-tip">共 {{ total }} 条足迹记录</span>
      </div>

      <el-table :data="footprints" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="user_id" label="用户ID" width="100" />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="product_id" label="商品ID" width="100" />
        <el-table-column prop="product_name" label="商品名称" min-width="200" show-overflow-tooltip />
        <el-table-column label="浏览次数" width="100" align="center">
          <template #default="{ row }">
            <el-badge :value="row.view_count" :max="99" type="primary" />
          </template>
        </el-table-column>
        <el-table-column prop="first_viewed_at" label="首次浏览" width="170">
          <template #default="{ row }">{{ formatDateTime(row.first_viewed_at) }}</template>
        </el-table-column>
        <el-table-column prop="last_viewed_at" label="最近浏览" width="170">
          <template #default="{ row }">{{ formatDateTime(row.last_viewed_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-popconfirm
              title="确定要删除这条足迹记录吗？"
              confirm-button-text="确定"
              cancel-button-text="取消"
              @confirm="handleDelete(row)"
            >
              <template #reference>
                <el-button type="danger" link size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="loadFootprints"
          @current-change="loadFootprints"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { footprintApi } from '@/api/modules'
import { formatDateTime } from '@/utils/datetime'

const loading = ref(false)
const footprints = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const searchKeyword = ref('')

const loadFootprints = async () => {
  loading.value = true
  try {
    const res = await footprintApi.list({
      page: page.value,
      page_size: pageSize.value,
      keyword: searchKeyword.value || undefined
    })
    if (res.code === 0) {
      footprints.value = res.data?.items || []
      total.value = res.data?.total || 0
    }
  } catch (e) {
    console.error('加载足迹列表失败', e)
  } finally {
    loading.value = false
  }
}

const handleDelete = async (row) => {
  try {
    const res = await footprintApi.remove(row.id)
    if (res.code === 0) {
      ElMessage.success('删除成功')
      loadFootprints()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (e) {
    console.error('删除足迹失败', e)
    ElMessage.error('删除失败')
  }
}

onMounted(() => {
  loadFootprints()
})
</script>

<style scoped>
.toolbar-tip {
  margin-left: auto;
  color: var(--text-secondary);
  font-size: 13px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
