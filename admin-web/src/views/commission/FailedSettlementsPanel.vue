<template>
  <div class="panel-card data-card">
    <div class="panel-heading">
      <h3>商品订单待处理</h3>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table v-loading="loading" :data="rows" row-key="order_id" empty-text="暂无待处理订单">
      <el-table-column type="expand"><template #default="{ row }">
        <el-descriptions :column="3" border class="order-detail">
          <el-descriptions-item label="商品售价">¥{{ row.sale_price_snapshot }}</el-descriptions-item>
          <el-descriptions-item label="付款时成本">¥{{ row.cost_price_snapshot }}</el-descriptions-item>
          <el-descriptions-item label="分润池">¥{{ row.profit_pool_snapshot }}</el-descriptions-item>
        </el-descriptions>
      </template></el-table-column>
      <el-table-column prop="order_no" label="订单号" min-width="190" />
      <el-table-column prop="user_id" label="购买者 ID" width="100" />
      <el-table-column prop="paid_amount" label="已付金额" width="110" />
      <el-table-column prop="settlement_error" label="原因" min-width="240" show-overflow-tooltip />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button link type="danger" :disabled="refundingId !== null" :loading="refundingId === row.order_id" @click="refund(row)">申请退款</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" :page-size="20" :total="total" layout="total, prev, pager, next" @current-change="load" />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { commissionApi, orderApi } from '@/api/modules'

const rows = ref([]), page = ref(1), total = ref(0), loading = ref(false), refundingId = ref(null)
async function load() {
  loading.value = true
  try {
    const data = await commissionApi.failedSettlements({ page: page.value })
    rows.value = data.items
    total.value = data.total
  } finally { loading.value = false }
}
async function refund(row) {
  try { await ElMessageBox.confirm(`为已付款订单 ${row.order_no} 申请全额退款 ¥${row.paid_amount}？`, '退款确认') } catch { return }
  refundingId.value = row.order_id
  try {
    const result = await orderApi.refund(row.order_id)
    if (result.completed) ElMessage.success('订单已退款')
    else if (['FAILED', 'CLOSED', 'ABNORMAL'].includes(result.provider_status)) ElMessage.error('退款未成功，请到订单管理核对渠道结果')
    else ElMessage.info('退款申请已提交，等待渠道处理')
    await load()
  } finally { refundingId.value = null }
}
onMounted(load)
</script>

<style scoped>
.panel-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 20px; }
.panel-heading h3 { margin: 0; font-size: 18px; color: var(--text-primary); }
.order-detail { margin: 12px 24px; }
.el-pagination { margin-top: 20px; justify-content: flex-end; }
</style>
