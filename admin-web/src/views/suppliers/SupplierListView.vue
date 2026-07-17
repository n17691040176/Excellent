<template>
  <div class="supplier-view">
    <!-- 统一页面头部 -->
    <PageHeader title="招商中心" :description="scopeHint">
      <template #actions>
        <el-button type="primary" @click="loadData">刷新数据</el-button>
      </template>
    </PageHeader>

    <!-- 指标卡片行 -->
    <div class="metric-grid">
      <MetricCard
        v-for="item in metrics"
        :key="item.label"
        :value="item.value"
        :label="item.label"
        :subtext="item.subtext"
        :variant="item.variant"
      />
    </div>

    <!-- 准入要求与四区商品分布 -->
    <div class="split-grid">
      <div class="panel-card data-card">
        <div class="section-title-lite">
          <h3>准入要求</h3>
          <p>供应商、区县代理、市代理都必须满足协议、价格红线和一件代发规则。</p>
        </div>
        <div class="notice-list">
          <div class="notice-item"><strong>供应商入场费</strong>基础入场费 500 元；若主推产品价格高于 500 元，则按实际整数金额收取。</div>
          <div class="notice-item"><strong>推荐奖励</strong>会员推荐供应商成功入驻，可获得入场费 15% 奖励。</div>
          <div class="notice-item"><strong>代理额度</strong>区县代理最多 2 款、市代理最多 5 款，且必须协议生效后方可占用额度。</div>
        </div>
      </div>

      <div class="panel-card data-card">
        <div class="section-title-lite">
          <h3>四区商品分布</h3>
          <p>这里只看供给规模；商品新增、导入、上下架和专区规则都已迁到商品管理页。</p>
        </div>
        <div class="tiny-stat-grid">
          <div v-for="item in zoneStats" :key="item.title" class="tiny-stat">
            <div class="title">{{ item.title }}</div>
            <div class="number">{{ item.count }}</div>
            <div class="meta">{{ item.meta }}</div>
          </div>
        </div>
        <el-button type="primary" plain size="small" style="margin-top: var(--space-4);" @click="openProductPage">进入商品管理</el-button>
      </div>
    </div>

    <!-- 供应商与资格管理 -->
    <div class="panel-card data-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="供应商列表" name="suppliers">
          <div class="toolbar-row">
            <el-input v-model="keyword" placeholder="搜索供应商名称 / 联系人" clearable style="max-width: 300px;" />
            <el-select v-model="statusFilter" placeholder="审核状态" clearable style="width: 180px;">
              <el-option label="待审核" value="PENDING" />
              <el-option label="已通过" value="APPROVED" />
              <el-option label="已驳回" value="REJECTED" />
              <el-option label="已启用" value="ACTIVE" />
            </el-select>
          </div>

          <el-table :data="pagedSuppliers" border>
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="supplier_name" label="供应商名称" min-width="180" />
            <el-table-column label="联系人" min-width="150">
              <template #default="{ row }">
                <div>{{ row.contact_name }}</div>
                <div class="cell-meta">{{ row.contact_phone }}</div>
              </template>
            </el-table-column>
            <el-table-column label="入场费" width="150">
              <template #default="{ row }">
                <div>{{ formatMoney(row.entry_fee_amount) }}</div>
                <el-tag size="small" :type="entryOrderType(row.latest_entry_order_status)">{{ entryOrderLabel(row.latest_entry_order_status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="协议状态" min-width="170">
              <template #default="{ row }">
                <StatusTag :status="row.active_agreement ? 'ACTIVE' : 'PENDING'" :label="row.active_agreement ? '协议有效' : '缺少有效协议'" type="agreement" />
                <div class="cell-meta">{{ row.agreement_type || '未上传协议' }}</div>
              </template>
            </el-table-column>
            <el-table-column label="资格统计" min-width="150">
              <template #default="{ row }">
                <div>已通过 {{ row.approved_qualification_count || 0 }}</div>
                <div class="cell-meta">待审核 {{ row.pending_qualification_count || 0 }}</div>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <StatusTag :status="row.status" type="supplier" />
              </template>
            </el-table-column>
            <el-table-column prop="qualification_desc" label="资质说明" min-width="220" show-overflow-tooltip />
          </el-table>

          <el-pagination v-model:current-page="page" v-model:page-size="pageSize" layout="total, prev, pager, next" :total="filteredSuppliers.length" />
        </el-tab-pane>

        <el-tab-pane label="上架资格" name="qualifications">
          <el-table :data="qualifications" border>
            <el-table-column prop="id" label="申请 ID" width="90" />
            <el-table-column label="商品 / 申请人" min-width="220">
              <template #default="{ row }">
                <div>{{ row.product_name || `商品#${row.product_id}` }}</div>
                <div class="cell-meta">用户 {{ row.applicant_user_id }} / {{ row.applicant_phone || '--' }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="supplier_name" label="关联供应商" min-width="150" />
            <el-table-column label="资格类型" min-width="140">
              <template #default="{ row }"><el-tag size="small" effect="plain">{{ row.qualification_type_label || row.qualification_type }}</el-tag></template>
            </el-table-column>
            <el-table-column label="资格来源" min-width="240">
              <template #default="{ row }">
                <div>{{ row.source_summary || '--' }}</div>
                <div class="cell-meta">来源 ID：{{ row.source_ref_id || '--' }}</div>
              </template>
            </el-table-column>
            <el-table-column label="来源状态" min-width="140">
              <template #default="{ row }">
                <el-tag size="small" :type="sourceStatusType(row)">{{ row.source_status || '--' }}</el-tag>
                <div class="cell-meta">{{ row.agreement_active ? '协议有效' : '协议待补' }}</div>
              </template>
            </el-table-column>
            <el-table-column label="额度消耗" width="130">
              <template #default="{ row }"><el-tag size="small" :type="quotaTagType(row)">{{ quotaText(row) }}</el-tag></template>
            </el-table-column>
            <el-table-column label="商品合规" min-width="220">
              <template #default="{ row }">
                <el-tag size="small" :type="complianceType(row.product_compliance)">{{ row.product_compliance?.drop_shipping_enabled ? '支持一件代发' : '未开一件代发' }}</el-tag>
                <div class="cell-meta">{{ row.product_compliance_summary || '--' }}</div>
              </template>
            </el-table-column>
            <el-table-column label="绑定归属" min-width="150">
              <template #default="{ row }">
                <div>{{ ownerTypeLabel(row.product_owner_type) }}</div>
                <div class="cell-meta">ID: {{ row.product_owner_id || '--' }}</div>
              </template>
            </el-table-column>
            <el-table-column label="审核状态" width="120">
              <template #default="{ row }">
                <StatusTag :status="row.audit_status" type="audit" />
              </template>
            </el-table-column>
            <el-table-column prop="audit_remark" label="审核备注" min-width="180" show-overflow-tooltip />
            <el-table-column label="申请时间" min-width="170">
              <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <el-button link type="success" :disabled="row.audit_status !== 'PENDING'" @click="reviewQualification(row, 'APPROVED')">通过</el-button>
                <el-button link type="danger" :disabled="row.audit_status !== 'PENDING'" @click="reviewQualification(row, 'REJECTED')">驳回</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="资格台账" name="qualification-ledgers">
          <el-table :data="qualificationLedgers" border>
            <el-table-column prop="id" label="台账 ID" width="90" />
            <el-table-column label="商品 / 申请人" min-width="230">
              <template #default="{ row }">
                <div>{{ row.product_name || `商品#${row.product_id}` }}</div>
                <div class="cell-meta">用户 {{ row.applicant_user_id }} / {{ row.applicant_phone || '--' }}</div>
              </template>
            </el-table-column>
            <el-table-column label="资格来源" min-width="250">
              <template #default="{ row }">
                <div>{{ row.qualification_type_label }}</div>
                <div class="cell-meta">{{ row.source_summary || '--' }}</div>
              </template>
            </el-table-column>
            <el-table-column label="占用状态" width="120">
              <template #default="{ row }"><el-tag size="small" :type="row.occupancy_active ? 'success' : 'info'">{{ row.occupancy_status_label }}</el-tag></template>
            </el-table-column>
            <el-table-column label="占用窗口" min-width="180">
              <template #default="{ row }">
                <div>{{ formatDate(row.occupied_at) }}</div>
                <div class="cell-meta">释放：{{ formatDate(row.released_at) }}</div>
              </template>
            </el-table-column>
            <el-table-column label="额度情况" width="130">
              <template #default="{ row }"><el-tag size="small" :type="quotaTagType(row)">{{ quotaText(row) }}</el-tag></template>
            </el-table-column>
            <el-table-column label="绑定归属" min-width="150">
              <template #default="{ row }">
                <el-tag size="small" :type="row.owner_bound ? 'success' : 'warning'">{{ row.owner_bound_label }}</el-tag>
                <div class="cell-meta">{{ ownerTypeLabel(row.product_owner_type) }} / ID: {{ row.product_owner_id || '--' }}</div>
              </template>
            </el-table-column>
            <el-table-column label="商品状态" width="120">
              <template #default="{ row }">
                <StatusTag :status="row.product_status" type="product" />
              </template>
            </el-table-column>
            <el-table-column label="备注" min-width="220" show-overflow-tooltip>
              <template #default="{ row }">{{ row.release_reason || row.audit_remark || '--' }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="专区商品" name="zones">
          <div class="panel-card data-card">
            <div class="section-title-lite">
              <h3>商品入口已独立</h3>
              <p>商品列表、移动端字段、Excel 导入和专区规则已迁到"商品管理"页面统一维护。</p>
            </div>
            <div class="notice-list">
              <div class="notice-item"><strong>当前页面保留</strong>供应商准入、资格申请、资格台账和四区供给概览。</div>
              <div class="notice-item"><strong>建议路径</strong>新增商品、批量导入、提审上架、专区规则配置统一在商品管理页处理。</div>
            </div>
            <el-button type="primary" style="margin-top: var(--space-4);" @click="openProductPage">进入商品管理</el-button>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'

import { productApi, supplierApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'
import { PageHeader, MetricCard, StatusTag } from '@/components/common'

const router = useRouter()
const userStore = useUserStore()
const suppliers = ref([])
const qualifications = ref([])
const qualificationLedgers = ref([])
const zoneCounts = ref({ REPURCHASE: 0, SELF_OPERATED: 0, HOT_SALE: 0, LOCAL_LIFE: 0 })
const activeTab = ref('suppliers')
const keyword = ref('')
const statusFilter = ref('')
const page = ref(1)
const pageSize = ref(8)

const zoneTabs = [
  { code: 'REPURCHASE', label: '复购区', desc: '康养套餐与二次复购商品。' },
  { code: 'SELF_OPERATED', label: '自营商城', desc: '支持兑换券和 AI 券规则。' },
  { code: 'HOT_SALE', label: '爆款区', desc: '积分或余额抢购活动商品。' },
  { code: 'LOCAL_LIFE', label: '本地生活', desc: '服务商品与线下核销场景。' }
]

const scopeHint = computed(() => (
  userStore.role === 'TEAM_ADMIN'
    ? '当前仅查看所属团队供应商、资格申请、资格台账和四区供给概览。'
    : '管理平台供应商准入、入场费规则、代理额度和四大专区供给结构。'
))

const metrics = computed(() => {
  const exhaustedCount = qualifications.value.filter((item) => item.source_quota_total != null && Number(item.source_quota_remaining || 0) <= 0).length
  const activeAgreementCount = suppliers.value.filter((item) => item.active_agreement).length
  const activeOccupancyCount = qualificationLedgers.value.filter((item) => item.occupancy_active).length
  const totalZoneProducts = Object.values(zoneCounts.value).reduce((sum, count) => sum + count, 0)
  return [
    { label: '供应商总数', value: suppliers.value.length, subtext: `已启用 ${suppliers.value.filter((item) => item.status === 'ACTIVE').length} 家`, variant: 'primary' },
    { label: '有效协议', value: activeAgreementCount, subtext: '协议有效后才能占用招商资格', variant: 'success' },
    { label: '待审资格', value: qualifications.value.filter((item) => item.audit_status === 'PENDING').length, subtext: '后台需重点核对来源与商品合规', variant: 'warning' },
    { label: '资格占用中', value: activeOccupancyCount, subtext: '含待审与已生效资格台账', variant: 'neutral' },
    { label: '额度已满', value: exhaustedCount, subtext: '套餐或代理额度已无剩余', variant: 'info' },
    { label: '四区商品池', value: totalZoneProducts, subtext: '商品维护已迁到商品管理页', variant: 'info' }
  ]
})

const zoneStats = computed(() => zoneTabs.map((item) => ({ title: item.label, count: zoneCounts.value[item.code] || 0, meta: item.desc })))
const filteredSuppliers = computed(() => suppliers.value.filter((item) => {
  const term = keyword.value.trim()
  return (!term || item.supplier_name?.includes(term) || item.contact_name?.includes(term)) && (!statusFilter.value || item.status === statusFilter.value)
}))
const pagedSuppliers = computed(() => filteredSuppliers.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value))

function openProductPage() {
  router.push('/products')
}

function entryOrderLabel(status) {
  return { CREATED: '待支付', PAID: '已支付', CANCELED: '已取消', REFUNDED: '已退款' }[status] || '无订单'
}

function entryOrderType(status) {
  return { CREATED: 'warning', PAID: 'success', CANCELED: 'info', REFUNDED: 'danger' }[status] || 'info'
}

function sourceStatusType(row) {
  if (!row.agreement_active) return 'warning'
  if (row.source_quota_total != null && Number(row.source_quota_remaining || 0) <= 0) return 'danger'
  if (row.source_status?.includes('有效') || row.source_status?.includes('已支付') || row.source_status?.includes('已缴')) return 'success'
  return 'info'
}

function quotaTagType(row) {
  if (row.source_quota_total == null) return 'info'
  return Number(row.source_quota_remaining || 0) <= 0 ? 'danger' : 'success'
}

function quotaText(row) {
  if (row.source_quota_total == null) return '非额度型'
  return `${row.source_quota_remaining || 0} / ${row.source_quota_total}`
}

function complianceType(compliance) {
  if (!compliance) return 'info'
  return compliance.drop_shipping_enabled && compliance.price_limit_ok ? 'success' : 'danger'
}

function ownerTypeLabel(type) {
  return { SELF_OPERATED: '平台自营', SUPPLIER: '供应商商品', LOCAL_MERCHANT: '本地商家' }[type] || type || '--'
}

function formatMoney(value) {
  return value == null ? '--' : `￥${Number(value).toFixed(2)}`
}

function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '--'
}

async function loadZoneStats() {
  const [repurchase, selfOperated, hotSale, localLife] = await Promise.all([
    productApi.repurchase(),
    productApi.selfOperated(),
    productApi.hotSale(),
    productApi.localLife()
  ])
  zoneCounts.value = {
    REPURCHASE: repurchase?.length || 0,
    SELF_OPERATED: selfOperated?.length || 0,
    HOT_SALE: hotSale?.length || 0,
    LOCAL_LIFE: localLife?.length || 0
  }
}

async function loadData() {
  const [supplierRows, qualificationRows, ledgerRows] = await Promise.all([
    supplierApi.list(),
    supplierApi.qualifications(),
    supplierApi.qualificationLedgers()
  ])
  suppliers.value = supplierRows || []
  qualifications.value = qualificationRows || []
  qualificationLedgers.value = ledgerRows || []
  await loadZoneStats()
}

async function reviewQualification(row, auditStatus) {
  const label = auditStatus === 'APPROVED' ? '通过' : '驳回'
  await ElMessageBox.confirm(`确认${label}该上架资格申请吗？`, '资格审核', { type: 'warning' })
  await supplierApi.auditQualification(row.id, { audit_status: auditStatus, audit_remark: auditStatus === 'APPROVED' ? '后台审核通过' : '后台审核驳回' })
  qualifications.value = await supplierApi.qualifications()
  qualificationLedgers.value = await supplierApi.qualificationLedgers()
  ElMessage.success(`已${label}申请`)
}

onMounted(loadData)
</script>

<style scoped>
@import '@/styles/variables.css';

.supplier-view {
  display: grid;
  gap: var(--space-4);
}

.section-title-lite {
  margin-bottom: var(--space-4);
}

.section-title-lite h3 {
  margin: 0;
  font-size: var(--text-xl);
  color: var(--text-primary);
}

.section-title-lite p {
  margin: var(--space-2) 0 0;
  color: var(--text-muted);
  line-height: var(--leading-relaxed);
}

.notice-list {
  display: grid;
  gap: var(--space-3);
}

.notice-item {
  padding: var(--space-3) var(--space-4);
  background: var(--primary-50);
  border-radius: var(--radius-lg);
  color: var(--text-secondary);
  line-height: var(--leading-relaxed);
}

.notice-item strong {
  color: var(--text-primary);
}

.tiny-stat-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
}

.tiny-stat {
  padding: var(--space-4);
  background: var(--primary-50);
  border-radius: var(--radius-lg);
  text-align: center;
}

.tiny-stat .title {
  color: var(--text-muted);
  font-size: var(--text-sm);
}

.tiny-stat .number {
  margin-top: var(--space-2);
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--primary-deep);
}

.tiny-stat .meta {
  margin-top: var(--space-1);
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.toolbar-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  align-items: center;
  margin-bottom: var(--space-4);
}

.cell-meta {
  margin-top: 4px;
  font-size: var(--text-xs);
  line-height: var(--leading-relaxed);
  color: var(--text-muted);
}

@media (max-width: 768px) {
  .tiny-stat-grid {
    grid-template-columns: 1fr;
  }
}
</style>
