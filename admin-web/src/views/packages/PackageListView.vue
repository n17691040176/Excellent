<template>
  <div class="packages-view">
    <div class="page-heading">
      <div>
        <h2>套餐管理</h2>
        <p>维护套餐价格、抵扣比例、赠券规则和上架资格来源。</p>
      </div>
      <div class="toolbar-row">
        <el-button type="primary" plain @click="loadData">刷新数据</el-button>
        <el-button v-permission="'packages:create'" type="primary" @click="openCreate">新增套餐</el-button>
      </div>
    </div>

    <div class="panel-card data-card block-gap">
      <el-table :data="packages" border>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="package_name" label="套餐名称" min-width="180" />
        <el-table-column prop="package_type" label="套餐类型" min-width="120" />
        <el-table-column prop="package_price" label="套餐价格" width="120" />
        <el-table-column prop="voucher_reward_rate" label="购买赠券%" width="120" />
        <el-table-column prop="referral_voucher_rate" label="推荐赠券%" width="120" />
        <el-table-column prop="ai_coupon_max_deduct_rate" label="AI抵扣%" width="120" />
        <el-table-column prop="grants_product_quota" label="上架额度" width="100" />
        <el-table-column label="积分补贴" width="100">
          <template #default="scope">{{ scope.row.points_subsidy_enabled ? '开启' : '关闭' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="scope">
            <el-tag :type="statusType(scope.row.status)">{{ statusLabel(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="260" fixed="right">
          <template #default="scope">
            <el-button v-permission="'packages:edit'" link type="primary" @click="openEdit(scope.row)">编辑</el-button>
            <el-button v-permission="'packages:shelf'" link type="success" :disabled="!canShelfUp(scope.row)" @click="updateStatus(scope.row, 'ON_SHELF')">上架</el-button>
            <el-button v-permission="'packages:shelf'" link type="info" :disabled="!canShelfDown(scope.row)" @click="updateStatus(scope.row, 'OFF_SHELF')">下架</el-button>
            <el-button v-permission="'packages:edit'" link type="danger" :disabled="scope.row.status === 'ON_SHELF'" @click="removePackage(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="panel-card data-card">
      <div class="section-title-lite">
        <h3>我的套餐资格</h3>
        <p>用于核查复购区准入与商品上架资格来源。</p>
      </div>
      <el-table :data="qualifications" border>
        <el-table-column prop="order_id" label="订单 ID" width="90" />
        <el-table-column prop="package_name" label="套餐名称" min-width="160" />
        <el-table-column prop="paid_amount" label="支付金额" width="120" />
        <el-table-column prop="grants_product_quota" label="上架额度" width="100" />
        <el-table-column prop="order_status" label="订单状态" width="120" />
        <el-table-column prop="paid_at" label="支付时间" min-width="180" />
      </el-table>
    </div>

    <el-drawer v-model="dialogVisible" :title="dialogTitle" size="520px">
      <div class="panel-card data-card">
        <el-form label-position="top" :model="form">
          <el-form-item label="套餐名称">
            <el-input v-model="form.package_name" placeholder="请输入套餐名称" />
          </el-form-item>
          <div class="form-split">
            <el-form-item label="套餐类型">
              <el-input v-model="form.package_type" placeholder="如康养套餐 / 创客套餐" />
            </el-form-item>
            <el-form-item label="套餐价格">
              <el-input-number v-model="form.package_price" :min="0.01" :step="100" :precision="2" controls-position="right" />
            </el-form-item>
          </div>
          <div class="form-split">
            <el-form-item label="购买赠券%">
              <el-input-number v-model="form.voucher_reward_rate" :min="0" :max="100" :step="1" :precision="2" controls-position="right" />
            </el-form-item>
            <el-form-item label="推荐赠券%">
              <el-input-number v-model="form.referral_voucher_rate" :min="0" :max="100" :step="1" :precision="2" controls-position="right" />
            </el-form-item>
          </div>
          <div class="form-split">
            <el-form-item label="AI抵扣%">
              <el-input-number v-model="form.ai_coupon_max_deduct_rate" :min="0" :max="100" :step="1" :precision="2" controls-position="right" />
            </el-form-item>
            <el-form-item label="上架额度">
              <el-input-number v-model="form.grants_product_quota" :min="0" :step="1" controls-position="right" />
            </el-form-item>
          </div>
          <el-form-item label="积分补贴">
            <el-switch v-model="form.points_subsidy_enabled" />
          </el-form-item>
        </el-form>
        <div class="config-tips">
          <div>套餐新增后默认以草稿状态保存，运营确认后再上架。</div>
          <div>当前套餐配置会影响 AI 券抵扣、购买赠券、推荐赠券和复购区资格发放。</div>
        </div>
        <div class="dialog-actions">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="savePackage">保存套餐</el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { packageApi } from '@/api/modules'

const packages = ref([])
const qualifications = ref([])
const dialogVisible = ref(false)
const saving = ref(false)
const editingId = ref(null)
const form = ref(createDefaultForm())

function createDefaultForm() {
  return {
    package_name: '',
    package_price: 5500,
    package_type: '康养套餐',
    voucher_reward_rate: 100,
    referral_voucher_rate: 50,
    ai_coupon_max_deduct_rate: 20,
    grants_product_quota: 1,
    points_subsidy_enabled: true
  }
}

const dialogTitle = computed(() => (editingId.value ? '编辑套餐' : '新增套餐'))

function statusType(status) {
  return {
    DRAFT: 'info',
    ON_SHELF: 'success',
    OFF_SHELF: 'warning',
    APPROVED: 'success'
  }[status] || 'info'
}

function statusLabel(status) {
  return {
    DRAFT: '草稿',
    ON_SHELF: '已上架',
    OFF_SHELF: '已下架',
    APPROVED: '已通过'
  }[status] || status || '--'
}

function canShelfUp(row) {
  return ['DRAFT', 'OFF_SHELF', 'APPROVED'].includes(row.status)
}

function canShelfDown(row) {
  return row.status === 'ON_SHELF'
}

function normalizeForm(row = {}) {
  return {
    package_name: row.package_name || '',
    package_price: row.package_price == null ? 0 : Number(row.package_price),
    package_type: row.package_type || '',
    voucher_reward_rate: row.voucher_reward_rate == null ? 100 : Number(row.voucher_reward_rate),
    referral_voucher_rate: row.referral_voucher_rate == null ? 50 : Number(row.referral_voucher_rate),
    ai_coupon_max_deduct_rate: row.ai_coupon_max_deduct_rate == null ? 20 : Number(row.ai_coupon_max_deduct_rate),
    grants_product_quota: row.grants_product_quota == null ? 0 : Number(row.grants_product_quota),
    points_subsidy_enabled: Boolean(row.points_subsidy_enabled)
  }
}

async function loadData() {
  packages.value = await packageApi.list()
  qualifications.value = await packageApi.qualifications()
}

function openCreate() {
  editingId.value = null
  form.value = createDefaultForm()
  dialogVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  form.value = normalizeForm(row)
  dialogVisible.value = true
}

async function savePackage() {
  if (!form.value.package_name.trim()) return ElMessage.warning('请先填写套餐名称')
  saving.value = true
  try {
    if (editingId.value) {
      await packageApi.update(editingId.value, form.value)
      ElMessage.success('套餐已更新')
    } else {
      await packageApi.create(form.value)
      ElMessage.success('套餐已创建')
    }
    dialogVisible.value = false
    await loadData()
  } finally {
    saving.value = false
  }
}

async function updateStatus(row, status) {
  const label = status === 'ON_SHELF' ? '上架' : '下架'
  await ElMessageBox.confirm(`确认${label}套餐“${row.package_name}”吗？`, '套餐状态', { type: 'warning' })
  await packageApi.updateStatus(row.id, { status })
  ElMessage.success(`套餐已${label}`)
  await loadData()
}

async function removePackage(row) {
  await ElMessageBox.confirm(`确认删除套餐“${row.package_name}”吗？删除后不可恢复。`, '删除套餐', { type: 'warning' })
  await packageApi.remove(row.id)
  ElMessage.success('套餐已删除')
  await loadData()
}

onMounted(loadData)
</script>

<style scoped>
.packages-view {
  display: grid;
  gap: 18px;
}

.block-gap {
  margin-bottom: 18px;
}

.section-title-lite {
  margin-bottom: 14px;
}

.section-title-lite h3 {
  margin: 0;
  font-size: 22px;
  color: var(--brand-deep);
}

.section-title-lite p {
  margin: 6px 0 0;
  color: rgba(58, 45, 36, 0.62);
}

.form-split {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.config-tips {
  margin-top: 12px;
  padding: 14px 16px;
  background: rgba(198, 132, 79, 0.1);
  border-radius: 14px;
  color: rgba(58, 45, 36, 0.78);
  line-height: 1.7;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 18px;
}

@media (max-width: 900px) {
  .form-split {
    grid-template-columns: 1fr;
  }
}
</style>
