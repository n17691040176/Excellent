<template>
  <div class="products-view">
    <div class="page-heading">
      <div>
        <h2>商品管理</h2>
        <p>对齐移动端商品卡片、详情文案和专区规则，支持 Excel / CSV 一键导入。</p>
      </div>
      <div class="toolbar-row">
        <el-button plain @click="loadData">刷新数据</el-button>
        <el-button plain @click="downloadTemplate">下载导入模板</el-button>
        <el-button :loading="importing" @click="triggerImport">Excel 导入</el-button>
        <el-button v-permission="'products:create'" type="primary" @click="openCreate">新增商品</el-button>
      </div>
    </div>

    <input
      ref="importInputRef"
      type="file"
      accept=".xlsx,.csv"
      style="display: none;"
      @change="handleImportChange"
    />

    <div class="metric-grid">
      <div v-for="item in metrics" :key="item.label" class="metric-card">
        <div class="label">{{ item.label }}</div>
        <div class="value">{{ item.value }}</div>
        <div class="subtext">{{ item.subtext }}</div>
      </div>
    </div>

    <div class="split-grid" style="margin-top: 18px;">
      <button
        v-for="item in zoneTabs"
        :key="item.code"
        type="button"
        class="panel-card zone-card"
        :class="{ 'is-active': filters.zone_type === item.code }"
        @click="toggleZone(item.code)"
      >
        <div class="zone-card-title">{{ item.label }}</div>
        <div class="zone-card-value">{{ zoneCount(item.code) }}</div>
        <div class="zone-card-meta">{{ item.desc }}</div>
      </button>
    </div>

    <div class="panel-card data-card" style="margin-top: 18px;">
      <div class="toolbar-row filters-wrap">
        <el-input
          v-model="filters.keyword"
          placeholder="搜索商品名称 / 品牌"
          clearable
          style="max-width: 280px;"
        />
        <el-select v-model="filters.status" placeholder="状态" clearable style="width: 170px;">
          <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.owner_type" placeholder="归属类型" clearable style="width: 170px;">
          <el-option v-for="item in ownerTypeFilterOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-button plain @click="resetFilters">重置筛选</el-button>
      </div>

      <div v-if="selectedRows.length" class="batch-toolbar">
        <div class="batch-toolbar__info">
          已选 {{ selectedRows.length }} 个商品。第一条会拿到最高排序值，用于快速对齐移动端列表顺序。
        </div>
        <div class="batch-toolbar__actions">
          <el-input-number v-model="batchForm.order_by_start" :min="0" :step="10" controls-position="right" />
          <el-input-number v-model="batchForm.order_by_step" :min="1" :step="1" controls-position="right" />
          <el-button plain @click="applyBatchHot(true)">设为热门</el-button>
          <el-button plain @click="applyBatchHot(false)">取消热门</el-button>
          <el-button type="primary" @click="applyBatchSort">批量排序</el-button>
          <el-button plain @click="applyBatchStatus('SUBMIT_REVIEW')">批量提审</el-button>
          <el-button plain @click="applyBatchStatus('ON_SHELF')">批量上架</el-button>
          <el-button plain @click="applyBatchStatus('OFF_SHELF')">批量下架</el-button>
          <el-button link type="primary" @click="clearSelection">清空选择</el-button>
        </div>
      </div>

      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="products"
        border
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="50" fixed="left" />
        <el-table-column prop="id" label="ID" width="88" />
        <el-table-column label="商品信息" min-width="260">
          <template #default="{ row }">
            <div class="product-cell">
              <el-image v-if="row.image || row.cover" :src="row.image || row.cover" fit="cover" class="product-thumb" />
              <div v-else class="product-thumb is-empty">无图</div>
              <div class="product-copy">
                <div class="cell-title product-title-row">
                  <span>{{ row.product_name }}</span>
                  <el-tag v-if="row.is_legacy_product" type="warning" size="small">历史商品</el-tag>
                </div>
                <div class="cell-meta">{{ zoneLabelMap[row.zone_type] || row.zone_type }} / {{ productTypeLabel(row.product_type) }}</div>
                <div class="cell-meta">{{ ownerTypeLabel(row.owner_type) }} / {{ row.owner_name || `ID: ${row.owner_id || '--'}` }}</div>
                <div class="tag-row">
                  <span class="mini-tag">{{ row.category_name || row.brand || '未分类' }}</span>
                  <span v-if="row.tag" class="mini-tag warm">{{ row.tag }}</span>
                  <span class="mini-tag muted">图集 {{ row.gallery_count || 0 }}</span>
                </div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="移动端预览" min-width="320">
          <template #default="{ row }">
            <div class="mobile-card">
              <div class="mobile-card__cover">
                <el-image
                  v-if="row.mobile_preview?.image"
                  :src="row.mobile_preview.image"
                  fit="cover"
                  class="mobile-card__image"
                />
                <div v-else class="mobile-card__image is-empty">待补图</div>
              </div>
              <div class="mobile-card__body">
                <div class="mobile-card__tag">{{ row.mobile_preview?.tag || '精选商品' }}</div>
                <div class="mobile-card__title">{{ row.mobile_preview?.title || row.product_name }}</div>
                <div class="mobile-card__desc">{{ row.mobile_preview?.description || '建议补充简介，移动端卡片信息会更完整。' }}</div>
                <div class="mobile-card__price-row">
                  <span class="mobile-card__price">{{ formatMoney(row.sale_price) }}</span>
                  <span v-if="row.market_price != null" class="mobile-card__market">{{ formatMoney(row.market_price) }}</span>
                </div>
                <div class="tag-row">
                  <span v-for="item in previewFeatureList(row)" :key="item" class="mini-tag">{{ item }}</span>
                </div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="价格 / 库存" width="160">
          <template #default="{ row }">
            <div>售价 {{ formatMoney(row.sale_price) }}</div>
            <div class="cell-meta">市场价 {{ formatMoney(row.market_price) }}</div>
            <div class="cell-meta">库存 {{ row.stock || 0 }} / 销量 {{ row.sold_count || 0 }}</div>
          </template>
        </el-table-column>
        <el-table-column label="运营设置" min-width="170">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_hot ? 'danger' : 'info'">{{ row.is_hot ? '热门' : '普通' }}</el-tag>
            <div class="cell-meta">排序 {{ row.order_by ?? '--' }}</div>
            <div class="cell-meta">{{ row.requires_shipping ? '需要物流' : '无需物流' }} / {{ row.drop_shipping_enabled ? '支持代发' : '普通履约' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="专区规则" min-width="240">
          <template #default="{ row }">
            <div class="cell-title small">{{ row.zone_rule_summary?.headline || '专区规则' }}</div>
            <div class="tag-row">
              <span
                v-for="item in row.zone_rule_summary?.badges || []"
                :key="item"
                class="mini-tag"
              >
                {{ item }}
              </span>
              <span class="mini-tag muted">{{ row.zone_rule_summary?.configured ? '已配置' : '默认规则' }}</span>
            </div>
            <div class="cell-meta">{{ row.zone_rule_summary?.description || '--' }}</div>
            <el-tag size="small" :type="publishGuardType(row.publish_guard)">{{ publishGuardText(row.publish_guard) }}</el-tag>
            <div class="cell-meta">{{ row.publish_guard?.reason || '--' }}</div>
            <el-button link type="primary" style="padding-left: 0;" @click="openZoneConfig(row)">规则配置</el-button>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="320" fixed="right">
          <template #default="{ row }">
            <el-button v-permission="'products:edit'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button
              v-permission="'products:submit-review'"
              link
              type="warning"
              :disabled="!canSubmitReview(row)"
              @click="submitReview(row)"
            >
              提审
            </el-button>
            <el-button
              v-permission="'products:shelf'"
              link
              type="success"
              :disabled="!canShelfUp(row)"
              @click="updateShelf(row, 'ON_SHELF')"
            >
              上架
            </el-button>
            <el-button
              v-permission="'products:shelf'"
              link
              type="info"
              :disabled="!canShelfDown(row)"
              @click="updateShelf(row, 'OFF_SHELF')"
            >
              下架
            </el-button>
            <el-button
              v-if="userStore.role === 'SUPER_ADMIN'"
              link
              type="success"
              :disabled="row.status !== 'PENDING_REVIEW'"
              @click="auditProduct(row, 'APPROVED')"
            >
              通过
            </el-button>
            <el-button
              v-if="userStore.role === 'SUPER_ADMIN'"
              link
              type="danger"
              :disabled="row.status !== 'PENDING_REVIEW'"
              @click="auditProduct(row, 'REJECTED')"
            >
              驳回
            </el-button>
            <el-button
              v-permission="'products:edit'"
              link
              type="danger"
              :disabled="row.status === 'ON_SHELF'"
              @click="removeProduct(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-drawer v-model="dialogVisible" :title="dialogTitle" size="1100px">
      <div class="drawer-layout">
        <div class="panel-card data-card">
          <el-form label-position="top" :model="form">
            <el-alert
              v-if="editingId && currentEditingProduct?.is_legacy_product"
              title="当前编辑的是历史导入商品，仅旧用户可见。"
              type="warning"
              :closable="false"
              style="margin-bottom: 16px;"
            />
            <div class="form-split">
              <el-form-item label="专区">
                <el-select v-model="form.zone_type">
                  <el-option v-for="item in zoneOptions" :key="item.value" :label="item.label" :value="item.value" />
                </el-select>
              </el-form-item>
              <el-form-item label="商品类型">
                <el-select v-model="form.product_type">
                  <el-option v-for="item in productTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
                </el-select>
              </el-form-item>
            </div>

            <div class="form-split">
              <el-form-item label="归属类型">
                <el-select v-model="form.owner_type">
                  <el-option v-for="item in ownerTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="form.owner_type === 'SUPPLIER'" label="关联供应商">
                <el-select v-model="form.owner_id" filterable placeholder="请选择供应商">
                  <el-option v-for="item in supplierOwnerOptions" :key="item.value" :label="item.label" :value="item.value" />
                </el-select>
              </el-form-item>
              <el-form-item v-else label="归属说明">
                <el-input model-value="平台自营默认归属当前管理员" disabled />
              </el-form-item>
            </div>

            <div class="form-split">
              <el-form-item label="商品名称"><el-input v-model="form.product_name" /></el-form-item>
              <el-form-item label="品牌 / 分类文案">
                <el-input v-model="form.brand" placeholder="会用于移动端分类或标签文案" />
              </el-form-item>
            </div>

            <div class="form-split">
              <el-form-item label="售价">
                <el-input-number v-model="form.sale_price" :min="0.01" :step="1" :precision="2" controls-position="right" />
              </el-form-item>
              <el-form-item label="市场价">
                <el-input-number v-model="form.market_price" :min="0" :step="1" :precision="2" controls-position="right" />
              </el-form-item>
            </div>

            <div class="form-split">
              <el-form-item label="成本价">
                <el-input-number v-model="form.cost_price" :min="0" :step="1" :precision="2" controls-position="right" />
              </el-form-item>
              <el-form-item label="库存">
                <el-input-number v-model="form.stock" :min="0" :step="1" controls-position="right" />
              </el-form-item>
            </div>

            <div class="form-split">
              <el-form-item label="排序">
                <el-input-number v-model="form.order_by" :min="0" :step="1" controls-position="right" />
              </el-form-item>
              <el-form-item label="热门商品">
                <el-switch v-model="form.is_hot" />
              </el-form-item>
            </div>

            <el-form-item label="主图地址"><el-input v-model="form.main_image" /></el-form-item>
            <el-form-item label="封面图地址"><el-input v-model="form.cover" /></el-form-item>
            <el-form-item label="轮播图">
              <el-input v-model="form.icons" placeholder="多个 URL 用英文逗号分隔" />
            </el-form-item>
            <el-form-item label="简介">
              <el-input v-model="form.profile" type="textarea" :rows="3" />
            </el-form-item>
            <el-form-item label="卖点">
              <el-input v-model="form.feature" type="textarea" :rows="2" />
            </el-form-item>
            <el-form-item label="详情">
              <el-input v-model="form.detail" type="textarea" :rows="5" />
            </el-form-item>

            <div class="form-split">
              <el-form-item label="需要物流">
                <el-switch v-model="form.requires_shipping" :disabled="form.zone_type === 'LOCAL_LIFE'" />
              </el-form-item>
              <el-form-item label="支持一件代发">
                <el-switch v-model="form.drop_shipping_enabled" />
              </el-form-item>
            </div>
          </el-form>

          <div class="config-tips">
            <div>导入和手工新增商品都会先保存为草稿，再走提审、审核和上架流程。</div>
            <div>模板里可直接填写商品 ID 更新已有商品，不填则创建新商品。</div>
            <div>模板现在也支持专区规则字段，商品资料和支付/资格规则可以一次导入完成。</div>
            <div>移动端展示最依赖主图、品牌、简介、卖点、详情和专区规则，建议一次补齐。</div>
          </div>

          <div class="dialog-actions">
            <el-button @click="dialogVisible = false">取消</el-button>
            <el-button type="primary" :loading="saving" @click="saveProduct">保存商品</el-button>
          </div>
        </div>

        <div class="panel-card data-card preview-panel">
          <div class="preview-panel__head">
            <div>
              <h3>移动端实时预览</h3>
              <p>这里会尽量按移动端商品卡片与详情摘要展示，便于运营边填边看。</p>
            </div>
            <div class="soft-tag">{{ zoneLabelMap[form.zone_type] || '--' }}</div>
          </div>

          <div class="preview-phone">
            <div class="preview-phone__screen">
              <div class="mobile-card mobile-card--editor">
                <div class="mobile-card__cover mobile-card__cover--editor">
                  <el-image v-if="formPreview.image" :src="formPreview.image" fit="cover" class="mobile-card__image" />
                  <div v-else class="mobile-card__image is-empty">待补图</div>
                </div>
                <div class="mobile-card__body">
                  <div class="mobile-card__tag">{{ formPreview.tag }}</div>
                  <div class="mobile-card__title">{{ formPreview.title }}</div>
                  <div class="mobile-card__desc">{{ formPreview.description }}</div>
                  <div class="mobile-card__price-row">
                    <span class="mobile-card__price">{{ formatMoney(form.sale_price) }}</span>
                    <span v-if="form.market_price != null" class="mobile-card__market">{{ formatMoney(form.market_price) }}</span>
                  </div>
                  <div class="tag-row">
                    <span v-for="item in formPreview.features" :key="item" class="mini-tag">{{ item }}</span>
                  </div>
                </div>
              </div>

              <div class="preview-block">
                <div class="preview-block__title">详情摘要</div>
                <div class="tag-row">
                  <span class="mini-tag warm">{{ formPreview.categoryName }}</span>
                  <span class="mini-tag muted">图集 {{ formPreview.gallery.length }}</span>
                  <span class="mini-tag muted">{{ form.requires_shipping ? '需要物流' : '无需物流' }}</span>
                </div>
                <ul class="preview-list">
                  <li v-for="item in formPreview.items" :key="item">{{ item }}</li>
                </ul>
              </div>

              <div class="preview-block">
                <div class="preview-block__title">运营提醒</div>
                <ul class="preview-list">
                  <li>当前标签：{{ formPreview.tag }}</li>
                  <li>当前排序：{{ form.order_by ?? '--' }} / {{ form.is_hot ? '热门商品' : '普通商品' }}</li>
                  <li>{{ form.drop_shipping_enabled ? '已开启一件代发' : '未开启一件代发' }}</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-drawer>

    <el-drawer v-model="zoneConfigVisible" :title="zoneConfigTitle" size="560px">
      <div class="panel-card data-card" v-loading="zoneConfigLoading">
        <div class="config-head">
          <div class="soft-tag">{{ zoneLabelMap[zoneConfigForm.zone_type] || '--' }}</div>
          <h3>{{ zoneConfigProduct.product_name || '--' }}</h3>
          <p class="config-desc">{{ zoneDescription }}</p>
          <div class="tag-row">
            <span
              v-for="item in zoneConfigSummary.badges"
              :key="item"
              class="mini-tag"
            >
              {{ item }}
            </span>
            <span class="mini-tag muted">{{ zoneConfigForm.configured ? '已配置' : '默认规则' }}</span>
          </div>
        </div>

        <el-form label-position="top" :model="zoneConfigForm">
          <el-form-item label="是否要求套餐资格">
            <el-switch v-model="zoneConfigForm.package_required" :disabled="zoneConfigForm.zone_type === 'HOT_SALE'" />
          </el-form-item>
          <el-form-item v-if="zoneConfigForm.package_required" label="绑定套餐 ID">
            <el-input-number v-model="zoneConfigForm.package_id" :min="1" :step="1" controls-position="right" />
          </el-form-item>

          <template v-if="zoneConfigForm.zone_type === 'REPURCHASE'">
            <div class="form-split">
              <el-form-item label="复购折扣率（%）">
                <el-input-number
                  v-model="zoneConfigForm.repurchase_discount_rate"
                  :min="0"
                  :max="100"
                  :step="0.5"
                  :precision="2"
                  controls-position="right"
                />
              </el-form-item>
              <el-form-item label="积分支付"><el-switch v-model="zoneConfigForm.points_purchase_enabled" /></el-form-item>
            </div>
            <el-form-item label="余额支付"><el-switch v-model="zoneConfigForm.balance_purchase_enabled" /></el-form-item>
          </template>

          <template v-if="zoneConfigForm.zone_type === 'SELF_OPERATED'">
            <div class="form-split">
              <el-form-item label="积分支付"><el-switch v-model="zoneConfigForm.points_purchase_enabled" /></el-form-item>
              <el-form-item label="余额支付"><el-switch v-model="zoneConfigForm.balance_purchase_enabled" /></el-form-item>
            </div>
            <div class="form-split">
              <el-form-item label="兑换券最低抵扣比例（%）">
                <el-input-number
                  v-model="zoneConfigForm.voucher_deduct_min_rate"
                  :min="0"
                  :max="100"
                  :step="1"
                  :precision="2"
                  controls-position="right"
                />
              </el-form-item>
              <el-form-item label="兑换券最高抵扣比例（%）">
                <el-input-number
                  v-model="zoneConfigForm.voucher_deduct_max_rate"
                  :min="0"
                  :max="100"
                  :step="1"
                  :precision="2"
                  controls-position="right"
                />
              </el-form-item>
            </div>
            <div class="form-split">
              <el-form-item label="购物返 AI 券比例（%）">
                <el-input-number
                  v-model="zoneConfigForm.ai_coupon_reward_rate"
                  :min="0"
                  :max="100"
                  :step="1"
                  :precision="2"
                  controls-position="right"
                />
              </el-form-item>
              <el-form-item label="AI 券最大抵扣比例（%）">
                <el-input-number
                  v-model="zoneConfigForm.ai_coupon_max_deduct_rate"
                  :min="0"
                  :max="100"
                  :step="1"
                  :precision="2"
                  controls-position="right"
                />
              </el-form-item>
            </div>
          </template>

          <template v-if="zoneConfigForm.zone_type === 'HOT_SALE'">
            <div class="form-split">
              <el-form-item label="积分支付"><el-switch v-model="zoneConfigForm.points_purchase_enabled" /></el-form-item>
              <el-form-item label="余额支付"><el-switch v-model="zoneConfigForm.balance_purchase_enabled" /></el-form-item>
            </div>
            <div class="form-split">
              <el-form-item label="限购件数">
                <el-input-number v-model="zoneConfigForm.per_user_limit" :min="1" :step="1" controls-position="right" />
              </el-form-item>
              <el-form-item label="开启闪购"><el-switch v-model="zoneConfigForm.flash_sale_enabled" /></el-form-item>
            </div>
          </template>

          <template v-if="zoneConfigForm.zone_type === 'LOCAL_LIFE'">
            <div class="form-split">
              <el-form-item label="积分支付"><el-switch v-model="zoneConfigForm.points_purchase_enabled" /></el-form-item>
              <el-form-item label="余额支付"><el-switch v-model="zoneConfigForm.balance_purchase_enabled" /></el-form-item>
            </div>
            <div class="form-split">
              <el-form-item label="分佣规则 ID">
                <el-input-number v-model="zoneConfigForm.merchant_commission_rule_id" :min="1" :step="1" controls-position="right" />
              </el-form-item>
              <el-form-item label="设备收益联动"><el-switch v-model="zoneConfigForm.device_revenue_enabled" /></el-form-item>
            </div>
          </template>

          <div class="purchase-mode-box">
            <div class="cell-title small">购买方式控制</div>
            <div class="form-split">
              <el-form-item label="纯积分购买"><el-switch v-model="zoneConfigForm.points_only_enabled" /></el-form-item>
              <el-form-item label="积分加现金购买"><el-switch v-model="zoneConfigForm.points_cash_enabled" /></el-form-item>
            </div>
            <div class="form-split">
              <el-form-item label="纯现金购买"><el-switch v-model="zoneConfigForm.cash_only_enabled" /></el-form-item>
              <el-form-item label="余额纯支付"><el-switch v-model="zoneConfigForm.balance_only_enabled" /></el-form-item>
            </div>
            <el-form-item label="余额+积分支付"><el-switch v-model="zoneConfigForm.balance_points_enabled" /></el-form-item>
          </div>
        </el-form>

        <div class="config-tips">
          <div>专区规则会直接影响移动端下单校验、支付方式和活动展示。</div>
          <div>建议商品创建后立刻补齐专区规则，避免前台已上架但支付与资格规则缺失。</div>
        </div>

        <div class="dialog-actions">
          <el-button @click="zoneConfigVisible = false">取消</el-button>
          <el-button type="primary" :loading="zoneConfigSaving" @click="saveZoneConfig">保存规则</el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { productApi, supplierApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const loading = ref(false)
const products = ref([])
const suppliers = ref([])
const selectedRows = ref([])
const tableRef = ref(null)
const importing = ref(false)
const importInputRef = ref(null)
const dialogVisible = ref(false)
const saving = ref(false)
const editingId = ref(null)
const zoneConfigVisible = ref(false)
const zoneConfigLoading = ref(false)
const zoneConfigSaving = ref(false)
const zoneConfigProduct = ref({})
const currentEditingProduct = ref(null)

const filters = reactive({ keyword: '', zone_type: '', status: '', owner_type: '' })
const batchForm = reactive({ order_by_start: 1000, order_by_step: 10 })

const zoneTabs = [
  { code: 'REPURCHASE', label: '复购区', desc: '套餐复购和持续消费商品。' },
  { code: 'SELF_OPERATED', label: '自营商城', desc: '平台自营和券类转化商品。' },
  { code: 'HOT_SALE', label: '爆款区', desc: '活动抢购和高频爆款商品。' },
  { code: 'LOCAL_LIFE', label: '本地生活', desc: '到店服务和核销类商品。' }
]
const zoneLabelMap = Object.fromEntries(zoneTabs.map((item) => [item.code, item.label]))
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
const ownerTypeFilterOptions = [...ownerTypeOptions, { label: '本地商家', value: 'LOCAL_MERCHANT' }]
const statusOptions = [
  { label: '草稿', value: 'DRAFT' },
  { label: '待审核', value: 'PENDING_REVIEW' },
  { label: '已通过', value: 'APPROVED' },
  { label: '已驳回', value: 'REJECTED' },
  { label: '已上架', value: 'ON_SHELF' },
  { label: '已下架', value: 'OFF_SHELF' }
]

function createDefaultForm(zoneType = 'REPURCHASE') {
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
    cover: '',
    icons: '',
    brand: '',
    profile: '',
    detail: '',
    feature: '',
    order_by: null,
    is_hot: false,
    requires_shipping: zoneType !== 'LOCAL_LIFE',
    drop_shipping_enabled: false
  }
}

function createDefaultZoneConfig() {
  return {
    product_id: null,
    zone_type: 'REPURCHASE',
    configured: false,
    package_required: false,
    package_id: null,
    repurchase_discount_rate: null,
    voucher_deduct_min_rate: null,
    voucher_deduct_max_rate: null,
    ai_coupon_reward_rate: null,
    ai_coupon_max_deduct_rate: null,
    points_purchase_enabled: false,
    balance_purchase_enabled: false,
    points_only_enabled: false,
    points_cash_enabled: true,
    cash_only_enabled: true,
    balance_only_enabled: true,
    balance_points_enabled: true,
    flash_sale_enabled: false,
    per_user_limit: null,
    merchant_commission_rule_id: null,
    device_revenue_enabled: false
  }
}

const form = ref(createDefaultForm())
const zoneConfigForm = ref(createDefaultZoneConfig())

watch(
  () => form.value.zone_type,
  (value) => {
    if (value === 'LOCAL_LIFE') {
      form.value.product_type = 'SERVICE'
      form.value.requires_shipping = false
    }
  }
)

watch(
  () => form.value.owner_type,
  (value) => {
    if (value !== 'SUPPLIER') {
      form.value.owner_id = null
    }
  }
)

const supplierOwnerOptions = computed(() => {
  return suppliers.value.map((item) => ({ label: `${item.supplier_name} / ${item.contact_name}`, value: item.id }))
})

const metrics = computed(() => [
  { label: '当前商品数', value: products.value.length, subtext: '当前筛选结果下的商品总量' },
  { label: '待审核', value: products.value.filter((item) => item.status === 'PENDING_REVIEW').length, subtext: '需要后台审核的商品' },
  { label: '已上架', value: products.value.filter((item) => item.status === 'ON_SHELF').length, subtext: '前台可见且可下单的商品' },
  { label: '历史商品', value: products.value.filter((item) => item.is_legacy_product).length, subtext: '旧系统导入、仅旧用户可见的商品' },
  { label: '热门商品', value: products.value.filter((item) => Number(item.is_hot)).length, subtext: '移动端优先承接的商品' }
])

const dialogTitle = computed(() => (editingId.value ? '编辑商品' : '新增商品'))
const zoneConfigTitle = computed(() => {
  if (!zoneConfigProduct.value.id) return '专区规则配置'
  return `${zoneLabelMap[zoneConfigForm.value.zone_type] || '专区'}规则 - ${zoneConfigProduct.value.product_name}`
})
const zoneDescription = computed(() => {
  return {
    REPURCHASE: '复购区以套餐资格、复购折扣和支付方式为核心。',
    SELF_OPERATED: '自营商城以兑换券和 AI 券规则为核心。',
    HOT_SALE: '爆款区以限购、闪购和活动支付方式为核心。',
    LOCAL_LIFE: '本地生活以分佣和设备收益联动为核心。'
  }[zoneConfigForm.value.zone_type] || ''
})
const selectedIds = computed(() => selectedRows.value.map((item) => item.id))

function firstFilled(values) {
  return values.map((item) => String(item || '').trim()).find(Boolean) || ''
}

function stripHtml(value) {
  return String(value || '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/\s+/g, ' ')
    .trim()
}

function truncate(value, limit = 72) {
  if (!value) return ''
  return value.length > limit ? `${value.slice(0, limit - 3).trim()}...` : value
}

function splitMedia(value) {
  return String(value || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function buildFeatureList(source) {
  const items = []
  const feature = truncate(stripHtml(source.feature), 24)
  if (feature) items.push(feature)
  if (source.brand) items.push(`品牌 ${source.brand}`)
  if (source.requires_shipping) items.push('支持发货')
  if (source.drop_shipping_enabled) items.push('支持一件代发')
  const result = items.filter(Boolean).slice(0, 4)
  return result.length ? result : ['精选商品', '支持下单', '库存同步']
}

function buildItemList(profile, detail) {
  const items = [truncate(stripHtml(profile), 64), truncate(stripHtml(detail), 100)].filter(Boolean)
  return items.length ? items : ['建议补充商品简介与详情，用于移动端详情页摘要展示。']
}

function buildZoneSummary(config = {}) {
  const badges = []
  if (config.zone_type === 'REPURCHASE') {
    badges.push(config.package_required ? '需套餐资格' : '无需套餐资格')
    if (config.repurchase_discount_rate != null) badges.push(`复购折扣 ${Number(config.repurchase_discount_rate).toFixed(2).replace(/\.00$/, '')}%`)
    if (config.points_purchase_enabled) badges.push('支持积分支付')
    if (config.balance_purchase_enabled) badges.push('支持余额支付')
    if (config.points_only_enabled) badges.push('纯积分')
    if (config.points_cash_enabled) badges.push('积分+现金')
    if (config.cash_only_enabled) badges.push('纯现金')
    if (config.balance_purchase_enabled && config.balance_only_enabled) badges.push('余额纯付')
    if (config.balance_purchase_enabled && config.balance_points_enabled) badges.push('余额+积分')
  } else if (config.zone_type === 'SELF_OPERATED') {
    if (config.voucher_deduct_min_rate != null && config.voucher_deduct_max_rate != null) {
      badges.push(`兑换券 ${Number(config.voucher_deduct_min_rate)}-${Number(config.voucher_deduct_max_rate)}%`)
    }
    if (config.ai_coupon_reward_rate != null) badges.push(`返 AI 券 ${Number(config.ai_coupon_reward_rate)}%`)
    if (config.ai_coupon_max_deduct_rate != null) badges.push(`AI 券抵扣 ${Number(config.ai_coupon_max_deduct_rate)}%`)
    if (config.points_only_enabled) badges.push('纯积分')
    if (config.points_cash_enabled) badges.push('积分+现金')
    if (config.cash_only_enabled) badges.push('纯现金')
    if (config.balance_purchase_enabled && config.balance_only_enabled) badges.push('余额纯付')
    if (config.balance_purchase_enabled && config.balance_points_enabled) badges.push('余额+积分')
  } else if (config.zone_type === 'HOT_SALE') {
    if (config.points_purchase_enabled) badges.push('支持积分支付')
    if (config.balance_purchase_enabled) badges.push('支持余额支付')
    if (config.points_only_enabled) badges.push('纯积分')
    if (config.points_cash_enabled) badges.push('积分+现金')
    if (config.cash_only_enabled) badges.push('纯现金')
    if (config.balance_purchase_enabled && config.balance_only_enabled) badges.push('余额纯付')
    if (config.balance_purchase_enabled && config.balance_points_enabled) badges.push('余额+积分')
    if (config.flash_sale_enabled) badges.push('开启闪购')
    if (config.per_user_limit != null) badges.push(`每人限购 ${config.per_user_limit} 件`)
  } else if (config.zone_type === 'LOCAL_LIFE') {
    if (config.points_purchase_enabled) badges.push('支持积分支付')
    if (config.balance_purchase_enabled) badges.push('支持余额支付')
    if (config.points_only_enabled) badges.push('纯积分')
    if (config.points_cash_enabled) badges.push('积分+现金')
    if (config.cash_only_enabled) badges.push('纯现金')
    if (config.balance_purchase_enabled && config.balance_only_enabled) badges.push('余额纯付')
    if (config.balance_purchase_enabled && config.balance_points_enabled) badges.push('余额+积分')
    if (config.merchant_commission_rule_id) badges.push(`分佣规则 #${config.merchant_commission_rule_id}`)
    if (config.device_revenue_enabled) badges.push('联动设备收益')
  }
  return { badges: badges.slice(0, 4) }
}

const formPreview = computed(() => {
  const gallery = splitMedia(form.value.icons)
  const image = firstFilled([form.value.cover, form.value.main_image, gallery[0]])
  const categoryName = firstFilled([form.value.brand, zoneLabelMap[form.value.zone_type], '精选商品'])
  const tag = form.value.is_hot ? '热销' : categoryName
  const description = truncate(stripHtml(form.value.profile) || stripHtml(form.value.detail) || '建议补充商品简介，移动端卡片会更完整。', 88)
  const features = buildFeatureList({
    feature: form.value.feature,
    brand: form.value.brand,
    requires_shipping: form.value.requires_shipping,
    drop_shipping_enabled: form.value.drop_shipping_enabled
  })
  const items = buildItemList(form.value.profile, form.value.detail)

  return {
    title: form.value.product_name || '商品名称待完善',
    image,
    categoryName,
    tag,
    description,
    gallery,
    features,
    items
  }
})

const zoneConfigSummary = computed(() => buildZoneSummary(zoneConfigForm.value))

function formatMoney(value) {
  return value == null ? '--' : `¥${Number(value).toFixed(2)}`
}

function productTypeLabel(type) {
  return { PHYSICAL: '实物商品', SERVICE: '服务商品', ACTIVITY: '活动商品' }[type] || type || '--'
}

function ownerTypeLabel(type) {
  return { SELF_OPERATED: '平台自营', SUPPLIER: '供应商商品', LOCAL_MERCHANT: '本地商家' }[type] || type || '--'
}

function statusType(status) {
  return { DRAFT: 'info', PENDING_REVIEW: 'warning', APPROVED: 'success', REJECTED: 'danger', ON_SHELF: 'success', OFF_SHELF: 'info' }[status] || 'info'
}

function statusLabel(status) {
  return { DRAFT: '草稿', PENDING_REVIEW: '待审核', APPROVED: '已通过', REJECTED: '已驳回', ON_SHELF: '已上架', OFF_SHELF: '已下架' }[status] || status || '--'
}

function publishGuardType(guard) {
  if (!guard?.required) return 'info'
  return guard.eligible ? 'success' : 'warning'
}

function publishGuardText(guard) {
  if (!guard?.required) return '无需校验'
  return guard.eligible ? '可发布' : '待补资格'
}

function previewFeatureList(row) {
  const items = row.mobile_preview?.features || row.features || []
  return items.slice(0, 3)
}

function canSubmitReview(row) {
  return ['DRAFT', 'REJECTED'].includes(row.status) && (row.publish_guard?.eligible ?? true)
}

function canShelfUp(row) {
  return ['APPROVED', 'OFF_SHELF'].includes(row.status) && (row.publish_guard?.eligible ?? true)
}

function canShelfDown(row) {
  return row.status === 'ON_SHELF'
}

function zoneCount(zoneCode) {
  return products.value.filter((item) => item.zone_type === zoneCode).length
}

function toggleZone(zoneCode) {
  filters.zone_type = filters.zone_type === zoneCode ? '' : zoneCode
}

function resetFilters() {
  filters.keyword = ''
  filters.zone_type = ''
  filters.status = ''
  filters.owner_type = ''
}

function handleSelectionChange(rows) {
  selectedRows.value = rows
}

function clearSelection() {
  tableRef.value?.clearSelection()
  selectedRows.value = []
}

function normalizeForm(row = {}) {
  return {
    product_name: row.product_name || '',
    product_type: row.product_type || 'PHYSICAL',
    zone_type: row.zone_type || 'REPURCHASE',
    owner_type: row.owner_type || 'SELF_OPERATED',
    owner_id: row.owner_id ?? null,
    market_price: row.market_price == null ? null : Number(row.market_price),
    sale_price: row.sale_price == null ? 0 : Number(row.sale_price),
    cost_price: row.cost_price == null ? null : Number(row.cost_price),
    stock: row.stock == null ? 0 : Number(row.stock),
    main_image: row.main_image || '',
    cover: row.cover || '',
    icons: row.icons || '',
    brand: row.brand || '',
    profile: row.profile || '',
    detail: row.detail || '',
    feature: row.feature || '',
    order_by: row.order_by == null ? null : Number(row.order_by),
    is_hot: Boolean(Number(row.is_hot || 0)),
    requires_shipping: Boolean(row.requires_shipping),
    drop_shipping_enabled: Boolean(row.drop_shipping_enabled)
  }
}

function normalizeZoneConfig(data = {}) {
  return {
    ...createDefaultZoneConfig(),
    ...data,
    configured: Boolean(data.configured),
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
    points_only_enabled: Boolean(data.points_only_enabled),
    points_cash_enabled: data.points_cash_enabled == null ? true : Boolean(data.points_cash_enabled),
    cash_only_enabled: data.cash_only_enabled == null ? true : Boolean(data.cash_only_enabled),
    balance_only_enabled: data.balance_only_enabled == null ? true : Boolean(data.balance_only_enabled),
    balance_points_enabled: data.balance_points_enabled == null ? true : Boolean(data.balance_points_enabled),
    flash_sale_enabled: Boolean(data.flash_sale_enabled),
    device_revenue_enabled: Boolean(data.device_revenue_enabled)
  }
}

async function loadData() {
  loading.value = true
  try {
    const [productRows, supplierRows] = await Promise.all([
      productApi.list({
        keyword: filters.keyword || undefined,
        zone_type: filters.zone_type || undefined,
        status: filters.status || undefined,
        owner_type: filters.owner_type || undefined
      }),
      supplierApi.list()
    ])
    products.value = productRows || []
    suppliers.value = supplierRows || []
    selectedRows.value = selectedRows.value.filter((item) => products.value.some((row) => row.id === item.id))
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  currentEditingProduct.value = null
  form.value = createDefaultForm(filters.zone_type || 'REPURCHASE')
  dialogVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  currentEditingProduct.value = row
  form.value = normalizeForm(row)
  dialogVisible.value = true
}

async function saveProduct() {
  if (!form.value.product_name.trim()) {
    return ElMessage.warning('请先填写商品名称')
  }
  if (form.value.owner_type === 'SUPPLIER' && !form.value.owner_id) {
    return ElMessage.warning('请选择供应商归属')
  }

  saving.value = true
  try {
    const payload = {
      ...form.value,
      owner_id: form.value.owner_type === 'SUPPLIER' ? form.value.owner_id : null,
      requires_shipping: form.value.zone_type === 'LOCAL_LIFE' ? false : form.value.requires_shipping,
      cover: form.value.cover || form.value.main_image || null
    }
    if (editingId.value) {
      await productApi.update(editingId.value, payload)
      ElMessage.success('商品已更新')
    } else {
      await productApi.create(payload)
      ElMessage.success('商品已创建')
    }
    dialogVisible.value = false
    currentEditingProduct.value = null
    await loadData()
  } finally {
    saving.value = false
  }
}

async function applyBatchHot(isHot) {
  if (!selectedIds.value.length) {
    return ElMessage.warning('请先选择商品')
  }
  await productApi.batchMerchandise({ product_ids: selectedIds.value, is_hot: isHot })
  ElMessage.success(isHot ? '已批量设为热门' : '已批量取消热门')
  clearSelection()
  await loadData()
}

async function applyBatchSort() {
  if (!selectedIds.value.length) {
    return ElMessage.warning('请先选择商品')
  }
  if (batchForm.order_by_start == null) {
    return ElMessage.warning('请填写排序起始值')
  }
  await productApi.batchMerchandise({
    product_ids: selectedIds.value,
    order_by_start: Number(batchForm.order_by_start),
    order_by_step: Number(batchForm.order_by_step || 1)
  })
  ElMessage.success('批量排序已更新')
  clearSelection()
  await loadData()
}

async function applyBatchStatus(operation) {
  if (!selectedIds.value.length) {
    return ElMessage.warning('请先选择商品')
  }
  const labelMap = {
    SUBMIT_REVIEW: '提审',
    ON_SHELF: '上架',
    OFF_SHELF: '下架'
  }
  const label = labelMap[operation] || '处理'
  await ElMessageBox.confirm(`确认批量${label}已选商品吗？`, '批量操作', { type: 'warning' })
  await productApi.batchStatus({ product_ids: selectedIds.value, operation })
  ElMessage.success(`已批量${label}商品`)
  clearSelection()
  await loadData()
}

async function submitReview(row) {
  await ElMessageBox.confirm(`确认提交商品“${row.product_name}”进入审核吗？`, '提交审核', { type: 'warning' })
  await productApi.submitReview(row.id)
  ElMessage.success('商品已提交审核')
  await loadData()
}

async function auditProduct(row, auditStatus) {
  const label = auditStatus === 'APPROVED' ? '通过' : '驳回'
  await ElMessageBox.confirm(`确认${label}商品“${row.product_name}”吗？`, '商品审核', { type: 'warning' })
  await productApi.audit(row.id, { audit_status: auditStatus })
  ElMessage.success(`已${label}商品审核`)
  await loadData()
}

async function updateShelf(row, status) {
  const label = status === 'ON_SHELF' ? '上架' : '下架'
  await ElMessageBox.confirm(`确认${label}商品“${row.product_name}”吗？`, '商品状态', { type: 'warning' })
  await productApi.updateStatus(row.id, { status })
  ElMessage.success(`商品已${label}`)
  await loadData()
}

async function removeProduct(row) {
  await ElMessageBox.confirm(`确认删除商品“${row.product_name}”吗？删除后不可恢复。`, '删除商品', { type: 'warning' })
  await productApi.remove(row.id)
  ElMessage.success('商品已删除')
  await loadData()
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
  if (!zoneConfigForm.value.points_only_enabled && !zoneConfigForm.value.points_cash_enabled && !zoneConfigForm.value.cash_only_enabled) {
    return ElMessage.warning('请至少开启一种购买方式')
  }
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
      points_only_enabled: zoneConfigForm.value.points_only_enabled,
      points_cash_enabled: zoneConfigForm.value.points_cash_enabled,
      cash_only_enabled: zoneConfigForm.value.cash_only_enabled,
      balance_only_enabled: zoneConfigForm.value.balance_only_enabled,
      balance_points_enabled: zoneConfigForm.value.balance_points_enabled,
      flash_sale_enabled: zoneConfigForm.value.flash_sale_enabled,
      per_user_limit: zoneConfigForm.value.per_user_limit,
      merchant_commission_rule_id: zoneConfigForm.value.merchant_commission_rule_id,
      device_revenue_enabled: zoneConfigForm.value.device_revenue_enabled
    })
    ElMessage.success('专区规则已保存')
    zoneConfigVisible.value = false
    await loadData()
  } finally {
    zoneConfigSaving.value = false
  }
}

function triggerImport() {
  importInputRef.value?.click()
}

function downloadFailedRows(result) {
  const failedRows = result.failed_rows || []
  const headers = []
  for (const item of failedRows) {
    for (const key of Object.keys(item.raw_row || {})) {
      if (!headers.includes(key)) headers.push(key)
    }
  }
  const rows = [[...headers, '失败原因']]
  for (const item of failedRows) {
    rows.push([...headers.map((key) => item.raw_row?.[key] || ''), item.reason || ''])
  }
  const csv = `\ufeff${rows.map((row) => row.map((cell) => `"${String(cell ?? '').replaceAll('"', '""')}"`).join(',')).join('\n')}`
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'product-import-failed-retry-template.csv'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

async function handleImportChange(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return

  importing.value = true
  try {
    const result = await productApi.importExcel(file)
    const preview = (result.failed_rows || [])
      .slice(0, 8)
      .map((item) => `第 ${item.row_number} 行 ${item.product_name}：${item.reason}`)
      .join('\n')
    ElMessage.success(`导入完成：新增 ${result.created_count} 条，更新 ${result.updated_count} 条`)
    if (result.failed_count) {
      downloadFailedRows(result)
      await ElMessageBox.alert(
        `失败 ${result.failed_count} 行，已自动下载可修改后重传的失败模板。\n${preview}${result.failed_count > 8 ? '\n...' : ''}`,
        '导入结果',
        { type: 'warning' }
      )
    }
    await loadData()
  } finally {
    importing.value = false
  }
}

async function downloadTemplate() {
  const blob = await productApi.downloadImportTemplate()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'product-import-template.csv'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

watch(
  () => ({ ...filters }),
  () => {
    loadData()
  },
  { deep: true }
)

watch(dialogVisible, (value) => {
  if (!value) {
    currentEditingProduct.value = null
  }
})

onMounted(loadData)
</script>

<style scoped>
.products-view { display: grid; gap: 18px; }
.filters-wrap { align-items: center; margin-bottom: 16px; }
.zone-card { width: 100%; padding: 20px; text-align: left; cursor: pointer; border: 1px solid var(--brand-line); background: linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(253, 248, 242, 0.92)); }
.zone-card.is-active { border-color: rgba(198, 132, 79, 0.42); box-shadow: 0 18px 36px rgba(166, 110, 62, 0.16); }
.zone-card-title { font-size: 18px; font-weight: 700; color: var(--brand-deep); }
.zone-card-value { margin-top: 10px; font-size: 30px; font-weight: 700; color: var(--brand-accent-deep); }
.zone-card-meta, .cell-meta, .config-desc { margin-top: 8px; color: rgba(58, 45, 36, 0.62); font-size: 12px; line-height: 1.5; }
.cell-title { font-weight: 700; color: var(--brand-deep); }
.product-title-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.cell-title.small { font-size: 13px; }
.product-cell { display: grid; grid-template-columns: 72px minmax(0, 1fr); gap: 12px; align-items: start; }
.product-thumb { width: 72px; height: 72px; border-radius: 16px; overflow: hidden; background: rgba(241, 232, 220, 0.7); }
.product-thumb.is-empty, .mobile-card__image.is-empty { display: grid; place-items: center; color: rgba(58, 45, 36, 0.5); font-size: 12px; }
.product-copy { min-width: 0; }
.tag-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.mini-tag { display: inline-flex; align-items: center; padding: 4px 10px; border-radius: 999px; background: rgba(198, 132, 79, 0.12); color: var(--brand-deep); font-size: 12px; line-height: 1.2; }
.mini-tag.warm { background: rgba(214, 96, 74, 0.14); color: #b44636; }
.mini-tag.muted { background: rgba(58, 45, 36, 0.08); color: rgba(58, 45, 36, 0.7); }
.batch-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 16px; padding: 14px 16px; border-radius: 16px; background: linear-gradient(135deg, rgba(252, 248, 241, 0.96), rgba(255, 255, 255, 0.96)); border: 1px solid rgba(198, 132, 79, 0.16); }
.batch-toolbar__info { flex: 1; color: rgba(58, 45, 36, 0.76); line-height: 1.6; }
.batch-toolbar__actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.mobile-card { display: grid; grid-template-columns: 88px minmax(0, 1fr); gap: 12px; padding: 12px; border-radius: 20px; background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 244, 238, 0.92)); border: 1px solid rgba(198, 132, 79, 0.12); }
.mobile-card--editor { grid-template-columns: 1fr; padding: 14px; }
.mobile-card__cover { height: 104px; border-radius: 16px; overflow: hidden; background: rgba(241, 232, 220, 0.7); }
.mobile-card__cover--editor { height: 168px; }
.mobile-card__image { width: 100%; height: 100%; }
.mobile-card__body { min-width: 0; }
.mobile-card__tag { display: inline-flex; align-items: center; padding: 4px 10px; border-radius: 999px; background: rgba(214, 96, 74, 0.14); color: #b44636; font-size: 12px; font-weight: 600; }
.mobile-card__title { margin-top: 8px; font-size: 15px; font-weight: 700; color: var(--brand-deep); line-height: 1.5; }
.mobile-card__desc { margin-top: 8px; color: rgba(58, 45, 36, 0.68); line-height: 1.6; font-size: 12px; }
.mobile-card__price-row { display: flex; align-items: baseline; gap: 8px; margin-top: 10px; }
.mobile-card__price { color: #d45640; font-size: 20px; font-weight: 800; }
.mobile-card__market { color: rgba(58, 45, 36, 0.42); text-decoration: line-through; font-size: 12px; }
.drawer-layout { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(340px, 0.8fr); gap: 18px; }
.preview-panel { position: sticky; top: 0; align-self: start; }
.preview-panel__head { display: flex; align-items: start; justify-content: space-between; gap: 12px; margin-bottom: 18px; }
.preview-panel__head h3 { margin: 0; color: var(--brand-deep); }
.preview-panel__head p { margin: 8px 0 0; color: rgba(58, 45, 36, 0.62); line-height: 1.6; }
.preview-phone { padding: 14px; border-radius: 28px; background: radial-gradient(circle at top, rgba(255, 255, 255, 0.96), rgba(246, 239, 230, 0.96)); border: 1px solid rgba(198, 132, 79, 0.12); }
.preview-phone__screen { display: grid; gap: 14px; padding: 16px; border-radius: 24px; background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(250, 246, 241, 0.98)); }
.preview-block { padding: 14px; border-radius: 18px; background: rgba(255, 255, 255, 0.88); border: 1px solid rgba(58, 45, 36, 0.08); }
.preview-block__title { font-weight: 700; color: var(--brand-deep); }
.preview-list { margin: 10px 0 0; padding-left: 18px; color: rgba(58, 45, 36, 0.76); line-height: 1.7; }
.form-split { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.config-head { margin-bottom: 16px; }
.config-head h3 { margin: 12px 0 8px; color: var(--brand-deep); }
.config-tips { margin-top: 12px; padding: 14px 16px; background: rgba(198, 132, 79, 0.1); border-radius: 14px; color: rgba(58, 45, 36, 0.78); line-height: 1.7; }
.purchase-mode-box { margin-top: 14px; padding: 14px; border-radius: 14px; border: 1px solid rgba(198, 132, 79, 0.16); background: rgba(255, 255, 255, 0.7); }
.dialog-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 18px; }
@media (max-width: 1260px) { .drawer-layout { grid-template-columns: 1fr; } .preview-panel { position: static; } }
@media (max-width: 960px) { .form-split, .product-cell, .mobile-card { grid-template-columns: 1fr; } .batch-toolbar { flex-direction: column; align-items: stretch; } }
</style>
