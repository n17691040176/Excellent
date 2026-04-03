<template>
  <div>
    <div class="page-heading">
      <div>
        <h2>招商中心</h2>
        <p>{{ scopeHint }}</p>
      </div>
      <el-button type="primary" @click="loadData">刷新数据</el-button>
    </div>

    <div class="metric-grid">
      <div v-for="item in metrics" :key="item.label" class="metric-card">
        <div class="label">{{ item.label }}</div>
        <div class="value">{{ item.value }}</div>
        <div class="subtext">{{ item.subtext }}</div>
      </div>
    </div>

    <div class="split-grid" style="margin-top: 18px;">
      <div class="panel-card data-card">
        <div class="section-title">
          <div>
            <h3>准入要求</h3>
            <p>供应商、区县代理、市代理都必须满足协议、价格红线和一件代发规则。</p>
          </div>
        </div>
        <div class="notice-list">
          <div class="notice-item"><strong>供应商入场费</strong>基础入场费 500 元；若主推产品价格高于 500 元，则按实际整数金额收取。</div>
          <div class="notice-item"><strong>推荐奖励</strong>会员推荐供应商成功入驻，可获得入场费 15% 奖励。</div>
          <div class="notice-item"><strong>代理额度</strong>区县代理最多 2 款、市代理最多 5 款，且必须协议生效后方可占用额度。</div>
        </div>
      </div>

      <div class="panel-card data-card">
        <div class="section-title">
          <div>
            <h3>四区商品分布</h3>
            <p>快速查看复购区、自营商城、爆款区、本地生活的当前供给情况。</p>
          </div>
        </div>
        <div class="tiny-stat-grid">
          <div v-for="item in zoneStats" :key="item.title" class="tiny-stat">
            <div class="title">{{ item.title }}</div>
            <div class="number">{{ item.count }}</div>
            <div class="meta">{{ item.meta }}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="panel-card data-card" style="margin-top: 18px;">
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
              <template #default="scope">
                <div>{{ scope.row.contact_name }}</div>
                <div class="cell-meta">{{ scope.row.contact_phone }}</div>
              </template>
            </el-table-column>
            <el-table-column label="入场费" width="150">
              <template #default="scope">
                <div>{{ formatMoney(scope.row.entry_fee_amount) }}</div>
                <el-tag size="small" :type="entryOrderType(scope.row.latest_entry_order_status)">
                  {{ entryOrderLabel(scope.row.latest_entry_order_status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="协议状态" min-width="170">
              <template #default="scope">
                <el-tag size="small" :type="scope.row.active_agreement ? 'success' : 'warning'">
                  {{ scope.row.active_agreement ? '协议有效' : '缺少有效协议' }}
                </el-tag>
                <div class="cell-meta">{{ scope.row.agreement_type || '未上传协议' }}</div>
              </template>
            </el-table-column>
            <el-table-column label="资格统计" min-width="150">
              <template #default="scope">
                <div>已通过 {{ scope.row.approved_qualification_count || 0 }}</div>
                <div class="cell-meta">待审核 {{ scope.row.pending_qualification_count || 0 }}</div>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="120">
              <template #default="scope">
                <el-tag :type="statusType(scope.row.status)">{{ statusLabel(scope.row.status) }}</el-tag>
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
              <template #default="scope">
                <div>{{ scope.row.product_name || `商品#${scope.row.product_id}` }}</div>
                <div class="cell-meta">用户 {{ scope.row.applicant_user_id }} / {{ scope.row.applicant_phone || '--' }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="supplier_name" label="关联供应商" min-width="150" />
            <el-table-column label="资格类型" min-width="140">
              <template #default="scope">
                <el-tag size="small" effect="plain">{{ scope.row.qualification_type_label || scope.row.qualification_type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="资格来源" min-width="240">
              <template #default="scope">
                <div>{{ scope.row.source_summary || '--' }}</div>
                <div class="cell-meta">来源 ID：{{ scope.row.source_ref_id || '--' }}</div>
              </template>
            </el-table-column>
            <el-table-column label="来源状态" min-width="140">
              <template #default="scope">
                <el-tag size="small" :type="sourceStatusType(scope.row)">{{ scope.row.source_status || '--' }}</el-tag>
                <div class="cell-meta">{{ scope.row.agreement_active ? '协议有效' : '协议待补' }}</div>
              </template>
            </el-table-column>
            <el-table-column label="额度消耗" width="130">
              <template #default="scope">
                <el-tag size="small" :type="quotaTagType(scope.row)">{{ quotaText(scope.row) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="商品合规" min-width="220">
              <template #default="scope">
                <el-tag size="small" :type="complianceType(scope.row.product_compliance)">
                  {{ scope.row.product_compliance?.drop_shipping_enabled ? '支持一件代发' : '未开一件代发' }}
                </el-tag>
                <div class="cell-meta">{{ scope.row.product_compliance_summary || '--' }}</div>
              </template>
            </el-table-column>
            <el-table-column label="绑定归属" min-width="150">
              <template #default="scope">
                <div>{{ ownerTypeLabel(scope.row.product_owner_type) }}</div>
                <div class="cell-meta">ID: {{ scope.row.product_owner_id || '--' }}</div>
              </template>
            </el-table-column>
            <el-table-column label="审核状态" width="120">
              <template #default="scope">
                <el-tag :type="statusType(scope.row.audit_status)">{{ statusLabel(scope.row.audit_status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="audit_remark" label="审核备注" min-width="180" show-overflow-tooltip />
            <el-table-column label="申请时间" min-width="170">
              <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="scope">
                <el-button link type="success" :disabled="scope.row.audit_status !== 'PENDING'" @click="reviewQualification(scope.row, 'APPROVED')">通过</el-button>
                <el-button link type="danger" :disabled="scope.row.audit_status !== 'PENDING'" @click="reviewQualification(scope.row, 'REJECTED')">驳回</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="资格台账" name="qualification-ledgers">
          <el-table :data="qualificationLedgers" border>
            <el-table-column prop="id" label="台账 ID" width="90" />
            <el-table-column label="商品 / 申请人" min-width="230">
              <template #default="scope">
                <div>{{ scope.row.product_name || `商品#${scope.row.product_id}` }}</div>
                <div class="cell-meta">用户 {{ scope.row.applicant_user_id }} / {{ scope.row.applicant_phone || '--' }}</div>
              </template>
            </el-table-column>
            <el-table-column label="资格来源" min-width="250">
              <template #default="scope">
                <div>{{ scope.row.qualification_type_label }}</div>
                <div class="cell-meta">{{ scope.row.source_summary || '--' }}</div>
              </template>
            </el-table-column>
            <el-table-column label="占用状态" width="120">
              <template #default="scope">
                <el-tag size="small" :type="scope.row.occupancy_active ? 'success' : 'info'">
                  {{ scope.row.occupancy_status_label }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="占用窗口" min-width="180">
              <template #default="scope">
                <div>{{ formatDate(scope.row.occupied_at) }}</div>
                <div class="cell-meta">释放：{{ formatDate(scope.row.released_at) }}</div>
              </template>
            </el-table-column>
            <el-table-column label="额度情况" width="130">
              <template #default="scope">
                <el-tag size="small" :type="quotaTagType(scope.row)">{{ quotaText(scope.row) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="绑定归属" min-width="150">
              <template #default="scope">
                <el-tag size="small" :type="scope.row.owner_bound ? 'success' : 'warning'">
                  {{ scope.row.owner_bound_label }}
                </el-tag>
                <div class="cell-meta">{{ ownerTypeLabel(scope.row.product_owner_type) }} / ID: {{ scope.row.product_owner_id || '--' }}</div>
              </template>
            </el-table-column>
            <el-table-column label="商品状态" width="120">
              <template #default="scope">
                <el-tag :type="statusType(scope.row.product_status)">{{ statusLabel(scope.row.product_status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="备注" min-width="220" show-overflow-tooltip>
              <template #default="scope">
                {{ scope.row.release_reason || scope.row.audit_remark || '--' }}
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="专区商品" name="zones">
          <div class="zone-toolbar">
            <div>
              <h3>{{ currentZoneMeta.label }}运营</h3>
              <p>{{ currentZoneMeta.desc }}</p>
            </div>
            <el-button v-permission="'products:create'" type="primary" @click="openProductCreate">新增商品</el-button>
          </div>
          <el-tabs v-model="zoneTab" type="border-card">
            <el-tab-pane v-for="item in zoneTabs" :key="item.name" :label="item.label" :name="item.name" />
          </el-tabs>
          <el-table :data="currentZoneRows" border style="margin-top: 14px;">
            <el-table-column prop="id" :label="currentZoneMeta.idLabel" width="90" />
            <el-table-column prop="product_name" :label="currentZoneMeta.nameLabel" min-width="180" />
            <el-table-column label="归属" min-width="170">
              <template #default="scope">
                <div>{{ ownerTypeLabel(scope.row.owner_type) }}</div>
                <div class="cell-meta">{{ scope.row.owner_name || `ID: ${scope.row.owner_id || '--'}` }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="product_type" label="类型" width="110">
              <template #default="scope">{{ productTypeLabel(scope.row.product_type) }}</template>
            </el-table-column>
            <el-table-column prop="sale_price" :label="currentZoneMeta.priceLabel" width="110" />
            <el-table-column prop="market_price" :label="currentZoneMeta.marketLabel" width="110" />
            <el-table-column :prop="currentZoneMeta.extraProp" :label="currentZoneMeta.extraLabel" width="100" />
            <el-table-column label="发布约束" min-width="200">
              <template #default="scope">
                <el-tag size="small" :type="publishGuardType(scope.row.publish_guard)">
                  {{ scope.row.publish_guard?.eligible ? '可发布' : scope.row.publish_guard?.required ? '需补资格' : '无需校验' }}
                </el-tag>
                <div class="cell-meta">{{ scope.row.publish_guard?.reason || '--' }}</div>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="120">
              <template #default="scope"><el-tag :type="statusType(scope.row.status)">{{ statusLabel(scope.row.status) }}</el-tag></template>
            </el-table-column>
            <el-table-column label="操作" min-width="340" fixed="right">
              <template #default="scope">
                <el-button v-permission="'products:edit'" link type="primary" @click="openProductEdit(scope.row)">编辑</el-button>
                <el-button v-permission="'products:submit-review'" link type="warning" :disabled="!canSubmitReview(scope.row)" @click="submitReview(scope.row)">提审</el-button>
                <el-button v-permission="'products:shelf'" link type="success" :disabled="!canShelfUp(scope.row)" @click="updateShelf(scope.row, 'ON_SHELF')">上架</el-button>
                <el-button v-permission="'products:shelf'" link type="info" :disabled="!canShelfDown(scope.row)" @click="updateShelf(scope.row, 'OFF_SHELF')">下架</el-button>
                <el-button v-if="userStore.role === 'SUPER_ADMIN'" link type="success" :disabled="scope.row.status !== 'PENDING_REVIEW'" @click="auditProduct(scope.row, 'APPROVED')">通过</el-button>
                <el-button v-if="userStore.role === 'SUPER_ADMIN'" link type="danger" :disabled="scope.row.status !== 'PENDING_REVIEW'" @click="auditProduct(scope.row, 'REJECTED')">驳回</el-button>
                <el-button link type="primary" @click="openZoneConfig(scope.row)">规则配置</el-button>
                <el-button v-permission="'products:edit'" link type="danger" :disabled="!canDeleteProduct(scope.row)" @click="deleteProduct(scope.row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <el-drawer v-model="productDialogVisible" :title="productDialogTitle" size="560px">
      <div class="panel-card data-card">
        <el-form label-position="top" :model="productForm" class="zone-config-form">
          <div class="form-split">
            <el-form-item label="专区">
              <el-select v-model="productForm.zone_type">
                <el-option v-for="item in zoneOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="商品类型">
              <el-select v-model="productForm.product_type">
                <el-option v-for="item in productTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
          </div>
          <div class="form-split">
            <el-form-item label="归属类型">
              <el-select v-model="productForm.owner_type">
                <el-option v-for="item in ownerTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="productForm.owner_type === 'SUPPLIER'" label="关联供应商">
              <el-select v-model="productForm.owner_id" placeholder="请选择供应商" filterable>
                <el-option
                  v-for="item in supplierOwnerOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item v-else label="归属说明">
              <el-input :model-value="productForm.owner_type === 'SELF_OPERATED' ? '默认归属当前管理员' : '当前页面暂不维护该归属类型'" disabled />
            </el-form-item>
          </div>
          <el-form-item label="商品名称"><el-input v-model="productForm.product_name" placeholder="请输入商品名称" /></el-form-item>
          <div class="form-split">
            <el-form-item label="售价"><el-input-number v-model="productForm.sale_price" :min="0.01" :step="1" :precision="2" controls-position="right" /></el-form-item>
            <el-form-item label="市场价"><el-input-number v-model="productForm.market_price" :min="0" :step="1" :precision="2" controls-position="right" /></el-form-item>
          </div>
          <div class="form-split">
            <el-form-item label="成本价"><el-input-number v-model="productForm.cost_price" :min="0" :step="1" :precision="2" controls-position="right" /></el-form-item>
            <el-form-item label="库存"><el-input-number v-model="productForm.stock" :min="0" :step="1" controls-position="right" /></el-form-item>
          </div>
          <el-form-item label="主图地址"><el-input v-model="productForm.main_image" placeholder="可填写 CDN / OSS 图片 URL" /></el-form-item>
          <div class="form-split">
            <el-form-item label="需要物流"><el-switch v-model="productForm.requires_shipping" :disabled="productForm.zone_type === 'LOCAL_LIFE'" /></el-form-item>
            <el-form-item label="支持一件代发"><el-switch v-model="productForm.drop_shipping_enabled" /></el-form-item>
          </div>
        </el-form>
        <div class="config-tips">
          <div>新增商品默认进入草稿状态，需提审后再由超级管理员审核。</div>
          <div>招商商品若要进入上架资格审核链路，必须同时满足一件代发、市场价 2 折红线、有效协议和已通过上架资格。</div>
        </div>
        <div class="dialog-actions">
          <el-button @click="productDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="productSaving" @click="saveProduct">保存商品</el-button>
        </div>
      </div>
    </el-drawer>
    <el-drawer v-model="zoneConfigVisible" :title="zoneConfigTitle" size="560px">
      <div v-loading="zoneConfigLoading">
        <div class="panel-card data-card">
          <div class="config-head">
            <div>
              <div class="soft-tag">{{ zoneLabelMap[zoneConfigForm.zone_type] || '--' }}</div>
              <h3 style="margin: 12px 0 8px;">{{ zoneConfigProduct.product_name || '--' }}</h3>
              <p class="config-desc">{{ zoneDescription }}</p>
            </div>
          </div>
          <el-form label-position="top" :model="zoneConfigForm" class="zone-config-form">
            <el-form-item label="是否要求套餐资格">
              <el-switch v-model="zoneConfigForm.package_required" :disabled="zoneConfigForm.zone_type === 'HOT_SALE'" />
            </el-form-item>
            <el-form-item v-if="zoneConfigForm.package_required" label="绑定套餐 ID">
              <el-input-number v-model="zoneConfigForm.package_id" :min="1" :step="1" controls-position="right" />
            </el-form-item>
            <el-form-item v-if="zoneConfigForm.zone_type === 'REPURCHASE'" label="复购折扣率（%）">
              <el-input-number v-model="zoneConfigForm.repurchase_discount_rate" :min="0" :max="100" :step="0.5" :precision="2" controls-position="right" />
            </el-form-item>
            <template v-if="zoneConfigForm.zone_type === 'SELF_OPERATED'">
              <div class="form-split">
                <el-form-item label="兑换券最低抵扣比例（%）"><el-input-number v-model="zoneConfigForm.voucher_deduct_min_rate" :min="0" :max="100" :step="1" :precision="2" controls-position="right" /></el-form-item>
                <el-form-item label="兑换券最高抵扣比例（%）"><el-input-number v-model="zoneConfigForm.voucher_deduct_max_rate" :min="0" :max="100" :step="1" :precision="2" controls-position="right" /></el-form-item>
              </div>
              <div class="form-split">
                <el-form-item label="购物返 AI 券比例（%）"><el-input-number v-model="zoneConfigForm.ai_coupon_reward_rate" :min="0" :max="100" :step="1" :precision="2" controls-position="right" /></el-form-item>
                <el-form-item label="AI 券最大抵扣比例（%）"><el-input-number v-model="zoneConfigForm.ai_coupon_max_deduct_rate" :min="0" :max="100" :step="1" :precision="2" controls-position="right" /></el-form-item>
              </div>
            </template>
            <template v-if="zoneConfigForm.zone_type === 'HOT_SALE'">
              <div class="form-split">
                <el-form-item label="积分支付"><el-switch v-model="zoneConfigForm.points_purchase_enabled" /></el-form-item>
                <el-form-item label="余额支付"><el-switch v-model="zoneConfigForm.balance_purchase_enabled" /></el-form-item>
              </div>
              <div class="form-split">
                <el-form-item label="限购件数"><el-input-number v-model="zoneConfigForm.per_user_limit" :min="1" :step="1" controls-position="right" /></el-form-item>
                <el-form-item label="开启闪购"><el-switch v-model="zoneConfigForm.flash_sale_enabled" /></el-form-item>
              </div>
            </template>
            <template v-if="zoneConfigForm.zone_type === 'LOCAL_LIFE'">
              <div class="form-split">
                <el-form-item label="积分支付"><el-switch v-model="zoneConfigForm.points_purchase_enabled" /></el-form-item>
                <el-form-item label="余额支付"><el-switch v-model="zoneConfigForm.balance_purchase_enabled" /></el-form-item>
              </div>
              <div class="form-split">
                <el-form-item label="分佣规则 ID"><el-input-number v-model="zoneConfigForm.merchant_commission_rule_id" :min="1" :step="1" controls-position="right" /></el-form-item>
                <el-form-item label="设备收益联动"><el-switch v-model="zoneConfigForm.device_revenue_enabled" /></el-form-item>
              </div>
            </template>
            <template v-if="zoneConfigForm.zone_type === 'REPURCHASE'">
              <div class="form-split">
                <el-form-item label="积分支付"><el-switch v-model="zoneConfigForm.points_purchase_enabled" /></el-form-item>
                <el-form-item label="余额支付"><el-switch v-model="zoneConfigForm.balance_purchase_enabled" /></el-form-item>
              </div>
            </template>
          </el-form>
          <div class="config-tips">
            <div>当前规则会直接影响 APP 下单校验、资产抵扣和支付后奖励发放。</div>
            <div>团队管理员仅可修改本团队范围内的商品规则。</div>
          </div>
          <div class="dialog-actions">
            <el-button @click="zoneConfigVisible = false">取消</el-button>
            <el-button type="primary" :loading="zoneConfigSaving" @click="saveZoneConfig">保存规则</el-button>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'

import { productApi, supplierApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const suppliers = ref([])
const qualifications = ref([])
const qualificationLedgers = ref([])
const zoneProducts = ref({ repurchase: [], selfOperated: [], hotSale: [], localLife: [] })
const activeTab = ref('suppliers')
const zoneTab = ref('repurchase')
const keyword = ref('')
const statusFilter = ref('')
const page = ref(1)
const pageSize = ref(8)
const productDialogVisible = ref(false)
const productSaving = ref(false)
const editingProductId = ref(null)
const zoneConfigVisible = ref(false)
const zoneConfigLoading = ref(false)
const zoneConfigSaving = ref(false)
const zoneConfigProduct = ref({})
const zoneLabelMap = {
  REPURCHASE: '复购区',
  SELF_OPERATED: '自营商城',
  HOT_SALE: '爆款区',
  LOCAL_LIFE: '本地生活'
}
const zoneTabs = [
  { name: 'repurchase', code: 'REPURCHASE', label: '复购区', desc: '康养套餐与二次复购商品。', idLabel: '商品 ID', nameLabel: '商品名称', priceLabel: '售价', marketLabel: '市场价', extraProp: 'stock', extraLabel: '库存' },
  { name: 'selfOperated', code: 'SELF_OPERATED', label: '自营商城', desc: '支持兑换券和 AI 券规则。', idLabel: '商品 ID', nameLabel: '商品名称', priceLabel: '售价', marketLabel: '市场价', extraProp: 'sold_count', extraLabel: '销量' },
  { name: 'hotSale', code: 'HOT_SALE', label: '爆款区', desc: '积分或余额抢购活动商品。', idLabel: '商品 ID', nameLabel: '商品名称', priceLabel: '抢购价', marketLabel: '参考价', extraProp: 'stock', extraLabel: '库存' },
  { name: 'localLife', code: 'LOCAL_LIFE', label: '本地生活', desc: '服务商品与线下核销场景。', idLabel: '服务 ID', nameLabel: '服务名称', priceLabel: '售价', marketLabel: '门市价', extraProp: 'sold_count', extraLabel: '销量' }
]
const zoneOptions = zoneTabs.map((item) => ({ label: item.label, value: item.code }))
const productTypeOptions = [
  { label: '实物商品', value: 'PHYSICAL' },
  { label: '服务商品', value: 'SERVICE' },
  { label: '活动商品', value: 'ACTIVITY' }
]
const ownerTypeOptions = [
  { label: '平台自营', value: 'SELF_OPERATED' },
  { label: '供应商商品', value: 'SUPPLIER' }
]

function createDefaultProduct(zoneType = 'REPURCHASE') {
  return {
    product_name: '',
    product_type: zoneType === 'LOCAL_LIFE' ? 'SERVICE' : 'PHYSICAL',
    zone_type: zoneType,
    owner_type: 'SELF_OPERATED',
    owner_id: null,
    market_price: null,
    sale_price: 0,
    cost_price: null,
    stock: 0,
    main_image: '',
    requires_shipping: zoneType !== 'LOCAL_LIFE',
    drop_shipping_enabled: false
  }
}

function createDefaultZoneConfig() {
  return {
    product_id: null,
    zone_type: 'REPURCHASE',
    package_required: false,
    package_id: null,
    repurchase_discount_rate: null,
    voucher_deduct_min_rate: null,
    voucher_deduct_max_rate: null,
    ai_coupon_reward_rate: null,
    ai_coupon_max_deduct_rate: null,
    points_purchase_enabled: false,
    balance_purchase_enabled: false,
    flash_sale_enabled: false,
    per_user_limit: null,
    merchant_commission_rule_id: null,
    device_revenue_enabled: false
  }
}

const productForm = ref(createDefaultProduct())
const zoneConfigForm = ref(createDefaultZoneConfig())

watch(() => productForm.value.zone_type, (value) => {
  if (value === 'LOCAL_LIFE') {
    productForm.value.product_type = 'SERVICE'
    productForm.value.requires_shipping = false
  }
})
watch(() => productForm.value.owner_type, (value) => {
  if (value !== 'SUPPLIER') {
    productForm.value.owner_id = null
  }
})

const scopeHint = computed(() => (
  userStore.role === 'TEAM_ADMIN'
    ? '当前仅查看所属团队供应商、资格申请和团队范围内的专区商品。'
    : '管理平台供应商准入、入场费规则、代理额度和四大专区供给结构。'
))
const currentZoneMeta = computed(() => zoneTabs.find((item) => item.name === zoneTab.value) || zoneTabs[0])
const currentZoneRows = computed(() => zoneProducts.value[zoneTab.value] || [])
const metrics = computed(() => {
  const exhaustedCount = qualifications.value.filter((item) => item.source_quota_total != null && Number(item.source_quota_remaining || 0) <= 0).length
  const activeAgreementCount = suppliers.value.filter((item) => item.active_agreement).length
  const activeOccupancyCount = qualificationLedgers.value.filter((item) => item.occupancy_active).length
  return [
    { label: '供应商总数', value: suppliers.value.length, subtext: `已启用 ${suppliers.value.filter((item) => item.status === 'ACTIVE').length} 家` },
    { label: '有效协议供应商', value: activeAgreementCount, subtext: '协议有效后才能占用招商资格' },
    { label: '待审核资格申请', value: qualifications.value.filter((item) => item.audit_status === 'PENDING').length, subtext: '后台需重点核对来源与商品合规' },
    { label: '资格占用中', value: activeOccupancyCount, subtext: '含待审与已生效资格台账' },
    { label: '额度已打满', value: exhaustedCount, subtext: '套餐或代理额度已无剩余' },
    { label: '四区商品池', value: Object.values(zoneProducts.value).reduce((sum, list) => sum + list.length, 0), subtext: '覆盖复购、自营、爆款、本地生活' }
  ]
})
const zoneStats = computed(() => zoneTabs.map((item) => ({ title: item.label, count: zoneProducts.value[item.name]?.length || 0, meta: item.desc })))
const supplierOwnerOptions = computed(() => suppliers.value.map((item) => ({
  label: `${item.supplier_name} / ${item.contact_name}`,
  value: item.id
})))
const filteredSuppliers = computed(() => suppliers.value.filter((item) => {
  const term = keyword.value.trim()
  return (!term || item.supplier_name?.includes(term) || item.contact_name?.includes(term)) && (!statusFilter.value || item.status === statusFilter.value)
}))
const pagedSuppliers = computed(() => filteredSuppliers.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value))
const productDialogTitle = computed(() => (editingProductId.value ? '编辑商品' : '新增商品'))
const zoneConfigTitle = computed(() => (!zoneConfigProduct.value.id ? '专区规则配置' : `${zoneLabelMap[zoneConfigForm.value.zone_type] || '专区'}规则 - ${zoneConfigProduct.value.product_name}`))
const zoneDescription = computed(() => ({
  REPURCHASE: '复购区以套餐资格和复购折扣为核心，适合康养套餐后的二次消费。',
  SELF_OPERATED: '自营商城以兑换券、AI 券规则为核心，直接影响支付抵扣和返券。',
  HOT_SALE: '爆款区以抢购门槛、资产支付和限购规则为核心，适合活动商品。',
  LOCAL_LIFE: '本地生活以联盟分佣与设备收益联动为核心，适合到店与服务类商品。'
}[zoneConfigForm.value.zone_type] || '请按专区业务规则维护商品配置。'))

function statusType(status) {
  return { PENDING: 'warning', APPROVED: 'success', ACTIVE: 'success', REJECTED: 'danger', DRAFT: 'info', PENDING_REVIEW: 'warning', ON_SHELF: 'success', OFF_SHELF: 'info' }[status] || 'info'
}
function statusLabel(status) {
  return { PENDING: '待审核', APPROVED: '已通过', ACTIVE: '已启用', REJECTED: '已驳回', DRAFT: '草稿', PENDING_REVIEW: '待审核', ON_SHELF: '已上架', OFF_SHELF: '已下架' }[status] || status || '--'
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
function formatMoney(value) {
  return value == null ? '--' : `￥${Number(value).toFixed(2)}`
}
function productTypeLabel(type) {
  return { PHYSICAL: '实物商品', SERVICE: '服务商品', ACTIVITY: '活动商品' }[type] || type || '--'
}
function ownerTypeLabel(type) {
  return { SELF_OPERATED: '平台自营', SUPPLIER: '供应商商品', LOCAL_MERCHANT: '本地商家' }[type] || type || '--'
}
function publishGuardType(guard) {
  if (!guard?.required) return 'info'
  return guard.eligible ? 'success' : 'warning'
}
function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '--'
}
function canSubmitReview(row) {
  return ['DRAFT', 'REJECTED'].includes(row.status) && (row.publish_guard?.eligible ?? true)
}
function canShelfUp(row) {
  return ['APPROVED', 'OFF_SHELF'].includes(row.status) && (row.publish_guard?.eligible ?? true)
}
function canShelfDown(row) { return row.status === 'ON_SHELF' }
function canDeleteProduct(row) { return row.status !== 'ON_SHELF' }

function normalizeProductForm(data = {}) {
  return {
    product_name: data.product_name || '',
    product_type: data.product_type || 'PHYSICAL',
    zone_type: data.zone_type || 'REPURCHASE',
    owner_type: data.owner_type || 'SELF_OPERATED',
    owner_id: data.owner_id ?? null,
    market_price: data.market_price == null ? null : Number(data.market_price),
    sale_price: data.sale_price == null ? 0 : Number(data.sale_price),
    cost_price: data.cost_price == null ? null : Number(data.cost_price),
    stock: data.stock == null ? 0 : Number(data.stock),
    main_image: data.main_image || '',
    requires_shipping: Boolean(data.requires_shipping),
    drop_shipping_enabled: Boolean(data.drop_shipping_enabled)
  }
}

function normalizeZoneConfig(data = {}) {
  return {
    ...createDefaultZoneConfig(),
    ...data,
    product_id: data.product_id ?? null,
    package_id: data.package_id ?? null,
    repurchase_discount_rate: data.repurchase_discount_rate == null ? null : Number(data.repurchase_discount_rate),
    voucher_deduct_min_rate: data.voucher_deduct_min_rate == null ? null : Number(data.voucher_deduct_min_rate),
    voucher_deduct_max_rate: data.voucher_deduct_max_rate == null ? null : Number(data.voucher_deduct_max_rate),
    ai_coupon_reward_rate: data.ai_coupon_reward_rate == null ? null : Number(data.ai_coupon_reward_rate),
    ai_coupon_max_deduct_rate: data.ai_coupon_max_deduct_rate == null ? null : Number(data.ai_coupon_max_deduct_rate),
    per_user_limit: data.per_user_limit ?? null,
    merchant_commission_rule_id: data.merchant_commission_rule_id ?? null,
    package_required: Boolean(data.package_required),
    points_purchase_enabled: Boolean(data.points_purchase_enabled),
    balance_purchase_enabled: Boolean(data.balance_purchase_enabled),
    flash_sale_enabled: Boolean(data.flash_sale_enabled),
    device_revenue_enabled: Boolean(data.device_revenue_enabled)
  }
}

async function loadZoneProducts() {
  const [repurchase, selfOperated, hotSale, localLife] = await Promise.all([productApi.repurchase(), productApi.selfOperated(), productApi.hotSale(), productApi.localLife()])
  zoneProducts.value = { repurchase: repurchase || [], selfOperated: selfOperated || [], hotSale: hotSale || [], localLife: localLife || [] }
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
  await loadZoneProducts()
}

async function reviewQualification(row, auditStatus) {
  const label = auditStatus === 'APPROVED' ? '通过' : '驳回'
  await ElMessageBox.confirm(`确认${label}该上架资格申请吗？`, '资格审核', { type: 'warning' })
  await supplierApi.auditQualification(row.id, { audit_status: auditStatus, audit_remark: auditStatus === 'APPROVED' ? '后台审核通过' : '后台审核驳回' })
  qualifications.value = await supplierApi.qualifications()
  qualificationLedgers.value = await supplierApi.qualificationLedgers()
  ElMessage.success(`已${label}申请`)
}

function openProductCreate() {
  editingProductId.value = null
  productForm.value = createDefaultProduct(currentZoneMeta.value.code)
  productDialogVisible.value = true
}

function openProductEdit(row) {
  editingProductId.value = row.id
  productForm.value = normalizeProductForm(row)
  productDialogVisible.value = true
}

async function saveProduct() {
  if (!productForm.value.product_name.trim()) return ElMessage.warning('请先填写商品名称')
  if (productForm.value.owner_type === 'SUPPLIER' && !productForm.value.owner_id) {
    return ElMessage.warning('请选择供应商归属')
  }
  productSaving.value = true
  try {
    const payload = {
      ...productForm.value,
      owner_id: productForm.value.owner_type === 'SUPPLIER' ? productForm.value.owner_id : null,
      requires_shipping: productForm.value.zone_type === 'LOCAL_LIFE' ? false : productForm.value.requires_shipping
    }
    if (editingProductId.value) {
      await productApi.update(editingProductId.value, payload)
      ElMessage.success('商品已更新')
    } else {
      await productApi.create(payload)
      ElMessage.success('商品已创建')
    }
    productDialogVisible.value = false
    await loadZoneProducts()
  } finally {
    productSaving.value = false
  }
}
async function submitReview(row) {
  await ElMessageBox.confirm(`确认提交商品“${row.product_name}”进入审核吗？`, '提交审核', { type: 'warning' })
  await productApi.submitReview(row.id)
  ElMessage.success('商品已提交审核')
  await loadZoneProducts()
}

async function auditProduct(row, auditStatus) {
  const label = auditStatus === 'APPROVED' ? '通过' : '驳回'
  await ElMessageBox.confirm(`确认${label}商品“${row.product_name}”吗？`, '商品审核', { type: 'warning' })
  await productApi.audit(row.id, { audit_status: auditStatus })
  ElMessage.success(`已${label}商品审核`)
  await loadZoneProducts()
}

async function updateShelf(row, status) {
  const label = status === 'ON_SHELF' ? '上架' : '下架'
  await ElMessageBox.confirm(`确认${label}商品“${row.product_name}”吗？`, '商品状态', { type: 'warning' })
  await productApi.updateStatus(row.id, { status })
  ElMessage.success(`商品已${label}`)
  await loadZoneProducts()
}

async function deleteProduct(row) {
  await ElMessageBox.confirm(`确认删除商品“${row.product_name}”吗？删除后不可恢复。`, '删除商品', { type: 'warning' })
  await productApi.remove(row.id)
  ElMessage.success('商品已删除')
  await loadZoneProducts()
}

async function openZoneConfig(row) {
  zoneConfigVisible.value = true
  zoneConfigLoading.value = true
  zoneConfigProduct.value = row
  try {
    zoneConfigForm.value = normalizeZoneConfig(await productApi.zoneConfig(row.id))
  } finally {
    zoneConfigLoading.value = false
  }
}

async function saveZoneConfig() {
  zoneConfigSaving.value = true
  try {
    await productApi.updateZoneConfig(zoneConfigProduct.value.id, {
      package_required: zoneConfigForm.value.package_required,
      package_id: zoneConfigForm.value.package_required ? zoneConfigForm.value.package_id : null,
      repurchase_discount_rate: zoneConfigForm.value.repurchase_discount_rate,
      voucher_deduct_min_rate: zoneConfigForm.value.voucher_deduct_min_rate,
      voucher_deduct_max_rate: zoneConfigForm.value.voucher_deduct_max_rate,
      ai_coupon_reward_rate: zoneConfigForm.value.ai_coupon_reward_rate,
      ai_coupon_max_deduct_rate: zoneConfigForm.value.ai_coupon_max_deduct_rate,
      points_purchase_enabled: zoneConfigForm.value.points_purchase_enabled,
      balance_purchase_enabled: zoneConfigForm.value.balance_purchase_enabled,
      flash_sale_enabled: zoneConfigForm.value.flash_sale_enabled,
      per_user_limit: zoneConfigForm.value.per_user_limit,
      merchant_commission_rule_id: zoneConfigForm.value.merchant_commission_rule_id,
      device_revenue_enabled: zoneConfigForm.value.device_revenue_enabled
    })
    ElMessage.success('专区规则已保存')
    zoneConfigVisible.value = false
    await loadZoneProducts()
  } finally {
    zoneConfigSaving.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.zone-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  gap: 16px;
}
.zone-toolbar h3 {
  margin: 0 0 6px;
}
.zone-toolbar p,
.config-desc,
.cell-meta {
  margin: 0;
  color: var(--el-text-color-secondary);
}
.cell-meta {
  font-size: 12px;
  margin-top: 4px;
  line-height: 1.5;
}
.config-head {
  margin-bottom: 16px;
}
.zone-config-form {
  margin-top: 18px;
}
.form-split {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
.config-tips {
  margin-top: 12px;
  padding: 14px 16px;
  background: rgba(27, 94, 32, 0.06);
  border-radius: 14px;
  color: var(--el-text-color-secondary);
  line-height: 1.7;
}
.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 18px;
}
@media (max-width: 900px) {
  .zone-toolbar {
    flex-direction: column;
    align-items: flex-start;
  }
  .form-split {
    grid-template-columns: 1fr;
  }
}
</style>
