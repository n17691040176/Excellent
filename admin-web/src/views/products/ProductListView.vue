<template>
  <div class="products-view">
    <!-- 页面头部 -->
    <PageHeader title="商品管理" description="对齐移动端商品卡片、详情文案和专区规则，支持 Excel / CSV 一键导入。">
      <template #actions>
        <el-button plain @click="loadData">刷新数据</el-button>
        <el-button plain @click="downloadTemplate">下载导入模板</el-button>
        <el-button :loading="importing" @click="triggerImport">Excel 导入</el-button>
        <el-button v-permission="'products:create'" type="primary" :disabled="loading" @click="openCreate">新增商品</el-button>
      </template>
    </PageHeader>

    <input ref="importInputRef" type="file" accept=".xlsx,.csv" style="display: none;" @change="handleImportChange" />

    <!-- 指标卡片 -->
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

    <!-- 专区切换 -->
    <div class="split-grid">
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

    <!-- 数据卡片 -->
    <div class="panel-card data-card">
      <!-- 筛选栏 -->
      <FilterBar :fields="filterFields" v-model="filters" @search="handleSearch" @reset="handleReset" />

      <!-- 批量操作栏 -->
      <div v-if="selectedRows.length" class="batch-toolbar">
        <div class="batch-toolbar__info">
          已选 {{ selectedRows.length }} 个商品。第一条会拿到最高排序值，用于快速对齐移动端列表顺序。
        </div>
        <div class="batch-toolbar__actions">
          <el-input-number v-model="batchForm.order_by_start" :min="0" :step="10" controls-position="right" />
          <el-input-number v-model="batchForm.order_by_step" :min="1" :step="1" controls-position="right" />
          <el-button plain @click="applyBatchHot(true)">设为爆款推荐</el-button>
          <el-button plain @click="applyBatchHot(false)">取消爆款推荐</el-button>
          <el-button type="primary" @click="applyBatchSort">批量排序</el-button>
          <el-button plain @click="applyBatchStatus('SUBMIT_REVIEW')">批量提审</el-button>
          <el-button plain @click="applyBatchStatus('ON_SHELF')">批量上架</el-button>
          <el-button plain @click="applyBatchStatus('OFF_SHELF')">批量下架</el-button>
          <el-button link type="primary" @click="clearSelection">清空选择</el-button>
        </div>
      </div>

      <!-- 数据表格 -->
      <el-table ref="tableRef" v-loading="loading" :data="pagedRows" border @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="50" fixed="left" />
        <el-table-column prop="id" label="ID" width="90" />
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
                  <span class="mini-tag">{{ row.category_name || getCategoryName(row.category_id) || '未分类' }}</span>
                  <span v-if="row.tag" class="mini-tag warm">{{ row.tag }}</span>
                  <span class="mini-tag muted">图集 {{ row.gallery_count || 0 }}</span>
                </div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="移动端预览" min-width="300" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="mobile-preview-cell">
              <el-image
                v-if="row.mobile_preview?.image"
                :src="row.mobile_preview.image"
                fit="cover"
                class="preview-thumb"
              />
              <div v-else class="preview-thumb is-empty">待补图</div>
              <div class="preview-info">
                <div class="mobile-card__tag">{{ row.mobile_preview?.tag || '精选商品' }}</div>
                <div class="preview-title">{{ row.mobile_preview?.title || row.product_name }}</div>
                <div class="preview-price">
                  <span class="price-current">¥{{ formatMoney(row.sale_price) }}</span>
                  <span v-if="row.market_price" class="price-market">¥{{ formatMoney(row.market_price) }}</span>
                </div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="价格/库存" width="130">
          <template #default="{ row }">
            <div class="amount-text">¥{{ formatMoney(row.sale_price) }}</div>
            <div class="cell-meta">库存 {{ row.stock || 0 }}</div>
          </template>
        </el-table-column>
        <el-table-column label="运营" width="150">
          <template #default="{ row }">
            <el-switch
              :model-value="Boolean(Number(row.is_hot))"
              active-text="爆款"
              inactive-text="普通"
              inline-prompt
              @change="(val) => toggleHot(row, val)"
            />
            <div class="cell-meta">排序 {{ row.order_by ?? '--' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <StatusTag :type="statusType(row.status)">{{ statusLabel(row.status) }}</StatusTag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="action-group">
              <el-button v-permission="'products:edit'" link type="primary" @click="openEdit(row)">编辑</el-button>
              <el-button v-permission="'products:submit-review'" link :disabled="!canSubmitReview(row)" @click="submitReview(row)">提审</el-button>
              <el-dropdown v-if="hasRowActions(row)" trigger="click" @command="(cmd) => handleRowAction(cmd, row)">
                <el-button link>
                  更多
                  <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item v-if="canShelfUp(row)" command="shelfUp">上架</el-dropdown-item>
                    <el-dropdown-item v-if="canShelfDown(row)" command="shelfDown">下架</el-dropdown-item>
                    <el-dropdown-item v-if="canAuditProducts && row.status === 'PENDING_REVIEW'" command="approve" divided>审核通过</el-dropdown-item>
                    <el-dropdown-item v-if="canAuditProducts && row.status === 'PENDING_REVIEW'" command="reject">审核驳回</el-dropdown-item>
                    <el-dropdown-item v-if="canEditProducts" command="zoneConfig">规则配置</el-dropdown-item>
                    <el-dropdown-item v-if="canEditProducts" command="delete" divided style="color: var(--danger-600);">
                      删除
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        class="table-pagination"
        layout="total, sizes, prev, pager, next"
        :page-sizes="[10, 20, 50, 100]"
        :total="filteredRows.length"
      />
    </div>

    <!-- 商品编辑抽屉 -->
    <el-drawer v-model="dialogVisible" :title="dialogTitle" size="1100px" direction="rtl">
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
              <el-form-item v-if="editingId" label="专区">
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
              <el-form-item label="商品分类" required>
                <el-select v-model="form.category_id" placeholder="请选择已启用分类">
                  <el-option v-for="item in categoryOptions" :key="item.value" :label="item.label" :value="item.value" />
                </el-select>
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
              <el-form-item label="爆款推荐标记">
                <el-switch v-model="form.is_hot" />
              </el-form-item>
            </div>

            <el-form-item label="商品主图">
              <div class="product-image-field">
                <el-image v-if="form.main_image" :src="form.main_image" fit="cover" class="product-image-preview" />
                <div v-else class="product-image-preview is-empty">暂无主图</div>
                <div class="product-image-controls">
                  <div class="upload-action-row">
                    <el-upload
                      :show-file-list="false"
                      accept="image/jpeg,image/png,image/webp,image/gif"
                      :http-request="(options) => uploadSingleProductImage(options, 'main_image')"
                    >
                      <el-button type="primary" plain :loading="uploadingImageFields.main_image">上传主图</el-button>
                    </el-upload>
                    <el-button v-if="form.main_image" plain @click="form.main_image = ''">清空</el-button>
                  </div>
                  <el-input v-model="form.main_image" placeholder="上传后自动回填，也可粘贴 HTTPS 图片地址" />
                  <div class="upload-hint">支持 JPG、PNG、WebP、GIF，单张不超过 5MB。</div>
                </div>
              </div>
            </el-form-item>

            <el-form-item label="商品封面">
              <div class="product-image-field">
                <el-image v-if="form.cover" :src="form.cover" fit="cover" class="product-image-preview" />
                <div v-else class="product-image-preview is-empty">默认使用主图</div>
                <div class="product-image-controls">
                  <div class="upload-action-row">
                    <el-upload
                      :show-file-list="false"
                      accept="image/jpeg,image/png,image/webp,image/gif"
                      :http-request="(options) => uploadSingleProductImage(options, 'cover')"
                    >
                      <el-button type="primary" plain :loading="uploadingImageFields.cover">上传封面</el-button>
                    </el-upload>
                    <el-button v-if="form.cover" plain @click="form.cover = ''">使用主图</el-button>
                  </div>
                  <el-input v-model="form.cover" placeholder="留空时保存商品会自动使用主图" />
                </div>
              </div>
            </el-form-item>

            <el-form-item label="商品轮播图">
              <div class="gallery-editor">
                <div class="upload-action-row">
                  <el-upload
                    multiple
                    :show-file-list="false"
                    accept="image/jpeg,image/png,image/webp,image/gif"
                    :http-request="uploadGalleryImage"
                  >
                    <el-button type="primary" plain :loading="galleryUploadCount > 0">上传轮播图</el-button>
                  </el-upload>
                  <span class="upload-hint">最多 8 张，可连续选择多张图片。</span>
                </div>
                <div v-if="galleryImages.length" class="gallery-grid">
                  <div v-for="(image, index) in galleryImages" :key="`${image}-${index}`" class="gallery-item">
                    <el-image :src="image" fit="cover" class="gallery-image" />
                    <div class="gallery-order">{{ index + 1 }}</div>
                    <div class="gallery-actions">
                      <el-button link :disabled="index === 0" @click="moveGalleryImage(index, -1)">前移</el-button>
                      <el-button link :disabled="index === galleryImages.length - 1" @click="moveGalleryImage(index, 1)">后移</el-button>
                      <el-button link type="danger" @click="removeGalleryImage(index)">删除</el-button>
                    </div>
                  </div>
                </div>
                <div v-else class="gallery-empty">尚未上传轮播图</div>
                <el-input v-model="form.icons" placeholder="也可粘贴多个 HTTPS 地址，并用英文逗号分隔" />
              </div>
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
                <div v-if="formPreview.gallery.length" class="mobile-gallery-preview">
                  <el-image
                    v-for="(image, index) in formPreview.gallery"
                    :key="`${image}-${index}`"
                    :src="image"
                    fit="cover"
                    class="mobile-gallery-preview__image"
                  />
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
                  <li>当前排序：{{ form.order_by ?? '--' }} / {{ form.is_hot ? '爆款推荐' : '普通商品' }}</li>
                  <li>{{ form.drop_shipping_enabled ? '已开启一件代发' : '未开启一件代发' }}</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- 专区规则配置抽屉 -->
    <el-drawer v-model="zoneConfigVisible" :title="zoneConfigTitle" size="min(560px, 100vw)">
      <div class="panel-card data-card" v-loading="zoneConfigLoading">
        <div class="config-head">
          <div class="soft-tag">{{ zoneLabelMap[zoneConfigForm.zone_type] || '--' }}</div>
          <h3>{{ zoneConfigProduct.product_name || '--' }}</h3>
          <p class="config-desc">{{ zoneDescription }}</p>
          <div class="tag-row">
            <span v-for="item in zoneConfigSummary.badges" :key="item" class="mini-tag">{{ item }}</span>
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
            <el-form-item label="复购折扣率（%）">
              <el-input-number v-model="zoneConfigForm.repurchase_discount_rate" :min="0" :max="100" :step="0.5" :precision="2" controls-position="right" />
            </el-form-item>
          </template>

          <template v-if="zoneConfigForm.zone_type === 'SELF_OPERATED'">
            <div class="form-split">
              <el-form-item label="兑换券最低抵扣比例（%）">
                <el-input-number v-model="zoneConfigForm.voucher_deduct_min_rate" :min="0" :max="100" :step="1" :precision="2" controls-position="right" />
              </el-form-item>
              <el-form-item label="兑换券最高抵扣比例（%）">
                <el-input-number v-model="zoneConfigForm.voucher_deduct_max_rate" :min="0" :max="100" :step="1" :precision="2" controls-position="right" />
              </el-form-item>
            </div>
            <div class="form-split">
              <el-form-item label="购物返 AI 券比例（%）">
                <el-input-number v-model="zoneConfigForm.ai_coupon_reward_rate" :min="0" :max="100" :step="1" :precision="2" controls-position="right" />
              </el-form-item>
              <el-form-item label="AI 券最大抵扣比例（%）">
                <el-input-number v-model="zoneConfigForm.ai_coupon_max_deduct_rate" :min="0" :max="100" :step="1" :precision="2" controls-position="right" />
              </el-form-item>
            </div>
          </template>

          <template v-if="zoneConfigForm.zone_type === 'HOT_SALE'">
            <div class="form-split">
              <el-form-item label="限购件数">
                <el-input-number v-model="zoneConfigForm.per_user_limit" :min="1" :step="1" controls-position="right" />
              </el-form-item>
              <el-form-item label="开启闪购"><el-switch v-model="zoneConfigForm.flash_sale_enabled" /></el-form-item>
            </div>
          </template>

          <template v-if="zoneConfigForm.zone_type === 'LOCAL_LIFE'">
            <div class="form-split">
              <el-form-item label="分佣规则 ID">
                <el-input-number v-model="zoneConfigForm.merchant_commission_rule_id" :min="1" :step="1" controls-position="right" />
              </el-form-item>
              <el-form-item label="设备收益联动"><el-switch v-model="zoneConfigForm.device_revenue_enabled" /></el-form-item>
            </div>
          </template>

          <div class="commission-rule-section">
            <div class="rule-section-heading">
              <div>
                <div class="cell-title small">商品专属分润</div>
                <div class="rule-section-meta">仅对当前商品生效</div>
              </div>
              <el-switch v-model="zoneConfigForm.custom_commission_enabled" />
            </div>

            <template v-if="zoneConfigForm.custom_commission_enabled">
              <el-alert
                title="专属规则启用后，不再触发该商品的通用分润和团队奖。"
                type="warning"
                :closable="false"
                show-icon
                class="commission-rule-alert"
              />
              <el-form-item label="计算方式">
                <el-radio-group v-model="zoneConfigForm.custom_commission_method">
                  <el-radio-button value="RATE">按利润比例</el-radio-button>
                  <el-radio-button value="FIXED_AMOUNT">每件固定金额</el-radio-button>
                </el-radio-group>
              </el-form-item>

              <div v-if="zoneConfigForm.custom_commission_method === 'RATE'" class="commission-value-grid">
                <el-form-item v-for="level in 3" :key="`rate-${level}`" :label="`${levelText[level]}比例（%）`">
                  <el-input-number
                    v-model="zoneConfigForm[`custom_commission_level${level}_rate`]"
                    :min="0"
                    :max="100"
                    :step="0.5"
                    :precision="2"
                    controls-position="right"
                  />
                </el-form-item>
              </div>
              <div v-else class="commission-value-grid">
                <el-form-item v-for="level in 3" :key="`amount-${level}`" :label="`${levelText[level]}金额（元/件）`">
                  <el-input-number
                    v-model="zoneConfigForm[`custom_commission_level${level}_amount`]"
                    :min="0"
                    :step="1"
                    :precision="2"
                    controls-position="right"
                  />
                </el-form-item>
              </div>
            </template>
          </div>

          <div class="payment-method-section">
            <div class="cell-title small">支付方式</div>
            <div class="form-split">
              <el-form-item label="余额支付">
                <el-switch v-model="zoneConfigForm.balance_purchase_enabled" />
              </el-form-item>
              <el-form-item>
                <template #label>
                  <span class="payment-method-label">
                    支付宝支付
                    <el-tag size="small" :type="zoneConfigForm.alipay_provider_ready ? 'success' : 'warning'">
                      {{ zoneConfigForm.alipay_provider_ready ? '配置就绪' : '配置未就绪' }}
                    </el-tag>
                  </span>
                </template>
                <el-switch v-model="zoneConfigForm.alipay_purchase_enabled" />
              </el-form-item>
            </div>
            <el-form-item>
              <template #label>
                <span class="payment-method-label">微信支付 <el-tag size="small" type="info">正在开发</el-tag></span>
              </template>
              <el-switch v-model="zoneConfigForm.wechat_purchase_enabled" disabled />
            </el-form-item>
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
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown } from '@element-plus/icons-vue'

import { productApi, supplierApi, categoryApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'
import { hasPermission } from '@/utils/permission'
import { PageHeader, MetricCard, FilterBar, StatusTag } from '@/components/common'

const userStore = useUserStore()
const canAuditProducts = computed(() => hasPermission(userStore.role, 'products:audit', userStore.permissions))
const levelText = { 1: '一级', 2: '二级', 3: '三级' }
const canEditProducts = computed(() => hasPermission(userStore.role, 'products:edit', userStore.permissions))
const canShelfProducts = computed(() => hasPermission(userStore.role, 'products:shelf', userStore.permissions))
const router = useRouter()
const loading = ref(false)
const products = ref([])
const suppliers = ref([])
const categories = ref([])
const selectedRows = ref([])
const tableRef = ref(null)
const importing = ref(false)
const importInputRef = ref(null)
const dialogVisible = ref(false)
const saving = ref(false)
const uploadingImageFields = reactive({ main_image: false, cover: false })
const galleryUploadCount = ref(0)
const editingId = ref(null)
const zoneConfigVisible = ref(false)
const zoneConfigLoading = ref(false)
const zoneConfigSaving = ref(false)
const zoneConfigProduct = ref({})
const currentEditingProduct = ref(null)

const filters = reactive({ keyword: '', zone_type: '', status: '', owner_type: '' })
const batchForm = reactive({ order_by_start: 1000, order_by_step: 10 })

// 分页
const page = ref(1)
const pageSize = ref(20)

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

// 筛选字段配置
const filterFields = [
  { key: 'keyword', type: 'input', placeholder: '搜索商品名称 / 品牌', width: 240 },
  { key: 'status', type: 'select', label: '状态', options: statusOptions, width: 160 },
  { key: 'owner_type', type: 'select', label: '归属类型', options: ownerTypeFilterOptions, width: 160 }
]

function createDefaultForm() {
  return {
    product_name: '',
    product_type: 'PHYSICAL',
    zone_type: 'SELF_OPERATED',
    owner_type: 'SELF_OPERATED',
    owner_id: null,
    category_id: null,
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
    requires_shipping: true,
    drop_shipping_enabled: false
  }
}

function createDefaultZoneConfig() {
  return {
    product_id: null,
    zone_type: 'SELF_OPERATED',
    configured: false,
    package_required: false,
    package_id: null,
    repurchase_discount_rate: null,
    voucher_deduct_min_rate: null,
    voucher_deduct_max_rate: null,
    ai_coupon_reward_rate: null,
    ai_coupon_max_deduct_rate: null,
    points_purchase_enabled: false,
    balance_purchase_enabled: true,
    alipay_purchase_enabled: true,
    wechat_purchase_enabled: false,
    alipay_provider_ready: false,
    wechat_provider_ready: false,
    points_only_enabled: false,
    points_cash_enabled: true,
    cash_only_enabled: true,
    balance_only_enabled: true,
    balance_points_enabled: true,
    flash_sale_enabled: false,
    per_user_limit: null,
    merchant_commission_rule_id: null,
    device_revenue_enabled: false,
    custom_commission_enabled: false,
    custom_commission_method: 'RATE',
    custom_commission_level1_rate: 0,
    custom_commission_level2_rate: 0,
    custom_commission_level3_rate: 0,
    custom_commission_level1_amount: 0,
    custom_commission_level2_amount: 0,
    custom_commission_level3_amount: 0
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

const categoryOptions = computed(() => {
  return categories.value
    .filter((item) => item.status === 'active' || (editingId.value && String(item.id) === String(form.value.category_id)))
    .map((item) => ({ label: item.name, value: item.id }))
})

const activeCategories = computed(() => categories.value.filter((item) => item.status === 'active'))

const metrics = computed(() => {
  const pending = products.value.filter((item) => item.status === 'PENDING_REVIEW').length
  const onShelf = products.value.filter((item) => item.status === 'ON_SHELF').length
  const legacy = products.value.filter((item) => item.is_legacy_product).length
  const hot = products.value.filter((item) => Number(item.is_hot)).length
  return [
    { label: '商品总数', value: products.value.length, subtext: '当前筛选结果', variant: 'primary' },
    { label: '待审核', value: pending, subtext: '需要后台审核', variant: pending > 0 ? 'warning' : 'neutral' },
    { label: '已上架', value: onShelf, subtext: '前台可见可下单', variant: 'success' },
    { label: '历史商品', value: legacy, subtext: '旧系统导入', variant: 'neutral' },
    { label: '爆款推荐', value: hot, subtext: '移动端爆款推荐标记', variant: hot > 0 ? 'danger' : 'neutral' }
  ]
})

const filteredRows = computed(() => {
  const term = filters.keyword?.trim().toLowerCase() || ''
  return products.value.filter((item) => {
    const hitKeyword =
      !term ||
      (item.product_name || '').toLowerCase().includes(term) ||
      (item.brand || '').toLowerCase().includes(term)
    const hitZone = !filters.zone_type || item.zone_type === filters.zone_type
    const hitStatus = !filters.status || item.status === filters.status
    const hitOwner = !filters.owner_type || item.owner_type === filters.owner_type
    return hitKeyword && hitZone && hitStatus && hitOwner
  })
})

const pagedRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredRows.value.slice(start, start + pageSize.value)
})

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

const galleryImages = computed(() => splitMedia(form.value.icons))

function validateProductImage(file) {
  const supportedTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
  if (!file || !supportedTypes.includes(file.type)) {
    ElMessage.error('仅支持 JPG、PNG、WebP、GIF 图片')
    return false
  }
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error('单张图片不能超过 5MB')
    return false
  }
  return true
}

async function uploadSingleProductImage(options, field) {
  const file = options?.file
  if (!validateProductImage(file)) {
    options?.onError?.(new Error('Invalid image'))
    return
  }
  uploadingImageFields[field] = true
  try {
    const data = await productApi.uploadImage(file)
    if (!data?.url) throw new Error('上传成功但未返回图片地址')
    form.value[field] = data.url
    ElMessage.success(field === 'main_image' ? '主图上传成功' : '封面上传成功')
    options?.onSuccess?.(data)
  } catch (error) {
    console.error(error)
    options?.onError?.(error)
  } finally {
    uploadingImageFields[field] = false
  }
}

async function uploadGalleryImage(options) {
  const file = options?.file
  if (!validateProductImage(file)) {
    options?.onError?.(new Error('Invalid image'))
    return
  }
  if (galleryImages.value.length + galleryUploadCount.value >= 8) {
    ElMessage.warning('轮播图最多上传 8 张')
    options?.onError?.(new Error('Gallery limit reached'))
    return
  }

  galleryUploadCount.value += 1
  try {
    const data = await productApi.uploadImage(file)
    if (!data?.url) throw new Error('上传成功但未返图片地址')
    form.value.icons = [...galleryImages.value, data.url].slice(0, 8).join(',')
    ElMessage.success('轮播图上传成功')
    options?.onSuccess?.(data)
  } catch (error) {
    console.error(error)
    options?.onError?.(error)
  } finally {
    galleryUploadCount.value = Math.max(0, galleryUploadCount.value - 1)
  }
}

function removeGalleryImage(index) {
  form.value.icons = galleryImages.value.filter((_, itemIndex) => itemIndex !== index).join(',')
}

function moveGalleryImage(index, offset) {
  const targetIndex = index + offset
  const items = [...galleryImages.value]
  if (targetIndex < 0 || targetIndex >= items.length) return
  const [item] = items.splice(index, 1)
  items.splice(targetIndex, 0, item)
  form.value.icons = items.join(',')
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
  const businessBadges = []
  const commissionBadges = []
  if (config.custom_commission_enabled) {
    const fixed = config.custom_commission_method === 'FIXED_AMOUNT'
    const suffix = fixed ? '元/件' : '%'
    const field = fixed ? 'amount' : 'rate'
    const values = [1, 2, 3].map((level) => Number(config[`custom_commission_level${level}_${field}`] || 0))
    commissionBadges.push(`专属分润 ${values.join('/')} ${suffix}`)
  } else {
    commissionBadges.push('通用分润')
  }
  if (config.zone_type === 'REPURCHASE') {
    businessBadges.push(config.package_required ? '需套餐资格' : '无需套餐资格')
    if (config.repurchase_discount_rate != null) businessBadges.push(`复购折扣 ${Number(config.repurchase_discount_rate).toFixed(2).replace(/\.00$/, '')}%`)
  } else if (config.zone_type === 'SELF_OPERATED') {
    if (config.voucher_deduct_min_rate != null && config.voucher_deduct_max_rate != null) {
      businessBadges.push(`兑换券 ${Number(config.voucher_deduct_min_rate)}-${Number(config.voucher_deduct_max_rate)}%`)
    }
    if (config.ai_coupon_reward_rate != null) businessBadges.push(`返 AI 券 ${Number(config.ai_coupon_reward_rate)}%`)
    if (config.ai_coupon_max_deduct_rate != null) businessBadges.push(`AI 券抵扣 ${Number(config.ai_coupon_max_deduct_rate)}%`)
  } else if (config.zone_type === 'HOT_SALE') {
    if (config.flash_sale_enabled) businessBadges.push('开启闪购')
    if (config.per_user_limit != null) businessBadges.push(`每人限购 ${config.per_user_limit} 件`)
  } else if (config.zone_type === 'LOCAL_LIFE') {
    if (config.merchant_commission_rule_id) businessBadges.push(`分佣规则 #${config.merchant_commission_rule_id}`)
    if (config.device_revenue_enabled) businessBadges.push('联动设备收益')
  }
  const paymentBadges = [
    config.balance_purchase_enabled ? '余额支付' : null,
    config.alipay_purchase_enabled ? '支付宝支付' : null,
    '微信开发中'
  ].filter(Boolean)
  return { badges: [...commissionBadges, ...paymentBadges, ...businessBadges].slice(0, 5) }
}

const formPreview = computed(() => {
  const gallery = splitMedia(form.value.icons)
  const image = firstFilled([form.value.cover, form.value.main_image, gallery[0]])
  const categoryName = firstFilled([getCategoryName(form.value.category_id), form.value.brand, zoneLabelMap[form.value.zone_type], '精选商品'])
  const tag = form.value.is_hot ? '爆款' : categoryName
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

function getCategoryName(categoryId) {
  if (!categoryId) return ''
  const cat = categories.value.find((c) => String(c.id) === String(categoryId))
  return cat?.name || ''
}

function statusType(status) {
  return { DRAFT: 'default', PENDING_REVIEW: 'warning', APPROVED: 'success', REJECTED: 'danger', ON_SHELF: 'success', OFF_SHELF: 'default' }[status] || 'default'
}

function statusLabel(status) {
  return { DRAFT: '草稿', PENDING_REVIEW: '待审核', APPROVED: '已通过', REJECTED: '已驳回', ON_SHELF: '已上架', OFF_SHELF: '已下架' }[status] || status || '--'
}

function hasRowActions(row) {
  return canShelfUp(row) || canShelfDown(row) || (canAuditProducts.value && row.status === 'PENDING_REVIEW') || (canEditProducts.value && row.status !== 'ON_SHELF')
}

function canSubmitReview(row) {
  return ['DRAFT', 'REJECTED'].includes(row.status) && (row.publish_guard?.eligible ?? true)
}

function canShelfUp(row) {
  return canShelfProducts.value && ['APPROVED', 'OFF_SHELF'].includes(row.status) && (row.publish_guard?.eligible ?? true)
}

function canShelfDown(row) {
  return canShelfProducts.value && row.status === 'ON_SHELF'
}

function zoneCount(zoneCode) {
  return products.value.filter((item) => item.zone_type === zoneCode).length
}

function toggleZone(zoneCode) {
  filters.zone_type = filters.zone_type === zoneCode ? '' : zoneCode
}

function handleSearch() {
  page.value = 1
}

function handleReset() {
  filters.keyword = ''
  filters.status = ''
  filters.owner_type = ''
  page.value = 1
}

function handleSelectionChange(rows) {
  selectedRows.value = rows
}

function clearSelection() {
  tableRef.value?.clearSelection()
  selectedRows.value = []
}

function handleRowAction(cmd, row) {
  switch (cmd) {
    case 'shelfUp':
      updateShelf(row, 'ON_SHELF')
      break
    case 'shelfDown':
      updateShelf(row, 'OFF_SHELF')
      break
    case 'approve':
      auditProduct(row, 'APPROVED')
      break
    case 'reject':
      auditProduct(row, 'REJECTED')
      break
    case 'zoneConfig':
      openZoneConfig(row)
      break
    case 'delete':
      removeProduct(row)
      break
  }
}

function normalizeForm(row = {}) {
  return {
    product_name: row.product_name || '',
    product_type: row.product_type || 'PHYSICAL',
    zone_type: row.zone_type || 'SELF_OPERATED',
    owner_type: row.owner_type || 'SELF_OPERATED',
    owner_id: row.owner_id ?? null,
    category_id: row.category_id ?? null,
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
    custom_commission_method: data.custom_commission_method || 'RATE',
    custom_commission_level1_rate: Number(data.custom_commission_level1_rate || 0),
    custom_commission_level2_rate: Number(data.custom_commission_level2_rate || 0),
    custom_commission_level3_rate: Number(data.custom_commission_level3_rate || 0),
    custom_commission_level1_amount: Number(data.custom_commission_level1_amount || 0),
    custom_commission_level2_amount: Number(data.custom_commission_level2_amount || 0),
    custom_commission_level3_amount: Number(data.custom_commission_level3_amount || 0),
    package_required: Boolean(data.package_required),
    points_purchase_enabled: Boolean(data.points_purchase_enabled),
    balance_purchase_enabled: Boolean(data.balance_purchase_enabled),
    alipay_purchase_enabled: data.alipay_purchase_enabled == null ? true : Boolean(data.alipay_purchase_enabled),
    wechat_purchase_enabled: false,
    alipay_provider_ready: Boolean(data.alipay_provider_ready),
    wechat_provider_ready: false,
    points_only_enabled: Boolean(data.points_only_enabled),
    points_cash_enabled: data.points_cash_enabled == null ? true : Boolean(data.points_cash_enabled),
    cash_only_enabled: data.cash_only_enabled == null ? true : Boolean(data.cash_only_enabled),
    balance_only_enabled: data.balance_only_enabled == null ? true : Boolean(data.balance_only_enabled),
    balance_points_enabled: data.balance_points_enabled == null ? true : Boolean(data.balance_points_enabled),
    flash_sale_enabled: Boolean(data.flash_sale_enabled),
    device_revenue_enabled: Boolean(data.device_revenue_enabled),
    custom_commission_enabled: Boolean(data.custom_commission_enabled)
  }
}

async function loadData() {
  loading.value = true
  try {
    const [productRows, supplierRows, categoryRows] = await Promise.all([
      productApi.list({
        keyword: filters.keyword || undefined,
        zone_type: filters.zone_type || undefined,
        status: filters.status || undefined,
        owner_type: filters.owner_type || undefined
      }),
      supplierApi.list(),
      categoryApi.list()
    ])
    products.value = productRows || []
    suppliers.value = supplierRows || []
    categories.value = categoryRows || []
    selectedRows.value = selectedRows.value.filter((item) => products.value.some((row) => row.id === item.id))
  } finally {
    loading.value = false
  }
}

async function openCreate() {
  if (!activeCategories.value.length) {
    try {
      await ElMessageBox.confirm('新增商品前必须先创建并启用商品分类。', '请先添加分类', {
        confirmButtonText: '前往分类管理',
        cancelButtonText: '取消',
        type: 'warning'
      })
      await router.push('/categories')
    } catch (error) {
      if (error !== 'cancel' && error !== 'close') throw error
    }
    return
  }
  editingId.value = null
  currentEditingProduct.value = null
  form.value = createDefaultForm()
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
  if (!form.value.category_id) {
    return ElMessage.warning('请选择商品分类')
  }
  if (form.value.owner_type === 'SUPPLIER' && !form.value.owner_id) {
    return ElMessage.warning('请选择供应商归属')
  }

  saving.value = true
  try {
    const payload = {
      ...form.value,
      zone_type: editingId.value ? form.value.zone_type : 'SELF_OPERATED',
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
  ElMessage.success(isHot ? '已批量设为爆款推荐' : '已批量取消爆款推荐')
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
  await ElMessageBox.confirm(`确认提交商品"${row.product_name}"进入审核吗？`, '提交审核', { type: 'warning' })
  await productApi.submitReview(row.id)
  ElMessage.success('商品已提交审核')
  await loadData()
}

async function auditProduct(row, auditStatus) {
  const label = auditStatus === 'APPROVED' ? '通过' : '驳回'
  await ElMessageBox.confirm(`确认${label}商品"${row.product_name}"吗？`, '商品审核', { type: 'warning' })
  await productApi.audit(row.id, { audit_status: auditStatus })
  ElMessage.success(`已${label}商品审核`)
  await loadData()
}

async function updateShelf(row, status) {
  const label = status === 'ON_SHELF' ? '上架' : '下架'
  await ElMessageBox.confirm(`确认${label}商品"${row.product_name}"吗？`, '商品状态', { type: 'warning' })
  await productApi.updateStatus(row.id, { status })
  ElMessage.success(`商品已${label}`)
  await loadData()
}

async function toggleHot(row, isHot) {
  try {
    await productApi.update(row.id, { is_hot: isHot })
    ElMessage.success(isHot ? '已标记为爆款' : '已取消爆款标记')
    row.is_hot = isHot ? 1 : 0
  } catch (error) {
    ElMessage.error('更新失败')
    await loadData()
  }
}

async function removeProduct(row) {
  await ElMessageBox.confirm(`确认删除商品"${row.product_name}"吗？删除后不可恢复。`, '删除商品', { type: 'warning' })
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
  if (zoneConfigForm.value.custom_commission_enabled) {
    const fixed = zoneConfigForm.value.custom_commission_method === 'FIXED_AMOUNT'
    const field = fixed ? 'amount' : 'rate'
    const values = [1, 2, 3].map((level) => Number(zoneConfigForm.value[`custom_commission_level${level}_${field}`] || 0))
    if (values.every((value) => value <= 0)) {
      ElMessage.warning('专属分润至少填写一个大于 0 的值')
      return
    }
    if (!fixed && values.reduce((sum, value) => sum + value, 0) > 100) {
      ElMessage.warning('专属分润比例合计不能超过 100%')
      return
    }
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
      alipay_purchase_enabled: zoneConfigForm.value.alipay_purchase_enabled,
      wechat_purchase_enabled: false,
      points_only_enabled: zoneConfigForm.value.points_only_enabled,
      points_cash_enabled: zoneConfigForm.value.points_cash_enabled,
      cash_only_enabled: zoneConfigForm.value.cash_only_enabled,
      balance_only_enabled: zoneConfigForm.value.balance_only_enabled,
      balance_points_enabled: zoneConfigForm.value.balance_points_enabled,
      flash_sale_enabled: zoneConfigForm.value.flash_sale_enabled,
      per_user_limit: zoneConfigForm.value.per_user_limit,
      merchant_commission_rule_id: zoneConfigForm.value.merchant_commission_rule_id,
      device_revenue_enabled: zoneConfigForm.value.device_revenue_enabled,
      custom_commission_enabled: zoneConfigForm.value.custom_commission_enabled,
      custom_commission_method: zoneConfigForm.value.custom_commission_method,
      custom_commission_level1_rate: zoneConfigForm.value.custom_commission_level1_rate,
      custom_commission_level2_rate: zoneConfigForm.value.custom_commission_level2_rate,
      custom_commission_level3_rate: zoneConfigForm.value.custom_commission_level3_rate,
      custom_commission_level1_amount: zoneConfigForm.value.custom_commission_level1_amount,
      custom_commission_level2_amount: zoneConfigForm.value.custom_commission_level2_amount,
      custom_commission_level3_amount: zoneConfigForm.value.custom_commission_level3_amount
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

watch(dialogVisible, (value) => {
  if (!value) {
    currentEditingProduct.value = null
  }
})

onMounted(loadData)
</script>

<style scoped>
@import '@/styles/variables.css';

.products-view {
  display: grid;
  gap: var(--space-4);
}

.data-card {
  padding: var(--space-5);
}

.zone-card {
  width: 100%;
  padding: var(--space-5);
  text-align: left;
  cursor: pointer;
  border: 1px solid var(--border-default);
  background: var(--bg-surface);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.zone-card.is-active {
  border-color: var(--primary-mid);
  box-shadow: var(--shadow-lg);
}

.zone-card-title {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}

.zone-card-value {
  margin-top: var(--space-2);
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  color: var(--primary-deep);
}

.zone-card-meta,
.cell-meta,
.config-desc {
  margin-top: var(--space-2);
  color: var(--text-muted);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
}

.cell-title {
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.cell-title.small {
  font-size: var(--text-sm);
}

.product-title-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.product-cell {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: var(--space-3);
  align-items: start;
}

.product-thumb {
  width: 72px;
  height: 72px;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--bg-muted);
}

.product-thumb.is-empty {
  display: grid;
  place-items: center;
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.product-copy {
  min-width: 0;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

.mini-tag {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--primary-100);
  color: var(--text-primary);
  font-size: var(--text-xs);
  line-height: 1.2;
}

.mini-tag.warm {
  background: var(--danger-50);
  color: var(--danger-600);
}

.mini-tag.muted {
  background: var(--bg-muted);
  color: var(--text-muted);
}

.batch-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  background: var(--bg-surface);
  border: 1px solid var(--primary-100);
}

.batch-toolbar__info {
  flex: 1;
  color: var(--text-secondary);
  line-height: var(--leading-relaxed);
}

.batch-toolbar__actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

/* 移动端预览单元格 */
.mobile-preview-cell {
  display: flex;
  gap: var(--space-3);
  align-items: center;
}

.preview-thumb {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--bg-muted);
  flex-shrink: 0;
}

.preview-thumb.is-empty {
  display: grid;
  place-items: center;
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.preview-info {
  min-width: 0;
}

.preview-title {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview-price {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  margin-top: var(--space-1);
}

.price-current {
  color: var(--danger-500);
  font-weight: var(--font-bold);
}

.price-market {
  color: var(--text-muted);
  font-size: var(--text-xs);
  text-decoration: line-through;
}

/* 移动端卡片 */
.mobile-card__tag {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--danger-50);
  color: var(--danger-600);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.mobile-card {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: var(--space-3);
  padding: var(--space-3);
  border-radius: var(--radius-xl);
  background: var(--bg-surface);
  border: 1px solid var(--primary-100);
}

.mobile-card--editor {
  grid-template-columns: 1fr;
  padding: var(--space-4);
}

.mobile-card__cover {
  height: 104px;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--bg-muted);
}

.mobile-card__cover--editor {
  height: 168px;
}

.mobile-gallery-preview {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: 64px;
  gap: var(--space-2);
  overflow-x: auto;
  padding-bottom: var(--space-1);
}

.mobile-gallery-preview__image {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
}

.mobile-card__image {
  width: 100%;
  height: 100%;
}

.mobile-card__image.is-empty {
  display: grid;
  place-items: center;
  color: var(--text-muted);
  font-size: var(--text-sm);
}

.mobile-card__body {
  min-width: 0;
}

.mobile-card__title {
  margin-top: var(--space-2);
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  line-height: var(--leading-relaxed);
}

.mobile-card__desc {
  margin-top: var(--space-2);
  color: var(--text-secondary);
  line-height: var(--leading-relaxed);
  font-size: var(--text-sm);
}

.mobile-card__price-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

.mobile-card__price {
  color: var(--danger-500);
  font-size: var(--text-xl);
  font-weight: var(--font-black);
}

.mobile-card__market {
  color: var(--text-muted);
  text-decoration: line-through;
  font-size: var(--text-sm);
}

.drawer-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(340px, 0.8fr);
  gap: var(--space-4);
}

.preview-panel {
  position: sticky;
  top: 0;
  align-self: start;
}

.preview-panel__head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.preview-panel__head h3 {
  margin: 0;
  color: var(--text-primary);
}

.preview-panel__head p {
  margin: var(--space-2) 0 0;
  color: var(--text-muted);
  line-height: var(--leading-relaxed);
}

.preview-phone {
  padding: var(--space-4);
  border-radius: var(--radius-xl);
  background: var(--bg-surface);
  border: 1px solid var(--primary-100);
}

.preview-phone__screen {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-4);
  border-radius: var(--radius-xl);
  background: var(--bg-surface);
}

.preview-block {
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid var(--border-light);
}

.preview-block__title {
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.preview-list {
  margin: var(--space-2) 0 0;
  padding-left: var(--space-5);
  color: var(--text-secondary);
  line-height: var(--leading-loose);
}

.form-split {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4);
}

.product-image-field {
  display: grid;
  grid-template-columns: 128px minmax(0, 1fr);
  gap: var(--space-4);
  width: 100%;
}

.product-image-preview {
  width: 128px;
  height: 128px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-light);
  background: var(--bg-muted);
}

.product-image-preview.is-empty {
  display: grid;
  place-items: center;
  padding: var(--space-3);
  color: var(--text-muted);
  font-size: var(--text-sm);
  text-align: center;
}

.product-image-controls,
.gallery-editor {
  display: grid;
  gap: var(--space-3);
  width: 100%;
}

.upload-action-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.upload-hint {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(138px, 1fr));
  gap: var(--space-3);
}

.gallery-item {
  position: relative;
  overflow: hidden;
  padding: var(--space-2);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  background: var(--bg-surface);
}

.gallery-image {
  width: 100%;
  height: 112px;
  border-radius: var(--radius-md);
}

.gallery-order {
  position: absolute;
  top: var(--space-3);
  left: var(--space-3);
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: 999px;
  color: #fff;
  background: rgba(15, 23, 42, 0.72);
  font-size: var(--text-xs);
}

.gallery-actions {
  display: flex;
  justify-content: center;
  margin-top: var(--space-1);
}

.gallery-empty {
  display: grid;
  place-items: center;
  min-height: 92px;
  border: 1px dashed var(--border-light);
  border-radius: var(--radius-lg);
  color: var(--text-muted);
  background: var(--bg-muted);
}

.config-head {
  margin-bottom: var(--space-4);
}

.config-head h3 {
  margin: var(--space-3) 0 var(--space-2);
  color: var(--text-primary);
}

.config-tips {
  margin-top: var(--space-3);
  padding: var(--space-4);
  background: var(--primary-50);
  border-radius: var(--radius-lg);
  color: var(--text-secondary);
  line-height: var(--leading-relaxed);
}

.payment-method-section {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-light);
}

.commission-rule-section {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-light);
}

.rule-section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-3);
}

.rule-section-meta {
  margin-top: var(--space-1);
  color: var(--text-muted);
  font-size: var(--font-size-sm);
}

.commission-rule-alert {
  margin-bottom: var(--space-4);
}

.commission-value-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
}

.commission-value-grid :deep(.el-input-number) {
  width: 100%;
}

.payment-method-label {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  margin-top: var(--space-4);
}

.table-pagination {
  margin-top: var(--space-5);
  justify-content: flex-end;
}

.action-group {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.amount-text {
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

@media (max-width: 1260px) {
  .drawer-layout {
    grid-template-columns: 1fr;
  }

  .preview-panel {
    position: static;
  }
}

@media (max-width: 960px) {
  .form-split,
  .commission-value-grid,
  .product-image-field,
  .product-cell,
  .mobile-card {
    grid-template-columns: 1fr;
  }

  .batch-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
