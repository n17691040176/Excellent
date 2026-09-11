<template>
  <div class="panel-card data-card">
    <template v-if="!pendingOnly">
    <div class="panel-heading">
      <h3>城市合伙人席位</h3>
      <div><el-button @click="load">刷新</el-button><el-button type="primary" @click="edit()">创建席位</el-button></div>
    </div>
    <el-input v-model="cityKeyword" placeholder="搜索城市或合伙人" clearable class="city-search" />
    <el-table v-loading="loading" :data="pagedSeats" row-key="id" empty-text="暂无城市席位">
      <el-table-column type="expand">
        <template #default="{ row }">
          <el-descriptions :column="2" border class="seat-detail">
            <el-descriptions-item label="初始价格">¥{{ money(row.initial_price) }}</el-descriptions-item>
            <el-descriptions-item label="价格上限">{{ row.price_cap == null ? '不限' : `¥${money(row.price_cap)}` }}</el-descriptions-item>
            <el-descriptions-item label="任期开始">{{ row.term_started_at ? formatDateTime(row.term_started_at) : '—' }}</el-descriptions-item>
            <el-descriptions-item label="当前订单">{{ row.current_order_no || '—' }}</el-descriptions-item>
          </el-descriptions>
        </template>
      </el-table-column>
      <el-table-column label="城市" min-width="180" show-overflow-tooltip><template #default="{ row }">{{ row.province }} / {{ row.city }}</template></el-table-column>
      <el-table-column label="当前合伙人" min-width="150" show-overflow-tooltip><template #default="{ row }">{{ row.current_user_nickname || '空缺' }}</template></el-table-column>
      <el-table-column label="购买价格" min-width="130"><template #default="{ row }">¥{{ money(row.current_price) }}</template></el-table-column>
      <el-table-column label="涨幅" width="90"><template #default="{ row }">{{ row.price_growth_rate }}%</template></el-table-column>
      <el-table-column prop="rotation_count" label="成交次数" width="100" />
      <el-table-column label="状态" width="90"><template #default="{ row }"><el-tag :type="row.status === 'ACTIVE' ? 'success' : 'info'">{{ row.status === 'ACTIVE' ? '启用' : '停用' }}</el-tag></template></el-table-column>
      <el-table-column label="操作" width="240" fixed="right"><template #default="{ row }"><el-button link type="primary" @click="edit(row)">配置</el-button><el-button link type="primary" @click="history(row)">结算记录</el-button><el-button link @click="historyId = row.id; auditVisible = true">修改记录</el-button></template></el-table-column>
    </el-table>
    <el-pagination v-model:current-page="seatPage" :page-size="10" :total="filteredSeats.length" layout="total, prev, pager, next" />
    </template>
    <el-dialog v-model="visible" :title="editingId ? '配置席位' : '创建席位'" width="520px">
      <el-form label-width="130px">
        <el-alert v-if="editingId" title="调整后，旧报价失效" type="info" :closable="false" class="edit-notice" />
        <el-form-item label="省 / 市"><el-cascader v-if="!editingId" v-model="regionPath" :options="cityOptions" filterable placeholder="选择省、市" /><span v-else>{{ form.province }} / {{ form.city }}</span></el-form-item>
        <el-form-item label="初始价格"><el-input-number v-model="form.initial_price" :disabled="!!editingId" :min="0.01" :precision="2" /></el-form-item>
        <el-form-item label="增长比例（%）"><el-input-number v-model="form.price_growth_rate" :min="0" :max="100" :precision="4" /></el-form-item>
        <el-form-item label="价格上限"><el-input-number v-model="form.price_cap" :min="0.01" :precision="2" placeholder="不设上限" /></el-form-item>
        <el-form-item v-if="editingId" label="启用"><el-switch v-model="enabled" /></el-form-item>
        <el-form-item label="修改原因"><el-input v-model="changeReason" placeholder="选填" maxlength="500" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="visible = false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存席位</el-button></template>
    </el-dialog>
    <el-drawer v-model="historyVisible" title="席位结算记录" size="75%">
      <el-table :data="rotations">
        <el-table-column prop="order_no" label="订单号" min-width="210" />
        <el-table-column prop="previous_user_id" label="上一任用户 ID" />
        <el-table-column prop="new_user_id" label="新任用户 ID" />
        <el-table-column prop="new_price" label="成交价" />
        <el-table-column prop="principal_refund_amount" label="返还本金" />
        <el-table-column prop="appreciation_reward_amount" label="上任奖励" />
        <el-table-column prop="parent_reward_amount" label="上级奖励" />
        <el-table-column prop="company_amount" label="公司收入" />
        <el-table-column prop="operations_amount" label="运维收入" />
        <el-table-column label="结算时间" min-width="175"><template #default="{ row }">{{ formatDateTime(row.confirmed_at) }}</template></el-table-column>
        <el-table-column prop="commission_rule_version" label="规则版本" min-width="160" show-overflow-tooltip />
      </el-table>
    </el-drawer>
    <RuleHistoryDrawer v-model="auditVisible" :entity-id="historyId" entity-type="SEAT" />
    <template v-if="pendingOnly">
    <div class="panel-heading"><h3>席位订单待处理</h3><el-button @click="loadUnsettled">刷新</el-button></div>
    <el-table :data="unsettled" empty-text="暂无待处理订单">
      <el-table-column prop="order_no" label="订单号" min-width="210" />
      <el-table-column prop="user_id" label="买家 ID" />
      <el-table-column prop="city" label="城市" />
      <el-table-column prop="paid_amount" label="已付金额" />
      <el-table-column prop="settlement_error" label="原因" min-width="240" show-overflow-tooltip />
      <el-table-column label="处理" width="120"><template #default="{ row }"><el-button :loading="refundingId === row.order_id" :disabled="refundingId !== null" @click="refund(row)">申请退款</el-button></template></el-table-column>
    </el-table>
    <el-pagination v-model:current-page="unsettledPage" :page-size="20" :total="unsettledTotal" layout="total, prev, pager, next" @current-change="loadUnsettled" />
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { cityPartnerApi, orderApi } from '@/api/modules'
import { formatDateTime } from '@/utils/datetime'
import { regionOptions } from '@/utils/region-options'
import RuleHistoryDrawer from './RuleHistoryDrawer.vue'
defineProps({ pendingOnly: Boolean })
function money(value) { return Number(value || 0).toFixed(2) }
const cityOptions = regionOptions.map(p => ({ ...p, children: p.children.map(c => ({ label: c.label, value: c.value })) }))
const regionPath = ref([]), changeReason = ref(''), auditVisible = ref(false), historyId = ref(null)
const unsettled = ref([]), unsettledPage = ref(1), unsettledTotal = ref(0), refundingId = ref(null)
const seats = ref([])
const cityKeyword = ref(''), seatPage = ref(1)
const filteredSeats = computed(() => seats.value.filter(row => `${row.province}${row.city}${row.current_user_nickname || ''}`.includes(cityKeyword.value.trim())))
const pagedSeats = computed(() => filteredSeats.value.slice((seatPage.value - 1) * 10, seatPage.value * 10))
watch(cityKeyword, () => { seatPage.value = 1 })
const loading = ref(false)
const visible = ref(false)
const editingId = ref(null)
const saving = ref(false)
const enabled = ref(true)
const form = ref({})
const rotations = ref([])
const historyVisible = ref(false)
async function load() {
  loading.value = true
  try { seats.value = (await cityPartnerApi.list()).items } finally { loading.value = false }
}
function edit(row) {
  regionPath.value = row ? [row.province, row.city] : []
  changeReason.value = ''
  editingId.value = row?.id || null
  form.value = row ? { ...row } : { province: '', city: '', initial_price: 1000, price_growth_rate: 20, price_cap: null }
  enabled.value = !row || row.status === 'ACTIVE'
  visible.value = true
}
async function save() {
  if (!editingId.value && regionPath.value.length !== 2) { ElMessage.warning('请选择省、市'); return }
  saving.value = true
  try {
    const data = { price_growth_rate: form.value.price_growth_rate, price_cap: form.value.price_cap ?? null, change_reason: changeReason.value || null }
    if (editingId.value) await cityPartnerApi.update(editingId.value, { ...data, status: enabled.value ? 'ACTIVE' : 'INACTIVE' })
    else await cityPartnerApi.create({ ...data, province: regionPath.value[0], city: regionPath.value[1], initial_price: form.value.initial_price })
    visible.value = false
    await load()
    ElMessage.success('席位已保存')
  } finally { saving.value = false }
}
async function history(row) {
  rotations.value = (await cityPartnerApi.rotations(row.id)).items
  historyVisible.value = true
}
async function loadUnsettled() { const data = await cityPartnerApi.unsettled({ page: unsettledPage.value }); unsettled.value = data.items; unsettledTotal.value = data.total }
async function refund(row) {
  try { await ElMessageBox.confirm(`为订单 ${row.order_no} 申请退款 ¥${row.paid_amount}？`, '确认未履约订单退款') } catch { return }
  refundingId.value = row.order_id
  try {
    const result = await orderApi.refund(row.order_id)
    if (result.completed) ElMessage.success('订单已退款')
    else if (['FAILED', 'CLOSED', 'ABNORMAL'].includes(result.provider_status)) ElMessage.error('退款未成功，请到订单管理核对渠道结果')
    else ElMessage.info('退款申请已提交，等待渠道处理')
    await loadUnsettled()
  } finally { refundingId.value = null }
}
onMounted(() => Promise.all([load(), loadUnsettled()]))
</script>

<style scoped>
.panel-heading { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }
.panel-heading h3 { margin: 0; font-size: 18px; color: var(--text-primary); }
.seat-detail { margin: 12px 24px; }
.city-search { max-width: 300px; margin-bottom: 20px; }
.edit-notice { margin-bottom: 20px; }
.el-pagination { margin-top: 20px; justify-content: flex-end; }
</style>
