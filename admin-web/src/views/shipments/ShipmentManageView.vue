<template>
  <div class="page-shell">
    <div class="page-header">
      <h2>快递物流</h2>
    </div>

    <div class="panel-card">
      <div class="panel-toolbar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索订单号/运单号"
          clearable
          style="width: 240px"
          @clear="loadShipments"
          @keyup.enter="loadShipments"
        >
          <template #append>
            <el-button :icon="Search" @click="loadShipments" />
          </template>
        </el-input>
        <el-select v-model="filterStatus" placeholder="物流状态" clearable style="width: 140px; margin-left: 12px" @change="loadShipments">
          <el-option value="pending" label="待发货" />
          <el-option value="shipping" label="运输中" />
          <el-option value="delivered" label="已签收" />
          <el-option value="cancelled" label="已取消" />
        </el-select>
      </div>

      <el-table :data="shipments" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="order_no" label="订单号" min-width="160">
          <template #default="{ row }">
            <span class="order-no">{{ row.order_no }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="商品标题" min-width="140" show-overflow-tooltip />
        <el-table-column label="物流状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ row.status_text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="tracking_no" label="运单号" min-width="160">
          <template #default="{ row }">
            <span v-if="row.tracking_no" class="tracking-no">{{ row.tracking_no }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="承运商" min-width="120">
          <template #default="{ row }">
            <span v-if="row.carrier_name">{{ row.carrier_name }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="订单金额" width="100" align="right">
          <template #default="{ row }">
            <span class="amount">¥{{ row.amount?.toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="下单时间" width="170" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="viewDetail(row)">
              查看详情
            </el-button>
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
          @size-change="loadShipments"
          @current-change="loadShipments"
        />
      </div>
    </div>

    <!-- 物流详情弹窗 -->
    <el-dialog v-model="detailDialogVisible" title="物流详情" width="600px">
      <div v-if="detail" class="shipment-detail">
        <div class="detail-section">
          <div class="detail-title">订单信息</div>
          <div class="detail-grid">
            <div class="detail-item">
              <span class="detail-label">订单号</span>
              <span class="detail-value">{{ detail.order_no }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">商品标题</span>
              <span class="detail-value">{{ detail.title }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">订单金额</span>
              <span class="detail-value amount">¥{{ detail.amount?.toFixed(2) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">配送方式</span>
              <span class="detail-value">{{ detail.delivery_mode_text }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">下单时间</span>
              <span class="detail-value">{{ detail.created_at }}</span>
            </div>
          </div>
        </div>

        <el-divider />

        <div class="detail-section">
          <div class="detail-title">物流信息</div>
          <div class="detail-grid">
            <div class="detail-item">
              <span class="detail-label">物流状态</span>
              <el-tag :type="getStatusType(detail.status)" size="small">{{ detail.status_text }}</el-tag>
            </div>
            <div class="detail-item">
              <span class="detail-label">运单号</span>
              <span v-if="detail.tracking_no" class="detail-value tracking-no">{{ detail.tracking_no }}</span>
              <span v-else class="detail-value text-muted">暂无</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">承运商</span>
              <span v-if="detail.carrier_name" class="detail-value">{{ detail.carrier_name }}</span>
              <span v-else class="detail-value text-muted">暂无</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">承运商电话</span>
              <span v-if="detail.carrier_phone" class="detail-value">{{ detail.carrier_phone }}</span>
              <span v-else class="detail-value text-muted">暂无</span>
            </div>
          </div>

          <!-- 物流进度 -->
          <div v-if="detail.status_hint" class="progress-hint">
            <el-icon><Warning /></el-icon>
            <span>{{ detail.status_hint }}</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: (detail.progress_percent || 0) + '%' }"></div>
          </div>
        </div>

        <el-divider />

        <div class="detail-section">
          <div class="detail-title">更新物流信息</div>
          <el-form label-width="100px">
            <el-form-item label="运单号">
              <el-input v-model="trackingForm.tracking_no" placeholder="请输入运单号" />
            </el-form-item>
            <el-form-item label="承运商名称">
              <el-input v-model="trackingForm.carrier_name" placeholder="如：顺丰速运、圆通速递" />
            </el-form-item>
            <el-form-item label="承运商电话">
              <el-input v-model="trackingForm.carrier_phone" placeholder="请输入承运商联系电话" />
            </el-form-item>
          </el-form>
        </div>
      </div>

      <template #footer>
        <el-button @click="detailDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="updateTracking" :loading="updating">保存物流信息</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Search, Warning } from '@element-plus/icons-vue'
import { shipmentApi } from '@/api/modules'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const shipments = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const searchKeyword = ref('')
const filterStatus = ref('')

const loadShipments = async () => {
  loading.value = true
  try {
    const res = await shipmentApi.list({
      page: page.value,
      page_size: pageSize.value,
      keyword: searchKeyword.value || undefined,
      status: filterStatus.value || undefined
    })
    if (res.code === 0) {
      shipments.value = res.data?.items || []
      total.value = res.data?.total || 0
    }
  } catch (e) {
    console.error('加载物流列表失败', e)
  } finally {
    loading.value = false
  }
}

const getStatusType = (status) => {
  const map = {
    pending: 'warning',
    shipping: 'primary',
    delivered: 'success',
    cancelled: 'info'
  }
  return map[status] || 'info'
}

// 详情弹窗
const detailDialogVisible = ref(false)
const detail = ref(null)
const trackingForm = ref({
  tracking_no: '',
  carrier_name: '',
  carrier_phone: ''
})
const updating = ref(false)

const viewDetail = async (row) => {
  try {
    const res = await shipmentApi.detail(row.id)
    if (res.code === 0) {
      detail.value = res.data
      trackingForm.value = {
        tracking_no: res.data.tracking_no || '',
        carrier_name: res.data.carrier_name || '',
        carrier_phone: res.data.carrier_phone || ''
      }
      detailDialogVisible.value = true
    }
  } catch (e) {
    console.error('加载物流详情失败', e)
  }
}

const updateTracking = async () => {
  if (!detail.value) return
  updating.value = true
  try {
    const res = await shipmentApi.updateTracking(detail.value.id, trackingForm.value)
    if (res.code === 0) {
      ElMessage.success('物流信息更新成功')
      detailDialogVisible.value = false
      loadShipments()
    } else {
      ElMessage.error(res.message || '更新失败')
    }
  } catch (e) {
    console.error('更新物流信息失败', e)
    ElMessage.error('更新失败')
  } finally {
    updating.value = false
  }
}

onMounted(() => {
  loadShipments()
})
</script>

<style scoped>
.order-no {
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.tracking-no {
  font-family: 'Courier New', monospace;
  color: var(--accent);
}

.text-muted {
  color: var(--text-secondary);
}

.amount {
  color: var(--accent);
  font-weight: 600;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.shipment-detail {
  padding: 0 8px;
}

.detail-section {
  margin-bottom: 8px;
}

.detail-title {
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.detail-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.detail-label {
  color: var(--text-secondary);
  font-size: 13px;
  min-width: 80px;
}

.detail-value {
  color: var(--text-primary);
  word-break: break-all;
}

.progress-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
  font-size: 13px;
  margin: 16px 0 8px;
}

.progress-bar {
  height: 6px;
  background: var(--border-light);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary), var(--accent));
  border-radius: 3px;
  transition: width 0.3s ease;
}
</style>