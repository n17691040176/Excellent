<template>
  <div class="earning-rule-view">
    <div class="page-heading">
      <div>
        <h2>收益规则</h2>
        <p>统一维护会员等级、三级分销、复购奖、团队奖和设备收益参数。</p>
      </div>
      <div class="toolbar-row">
        <el-select v-model="filterType" clearable placeholder="规则类型" style="width: 180px" @change="loadRules">
          <el-option v-for="item in ruleTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filterActive" clearable placeholder="启用状态" style="width: 140px" @change="loadRules">
          <el-option label="启用" :value="true" />
          <el-option label="停用" :value="false" />
        </el-select>
        <el-button @click="loadRules">刷新</el-button>
        <el-button type="primary" @click="openCreate">新增规则</el-button>
      </div>
    </div>

    <div class="metric-grid">
      <div v-for="item in metrics" :key="item.label" class="metric-card">
        <div class="label">{{ item.label }}</div>
        <div class="value">{{ item.value }}</div>
        <div class="subtext">{{ item.subtext }}</div>
      </div>
    </div>

    <div class="panel-card data-card block-gap">
      <div class="section-title">
        <div>
          <h3>规则配置表</h3>
          <p>分销比例、团队奖比例、复购奖比例均从这里读取；商品 ID 为空时作为通用规则。</p>
        </div>
      </div>

      <el-table v-loading="loading" :data="rules" border>
        <el-table-column prop="rule_code" label="规则编码" min-width="190" fixed />
        <el-table-column prop="rule_name" label="规则名称" min-width="170" />
        <el-table-column label="类型" width="120">
          <template #default="scope">{{ labelOf(ruleTypeOptions, scope.row.rule_type) }}</template>
        </el-table-column>
        <el-table-column label="商品ID" width="100">
          <template #default="scope">{{ scope.row.product_id || '通用' }}</template>
        </el-table-column>
        <el-table-column label="会员等级" width="140">
          <template #default="scope">{{ labelOf(memberLevelOptions, scope.row.member_level) }}</template>
        </el-table-column>
        <el-table-column label="佣金层级" width="100">
          <template #default="scope">{{ scope.row.commission_level || '--' }}</template>
        </el-table-column>
        <el-table-column label="计算方式" width="120">
          <template #default="scope">{{ labelOf(methodOptions, scope.row.calculation_method) }}</template>
        </el-table-column>
        <el-table-column label="比例%" width="100">
          <template #default="scope">{{ Number(scope.row.reward_rate || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="固定金额" width="110">
          <template #default="scope">{{ amountText(scope.row.reward_amount) }}</template>
        </el-table-column>
        <el-table-column prop="settlement_cycle" label="结算周期" width="110" />
        <el-table-column prop="freeze_days" label="冻结天数" width="90" />
        <el-table-column label="状态" width="90">
          <template #default="scope">
            <el-switch
              v-model="scope.row.is_active"
              :loading="statusSavingId === scope.row.id"
              @change="toggleStatus(scope.row)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="compliance_note" label="合规备注" min-width="260" show-overflow-tooltip />
        <el-table-column label="更新时间" min-width="160">
          <template #default="scope">{{ formatDate(scope.row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="scope">
            <el-button link type="primary" @click="openEdit(scope.row)">编辑</el-button>
            <el-button link type="danger" @click="removeRule(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-drawer v-model="drawerVisible" :title="drawerTitle" size="720px">
      <div class="panel-card data-card">
        <el-alert
          title="自动结算只应接入真实商品订单、真实设备收益和可审计利润；会员礼包必须是等值实物商品。"
          type="warning"
          show-icon
          :closable="false"
          class="form-alert"
        />
        <el-form label-position="top" :model="form">
          <div class="form-split">
            <el-form-item label="规则编码">
              <el-input v-model="form.rule_code" :disabled="Boolean(editingId)" placeholder="例如 DISTRIBUTION_LEVEL_1" />
            </el-form-item>
            <el-form-item label="规则名称">
              <el-input v-model="form.rule_name" placeholder="例如 一级分销佣金" />
            </el-form-item>
          </div>

          <div class="form-split">
            <el-form-item label="规则类型">
              <el-select v-model="form.rule_type">
                <el-option v-for="item in ruleTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="适用对象">
              <el-select v-model="form.subject_type">
                <el-option v-for="item in subjectOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
          </div>

          <div class="form-split three">
            <el-form-item label="商品ID">
              <el-input-number v-model="form.product_id" :min="1" :step="1" controls-position="right" placeholder="为空表示通用" />
            </el-form-item>
            <el-form-item label="会员等级">
              <el-select v-model="form.member_level" clearable placeholder="不限制">
                <el-option v-for="item in memberLevelOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="佣金层级">
              <el-select v-model="form.commission_level" clearable placeholder="不限制">
                <el-option label="一级" :value="1" />
                <el-option label="二级" :value="2" />
                <el-option label="三级" :value="3" />
              </el-select>
            </el-form-item>
          </div>

          <div class="form-split">
            <el-form-item label="触发事件">
              <el-input v-model="form.trigger_event" placeholder="ORDER_COMPLETE / REPEAT_PURCHASE / DAILY_SETTLEMENT" />
            </el-form-item>
            <el-form-item label="计算方式">
              <el-select v-model="form.calculation_method">
                <el-option v-for="item in methodOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
          </div>

          <el-form-item label="计算基数">
            <el-input v-model="form.calculation_basis" placeholder="例如 商品利润、托管设备有效天数、月度净收益" />
          </el-form-item>

          <div class="form-split three">
            <el-form-item label="奖励比例%">
              <el-input-number v-model="form.reward_rate" :min="0" :max="100" :precision="4" :step="0.5" controls-position="right" />
            </el-form-item>
            <el-form-item label="固定金额">
              <el-input-number v-model="form.reward_amount" :min="0" :precision="2" :step="1" controls-position="right" />
            </el-form-item>
            <el-form-item label="封顶金额">
              <el-input-number v-model="form.cap_amount" :min="0" :precision="2" :step="100" controls-position="right" />
            </el-form-item>
          </div>

          <div class="form-split three">
            <el-form-item label="结算周期">
              <el-select v-model="form.settlement_cycle">
                <el-option v-for="item in cycleOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="延迟结算天数">
              <el-input-number v-model="form.settlement_delay_days" :min="0" :max="365" controls-position="right" />
            </el-form-item>
            <el-form-item label="冻结天数">
              <el-input-number v-model="form.freeze_days" :min="0" :max="365" controls-position="right" />
            </el-form-item>
          </div>

          <div class="form-split">
            <el-form-item label="资格等级">
              <el-input v-model="form.qualification_level" placeholder="SUPERVISOR / MANAGER / DIRECTOR" />
            </el-form-item>
            <el-form-item label="优先级">
              <el-input-number v-model="form.priority" :min="-10000" :max="10000" controls-position="right" />
            </el-form-item>
          </div>

          <el-form-item label="生效条件">
            <el-input v-model="form.min_condition" type="textarea" :rows="2" placeholder="例如 月度团队销售额达标、礼包为等值实物商品" />
          </el-form-item>

          <div class="form-split">
            <el-form-item label="生效时间">
              <el-date-picker v-model="form.valid_from" type="datetime" placeholder="不限" style="width: 100%" />
            </el-form-item>
            <el-form-item label="失效时间">
              <el-date-picker v-model="form.valid_to" type="datetime" placeholder="不限" style="width: 100%" />
            </el-form-item>
          </div>

          <el-form-item label="合规备注">
            <el-input v-model="form.compliance_note" type="textarea" :rows="3" placeholder="说明收益来源、审计要求、封顶或人工复核条件" />
          </el-form-item>
          <el-form-item label="运营备注">
            <el-input v-model="form.remark" type="textarea" :rows="2" />
          </el-form-item>
          <el-form-item label="启用">
            <el-switch v-model="form.is_active" />
          </el-form-item>
        </el-form>
        <div class="dialog-actions">
          <el-button @click="drawerVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="saveRule">保存规则</el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'

import { earningRuleApi } from '@/api/modules'

const rules = ref([])
const loading = ref(false)
const saving = ref(false)
const drawerVisible = ref(false)
const editingId = ref(null)
const statusSavingId = ref(null)
const filterType = ref('')
const filterActive = ref(null)
const form = ref(createForm())

const ruleTypeOptions = [
  { label: '会员等级', value: 'MEMBER_LEVEL' },
  { label: '直推/分销奖励', value: 'DIRECT_REWARD' },
  { label: '设备收益', value: 'DEVICE_INCOME' },
  { label: '团队奖励', value: 'TEAM_REWARD' },
  { label: '资金池分配', value: 'POOL_DISTRIBUTION' },
  { label: '补贴', value: 'SUBSIDY' },
  { label: '线下权益', value: 'OFFLINE_BENEFIT' }
]

const memberLevelOptions = [
  { label: '普通会员', value: 'NORMAL_MEMBER' },
  { label: 'VIP会员', value: 'VIP_MEMBER' },
  { label: '经销商', value: 'DEALER' },
  { label: '总经销商', value: 'MASTER_DEALER' }
]

const subjectOptions = [
  { label: '用户', value: 'USER' },
  { label: '团队', value: 'TEAM' },
  { label: '订单', value: 'ORDER' },
  { label: '设备', value: 'DEVICE' },
  { label: '资金池', value: 'POOL' },
  { label: '项目', value: 'PROJECT' }
]

const methodOptions = [
  { label: '固定金额', value: 'FIXED_AMOUNT' },
  { label: '按比例', value: 'RATE' },
  { label: '阶梯比例', value: 'TIERED_RATE' },
  { label: '权重资金池', value: 'WEIGHTED_POOL' },
  { label: '人工审核', value: 'MANUAL_AUDIT' }
]

const cycleOptions = [
  { label: '即时', value: 'IMMEDIATE' },
  { label: '每日', value: 'DAILY' },
  { label: '每周', value: 'WEEKLY' },
  { label: '半月', value: 'HALF_MONTHLY' },
  { label: '每月', value: 'MONTHLY' },
  { label: '每年', value: 'YEARLY' },
  { label: '人工', value: 'MANUAL' }
]

const drawerTitle = computed(() => (editingId.value ? '编辑收益规则' : '新增收益规则'))

const metrics = computed(() => {
  const activeCount = rules.value.filter((item) => item.is_active).length
  const directRules = rules.value.filter((item) => item.rule_type === 'DIRECT_REWARD').length
  const teamRules = rules.value.filter((item) => item.rule_type === 'TEAM_REWARD').length
  const memberRules = rules.value.filter((item) => item.rule_type === 'MEMBER_LEVEL').length
  return [
    { label: '规则总数', value: rules.value.length, subtext: `启用 ${activeCount} 条，停用 ${rules.value.length - activeCount} 条` },
    { label: '会员等级规则', value: memberRules, subtext: '用于记录激活和晋升条件' },
    { label: '分销奖励规则', value: directRules, subtext: '订单完成后按商品利润计提' },
    { label: '团队奖励规则', value: teamRules, subtext: '仅计算直接推荐团队' }
  ]
})

function createForm() {
  return {
    rule_code: '',
    rule_name: '',
    rule_type: 'DIRECT_REWARD',
    product_id: null,
    member_level: '',
    commission_level: null,
    subject_type: 'ORDER',
    trigger_event: 'ORDER_COMPLETE',
    calculation_basis: '',
    calculation_method: 'RATE',
    reward_rate: 0,
    reward_amount: 0,
    cap_amount: null,
    min_condition: '',
    qualification_level: '',
    settlement_cycle: 'IMMEDIATE',
    settlement_delay_days: 0,
    freeze_days: 0,
    priority: 0,
    is_active: false,
    compliance_note: '',
    remark: '',
    valid_from: null,
    valid_to: null
  }
}

function labelOf(options, value) {
  return options.find((item) => item.value === value)?.label || value || '--'
}

function amountText(value) {
  return Number(value || 0).toFixed(2)
}

function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '--'
}

function toPayload() {
  const payload = { ...form.value }
  payload.rule_code = String(payload.rule_code || '').trim().toUpperCase()
  payload.rule_name = String(payload.rule_name || '').trim()
  payload.rule_type = String(payload.rule_type || '').trim().toUpperCase()
  payload.member_level = payload.member_level ? String(payload.member_level).trim().toUpperCase() : null
  payload.trigger_event = String(payload.trigger_event || '').trim().toUpperCase()
  payload.calculation_basis = String(payload.calculation_basis || '').trim()
  payload.qualification_level = String(payload.qualification_level || '').trim().toUpperCase()
  payload.min_condition = String(payload.min_condition || '').trim()
  payload.compliance_note = String(payload.compliance_note || '').trim()
  payload.remark = String(payload.remark || '').trim()
  payload.product_id = payload.product_id || null
  payload.commission_level = payload.commission_level || null
  payload.cap_amount = payload.cap_amount === '' ? null : payload.cap_amount
  payload.valid_from = payload.valid_from ? new Date(payload.valid_from).toISOString() : null
  payload.valid_to = payload.valid_to ? new Date(payload.valid_to).toISOString() : null
  return payload
}

function validateForm(payload) {
  if (!payload.rule_name) return '请填写规则名称'
  if (!payload.rule_code && !editingId.value) return '请填写规则编码'
  if (!payload.trigger_event) return '请填写触发事件'
  if (!payload.calculation_basis) return '请填写计算基数'
  if (payload.reward_rate > 100) return '奖励比例不能超过 100%'
  if (payload.commission_level && (payload.commission_level < 1 || payload.commission_level > 3)) return '佣金层级只能是 1-3'
  return ''
}

async function loadRules() {
  loading.value = true
  try {
    const isActive = filterActive.value === null || filterActive.value === '' || filterActive.value === undefined
      ? undefined
      : filterActive.value
    const data = await earningRuleApi.list({
      rule_type: filterType.value || undefined,
      is_active: isActive
    })
    rules.value = data || []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.value = createForm()
  drawerVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  form.value = {
    ...createForm(),
    ...row,
    product_id: row.product_id ?? null,
    member_level: row.member_level || '',
    commission_level: row.commission_level ?? null,
    cap_amount: row.cap_amount ?? null,
    valid_from: row.valid_from ? new Date(row.valid_from) : null,
    valid_to: row.valid_to ? new Date(row.valid_to) : null
  }
  drawerVisible.value = true
}

async function saveRule() {
  const payload = toPayload()
  const error = validateForm(payload)
  if (error) {
    ElMessage.warning(error)
    return
  }

  saving.value = true
  try {
    if (editingId.value) {
      const updatePayload = { ...payload }
      delete updatePayload.rule_code
      await earningRuleApi.update(editingId.value, updatePayload)
      ElMessage.success('规则已更新')
    } else {
      await earningRuleApi.create(payload)
      ElMessage.success('规则已创建')
    }
    drawerVisible.value = false
    await loadRules()
  } finally {
    saving.value = false
  }
}

async function toggleStatus(row) {
  statusSavingId.value = row.id
  try {
    await earningRuleApi.updateStatus(row.id, { is_active: row.is_active })
    ElMessage.success(row.is_active ? '规则已启用' : '规则已停用')
  } catch (error) {
    row.is_active = !row.is_active
  } finally {
    statusSavingId.value = null
  }
}

async function removeRule(row) {
  await ElMessageBox.confirm(`确认删除收益规则 ${row.rule_code} 吗？`, '删除收益规则', { type: 'warning' })
  await earningRuleApi.remove(row.id)
  ElMessage.success('规则已删除')
  await loadRules()
}

onMounted(loadRules)
</script>

<style scoped>
.earning-rule-view {
  display: grid;
  gap: 18px;
}

.page-heading,
.metric-card,
.panel-card {
  border-radius: 18px;
  border: 1px solid rgba(255, 122, 0, 0.14);
  background: linear-gradient(180deg, #fffdfb 0%, #fff6ee 100%);
  box-shadow: 0 12px 28px rgba(255, 108, 46, 0.08);
}

.page-heading {
  padding: 20px 22px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.page-heading h2,
.section-title h3 {
  margin: 0;
  color: #4a2410;
}

.page-heading p,
.section-title p {
  color: #7b5e4b;
}

.toolbar-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.metric-card {
  padding: 18px;
}

.metric-card .label {
  color: #8b6a57;
}

.metric-card .value {
  margin-top: 8px;
  font-size: 28px;
  font-weight: 800;
  color: #ff6a00;
}

.metric-card .subtext {
  margin-top: 8px;
  color: #8d6f5a;
}

.panel-card {
  padding: 20px;
}

.block-gap {
  margin-top: 18px;
}

.form-alert {
  margin-bottom: 16px;
}

.form-split {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.form-split.three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 18px;
}

@media (max-width: 1200px) {
  .metric-grid,
  .form-split,
  .form-split.three {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .page-heading {
    align-items: stretch;
    flex-direction: column;
  }

  .metric-grid,
  .form-split,
  .form-split.three {
    grid-template-columns: 1fr;
  }
}
</style>
