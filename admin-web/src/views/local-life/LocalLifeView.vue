<template>
  <div class="local-life-view">
    <div class="page-heading">
      <div>
        <h2>本地生活</h2>
        <p>{{ scopeHint }}</p>
      </div>
      <div class="toolbar-row">
        <el-button type="primary" plain @click="loadData">刷新数据</el-button>
        <el-button v-if="activeTab === 'merchants'" v-permission="'local-life:create'" type="primary" @click="openMerchantCreate">新增商家</el-button>
        <el-button v-if="activeTab === 'stores'" v-permission="'local-life:create'" type="primary" @click="openStoreCreate">新增门店</el-button>
        <el-button v-if="activeTab === 'services'" v-permission="'local-life:create'" type="primary" @click="openServiceCreate">新增服务</el-button>
        <el-button v-if="activeTab === 'rules'" v-permission="'local-life:create'" type="primary" @click="openRuleCreate">新增规则</el-button>
      </div>
    </div>

    <div class="metric-grid">
      <div v-for="item in metrics" :key="item.label" class="metric-card">
        <div class="label">{{ item.label }}</div>
        <div class="value">{{ item.value }}</div>
        <div class="subtext">{{ item.subtext }}</div>
      </div>
    </div>

    <div class="split-grid block-gap">
      <div class="panel-card data-card">
        <div class="section-title">
          <div>
            <h3>核销中心</h3>
            <p>输入验证码完成核销，订单确认后同步触发分佣链路。</p>
          </div>
        </div>
        <el-form :inline="true" :model="verifyForm">
          <el-form-item label="核销码">
            <el-input v-model="verifyForm.verification_code" placeholder="请输入验证码" style="width: 220px;" />
          </el-form-item>
          <el-form-item>
            <el-button v-permission="'local-life:verify'" type="primary" @click="handleVerify">立即核销</el-button>
          </el-form-item>
        </el-form>
        <div class="notice-list">
          <div class="notice-item"><strong>联盟分佣</strong>区县代理、市代理、个人与商家均可按规则获得对应分佣。</div>
          <div class="notice-item"><strong>收益来源</strong>快充宝、手机设备与广告位收益统一沉淀在本地生活收益流水中。</div>
        </div>
      </div>

      <div class="panel-card data-card">
        <div class="section-title">
          <div>
            <h3>收益概览</h3>
            <p>设备收益与广告收益用于支撑余额分佣池。</p>
          </div>
        </div>
        <div class="tiny-stat-grid">
          <div class="tiny-stat">
            <div class="title">设备收益总额</div>
            <div class="number">{{ deviceRevenueTotal }}</div>
            <div class="meta">快充宝、手机设备等硬件收益</div>
          </div>
          <div class="tiny-stat">
            <div class="title">广告收益总额</div>
            <div class="number">{{ adRevenueTotal }}</div>
            <div class="meta">广告投放与门店宣传位收益</div>
          </div>
          <div class="tiny-stat">
            <div class="title">佣金规则数</div>
            <div class="number">{{ rules.length }}</div>
            <div class="meta">联盟分佣比例配置数量</div>
          </div>
        </div>
      </div>
    </div>

    <div class="panel-card data-card block-gap">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="商家列表" name="merchants">
          <el-table :data="merchants" border>
            <el-table-column prop="id" label="商家 ID" width="100" />
            <el-table-column prop="merchant_name" label="商家名称" min-width="180" />
            <el-table-column prop="category_name" label="分类" min-width="120" />
            <el-table-column prop="contact_phone" label="联系电话" min-width="140" />
            <el-table-column prop="city_code" label="城市编码" min-width="110" />
            <el-table-column label="状态" width="120">
              <template #default="scope"><el-tag :type="merchantStatusType(scope.row.status)">{{ merchantStatusLabel(scope.row.status) }}</el-tag></template>
            </el-table-column>
            <el-table-column label="操作" min-width="170" fixed="right">
              <template #default="scope">
                <el-button v-permission="'local-life:edit'" link type="primary" @click="openMerchantEdit(scope.row)">编辑</el-button>
                <el-button v-permission="'local-life:edit'" link type="danger" @click="removeMerchant(scope.row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="门店列表" name="stores">
          <el-table :data="stores" border>
            <el-table-column prop="id" label="门店 ID" width="100" />
            <el-table-column prop="merchant_id" label="商家 ID" width="100" />
            <el-table-column prop="store_name" label="门店名称" min-width="180" />
            <el-table-column prop="contact_phone" label="联系电话" min-width="140" />
            <el-table-column label="地址" min-width="220">
              <template #default="scope">{{ joinAddress(scope.row) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="120">
              <template #default="scope"><el-tag :type="scope.row.status === 'ACTIVE' ? 'success' : 'info'">{{ scope.row.status === 'ACTIVE' ? '启用' : '停用' }}</el-tag></template>
            </el-table-column>
            <el-table-column label="操作" min-width="170" fixed="right">
              <template #default="scope">
                <el-button v-permission="'local-life:edit'" link type="primary" @click="openStoreEdit(scope.row)">编辑</el-button>
                <el-button v-permission="'local-life:edit'" link type="danger" @click="removeStore(scope.row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="服务列表" name="services">
          <el-table :data="services" border>
            <el-table-column prop="id" label="服务 ID" width="100" />
            <el-table-column prop="merchant_id" label="商家 ID" width="100" />
            <el-table-column prop="store_id" label="门店 ID" width="100" />
            <el-table-column prop="service_name" label="服务名称" min-width="180" />
            <el-table-column prop="sale_price" label="售价" width="100" />
            <el-table-column prop="market_price" label="门市价" width="100" />
            <el-table-column prop="service_type" label="服务类型" min-width="120" />
            <el-table-column prop="verification_type" label="核销方式" min-width="120" />
            <el-table-column label="状态" width="120">
              <template #default="scope"><el-tag :type="scope.row.status === 'ON_SHELF' ? 'success' : 'info'">{{ scope.row.status === 'ON_SHELF' ? '已上架' : '已下架' }}</el-tag></template>
            </el-table-column>
            <el-table-column label="操作" min-width="170" fixed="right">
              <template #default="scope">
                <el-button v-permission="'local-life:edit'" link type="primary" @click="openServiceEdit(scope.row)">编辑</el-button>
                <el-button v-permission="'local-life:edit'" link type="danger" @click="removeService(scope.row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="核销订单" name="orders">
          <el-table :data="orders" border>
            <el-table-column prop="id" label="记录 ID" width="100" />
            <el-table-column prop="order_id" label="订单 ID" width="100" />
            <el-table-column prop="merchant_id" label="商家 ID" width="100" />
            <el-table-column prop="store_id" label="门店 ID" width="100" />
            <el-table-column prop="service_id" label="服务 ID" width="100" />
            <el-table-column prop="verification_code" label="核销码" min-width="160" />
            <el-table-column label="核销时间" min-width="170">
              <template #default="scope">{{ formatDate(scope.row.verified_at) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="联盟分佣规则" name="rules">
          <el-table :data="rules" border>
            <el-table-column prop="id" label="规则 ID" width="90" />
            <el-table-column prop="merchant_id" label="商家 ID" width="100" />
            <el-table-column prop="county_agent_rate" label="区县代理%" min-width="120" />
            <el-table-column prop="city_agent_rate" label="市代理%" min-width="110" />
            <el-table-column prop="user_rate" label="个人%" width="90" />
            <el-table-column prop="merchant_rate" label="商家%" width="90" />
            <el-table-column prop="device_rate" label="设备%" width="90" />
            <el-table-column prop="ad_rate" label="广告%" width="90" />
            <el-table-column label="启用" width="90">
              <template #default="scope">{{ scope.row.is_active ? '是' : '否' }}</template>
            </el-table-column>
            <el-table-column label="操作" min-width="170" fixed="right">
              <template #default="scope">
                <el-button v-permission="'local-life:edit'" link type="primary" @click="openRuleEdit(scope.row)">编辑</el-button>
                <el-button v-permission="'local-life:edit'" link type="danger" @click="removeRule(scope.row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="设备收益" name="device">
          <el-table :data="deviceRevenues" border>
            <el-table-column prop="id" label="流水 ID" width="100" />
            <el-table-column prop="device_type" label="设备类型" min-width="130" />
            <el-table-column prop="business_ref_no" label="业务单号" min-width="170" />
            <el-table-column prop="beneficiary_user_id" label="受益用户" width="110" />
            <el-table-column prop="amount" label="金额" width="100" />
            <el-table-column prop="source_desc" label="来源说明" min-width="180" show-overflow-tooltip />
            <el-table-column label="时间" min-width="170">
              <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="广告收益" name="ad">
          <el-table :data="adRevenues" border>
            <el-table-column prop="id" label="流水 ID" width="100" />
            <el-table-column prop="ad_ref_no" label="广告单号" min-width="170" />
            <el-table-column prop="beneficiary_user_id" label="受益用户" width="110" />
            <el-table-column prop="amount" label="金额" width="100" />
            <el-table-column prop="source_desc" label="来源说明" min-width="180" show-overflow-tooltip />
            <el-table-column label="时间" min-width="170">
              <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <el-drawer v-model="merchantDialogVisible" :title="merchantDialogTitle" size="520px">
      <div class="panel-card data-card">
        <el-form label-position="top" :model="merchantForm">
          <el-form-item label="商家名称"><el-input v-model="merchantForm.merchant_name" /></el-form-item>
          <div class="form-split">
            <el-form-item label="分类"><el-input v-model="merchantForm.category_name" /></el-form-item>
            <el-form-item label="联系电话"><el-input v-model="merchantForm.contact_phone" /></el-form-item>
          </div>
          <div class="form-split">
            <el-form-item label="城市编码"><el-input v-model="merchantForm.city_code" /></el-form-item>
            <el-form-item label="状态">
              <el-select v-model="merchantForm.status">
                <el-option label="待审核" value="PENDING" />
                <el-option label="已启用" value="ACTIVE" />
                <el-option label="已停用" value="DISABLED" />
              </el-select>
            </el-form-item>
          </div>
        </el-form>
        <div class="dialog-actions">
          <el-button @click="merchantDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="merchantSaving" @click="saveMerchant">保存商家</el-button>
        </div>
      </div>
    </el-drawer>

    <el-drawer v-model="storeDialogVisible" :title="storeDialogTitle" size="560px">
      <div class="panel-card data-card">
        <el-form label-position="top" :model="storeForm">
          <div class="form-split">
            <el-form-item label="商家 ID"><el-input-number v-model="storeForm.merchant_id" :min="1" controls-position="right" /></el-form-item>
            <el-form-item label="门店名称"><el-input v-model="storeForm.store_name" /></el-form-item>
          </div>
          <div class="form-split">
            <el-form-item label="联系电话"><el-input v-model="storeForm.contact_phone" /></el-form-item>
            <el-form-item label="状态">
              <el-select v-model="storeForm.status">
                <el-option label="启用" value="ACTIVE" />
                <el-option label="停用" value="DISABLED" />
              </el-select>
            </el-form-item>
          </div>
          <div class="form-split">
            <el-form-item label="省份"><el-input v-model="storeForm.province" /></el-form-item>
            <el-form-item label="城市"><el-input v-model="storeForm.city" /></el-form-item>
          </div>
          <div class="form-split">
            <el-form-item label="区县"><el-input v-model="storeForm.district" /></el-form-item>
            <el-form-item label="详细地址"><el-input v-model="storeForm.detail_address" /></el-form-item>
          </div>
        </el-form>
        <div class="dialog-actions">
          <el-button @click="storeDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="storeSaving" @click="saveStore">保存门店</el-button>
        </div>
      </div>
    </el-drawer>

    <el-drawer v-model="serviceDialogVisible" :title="serviceDialogTitle" size="560px">
      <div class="panel-card data-card">
        <el-form label-position="top" :model="serviceForm">
          <div class="form-split">
            <el-form-item label="商家 ID"><el-input-number v-model="serviceForm.merchant_id" :min="1" controls-position="right" /></el-form-item>
            <el-form-item label="门店 ID"><el-input-number v-model="serviceForm.store_id" :min="1" controls-position="right" /></el-form-item>
          </div>
          <el-form-item label="服务名称"><el-input v-model="serviceForm.service_name" /></el-form-item>
          <div class="form-split">
            <el-form-item label="售价"><el-input-number v-model="serviceForm.sale_price" :min="0.01" :step="1" :precision="2" controls-position="right" /></el-form-item>
            <el-form-item label="门市价"><el-input-number v-model="serviceForm.market_price" :min="0" :step="1" :precision="2" controls-position="right" /></el-form-item>
          </div>
          <div class="form-split">
            <el-form-item label="服务类型"><el-input v-model="serviceForm.service_type" /></el-form-item>
            <el-form-item label="核销方式"><el-input v-model="serviceForm.verification_type" /></el-form-item>
          </div>
          <el-form-item label="状态">
            <el-select v-model="serviceForm.status">
              <el-option label="已上架" value="ON_SHELF" />
              <el-option label="已下架" value="OFF_SHELF" />
            </el-select>
          </el-form-item>
        </el-form>
        <div class="dialog-actions">
          <el-button @click="serviceDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="serviceSaving" @click="saveService">保存服务</el-button>
        </div>
      </div>
    </el-drawer>

    <el-drawer v-model="ruleDialogVisible" :title="ruleDialogTitle" size="560px">
      <div class="panel-card data-card">
        <el-form label-position="top" :model="ruleForm">
          <el-form-item label="商家 ID"><el-input-number v-model="ruleForm.merchant_id" :min="1" controls-position="right" /></el-form-item>
          <div class="form-split">
            <el-form-item label="区县代理%"><el-input-number v-model="ruleForm.county_agent_rate" :min="0" :max="100" :step="0.5" :precision="2" controls-position="right" /></el-form-item>
            <el-form-item label="市代理%"><el-input-number v-model="ruleForm.city_agent_rate" :min="0" :max="100" :step="0.5" :precision="2" controls-position="right" /></el-form-item>
          </div>
          <div class="form-split">
            <el-form-item label="个人%"><el-input-number v-model="ruleForm.user_rate" :min="0" :max="100" :step="0.5" :precision="2" controls-position="right" /></el-form-item>
            <el-form-item label="商家%"><el-input-number v-model="ruleForm.merchant_rate" :min="0" :max="100" :step="0.5" :precision="2" controls-position="right" /></el-form-item>
          </div>
          <div class="form-split">
            <el-form-item label="设备%"><el-input-number v-model="ruleForm.device_rate" :min="0" :max="100" :step="0.5" :precision="2" controls-position="right" /></el-form-item>
            <el-form-item label="广告%"><el-input-number v-model="ruleForm.ad_rate" :min="0" :max="100" :step="0.5" :precision="2" controls-position="right" /></el-form-item>
          </div>
          <el-form-item label="启用"><el-switch v-model="ruleForm.is_active" /></el-form-item>
        </el-form>
        <div class="dialog-actions">
          <el-button @click="ruleDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="ruleSaving" @click="saveRule">保存规则</el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { formatDateTime } from '@/utils/datetime'
import { ElMessage, ElMessageBox } from 'element-plus'

import { localLifeApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const merchants = ref([])
const stores = ref([])
const services = ref([])
const orders = ref([])
const rules = ref([])
const deviceRevenues = ref([])
const adRevenues = ref([])
const activeTab = ref('merchants')
const verifyForm = reactive({ verification_code: '' })

const merchantDialogVisible = ref(false)
const merchantSaving = ref(false)
const merchantEditingId = ref(null)
const merchantForm = ref(createMerchantForm())

const storeDialogVisible = ref(false)
const storeSaving = ref(false)
const storeEditingId = ref(null)
const storeForm = ref(createStoreForm())

const serviceDialogVisible = ref(false)
const serviceSaving = ref(false)
const serviceEditingId = ref(null)
const serviceForm = ref(createServiceForm())

const ruleDialogVisible = ref(false)
const ruleSaving = ref(false)
const ruleEditingId = ref(null)
const ruleForm = ref(createRuleForm())

function createMerchantForm() {
  return { owner_user_id: null, merchant_name: '', category_name: '', contact_phone: '', city_code: '', status: 'PENDING' }
}

function createStoreForm() {
  return { merchant_id: null, store_name: '', contact_phone: '', province: '', city: '', district: '', detail_address: '', latitude: null, longitude: null, status: 'ACTIVE' }
}

function createServiceForm() {
  return { merchant_id: null, store_id: null, service_name: '', market_price: null, sale_price: 0, service_type: '', verification_type: 'QR_CODE', status: 'ON_SHELF' }
}

function createRuleForm() {
  return { merchant_id: null, county_agent_rate: 0, city_agent_rate: 0, user_rate: 0, merchant_rate: 0, device_rate: 0, ad_rate: 0, is_active: true }
}

const scopeHint = computed(() =>
  userStore.role === 'TEAM_ADMIN'
    ? '当前仅查看所属团队商家、门店、服务、核销订单与本团队收益流水。'
    : '聚合平台商家、门店、服务、核销订单与设备广告收益，服务百业联盟落地。'
)

const metrics = computed(() => [
  { label: '联盟商家', value: merchants.value.length, subtext: '已接入本地生活商户' },
  { label: '门店总数', value: stores.value.length, subtext: '可核销履约门店数量' },
  { label: '服务总数', value: services.value.length, subtext: '已配置到店服务商品' },
  { label: '收益流水', value: deviceRevenues.value.length + adRevenues.value.length, subtext: '设备收益与广告收益合计' }
])

const deviceRevenueTotal = computed(() => deviceRevenues.value.reduce((sum, item) => sum + Number(item.amount || 0), 0).toFixed(2))
const adRevenueTotal = computed(() => adRevenues.value.reduce((sum, item) => sum + Number(item.amount || 0), 0).toFixed(2))
const merchantDialogTitle = computed(() => (merchantEditingId.value ? '编辑商家' : '新增商家'))
const storeDialogTitle = computed(() => (storeEditingId.value ? '编辑门店' : '新增门店'))
const serviceDialogTitle = computed(() => (serviceEditingId.value ? '编辑服务' : '新增服务'))
const ruleDialogTitle = computed(() => (ruleEditingId.value ? '编辑分佣规则' : '新增分佣规则'))

function merchantStatusType(status) {
  return { ACTIVE: 'success', PENDING: 'warning', DISABLED: 'info' }[status] || 'info'
}

function merchantStatusLabel(status) {
  return { ACTIVE: '已启用', PENDING: '待审核', DISABLED: '已停用' }[status] || status || '--'
}

function formatDate(value) {
  return formatDateTime(value)
}

function joinAddress(row) {
  return [row.province, row.city, row.district, row.detail_address].filter(Boolean).join(' ')
}

function normalizeMerchantForm(row = {}) {
  return { owner_user_id: row.owner_user_id ?? null, merchant_name: row.merchant_name || '', category_name: row.category_name || '', contact_phone: row.contact_phone || '', city_code: row.city_code || '', status: row.status || 'PENDING' }
}

function normalizeStoreForm(row = {}) {
  return { merchant_id: row.merchant_id ?? null, store_name: row.store_name || '', contact_phone: row.contact_phone || '', province: row.province || '', city: row.city || '', district: row.district || '', detail_address: row.detail_address || '', latitude: row.latitude ?? null, longitude: row.longitude ?? null, status: row.status || 'ACTIVE' }
}

function normalizeServiceForm(row = {}) {
  return { merchant_id: row.merchant_id ?? null, store_id: row.store_id ?? null, service_name: row.service_name || '', market_price: row.market_price == null ? null : Number(row.market_price), sale_price: row.sale_price == null ? 0 : Number(row.sale_price), service_type: row.service_type || '', verification_type: row.verification_type || 'QR_CODE', status: row.status || 'ON_SHELF' }
}

function normalizeRuleForm(row = {}) {
  return { merchant_id: row.merchant_id ?? null, county_agent_rate: Number(row.county_agent_rate || 0), city_agent_rate: Number(row.city_agent_rate || 0), user_rate: Number(row.user_rate || 0), merchant_rate: Number(row.merchant_rate || 0), device_rate: Number(row.device_rate || 0), ad_rate: Number(row.ad_rate || 0), is_active: Boolean(row.is_active) }
}

async function loadData() {
  const [merchantRows, storeRows, serviceRows, orderRows, ruleRows, deviceRows, adRows] = await Promise.all([
    localLifeApi.merchants(),
    localLifeApi.stores(),
    localLifeApi.services(),
    localLifeApi.orders(),
    localLifeApi.rules(),
    localLifeApi.deviceRevenues(),
    localLifeApi.adRevenues()
  ])
  merchants.value = merchantRows || []
  stores.value = storeRows || []
  services.value = serviceRows || []
  orders.value = orderRows || []
  rules.value = ruleRows || []
  deviceRevenues.value = deviceRows || []
  adRevenues.value = adRows || []
}

async function handleVerify() {
  if (!verifyForm.verification_code) return
  await localLifeApi.verifyOrder({ verification_code: verifyForm.verification_code })
  ElMessage.success('核销成功')
  verifyForm.verification_code = ''
  await loadData()
}

function openMerchantCreate() {
  merchantEditingId.value = null
  merchantForm.value = createMerchantForm()
  merchantDialogVisible.value = true
}

function openMerchantEdit(row) {
  merchantEditingId.value = row.id
  merchantForm.value = normalizeMerchantForm(row)
  merchantDialogVisible.value = true
}

async function saveMerchant() {
  if (!merchantForm.value.merchant_name.trim()) return ElMessage.warning('请先填写商家名称')
  merchantSaving.value = true
  try {
    if (merchantEditingId.value) {
      await localLifeApi.updateMerchant(merchantEditingId.value, merchantForm.value)
      ElMessage.success('商家已更新')
    } else {
      await localLifeApi.createMerchant(merchantForm.value)
      ElMessage.success('商家已创建')
    }
    merchantDialogVisible.value = false
    await loadData()
  } finally {
    merchantSaving.value = false
  }
}

async function removeMerchant(row) {
  await ElMessageBox.confirm(`确认删除商家“${row.merchant_name}”吗？`, '删除商家', { type: 'warning' })
  await localLifeApi.removeMerchant(row.id)
  ElMessage.success('商家已删除')
  await loadData()
}

function openStoreCreate() {
  storeEditingId.value = null
  storeForm.value = createStoreForm()
  storeDialogVisible.value = true
}

function openStoreEdit(row) {
  storeEditingId.value = row.id
  storeForm.value = normalizeStoreForm(row)
  storeDialogVisible.value = true
}

async function saveStore() {
  if (!storeForm.value.store_name.trim() || !storeForm.value.merchant_id) return ElMessage.warning('请先填写门店名称和商家 ID')
  storeSaving.value = true
  try {
    if (storeEditingId.value) {
      await localLifeApi.updateStore(storeEditingId.value, storeForm.value)
      ElMessage.success('门店已更新')
    } else {
      await localLifeApi.createStore(storeForm.value)
      ElMessage.success('门店已创建')
    }
    storeDialogVisible.value = false
    await loadData()
  } finally {
    storeSaving.value = false
  }
}

async function removeStore(row) {
  await ElMessageBox.confirm(`确认删除门店“${row.store_name}”吗？`, '删除门店', { type: 'warning' })
  await localLifeApi.removeStore(row.id)
  ElMessage.success('门店已删除')
  await loadData()
}

function openServiceCreate() {
  serviceEditingId.value = null
  serviceForm.value = createServiceForm()
  serviceDialogVisible.value = true
}

function openServiceEdit(row) {
  serviceEditingId.value = row.id
  serviceForm.value = normalizeServiceForm(row)
  serviceDialogVisible.value = true
}

async function saveService() {
  if (!serviceForm.value.service_name.trim() || !serviceForm.value.merchant_id) return ElMessage.warning('请先填写服务名称和商家 ID')
  serviceSaving.value = true
  try {
    if (serviceEditingId.value) {
      await localLifeApi.updateService(serviceEditingId.value, serviceForm.value)
      ElMessage.success('服务已更新')
    } else {
      await localLifeApi.createService(serviceForm.value)
      ElMessage.success('服务已创建')
    }
    serviceDialogVisible.value = false
    await loadData()
  } finally {
    serviceSaving.value = false
  }
}

async function removeService(row) {
  await ElMessageBox.confirm(`确认删除服务“${row.service_name}”吗？`, '删除服务', { type: 'warning' })
  await localLifeApi.removeService(row.id)
  ElMessage.success('服务已删除')
  await loadData()
}

function openRuleCreate() {
  ruleEditingId.value = null
  ruleForm.value = createRuleForm()
  ruleDialogVisible.value = true
}

function openRuleEdit(row) {
  ruleEditingId.value = row.id
  ruleForm.value = normalizeRuleForm(row)
  ruleDialogVisible.value = true
}

async function saveRule() {
  ruleSaving.value = true
  try {
    if (ruleEditingId.value) {
      await localLifeApi.updateRule(ruleEditingId.value, ruleForm.value)
      ElMessage.success('规则已更新')
    } else {
      await localLifeApi.createRule(ruleForm.value)
      ElMessage.success('规则已创建')
    }
    ruleDialogVisible.value = false
    await loadData()
  } finally {
    ruleSaving.value = false
  }
}

async function removeRule(row) {
  await ElMessageBox.confirm(`确认删除规则 ${row.id} 吗？`, '删除规则', { type: 'warning' })
  await localLifeApi.removeRule(row.id)
  ElMessage.success('规则已删除')
  await loadData()
}

onMounted(loadData)
</script>

<style scoped>
.local-life-view {
  display: grid;
  gap: 18px;
}

.block-gap {
  margin-top: 18px;
}

.form-split {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
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
