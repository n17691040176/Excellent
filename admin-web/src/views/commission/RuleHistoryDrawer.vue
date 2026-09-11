<template>
  <el-drawer :model-value="modelValue" title="规则修改记录" size="80%" @update:model-value="$emit('update:modelValue', $event)">
    <el-table v-loading="loading" :data="items" row-key="id">
      <el-table-column type="expand">
        <template #default="{ row }">
          <el-table :data="changes(row)" size="small">
            <el-table-column prop="label" label="配置项" />
            <el-table-column prop="before" label="修改前" />
            <el-table-column prop="after" label="修改后" />
          </el-table>
        </template>
      </el-table-column>
      <el-table-column label="修改时间" min-width="175"><template #default="{ row }">{{ formatDateTime(row.created_at) }}</template></el-table-column>
      <el-table-column prop="operator_name" label="操作人" min-width="130" />
      <el-table-column prop="reason" label="原因" min-width="180" />
      <el-table-column prop="rule_version" label="规则版本" min-width="250" show-overflow-tooltip />
    </el-table>
    <el-pagination v-model:current-page="page" :page-size="20" :total="total" layout="total, prev, pager, next" @current-change="load" />
  </el-drawer>
</template>
<script setup>
import { ref, watch } from 'vue'
import { commissionApi } from '@/api/modules'
import { formatDateTime } from '@/utils/datetime'
const props = defineProps({ modelValue: Boolean, entityId: Number, entityType: String })
defineEmits(['update:modelValue'])
const loading = ref(false), items = ref([]), page = ref(1), total = ref(0)
const labels = {
  province: '省', city: '市', initial_price: '初始价格', current_price: '购买报价',
  price_growth_rate: '增长比例（%）', price_cap: '价格上限', status: '席位状态',
  _sale_price: '商品售价', _cost_price: '商品成本',
  city_partner_commission_enabled: '参与城市合伙人分润', city_partner_amount: '城市合伙人金额',
  city_partner_direct_reward_amount: '直推奖金额', city_partner_upline_initial_amount: '上级起始金额',
  city_partner_upline_max_levels: '上级层数', city_partner_upline_decay_rate: '层级递减比例（%）',
  city_partner_remainder_account: '尾差账户', custom_commission_enabled: '原模式专属分润',
  custom_commission_method: '原模式分润方式'
}
for (const [role, label] of Object.entries({ level1: '普通会员', level2: '经销商', county_agent: '区代理', city_agent: '市代理' })) {
  for (const [field, suffix] of Object.entries({ enabled: '启用', rate: '比例（%）', amount: '固定金额' })) labels[`custom_commission_${role}_${field}`] = `${label}${suffix}`
}
function value(v) {
  if (v == null) return '未设置'
  if (typeof v === 'boolean') return v ? '是' : '否'
  return ({ COMPANY: '公司', ACTIVE: '启用', INACTIVE: '停用', RATE: '比例', FIXED_AMOUNT: '固定金额' })[v] || String(v)
}
function changes(row) {
  return Object.entries(labels).filter(([key]) => row.before_values[key] !== row.after_values[key]).map(([key, label]) => ({ label, before: value(row.before_values[key]), after: value(row.after_values[key]) }))
}
async function load() {
  loading.value = true
  try { const data = await commissionApi.ruleHistory(props.entityType, props.entityId, { page: page.value }); items.value = data.items; total.value = data.total } finally { loading.value = false }
}
watch(() => [props.modelValue, props.entityId, props.entityType], () => { if (props.modelValue && props.entityId) { page.value = 1; load() } })
</script>
