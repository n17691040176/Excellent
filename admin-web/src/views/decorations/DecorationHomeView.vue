<template>
  <div>
    <div class="page-heading">
      <div>
        <h2>uni 首页装修</h2>
        <p>参考 GitHub 商城项目的页面装修方式，先做后台可维护的数据编排，再逐步扩成可视化拖拽。</p>
      </div>
      <div class="toolbar-stack">
        <div class="preset-row">
          <span class="toolbar-label">模板预设</span>
          <el-button-group>
            <el-button plain @click="applyPreset('default')">标准版</el-button>
            <el-button plain @click="applyPreset('growth')">增长版</el-button>
            <el-button plain @click="applyPreset('localLife')">本地生活版</el-button>
          </el-button-group>
        </div>
        <div class="toolbar-row">
          <el-button type="primary" plain @click="loadData">刷新配置</el-button>
          <el-button v-permission="'decoration:edit'" type="primary" :loading="saving" @click="saveDecoration">保存装修</el-button>
        </div>
      </div>
    </div>

    <div class="panel-card data-card section-panel">
      <div class="section-title-row">
        <h3>布局顺序</h3>
        <span>Layout Flow</span>
      </div>
      <div class="block-list">
        <div
          v-for="(sectionKey, index) in form.layout"
          :key="sectionKey"
          class="layout-block"
          :class="{ 'drag-active': isDragActive('layout', 'root', index) }"
          @dragover.prevent="dragOverDrag('layout', 'root', index)"
          @drop="dropDrag(form.layout, 'layout', 'root', index)"
        >
          <div>
            <strong>{{ sectionLabel(sectionKey) }}</strong>
            <p>{{ sectionHint(sectionKey) }}</p>
          </div>
          <div class="block-actions">
            <span
              class="drag-handle"
              draggable="true"
              @dragstart="startDrag('layout', 'root', index)"
              @dragend="endDrag"
            >
              拖拽排序
            </span>
            <span class="layout-status" :class="{ enabled: sectionEnabled(sectionKey) }">
              {{ sectionEnabled(sectionKey) ? '已启用' : '已关闭' }}
            </span>
            <el-button-group>
              <el-button plain :disabled="index === 0" @click="moveLayoutSection(index, -1)">上移</el-button>
              <el-button plain :disabled="index === form.layout.length - 1" @click="moveLayoutSection(index, 1)">下移</el-button>
            </el-button-group>
          </div>
        </div>
      </div>
    </div>

    <div class="panel-card data-card section-panel">
      <div class="section-header-actions">
        <div class="section-title-row compact">
          <h3>自定义模块</h3>
          <span>Custom Blocks</span>
        </div>
        <div class="toolbar-row wrap">
          <el-button-group>
            <el-button plain @click="expandAllCustomBlocks">展开全部</el-button>
            <el-button plain @click="collapseAllCustomBlocks">收起全部</el-button>
          </el-button-group>
          <el-button-group>
            <el-button plain :disabled="!form.custom_blocks.length" @click="openExportDialog">导出模块 JSON</el-button>
            <el-button plain @click="openImportDialog">导入模块 JSON</el-button>
          </el-button-group>
          <el-button-group>
            <el-button plain @click="insertTemplateBlocks('newcomer')">插入新客模板</el-button>
            <el-button plain @click="insertTemplateBlocks('campaign')">插入会场模板</el-button>
            <el-button plain @click="insertTemplateBlocks('localLife')">插入本地生活模板</el-button>
          </el-button-group>
          <el-button-group>
            <el-button plain @click="addCustomBlock('banner')">新增横幅</el-button>
            <el-button plain @click="addCustomBlock('grid')">新增宫格</el-button>
            <el-button plain @click="addCustomBlock('coupon_strip')">新增权益条</el-button>
            <el-button plain @click="addCustomBlock('zone_feed')">新增商品流</el-button>
            <el-button plain @click="addCustomBlock('image_swiper')">新增轮播</el-button>
            <el-button plain @click="addCustomBlock('mixed_goods')">新增混合商品</el-button>
          </el-button-group>
        </div>
      </div>
      <div v-if="!form.custom_blocks.length" class="empty-inline">
        暂无自定义模块，适合补充活动横幅、专题导航、券权益条和专区商品流。
      </div>
      <div v-else class="block-list">
        <div
          v-for="(block, index) in form.custom_blocks"
          :key="block.id"
          class="config-block"
          :class="{ 'drag-active': isDragActive('custom', 'root', index) }"
          @dragover.prevent="dragOverDrag('custom', 'root', index)"
          @drop="dropDrag(form.custom_blocks, 'custom', 'root', index)"
        >
          <div class="config-block-head">
            <div>
              <strong>{{ customBlockTypeLabel(block.type) }} {{ index + 1 }}</strong>
              <p class="mini-desc">布局标识：{{ customLayoutKey(block.id) }}</p>
            </div>
            <div class="block-actions">
              <el-button plain @click="toggleCustomBlockCollapsed(block.id)">
                {{ isCustomBlockCollapsed(block.id) ? '展开模块' : '收起模块' }}
              </el-button>
              <span
                class="drag-handle"
                draggable="true"
                @dragstart="startDrag('custom', 'root', index)"
                @dragend="endDrag"
              >
                拖拽排序
              </span>
              <el-switch v-model="block.enabled" inline-prompt active-text="开" inactive-text="关" />
              <el-button v-permission="'decoration:edit'" plain @click="duplicateCustomBlock(block)">复制模块</el-button>
              <el-button v-permission="'decoration:edit'" link type="danger" @click="removeCustomBlock(index)">删除模块</el-button>
            </div>
          </div>

          <template v-if="!isCustomBlockCollapsed(block.id) && block.type === 'banner'">
            <div class="form-split">
              <el-form-item label="徽标">
                <el-input v-model="block.badge" />
              </el-form-item>
              <el-form-item label="标题">
                <el-input v-model="block.title" />
              </el-form-item>
            </div>
            <el-form-item label="描述">
              <el-input v-model="block.desc" type="textarea" :rows="2" />
            </el-form-item>
            <div class="form-split">
              <el-form-item label="按钮文案">
                <el-input v-model="block.button_text" />
              </el-form-item>
              <el-form-item label="跳转地址">
                <el-input v-model="block.path" />
              </el-form-item>
            </div>
            <el-form-item label="打开方式">
              <el-select v-model="block.open_type">
                <el-option label="页面跳转" value="navigate" />
                <el-option label="切换 Tab" value="switchTab" />
              </el-select>
            </el-form-item>
          </template>

          <template v-else-if="!isCustomBlockCollapsed(block.id) && block.type === 'grid'">
            <div class="form-split">
              <el-form-item label="标题">
                <el-input v-model="block.title" />
              </el-form-item>
              <el-form-item label="副标题">
                <el-input v-model="block.subtitle" />
              </el-form-item>
            </div>
            <div class="section-header-actions nested-actions">
              <span class="mini-desc">宫格入口</span>
              <el-button plain @click="addGridItem(block)">新增入口</el-button>
            </div>
            <div class="block-list">
              <div
                v-for="(item, itemIndex) in block.items"
                :key="`${block.id}-${itemIndex}`"
                class="sub-block"
                :class="{ 'drag-active': isDragActive('grid_items', block.id, itemIndex) }"
                @dragover.prevent="dragOverDrag('grid_items', block.id, itemIndex)"
                @drop="dropDrag(block.items, 'grid_items', block.id, itemIndex)"
              >
                <div class="config-block-head">
                  <strong>入口 {{ itemIndex + 1 }}</strong>
                  <div class="block-actions">
                    <span
                      class="drag-handle"
                      draggable="true"
                      @dragstart="startDrag('grid_items', block.id, itemIndex)"
                      @dragend="endDrag"
                    >
                      拖拽排序
                    </span>
                    <el-switch v-model="item.enabled" inline-prompt active-text="开" inactive-text="关" />
                    <el-button plain @click="duplicateGridItem(block, item)">复制</el-button>
                    <el-button-group>
                      <el-button plain :disabled="itemIndex === 0" @click="moveItem(block.items, itemIndex, -1)">上移</el-button>
                      <el-button plain :disabled="itemIndex === block.items.length - 1" @click="moveItem(block.items, itemIndex, 1)">下移</el-button>
                    </el-button-group>
                    <el-button link type="danger" @click="removeGridItem(block, itemIndex)">删除</el-button>
                  </div>
                </div>
                <div class="form-split">
                  <el-form-item label="标题">
                    <el-input v-model="item.title" />
                  </el-form-item>
                  <el-form-item label="说明">
                    <el-input v-model="item.desc" />
                  </el-form-item>
                </div>
                <el-form-item label="图标地址">
                  <el-input v-model="item.icon_url" placeholder="https:// 或后台上传后的图标地址" />
                </el-form-item>
                <div class="item-upload-row">
                  <el-upload
                    :show-file-list="false"
                    accept="image/*"
                    :http-request="(options) => uploadDecorationItemImage(options, item, itemImageUploadKey(block.id, 'grid', itemIndex))"
                  >
                    <el-button :loading="uploadingImageKey === itemImageUploadKey(block.id, 'grid', itemIndex)">上传图标</el-button>
                  </el-upload>
                  <el-button v-if="item.icon_url" plain @click="item.icon_url = ''">清空图标</el-button>
                </div>
                <div v-if="item.icon_url" class="item-image-preview-shell">
                  <img :src="item.icon_url" alt="宫格图标预览" class="item-image-preview" />
                </div>
                <div class="form-split">
                  <el-form-item label="跳转地址">
                    <el-input v-model="item.path" />
                  </el-form-item>
                  <el-form-item label="打开方式">
                    <el-select v-model="item.open_type">
                      <el-option label="页面跳转" value="navigate" />
                      <el-option label="切换 Tab" value="switchTab" />
                    </el-select>
                  </el-form-item>
                </div>
              </div>
            </div>
          </template>

          <template v-else-if="!isCustomBlockCollapsed(block.id) && block.type === 'coupon_strip'">
            <div class="form-split">
              <el-form-item label="徽标">
                <el-input v-model="block.badge" />
              </el-form-item>
              <el-form-item label="标题">
                <el-input v-model="block.title" />
              </el-form-item>
            </div>
            <el-form-item label="说明">
              <el-input v-model="block.desc" type="textarea" :rows="2" />
            </el-form-item>
            <div class="form-split">
              <el-form-item label="跳转地址">
                <el-input v-model="block.path" />
              </el-form-item>
              <el-form-item label="打开方式">
                <el-select v-model="block.open_type">
                  <el-option label="页面跳转" value="navigate" />
                  <el-option label="切换 Tab" value="switchTab" />
                </el-select>
              </el-form-item>
            </div>
          </template>

          <template v-else-if="!isCustomBlockCollapsed(block.id) && block.type === 'zone_feed'">
            <div class="form-split">
              <el-form-item label="标题">
                <el-input v-model="block.title" />
              </el-form-item>
              <el-form-item label="副标题">
                <el-input v-model="block.subtitle" />
              </el-form-item>
            </div>
            <div class="form-split">
              <el-form-item label="数据来源">
                <el-select v-model="block.source_key">
                  <el-option v-for="item in zoneSourceOptions" :key="item.value" :label="item.label" :value="item.value" />
                </el-select>
              </el-form-item>
              <el-form-item label="展示数量">
                <el-input-number v-model="block.limit" :min="1" :max="12" />
              </el-form-item>
            </div>
            <div class="form-split">
              <el-form-item label="查看更多跳转">
                <el-input v-model="block.path" />
              </el-form-item>
              <el-form-item label="打开方式">
                <el-select v-model="block.open_type">
                  <el-option label="页面跳转" value="navigate" />
                  <el-option label="切换 Tab" value="switchTab" />
                </el-select>
              </el-form-item>
            </div>
          </template>

          <template v-else-if="!isCustomBlockCollapsed(block.id) && block.type === 'image_swiper'">
            <div class="form-split">
              <el-form-item label="模块标题">
                <el-input v-model="block.title" />
              </el-form-item>
              <el-form-item label="自动轮播">
                <el-switch v-model="block.autoplay" />
              </el-form-item>
            </div>
            <div class="form-split">
              <el-form-item label="标题上方文案">
                <el-input v-model="block.section_kicker" placeholder="如：Featured" />
              </el-form-item>
              <el-form-item label="数量单位">
                <el-input v-model="block.count_suffix" placeholder="如：张" />
              </el-form-item>
            </div>
            <div class="form-split">
              <el-form-item label="顶部标签">
                <el-input v-model="block.kicker" placeholder="如：精选活动" />
              </el-form-item>
              <el-form-item label="顶部胶囊文案">
                <el-input
                  :model-value="joinLines(block.tags)"
                  placeholder="每行一个，如：当日精选"
                  @update:model-value="block.tags = splitLines($event)"
                />
              </el-form-item>
            </div>
            <el-form-item label="顶部说明">
              <el-input v-model="block.desc" type="textarea" :rows="2" />
            </el-form-item>
            <el-form-item label="轮播按钮文案">
              <el-input
                :model-value="joinLines(block.slide_tags)"
                type="textarea"
                :rows="2"
                placeholder="每行一个，如：专题推荐"
                @update:model-value="block.slide_tags = splitLines($event)"
              />
            </el-form-item>
            <div class="section-header-actions nested-actions">
              <span class="mini-desc">轮播内容</span>
              <el-button plain @click="addSwiperItem(block)">新增轮播项</el-button>
            </div>
            <div class="block-list">
              <div
                v-for="(item, itemIndex) in block.items"
                :key="`${block.id}-swiper-${itemIndex}`"
                class="sub-block"
                :class="{ 'drag-active': isDragActive('swiper_items', block.id, itemIndex) }"
                @dragover.prevent="dragOverDrag('swiper_items', block.id, itemIndex)"
                @drop="dropDrag(block.items, 'swiper_items', block.id, itemIndex)"
              >
                <div class="config-block-head">
                  <strong>轮播 {{ itemIndex + 1 }}</strong>
                  <div class="block-actions">
                    <span
                      class="drag-handle"
                      draggable="true"
                      @dragstart="startDrag('swiper_items', block.id, itemIndex)"
                      @dragend="endDrag"
                    >
                      拖拽排序
                    </span>
                    <el-switch v-model="item.enabled" inline-prompt active-text="开" inactive-text="关" />
                    <el-button plain @click="duplicateSwiperItem(block, item)">复制</el-button>
                    <el-button-group>
                      <el-button plain :disabled="itemIndex === 0" @click="moveItem(block.items, itemIndex, -1)">上移</el-button>
                      <el-button plain :disabled="itemIndex === block.items.length - 1" @click="moveItem(block.items, itemIndex, 1)">下移</el-button>
                    </el-button-group>
                    <el-button link type="danger" @click="removeSwiperItem(block, itemIndex)">删除</el-button>
                  </div>
                </div>
                <div class="form-split">
                  <el-form-item label="徽标">
                    <el-input v-model="item.badge" />
                  </el-form-item>
                  <el-form-item label="标题">
                    <el-input v-model="item.title" />
                  </el-form-item>
                </div>
                <el-form-item label="描述">
                  <el-input v-model="item.desc" type="textarea" :rows="2" />
                </el-form-item>
                <el-form-item label="图片地址">
                  <el-input v-model="item.image_url" placeholder="https:// 或后台上传后的图片地址" />
                </el-form-item>
                <div class="swiper-upload-row">
                  <el-upload
                    :show-file-list="false"
                    accept="image/*"
                    :http-request="(options) => uploadSwiperImage(options, block, item, itemIndex)"
                  >
                    <el-button :loading="uploadingSwiperImageKey === swiperImageUploadKey(block.id, itemIndex)">
                      上传图片
                    </el-button>
                  </el-upload>
                  <el-button
                    v-if="item.image_url"
                    plain
                    @click="item.image_url = ''"
                  >
                    清空图片
                  </el-button>
                </div>
                <div v-if="item.image_url" class="swiper-image-preview-shell">
                  <img :src="item.image_url" alt="轮播图预览" class="swiper-image-preview" />
                </div>
                <div class="form-split">
                  <el-form-item label="跳转地址">
                    <el-input v-model="item.path" />
                  </el-form-item>
                  <el-form-item label="打开方式">
                    <el-select v-model="item.open_type">
                      <el-option label="页面跳转" value="navigate" />
                      <el-option label="切换 Tab" value="switchTab" />
                    </el-select>
                  </el-form-item>
                </div>
              </div>
            </div>
          </template>

          <template v-else-if="!isCustomBlockCollapsed(block.id) && block.type === 'mixed_goods'">
            <div class="form-split">
              <el-form-item label="标题">
                <el-input v-model="block.title" />
              </el-form-item>
              <el-form-item label="副标题">
                <el-input v-model="block.subtitle" />
              </el-form-item>
            </div>
            <div class="section-header-actions nested-actions">
              <span class="mini-desc">商品条目</span>
              <el-button plain @click="addMixedGoodsItem(block)">新增商品</el-button>
            </div>
            <div class="block-list">
              <div
                v-for="(item, itemIndex) in block.items"
                :key="`${block.id}-goods-${itemIndex}`"
                class="sub-block"
                :class="{ 'drag-active': isDragActive('mixed_items', block.id, itemIndex) }"
                @dragover.prevent="dragOverDrag('mixed_items', block.id, itemIndex)"
                @drop="dropDrag(block.items, 'mixed_items', block.id, itemIndex)"
              >
                <div class="config-block-head">
                  <strong>商品 {{ itemIndex + 1 }}</strong>
                  <div class="block-actions">
                    <span
                      class="drag-handle"
                      draggable="true"
                      @dragstart="startDrag('mixed_items', block.id, itemIndex)"
                      @dragend="endDrag"
                    >
                      拖拽排序
                    </span>
                    <el-switch v-model="item.enabled" inline-prompt active-text="开" inactive-text="关" />
                    <el-button plain @click="duplicateMixedGoodsItem(block, item)">复制</el-button>
                    <el-button-group>
                      <el-button plain :disabled="itemIndex === 0" @click="moveItem(block.items, itemIndex, -1)">上移</el-button>
                      <el-button plain :disabled="itemIndex === block.items.length - 1" @click="moveItem(block.items, itemIndex, 1)">下移</el-button>
                    </el-button-group>
                    <el-button link type="danger" @click="removeMixedGoodsItem(block, itemIndex)">删除</el-button>
                  </div>
                </div>
                <div class="form-split">
                  <el-form-item label="标签">
                    <el-input v-model="item.tag" />
                  </el-form-item>
                  <el-form-item label="价格文案">
                    <el-input v-model="item.price_text" placeholder="¥199 / 券后 5 折" />
                  </el-form-item>
                </div>
                <div class="form-split">
                  <el-form-item label="标题">
                    <el-input v-model="item.title" />
                  </el-form-item>
                  <el-form-item label="说明">
                    <el-input v-model="item.desc" />
                  </el-form-item>
                </div>
                <div class="form-split">
                  <el-form-item label="跳转地址">
                    <el-input v-model="item.path" />
                  </el-form-item>
                  <el-form-item label="打开方式">
                    <el-select v-model="item.open_type">
                      <el-option label="页面跳转" value="navigate" />
                      <el-option label="切换 Tab" value="switchTab" />
                    </el-select>
                  </el-form-item>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>

    <div class="editor-grid">
      <div class="panel-card data-card">
        <div class="section-title-row">
          <h3>公告区</h3>
          <div class="section-meta">
            <span>Announcement</span>
            <el-switch v-model="form.announcement.enabled" />
          </div>
        </div>
        <el-form label-position="top">
          <el-form-item label="标题">
            <el-input v-model="form.announcement.title" />
          </el-form-item>
          <el-form-item label="文案">
            <el-input v-model="announcementLinesText" type="textarea" :rows="4" placeholder="每行一条公告" />
          </el-form-item>
        </el-form>
      </div>
    </div>

    <div class="editor-grid">
      <div class="panel-card data-card">
        <div class="section-title-row">
          <h3>四区导航</h3>
          <div class="section-meta">
            <span>Zone Navigation</span>
            <el-switch v-model="form.zone_section.enabled" />
          </div>
        </div>
        <el-form label-position="top">
          <div class="form-split">
            <el-form-item label="标题">
              <el-input v-model="form.zone_section.title" />
            </el-form-item>
            <el-form-item label="副标题">
              <el-input v-model="form.zone_section.subtitle" />
            </el-form-item>
          </div>
          <el-form-item label="展示说明">
            <div class="section-tip">首页会按 2 x 2 宫格渲染四区入口，并显示每个专区的内容数量与引导文案。</div>
          </el-form-item>
        </el-form>
      </div>

      <div class="panel-card data-card">
        <div class="section-title-row">
          <h3>瀑布流</h3>
          <div class="section-meta">
            <span>Waterfall Feed</span>
            <el-switch v-model="form.waterfall_section.enabled" />
          </div>
        </div>
        <el-form label-position="top">
          <div class="form-split">
            <el-form-item label="标题">
              <el-input v-model="form.waterfall_section.title" />
            </el-form-item>
            <el-form-item label="副标题">
              <el-input v-model="form.waterfall_section.subtitle" />
            </el-form-item>
          </div>
          <div class="form-split">
            <el-form-item label="每次加载数量">
              <el-input-number v-model="form.waterfall_section.page_size" :min="4" :max="20" />
            </el-form-item>
            <el-form-item label="数据来源">
              <el-select v-model="form.waterfall_section.source_keys" multiple collapse-tags collapse-tags-tooltip>
                <el-option v-for="item in zoneSourceOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
          </div>
        </el-form>
      </div>
    </div>

    <div class="panel-card data-card section-panel">
      <div class="section-header-actions">
        <div class="section-title-row compact">
          <h3>套餐区</h3>
          <div class="section-meta">
            <span>Featured Packages</span>
            <el-switch v-model="form.package_section.enabled" />
          </div>
        </div>
      </div>
      <el-form label-position="top">
        <div class="form-split">
          <el-form-item label="标题">
            <el-input v-model="form.package_section.title" />
          </el-form-item>
          <el-form-item label="显示数量">
            <el-input-number v-model="form.package_section.limit" :min="1" :max="6" />
          </el-form-item>
        </div>
        <el-form-item label="说明">
          <el-input v-model="form.package_section.desc" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
    </div>

    <div class="panel-card data-card section-panel">
      <div class="section-header-actions">
        <div class="section-title-row compact">
          <h3>运营卡片</h3>
          <div class="section-meta">
            <span>Promo Cards</span>
            <el-switch v-model="form.promo_section.enabled" />
          </div>
        </div>
        <el-button v-permission="'decoration:edit'" type="primary" plain @click="addPromoCard">新增卡片</el-button>
      </div>
      <div class="form-split section-config-row">
        <el-form-item label="区块标题">
          <el-input v-model="form.promo_section.title" />
        </el-form-item>
        <el-form-item label="右侧文案">
          <el-input v-model="form.promo_section.subtitle" placeholder="为空则前台隐藏" />
        </el-form-item>
      </div>
      <div class="section-config-row">
        <div class="section-tip">支持单卡禁用、上下排序，区块本身的上下顺序在“布局顺序”里调整。</div>
      </div>
      <div class="block-list">
        <div
          v-for="(item, index) in form.promo_section.items"
          :key="`promo-${index}`"
          class="config-block"
          :class="{ 'drag-active': isDragActive('promo_items', 'promo_section', index) }"
          @dragover.prevent="dragOverDrag('promo_items', 'promo_section', index)"
          @drop="dropDrag(form.promo_section.items, 'promo_items', 'promo_section', index)"
        >
          <div class="config-block-head">
            <strong>卡片 {{ index + 1 }}</strong>
            <div class="block-actions">
              <span
                class="drag-handle"
                draggable="true"
                @dragstart="startDrag('promo_items', 'promo_section', index)"
                @dragend="endDrag"
              >
                拖拽排序
              </span>
              <el-switch v-model="item.enabled" inline-prompt active-text="开" inactive-text="关" />
              <el-button plain @click="duplicatePromoCard(item)">复制</el-button>
              <el-button-group>
                <el-button plain :disabled="index === 0" @click="moveItem(form.promo_section.items, index, -1)">上移</el-button>
                <el-button plain :disabled="index === form.promo_section.items.length - 1" @click="moveItem(form.promo_section.items, index, 1)">下移</el-button>
              </el-button-group>
              <el-button v-permission="'decoration:edit'" link type="danger" @click="removePromoCard(index)">删除</el-button>
            </div>
          </div>
          <div class="form-split">
            <el-form-item label="徽标">
              <el-input v-model="item.badge" />
            </el-form-item>
            <el-form-item label="标题">
              <el-input v-model="item.title" />
            </el-form-item>
          </div>
          <el-form-item label="描述">
            <el-input v-model="item.desc" type="textarea" :rows="2" />
          </el-form-item>
          <div class="form-split">
            <el-form-item label="跳转地址">
              <el-input v-model="item.path" placeholder="/pages/packages/list" />
            </el-form-item>
            <el-form-item label="打开方式">
              <el-select v-model="item.open_type">
                <el-option label="页面跳转" value="navigate" />
                <el-option label="切换 Tab" value="switchTab" />
              </el-select>
            </el-form-item>
          </div>
        </div>
      </div>
    </div>

    <div class="panel-card data-card section-panel">
      <div class="section-header-actions">
        <div class="section-title-row compact">
          <h3>四区卡片</h3>
          <div class="section-meta">
            <span>Zone Items</span>
            <el-switch v-model="form.zone_section.enabled" />
          </div>
        </div>
        <el-button v-permission="'decoration:edit'" type="primary" plain @click="addZoneItem">新增分区</el-button>
      </div>
      <div class="block-list">
        <div
          v-for="(item, index) in form.zone_section.items"
          :key="`zone-${index}`"
          class="config-block"
          :class="{ 'drag-active': isDragActive('zone_items', 'zone_section', index) }"
          @dragover.prevent="dragOverDrag('zone_items', 'zone_section', index)"
          @drop="dropDrag(form.zone_section.items, 'zone_items', 'zone_section', index)"
        >
          <div class="config-block-head">
            <strong>分区 {{ index + 1 }}</strong>
            <div class="block-actions">
              <span
                class="drag-handle"
                draggable="true"
                @dragstart="startDrag('zone_items', 'zone_section', index)"
                @dragend="endDrag"
              >
                拖拽排序
              </span>
              <el-switch v-model="item.enabled" inline-prompt active-text="开" inactive-text="关" />
              <el-button plain @click="duplicateZoneItem(item)">复制</el-button>
              <el-button-group>
                <el-button plain :disabled="index === 0" @click="moveItem(form.zone_section.items, index, -1)">上移</el-button>
                <el-button plain :disabled="index === form.zone_section.items.length - 1" @click="moveItem(form.zone_section.items, index, 1)">下移</el-button>
              </el-button-group>
              <el-button v-permission="'decoration:edit'" link type="danger" @click="removeZoneItem(index)">删除</el-button>
            </div>
          </div>
          <div class="form-split">
            <el-form-item label="key">
              <el-input v-model="item.key" placeholder="repurchase / selfOperated / hotSale / localLife" />
            </el-form-item>
            <el-form-item label="标题">
              <el-input v-model="item.title" />
            </el-form-item>
          </div>
          <el-form-item label="说明">
            <el-input v-model="item.tip" />
          </el-form-item>
          <div class="form-split">
            <el-form-item label="卡片跳转文案">
              <el-input v-model="item.link_text" placeholder="为空则前台隐藏" />
            </el-form-item>
            <el-form-item label="显示数量角标">
              <el-switch v-model="item.show_count" inline-prompt active-text="显示" inactive-text="隐藏" />
            </el-form-item>
          </div>
          <el-form-item label="图标地址">
            <el-input v-model="item.icon_url" placeholder="https:// 或后台上传后的图标地址" />
          </el-form-item>
          <div class="item-upload-row">
            <el-upload
              :show-file-list="false"
              accept="image/*"
              :http-request="(options) => uploadDecorationItemImage(options, item, itemImageUploadKey('zone_section', 'zone', index))"
            >
              <el-button :loading="uploadingImageKey === itemImageUploadKey('zone_section', 'zone', index)">上传图标</el-button>
            </el-upload>
            <el-button v-if="item.icon_url" plain @click="item.icon_url = ''">清空图标</el-button>
          </div>
          <div v-if="item.icon_url" class="item-image-preview-shell">
            <img :src="item.icon_url" alt="分区图标预览" class="item-image-preview" />
          </div>
          <div class="form-split">
            <el-form-item label="跳转地址">
              <el-input v-model="item.path" />
            </el-form-item>
            <el-form-item label="打开方式">
              <el-select v-model="item.open_type">
                <el-option label="页面跳转" value="navigate" />
                <el-option label="切换 Tab" value="switchTab" />
              </el-select>
            </el-form-item>
          </div>
        </div>
      </div>
    </div>

    <div class="panel-card data-card section-panel">
      <div class="section-header-actions">
        <div class="section-title-row compact">
          <h3>快捷入口</h3>
          <div class="section-meta">
            <span>Quick Actions</span>
            <el-switch v-model="form.quick_section.enabled" />
          </div>
        </div>
        <el-button v-permission="'decoration:edit'" type="primary" plain @click="addQuickItem">新增入口</el-button>
      </div>
      <div class="form-split">
        <el-form-item label="区块标题">
          <el-input v-model="form.quick_section.title" />
        </el-form-item>
        <el-form-item label="右侧文案">
          <el-input v-model="form.quick_section.subtitle" />
        </el-form-item>
      </div>
      <div class="block-list">
        <div
          v-for="(item, index) in form.quick_section.items"
          :key="`quick-${index}`"
          class="config-block"
          :class="{ 'drag-active': isDragActive('quick_items', 'quick_section', index) }"
          @dragover.prevent="dragOverDrag('quick_items', 'quick_section', index)"
          @drop="dropDrag(form.quick_section.items, 'quick_items', 'quick_section', index)"
        >
          <div class="config-block-head">
            <strong>入口 {{ index + 1 }}</strong>
            <div class="block-actions">
              <span
                class="drag-handle"
                draggable="true"
                @dragstart="startDrag('quick_items', 'quick_section', index)"
                @dragend="endDrag"
              >
                拖拽排序
              </span>
              <el-switch v-model="item.enabled" inline-prompt active-text="开" inactive-text="关" />
              <el-button plain @click="duplicateQuickItem(item)">复制</el-button>
              <el-button-group>
                <el-button plain :disabled="index === 0" @click="moveItem(form.quick_section.items, index, -1)">上移</el-button>
                <el-button plain :disabled="index === form.quick_section.items.length - 1" @click="moveItem(form.quick_section.items, index, 1)">下移</el-button>
              </el-button-group>
              <el-button v-permission="'decoration:edit'" link type="danger" @click="removeQuickItem(index)">删除</el-button>
            </div>
          </div>
          <div class="form-split">
            <el-form-item label="标题">
              <el-input v-model="item.title" />
            </el-form-item>
            <el-form-item label="说明">
              <el-input v-model="item.desc" />
            </el-form-item>
          </div>
          <el-form-item label="图标地址">
            <el-input v-model="item.icon_url" placeholder="https:// 或后台上传后的图标地址" />
          </el-form-item>
          <div class="item-upload-row">
            <el-upload
              :show-file-list="false"
              accept="image/*"
              :http-request="(options) => uploadDecorationItemImage(options, item, itemImageUploadKey('quick_section', 'quick', index))"
            >
              <el-button :loading="uploadingImageKey === itemImageUploadKey('quick_section', 'quick', index)">上传图标</el-button>
            </el-upload>
            <el-button v-if="item.icon_url" plain @click="item.icon_url = ''">清空图标</el-button>
          </div>
          <div v-if="item.icon_url" class="item-image-preview-shell">
            <img :src="item.icon_url" alt="快捷图标预览" class="item-image-preview" />
          </div>
          <div class="form-split">
            <el-form-item label="跳转地址">
              <el-input v-model="item.path" />
            </el-form-item>
            <el-form-item label="打开方式">
              <el-select v-model="item.open_type">
                <el-option label="页面跳转" value="navigate" />
                <el-option label="切换 Tab" value="switchTab" />
              </el-select>
            </el-form-item>
          </div>
        </div>
      </div>
    </div>

    <div class="preview-shell">
      <div class="page-heading preview-heading">
        <div>
          <h2>预览</h2>
          <p>这里按 uni 首页的区块开关、布局顺序和自定义模块实时预览。</p>
        </div>
      </div>
      <div class="mobile-preview">
          <div v-if="previewPrimarySwiperItems.length" class="preview-card preview-banner-card">
            <div class="preview-grid">
              <div
                v-for="(item, index) in previewPrimarySwiperItems"
                :key="`preview-top-swiper-${index}`"
                class="preview-mini-card preview-swiper-mini-card"
                :style="previewSwiperStyle(item)"
              >
                <div class="preview-swiper-mask"></div>
                <div class="preview-swiper-content">
                  <div class="preview-badge muted">{{ item.badge || '轮播图' }}</div>
                  <strong>{{ item.title || '未命名轮播' }}</strong>
                  <p>{{ item.desc || '请补充轮播说明' }}</p>
                </div>
              </div>
            </div>
          </div>

        <template v-for="sectionKey in orderedPreviewKeys" :key="sectionKey">
          <div v-if="sectionKey === 'announcement'" class="preview-card">
            <div v-if="form.announcement.title" class="preview-head">
              <strong>{{ form.announcement.title }}</strong>
              <span>公告区</span>
            </div>
            <div class="preview-lines">
              <div v-for="item in previewAnnouncementLines" :key="item">{{ item }}</div>
            </div>
          </div>

          <div v-else-if="sectionKey === 'package_section'" class="preview-card">
            <div v-if="form.package_section.title || form.package_section.limit" class="preview-head">
              <strong v-if="form.package_section.title">{{ form.package_section.title }}</strong>
              <span>展示 {{ form.package_section.limit }} 档</span>
            </div>
            <p>{{ form.package_section.desc }}</p>
          </div>

          <div v-else-if="sectionKey === 'promo_section'" class="preview-card">
            <div v-if="form.promo_section.title || form.promo_section.subtitle || previewPromoCards.length" class="preview-head">
              <strong v-if="form.promo_section.title">{{ form.promo_section.title }}</strong>
              <span>{{ form.promo_section.subtitle || `${previewPromoCards.length} 张` }}</span>
            </div>
            <div class="preview-grid">
              <div v-for="(item, index) in previewPromoCards" :key="`preview-promo-${index}`" class="preview-mini-card">
                <div class="preview-badge muted">{{ item.badge || '运营卡' }}</div>
                <strong>{{ item.title || '未命名卡片' }}</strong>
                <p>{{ item.desc || '请补充描述' }}</p>
              </div>
            </div>
          </div>

          <div v-else-if="sectionKey === 'zone_section'" class="preview-card">
            <div v-if="form.zone_section.title || form.zone_section.subtitle" class="preview-head">
              <strong v-if="form.zone_section.title">{{ form.zone_section.title }}</strong>
              <span v-if="form.zone_section.subtitle">{{ form.zone_section.subtitle }}</span>
            </div>
            <div class="preview-grid">
              <div v-for="(item, index) in previewZoneItems" :key="`preview-zone-${index}`" class="preview-mini-card">
                <strong>{{ item.title || item.key || '未命名分区' }}</strong>
                <p>{{ item.tip || '请补充分区说明' }}</p>
                <p v-if="item.link_text || item.show_count !== false">{{ item.link_text || '无跳转文案' }} · {{ item.show_count === false ? '隐藏数量' : '显示数量' }}</p>
              </div>
            </div>
          </div>

          <div v-else-if="sectionKey === 'waterfall_section'" class="preview-card">
            <div v-if="form.waterfall_section.title || form.waterfall_section.subtitle" class="preview-head">
              <strong v-if="form.waterfall_section.title">{{ form.waterfall_section.title }}</strong>
              <span v-if="form.waterfall_section.subtitle">{{ form.waterfall_section.subtitle }}</span>
            </div>
            <div class="preview-lines">
              <div>来源：{{ previewWaterfallSources || '未选择' }}</div>
              <div>每次加载 {{ form.waterfall_section.page_size }} 条，前台双列瀑布布局并支持下拉刷新。</div>
            </div>
            <div class="preview-grid">
              <div v-for="index in Math.min(Number(form.waterfall_section.page_size || 8), 6)" :key="`preview-waterfall-${index}`" class="preview-mini-card">
                <div class="preview-badge muted">商品流</div>
                <strong>推荐内容 {{ index }}</strong>
                <p>按所选专区混排后进入首页瀑布流展示。</p>
              </div>
            </div>
          </div>

          <div v-else-if="sectionKey === 'quick_section'" class="preview-card">
            <div v-if="form.quick_section.title || form.quick_section.subtitle" class="preview-head">
              <strong v-if="form.quick_section.title">{{ form.quick_section.title }}</strong>
              <span v-if="form.quick_section.subtitle">{{ form.quick_section.subtitle }}</span>
            </div>
            <div class="preview-grid">
              <div v-for="(item, index) in previewQuickItems" :key="`preview-quick-${index}`" class="preview-mini-card">
                <div class="preview-item-icon">
                  <img v-if="item.icon_url" :src="item.icon_url" alt="快捷图标" class="preview-item-icon-image" />
                  <span v-else>{{ navItemFallbackText(item, '入口') }}</span>
                </div>
                <strong>{{ item.title || '未命名入口' }}</strong>
                <p>{{ item.desc || '请补充入口说明' }}</p>
              </div>
            </div>
          </div>

          <div v-else-if="customBlockFromLayout(sectionKey)?.type === 'banner'" class="preview-card preview-banner-card">
            <div class="preview-badge muted">{{ customBlockFromLayout(sectionKey)?.badge || '活动横幅' }}</div>
            <strong v-if="customBlockFromLayout(sectionKey)?.title">{{ customBlockFromLayout(sectionKey)?.title }}</strong>
            <p>{{ customBlockFromLayout(sectionKey)?.desc || '请补充活动说明' }}</p>
            <div class="preview-action">{{ customBlockFromLayout(sectionKey)?.button_text || '立即查看' }}</div>
          </div>

          <div v-else-if="customBlockFromLayout(sectionKey)?.type === 'grid'" class="preview-card">
            <div v-if="customBlockFromLayout(sectionKey)?.title || customBlockFromLayout(sectionKey)?.subtitle" class="preview-head">
              <strong v-if="customBlockFromLayout(sectionKey)?.title">{{ customBlockFromLayout(sectionKey)?.title }}</strong>
              <span v-if="customBlockFromLayout(sectionKey)?.subtitle">{{ customBlockFromLayout(sectionKey)?.subtitle }}</span>
            </div>
            <div class="preview-grid">
              <div
                v-for="(item, index) in customGridItems(customBlockFromLayout(sectionKey))"
                :key="`preview-custom-grid-${sectionKey}-${index}`"
                class="preview-mini-card"
              >
                <div class="preview-item-icon">
                  <img v-if="item.icon_url" :src="item.icon_url" alt="宫格图标" class="preview-item-icon-image" />
                  <span v-else>{{ navItemFallbackText(item, '宫格') }}</span>
                </div>
                <strong>{{ item.title || '未命名入口' }}</strong>
                <p>{{ item.desc || '请补充说明' }}</p>
              </div>
            </div>
          </div>

          <div v-else-if="customBlockFromLayout(sectionKey)?.type === 'coupon_strip'" class="preview-card preview-coupon-card">
            <div class="preview-badge muted">{{ customBlockFromLayout(sectionKey)?.badge || '权益专区' }}</div>
            <strong v-if="customBlockFromLayout(sectionKey)?.title">{{ customBlockFromLayout(sectionKey)?.title }}</strong>
            <p>{{ customBlockFromLayout(sectionKey)?.desc || '请补充权益文案' }}</p>
          </div>

          <div v-else-if="customBlockFromLayout(sectionKey)?.type === 'zone_feed'" class="preview-card">
            <div v-if="customBlockFromLayout(sectionKey)?.title || customBlockFromLayout(sectionKey)?.source_key" class="preview-head">
              <strong v-if="customBlockFromLayout(sectionKey)?.title">{{ customBlockFromLayout(sectionKey)?.title }}</strong>
              <span>{{ zoneSourceLabel(customBlockFromLayout(sectionKey)?.source_key) }}</span>
            </div>
            <div class="preview-grid">
              <div
                v-for="index in Number(customBlockFromLayout(sectionKey)?.limit || 4)"
                :key="`preview-zone-feed-${sectionKey}-${index}`"
                class="preview-mini-card"
              >
                <strong>{{ zoneSourceLabel(customBlockFromLayout(sectionKey)?.source_key) }} {{ index }}</strong>
                <p>按专区真实数据输出商品卡片。</p>
              </div>
            </div>
          </div>

          <div v-else-if="customBlockFromLayout(sectionKey)?.type === 'image_swiper'" class="preview-swiper-strip">
            <div
              v-for="(item, index) in customSwiperItems(customBlockFromLayout(sectionKey))"
              :key="`preview-swiper-${sectionKey}-${index}`"
              class="preview-mini-card preview-swiper-mini-card"
              :style="previewSwiperStyle(item)"
            >
              <div class="preview-swiper-mask"></div>
              <div class="preview-swiper-content">
                <div class="preview-badge muted">{{ item.badge || '轮播图' }}</div>
                <strong>{{ item.title || '未命名轮播' }}</strong>
                <p>{{ item.desc || '请补充轮播说明' }}</p>
              </div>
            </div>
          </div>

          <div v-else-if="customBlockFromLayout(sectionKey)?.type === 'mixed_goods'" class="preview-card">
            <div v-if="customBlockFromLayout(sectionKey)?.title || customBlockFromLayout(sectionKey)?.subtitle" class="preview-head">
              <strong v-if="customBlockFromLayout(sectionKey)?.title">{{ customBlockFromLayout(sectionKey)?.title }}</strong>
              <span v-if="customBlockFromLayout(sectionKey)?.subtitle">{{ customBlockFromLayout(sectionKey)?.subtitle }}</span>
            </div>
            <div class="preview-grid">
              <div
                v-for="(item, index) in customMixedGoodsItems(customBlockFromLayout(sectionKey))"
                :key="`preview-mixed-goods-${sectionKey}-${index}`"
                class="preview-mini-card"
              >
                <div class="preview-badge muted">{{ item.tag || '商品' }}</div>
                <strong>{{ item.title || '未命名商品' }}</strong>
                <p>{{ item.price_text || item.desc || '请补充价格或说明' }}</p>
              </div>
            </div>
          </div>
        </template>

        <div v-if="!orderedPreviewKeys.length" class="preview-empty">
          当前没有启用的首页区块，保存后 uni 首页将不展示装修内容。
        </div>
      </div>
    </div>

    <el-dialog v-model="exportDialogVisible" title="导出自定义模块 JSON" width="760px">
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="导出内容只包含 custom_blocks，可复制到其他环境的同一装修页导入。"
      />
      <el-input
        v-model="exportJsonText"
        class="json-textarea"
        type="textarea"
        :rows="18"
        readonly
      />
      <template #footer>
        <el-button @click="exportDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="copyExportJson">复制 JSON</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importDialogVisible" title="导入自定义模块 JSON" width="760px">
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        title="支持导入单个模块、模块数组，或包含 custom_blocks 字段的对象。导入后会自动重建模块 ID。"
      />
      <el-input
        v-model="importJsonText"
        class="json-textarea"
        type="textarea"
        :rows="18"
        placeholder="粘贴导出的模块 JSON"
      />
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button plain @click="importCustomBlocks('append')">追加导入</el-button>
        <el-button type="primary" @click="importCustomBlocks('replace')">替换全部模块</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { decorationApi } from '@/api/modules'

const SECTION_ORDER = ['announcement', 'zone_section', 'waterfall_section', 'package_section', 'promo_section', 'quick_section']
const SECTION_META = {
  announcement: { label: '公告区', hint: '顶部公告与运营提醒' },
  zone_section: { label: '四区导航', hint: '后台配置的分区入口、角标和跳转文案' },
  waterfall_section: { label: '瀑布商品流', hint: '双列商品推荐，可下拉刷新与继续加载' },
  package_section: { label: '套餐区', hint: '套餐推荐与权益转化' },
  promo_section: { label: '运营卡片', hint: '活动卡片与重点引导' },
  quick_section: { label: '我的常用', hint: '团队、邀请、佣金、资产等个人常用入口' }
}
const ZONE_SOURCE_OPTIONS = [
  { value: 'repurchase', label: '复购来源' },
  { value: 'selfOperated', label: '商城来源' },
  { value: 'hotSale', label: '热卖来源' },
  { value: 'localLife', label: '本地生活' }
]
const CUSTOM_BLOCK_TEMPLATE_META = {
  newcomer: { label: '新客转化模板' },
  campaign: { label: '活动会场模板' },
  localLife: { label: '本地生活模板' }
}

function customLayoutKey(id) {
  return `custom:${id}`
}

function createBlockId(prefix = 'block') {
  return `${prefix}_${Math.random().toString(36).slice(2, 8)}`
}

function customBlockIdPrefix(type) {
  return {
    banner: 'banner',
    grid: 'grid',
    coupon_strip: 'coupon',
    zone_feed: 'feed',
    image_swiper: 'swiper',
    mixed_goods: 'mixed'
  }[type] || 'block'
}

function createPromoCard() {
  return { enabled: true, badge: '', title: '', desc: '', path: '', open_type: 'navigate' }
}

function createZoneItem() {
  return { enabled: true, key: '', title: '', tip: '', icon_url: '', link_text: '进入专区', show_count: true, path: '', open_type: 'navigate' }
}

function createQuickItem() {
  return { enabled: true, title: '', desc: '', icon_url: '', path: '', open_type: 'navigate' }
}

function createGridItem() {
  return { enabled: true, title: '', desc: '', icon_url: '', path: '', open_type: 'navigate' }
}

function createSwiperItem() {
  return { enabled: true, badge: '', title: '', desc: '', image_url: '', path: '', open_type: 'navigate' }
}

function createMixedGoodsItem() {
  return { enabled: true, tag: '', title: '', desc: '', price_text: '', path: '', open_type: 'navigate' }
}

function createDefaultHomeSwiper() {
  return {
    id: 'home_swiper_main',
    type: 'image_swiper',
    enabled: true,
    title: '首页轮播',
    section_kicker: 'Featured',
    count_suffix: '张',
    kicker: '精选活动',
    desc: '主推活动、重点分区和新内容统一展示。',
    tags: ['当日精选', '持续上新'],
    slide_tags: ['专题推荐', '立即进入'],
    autoplay: true,
    items: [
      {
        enabled: true,
        badge: '商城主推',
        title: '热门专区与首单权益一起前置',
        desc: '参考主流电商首页，把主推活动、分区会场和转化入口收进首屏轮播。',
        image_url: '',
        path: '/pages/packages/list',
        open_type: 'switchTab'
      },
      {
        enabled: true,
        badge: '本地生活',
        title: '到店服务和联盟商家进入底部导航',
        desc: '把本地生活从二级入口抬升到底部栏，门店服务触达更直接。',
        image_url: '',
        path: '/pages/local-life/index',
        open_type: 'switchTab'
      },
      {
        enabled: true,
        badge: '爆款专区',
        title: '首页下滑直达双列瀑布商品流',
        desc: '支持下拉刷新和继续加载，持续承接爆款、自营和本地生活内容。',
        image_url: '',
        path: '/pages/packages/list',
        open_type: 'switchTab'
      }
    ]
  }
}

function createCustomBanner() {
  return {
    id: createBlockId('banner'),
    type: 'banner',
    enabled: true,
    badge: '限时活动',
    title: '新增一个后台可配置的活动横幅',
    desc: '适合承接限时促销、专题会场或招商活动，保存后首页会立即按布局顺序展示。',
    button_text: '立即查看',
    path: '/pages/packages/list',
    open_type: 'switchTab'
  }
}

function createCustomGrid() {
  return {
    id: createBlockId('grid'),
    type: 'grid',
    enabled: true,
    title: '专题导航',
    subtitle: '运营配置',
    items: [createGridItem(), createGridItem(), createGridItem(), createGridItem()]
  }
}

function createCustomCouponStrip() {
  return {
    id: createBlockId('coupon'),
    type: 'coupon_strip',
    enabled: true,
    badge: '权益条',
    title: '领券后优先承接套餐和商城转化',
    desc: '适合表达抵扣券、满减券、会员券等运营权益。',
    path: '/pages/packages/list',
    open_type: 'switchTab'
  }
}

function createCustomZoneFeed() {
  return {
    id: createBlockId('feed'),
    type: 'zone_feed',
    enabled: true,
    title: '专区商品流',
    subtitle: '真实专区数据',
    source_key: 'hotSale',
    limit: 4,
    path: '/pages/packages/list',
    open_type: 'switchTab'
  }
}

function createCustomImageSwiper() {
  return {
    id: createBlockId('swiper'),
    type: 'image_swiper',
    enabled: true,
    title: '活动轮播',
    section_kicker: '',
    count_suffix: '',
    kicker: '',
    desc: '',
    tags: [],
    slide_tags: [],
    autoplay: true,
    items: [createSwiperItem(), createSwiperItem(), createSwiperItem()]
  }
}

function createCustomMixedGoods() {
  return {
    id: createBlockId('mixed'),
    type: 'mixed_goods',
    enabled: true,
    title: '精选商品',
    subtitle: '运营自定义',
    items: [createMixedGoodsItem(), createMixedGoodsItem(), createMixedGoodsItem(), createMixedGoodsItem()]
  }
}

function createNewcomerTemplateBlocks() {
  const banner = createCustomBanner()
  banner.badge = '新人专享'
  banner.title = '先领券，再挑套餐和热门商品'
  banner.desc = '适合首页首屏承接新客注册、首单优惠和入场资格转化。'
  banner.button_text = '领取权益'

  const coupon = createCustomCouponStrip()
  coupon.badge = '新人礼包'
  coupon.title = '首单礼包、满减券和复购券统一承接'
  coupon.desc = '把新人券包和套餐权益放在同一个入口，减少用户理解成本。'

  const goods = createCustomMixedGoods()
  goods.title = '新客必看'
  goods.subtitle = '首单推荐'
  goods.items = [
    {
      enabled: true,
      tag: '首单特价',
      title: '新人试水套餐',
      desc: '适合先开权益再进入复购链路',
      price_text: '¥99 起',
      path: '/pages/packages/list',
      open_type: 'switchTab'
    },
    {
      enabled: true,
      tag: '热门专区',
      title: '爆款专区精选',
      desc: '优先看低门槛、成交快的引流商品',
      price_text: '限时活动',
      path: '/pages/packages/list',
      open_type: 'switchTab'
    },
    {
      enabled: true,
      tag: '权益叠加',
      title: '领券后再下单',
      desc: '突出券后价和返券权益，拉高首单转化',
      price_text: '券后更省',
      path: '/pages/packages/list',
      open_type: 'switchTab'
    }
  ]

  return [banner, coupon, goods]
}

function createCampaignTemplateBlocks() {
  const swiper = createCustomImageSwiper()
  swiper.title = '活动会场'
  swiper.items = [
    {
      enabled: true,
      badge: '主会场',
      title: '限时秒杀专场',
      desc: '大促主视觉、会场氛围和主推商品集中展示',
      path: '/pages/packages/list',
      open_type: 'switchTab'
    },
    {
      enabled: true,
      badge: '加码场',
      title: '券后爆款专区',
      desc: '突出低价心智，配合权益条做二次承接',
      path: '/pages/packages/list',
      open_type: 'switchTab'
    },
    {
      enabled: true,
      badge: '返场',
      title: '返场加购推荐',
      desc: '承接错峰流量，延长活动成交周期',
      path: '/pages/packages/list',
      open_type: 'switchTab'
    }
  ]

  const grid = createCustomGrid()
  grid.title = '会场分区'
  grid.subtitle = '楼层导航'
  grid.items = [
    { enabled: true, title: '爆款区', desc: '低价抢购', path: '/pages/packages/list', open_type: 'switchTab' },
    { enabled: true, title: '套餐区', desc: '权益转化', path: '/pages/packages/list', open_type: 'switchTab' },
    { enabled: true, title: '满减券', desc: '活动券包', path: '/pages/packages/list', open_type: 'switchTab' },
    { enabled: true, title: '返场区', desc: '晚场补单', path: '/pages/packages/list', open_type: 'switchTab' }
  ]

  const goods = createCustomMixedGoods()
  goods.title = '主推商品'
  goods.subtitle = '运营精选'
  goods.items = [
    {
      enabled: true,
      tag: '热卖',
      title: '活动主推套餐',
      desc: '大促期重点承接的核心权益套餐',
      price_text: '活动价',
      path: '/pages/packages/list',
      open_type: 'switchTab'
    },
    {
      enabled: true,
      tag: '加购',
      title: '爆款加购商品',
      desc: '适合和券包组合展示，提升客单价',
      price_text: '限时加购',
      path: '/pages/packages/list',
      open_type: 'switchTab'
    }
  ]

  return [swiper, grid, goods]
}

function createLocalLifeTemplateBlocks() {
  const banner = createCustomBanner()
  banner.badge = '到店精选'
  banner.title = '附近门店服务与爆品一起前置'
  banner.desc = '突出门店服务、到店履约和联盟商家合作，适合本地生活首页氛围。'
  banner.button_text = '查看门店'
  banner.path = '/pages/local-life/index'
  banner.open_type = 'switchTab'

  const feed = createCustomZoneFeed()
  feed.title = '本地热门服务'
  feed.subtitle = '实时商家数据'
  feed.source_key = 'localLife'
  feed.limit = 6
  feed.path = '/pages/local-life/index'
  feed.open_type = 'switchTab'

  const grid = createCustomGrid()
  grid.title = '服务导航'
  grid.subtitle = '到店 / 团购 / 商家'
  grid.items = [
    { enabled: true, title: '到店服务', desc: '门店核销', path: '/pages/local-life/index', open_type: 'switchTab' },
    { enabled: true, title: '团购套餐', desc: '本地团购', path: '/pages/local-life/index', open_type: 'switchTab' },
    { enabled: true, title: '联盟商家', desc: '合作门店', path: '/pages/local-life/index', open_type: 'switchTab' },
    { enabled: true, title: '订单核销', desc: '履约进度', path: '/subpackages/life/orders', open_type: 'navigate' }
  ]

  return [banner, feed, grid]
}

function createDefaultPayload() {
  const homeSwiper = createDefaultHomeSwiper()
  return {
    layout: [customLayoutKey(homeSwiper.id), ...SECTION_ORDER],
    custom_blocks: [homeSwiper],
    announcement: {
      enabled: true,
      title: '首页提醒',
      lines: [
        '首页首屏统一承接轮播活动、四区导航和推荐商品流。',
        '订单统一收进“我的”，本地生活已经进入底部导航栏。'
      ]
    },
    waterfall_section: {
      enabled: true,
      title: '推荐好货',
      subtitle: '下拉刷新，继续发现',
      page_size: 8,
      source_keys: ['hotSale', 'selfOperated', 'localLife']
    },
    package_section: {
      enabled: true,
      title: '套餐入口',
      desc: '套餐仍保留在首页中段，服务入场资格、抵扣规则和经营权益判断。',
      limit: 2
    },
    promo_section: {
      enabled: true,
      title: '会场推荐',
      subtitle: '运营精选',
      items: [
        {
          enabled: true,
          badge: '新人转化',
          title: '首单先看权益和热门专区',
          desc: '把新手礼包、主推套餐和爆款商品收进同一层转化入口。',
          path: '/pages/packages/list',
          open_type: 'switchTab'
        },
        {
          enabled: true,
          badge: '本地生活',
          title: '到店服务和联盟商家进入底部栏',
          desc: '本地生活从首页运营卡升级为底部导航，门店服务触达更直接。',
          path: '/pages/local-life/index',
          open_type: 'switchTab'
        }
      ]
    },
    zone_section: {
      enabled: true,
      title: '四区导航',
      subtitle: '热门分区',
      items: [
        { enabled: true, key: 'repurchase', title: '复购区', tip: '套餐进入，二次复购 4-6 折', icon_url: '', link_text: '进入专区', show_count: true, path: '/pages/packages/list', open_type: 'switchTab' },
        { enabled: true, key: 'selfOperated', title: '自营商城', tip: '兑换券 5-7 折抵扣，返 AI 券', icon_url: '', link_text: '进入专区', show_count: true, path: '/pages/packages/list', open_type: 'switchTab' },
        { enabled: true, key: 'hotSale', title: '爆款区', tip: '低价抢购，支持积分或余额', icon_url: '', link_text: '进入专区', show_count: true, path: '/pages/packages/list', open_type: 'switchTab' },
        { enabled: true, key: 'localLife', title: '本地生活', tip: '联盟商家服务、门店履约与收益联动', icon_url: '', link_text: '进入专区', show_count: true, path: '/pages/local-life/index', open_type: 'switchTab' }
      ]
    },
    quick_section: {
      enabled: true,
      title: '我的常用',
      subtitle: '个人中心',
      items: [
        { enabled: true, title: '套餐中心', desc: '查看入场资格与权益档位', icon_url: '', path: '/pages/packages/list', open_type: 'switchTab' },
        { enabled: true, title: '我的团队', desc: '管理归属与成员结构', icon_url: '', path: '/subpackages/team/index', open_type: 'navigate' },
        { enabled: true, title: '邀请好友', desc: '分享邀请码完成绑定', icon_url: '', path: '/subpackages/invite/index', open_type: 'navigate' },
        { enabled: true, title: '佣金中心', desc: '跟进冻结与可提现状态', icon_url: '', path: '/subpackages/commission/index', open_type: 'navigate' },
        { enabled: true, title: '我的资产', desc: '查看余额、消费金、积分和充电宝', icon_url: '', path: '/subpackages/assets/index', open_type: 'navigate' },
        { enabled: true, title: '个人中心', desc: '维护资料、签到和账号设置', icon_url: '', path: '/pages/profile/index', open_type: 'switchTab' }
      ]
    }
  }
}

function createGrowthPayload() {
  const payload = clonePayload(createDefaultPayload())
  payload.layout = ['custom:home_swiper_main', 'announcement', 'zone_section', 'waterfall_section', 'package_section', 'promo_section', 'quick_section']
  payload.announcement.title = '增长重点'
  payload.announcement.lines = [
    '先用首屏轮播和瀑布流拉起点击，再承接套餐和邀请绑定。',
    '订单沉淀到“我的”，首页不再承担订单中心角色。'
  ]
  payload.promo_section.items = [
    {
      enabled: true,
      badge: '拉新优先',
      title: '邀请码和热门专区联动转化',
      desc: '先让用户点击活动和热区，再承接邀请绑定和首单。',
      path: '/subpackages/invite/index',
      open_type: 'navigate'
    },
    {
      enabled: true,
      badge: '转化优先',
      title: '瀑布流继续承接套餐和爆款商品',
      desc: '首屏转化后，继续用双列商品流推动点击和下单。',
      path: '/pages/packages/list',
      open_type: 'switchTab'
    }
  ]
  payload.custom_blocks.push(createCustomCouponStrip())
  payload.layout.push(customLayoutKey(payload.custom_blocks[payload.custom_blocks.length - 1].id))
  return payload
}

function createLocalLifePayload() {
  const payload = clonePayload(createDefaultPayload())
  payload.layout = ['custom:home_swiper_main', 'announcement', 'zone_section', 'waterfall_section', 'promo_section', 'package_section', 'quick_section']
  payload.announcement.title = '本地生活重点'
  payload.announcement.lines = [
    '轮播和瀑布流都会优先承接本地生活内容与服务供给。',
    '本地生活已进入底部导航，首页保留四区导流与推荐承接。'
  ]
  payload.promo_section.items = [
    {
      enabled: true,
      badge: '门店履约',
      title: '本地生活订单围绕核销节点组织',
      desc: '支付后待核销，核销完成后再进入佣金释放和结算。',
      path: '/subpackages/life/orders',
      open_type: 'navigate'
    },
    {
      enabled: true,
      badge: '商家经营',
      title: '先看联盟商家，再看服务供给',
      desc: '让线下团队更快判断门店规模和商品服务承接能力。',
      path: '/pages/local-life/index',
      open_type: 'switchTab'
    }
  ]
  payload.zone_section.items = [
    { enabled: true, key: 'localLife', title: '本地生活', tip: '联盟商家服务、门店履约与收益联动', icon_url: '', link_text: '进入专区', show_count: true, path: '/pages/local-life/index', open_type: 'switchTab' },
    { enabled: true, key: 'repurchase', title: '复购区', tip: '套餐进入，二次复购 4-6 折', icon_url: '', link_text: '进入专区', show_count: true, path: '/pages/packages/list', open_type: 'switchTab' },
    { enabled: true, key: 'selfOperated', title: '自营商城', tip: '兑换券 5-7 折抵扣，返 AI 券', icon_url: '', link_text: '进入专区', show_count: true, path: '/pages/packages/list', open_type: 'switchTab' },
    { enabled: true, key: 'hotSale', title: '爆款区', tip: '低价抢购，支持积分或余额', icon_url: '', link_text: '进入专区', show_count: true, path: '/pages/packages/list', open_type: 'switchTab' }
  ]
  payload.waterfall_section = {
    enabled: true,
    title: '本地优选',
    subtitle: '门店服务和热点专区混排推荐',
    page_size: 8,
    source_keys: ['localLife', 'hotSale', 'selfOperated']
  }
  const localFeed = createCustomZoneFeed()
  localFeed.source_key = 'localLife'
  localFeed.path = '/pages/local-life/index'
  localFeed.open_type = 'switchTab'
  payload.custom_blocks.push(localFeed)
  payload.layout.splice(4, 0, customLayoutKey(localFeed.id))
  return payload
}

function splitLines(value) {
  return String(value || '')
    .split(/[\n,，]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function joinLines(values) {
  return Array.isArray(values) ? values.filter(Boolean).join('\n') : ''
}

function clonePayload(payload) {
  return JSON.parse(JSON.stringify(payload || createDefaultPayload()))
}

function normalizeEnabled(value, fallback = true) {
  if (typeof value === 'boolean') {
    return value
  }
  if (value === 'false' || value === '0' || value === 0) {
    return false
  }
  if (value === 'true' || value === '1' || value === 1) {
    return true
  }
  return fallback
}

function fieldOrDefault(source, field, fallback = '') {
  return Object.prototype.hasOwnProperty.call(source || {}, field) ? String(source?.[field] || '').trim() : fallback
}

function normalizeLayout(layout, fallback = SECTION_ORDER, customBlocks = []) {
  const source = Array.isArray(layout) ? layout : fallback
  const customKeys = customBlocks.map((item) => customLayoutKey(item.id))
  const allowed = [...SECTION_ORDER, ...customKeys]
  const rows = []
  source.forEach((item) => {
    if (allowed.includes(item) && !rows.includes(item)) {
      rows.push(item)
    }
  })
  fallback.forEach((item) => {
    if (!rows.includes(item)) {
      rows.push(item)
    }
  })
  customKeys.forEach((item) => {
    if (!rows.includes(item)) {
      rows.push(item)
    }
  })
  return rows
}

function normalizeCustomBlock(block, index = 0) {
  const type = ['grid', 'coupon_strip', 'zone_feed', 'image_swiper', 'mixed_goods'].includes(block?.type) ? block.type : 'banner'
  if (type === 'grid') {
    return {
      id: block?.id || createBlockId(`grid_${index}`),
      type,
      enabled: normalizeEnabled(block?.enabled, true),
      title: block?.title || '',
      subtitle: block?.subtitle || '',
      items: Array.isArray(block?.items) && block.items.length
        ? block.items.map((item) => ({
            ...createGridItem(),
            ...item,
            enabled: normalizeEnabled(item?.enabled, true)
          }))
        : [createGridItem(), createGridItem()]
    }
  }
  if (type === 'coupon_strip') {
    return {
      id: block?.id || createBlockId(`coupon_${index}`),
      type,
      enabled: normalizeEnabled(block?.enabled, true),
      badge: block?.badge || '',
      title: block?.title || '',
      desc: block?.desc || '',
      path: block?.path || '',
      open_type: block?.open_type || 'navigate'
    }
  }
  if (type === 'zone_feed') {
    return {
      id: block?.id || createBlockId(`feed_${index}`),
      type,
      enabled: normalizeEnabled(block?.enabled, true),
      title: block?.title || '',
      subtitle: block?.subtitle || '',
      source_key: ZONE_SOURCE_OPTIONS.some((item) => item.value === block?.source_key) ? block.source_key : 'repurchase',
      limit: Math.max(1, Math.min(12, Number(block?.limit || 4))),
      path: block?.path || '',
      open_type: block?.open_type || 'navigate'
    }
  }
  if (type === 'image_swiper') {
    const fallbackBlock = block?.id === 'home_swiper_main' ? createDefaultHomeSwiper() : {}
    return {
      id: block?.id || createBlockId(`swiper_${index}`),
      type,
      enabled: normalizeEnabled(block?.enabled, true),
      title: fieldOrDefault(block, 'title', fallbackBlock.title || ''),
      section_kicker: fieldOrDefault(block, 'section_kicker', fallbackBlock.section_kicker || ''),
      count_suffix: fieldOrDefault(block, 'count_suffix', fallbackBlock.count_suffix || ''),
      kicker: fieldOrDefault(block, 'kicker', fallbackBlock.kicker || ''),
      desc: fieldOrDefault(block, 'desc', fallbackBlock.desc || ''),
      tags: Array.isArray(block?.tags) ? block.tags.filter(Boolean) : (fallbackBlock.tags || []),
      slide_tags: Array.isArray(block?.slide_tags) ? block.slide_tags.filter(Boolean) : (fallbackBlock.slide_tags || []),
      autoplay: normalizeEnabled(block?.autoplay, true),
      items: Array.isArray(block?.items) && block.items.length
        ? block.items.map((item) => ({
            ...createSwiperItem(),
            ...item,
            enabled: normalizeEnabled(item?.enabled, true)
          }))
        : (fallbackBlock.items || [createSwiperItem(), createSwiperItem()])
    }
  }
  if (type === 'mixed_goods') {
    return {
      id: block?.id || createBlockId(`mixed_${index}`),
      type,
      enabled: normalizeEnabled(block?.enabled, true),
      title: block?.title || '',
      subtitle: block?.subtitle || '',
      items: Array.isArray(block?.items) && block.items.length
        ? block.items.map((item) => ({
            ...createMixedGoodsItem(),
            ...item,
            enabled: normalizeEnabled(item?.enabled, true)
          }))
        : [createMixedGoodsItem(), createMixedGoodsItem()]
    }
  }
  return {
    id: block?.id || createBlockId(`banner_${index}`),
    type,
    enabled: normalizeEnabled(block?.enabled, true),
    badge: block?.badge || '',
    title: block?.title || '',
    desc: block?.desc || '',
    button_text: block?.button_text || '立即查看',
    path: block?.path || '',
    open_type: block?.open_type || 'navigate'
  }
}

function normalizePayload(payload) {
  const defaults = createDefaultPayload()
  const next = clonePayload(payload || defaults)
  const customBlocksSource = Array.isArray(next.custom_blocks) ? next.custom_blocks : defaults.custom_blocks
  const customBlocks = customBlocksSource.map((block, index) => normalizeCustomBlock(block, index))

  next.custom_blocks = customBlocks
  next.layout = normalizeLayout(next.layout, defaults.layout, customBlocks)
  next.announcement = {
    enabled: normalizeEnabled(next.announcement?.enabled, defaults.announcement.enabled),
    title: fieldOrDefault(next.announcement, 'title', defaults.announcement.title),
    lines: Array.isArray(next.announcement?.lines) ? next.announcement.lines.filter(Boolean) : defaults.announcement.lines
  }
  next.package_section = {
    enabled: normalizeEnabled(next.package_section?.enabled, defaults.package_section.enabled),
    title: fieldOrDefault(next.package_section, 'title', defaults.package_section.title),
    desc: next.package_section?.desc || defaults.package_section.desc,
    limit: Math.max(1, Math.min(6, Number(next.package_section?.limit || defaults.package_section.limit)))
  }
  next.promo_section = {
    enabled: normalizeEnabled(next.promo_section?.enabled, defaults.promo_section.enabled),
    title: fieldOrDefault(next.promo_section, 'title', defaults.promo_section.title),
    subtitle: fieldOrDefault(next.promo_section, 'subtitle', defaults.promo_section.subtitle),
    items: Array.isArray(next.promo_section?.items) && next.promo_section.items.length
      ? next.promo_section.items.map((item) => ({
          ...createPromoCard(),
          ...item,
          enabled: normalizeEnabled(item?.enabled, true)
        }))
      : clonePayload(defaults.promo_section.items)
  }
  next.zone_section = {
    enabled: normalizeEnabled(next.zone_section?.enabled, defaults.zone_section.enabled),
    title: fieldOrDefault(next.zone_section, 'title', defaults.zone_section.title),
    subtitle: fieldOrDefault(next.zone_section, 'subtitle', defaults.zone_section.subtitle),
    items: Array.isArray(next.zone_section?.items) && next.zone_section.items.length
      ? next.zone_section.items.map((item) => ({
          ...createZoneItem(),
          ...item,
          enabled: normalizeEnabled(item?.enabled, true),
          link_text: fieldOrDefault(item, 'link_text', '进入专区'),
          show_count: normalizeEnabled(item?.show_count, true)
        }))
      : clonePayload(defaults.zone_section.items)
  }
  next.waterfall_section = {
    enabled: normalizeEnabled(next.waterfall_section?.enabled, defaults.waterfall_section.enabled),
    title: fieldOrDefault(next.waterfall_section, 'title', defaults.waterfall_section.title),
    subtitle: fieldOrDefault(next.waterfall_section, 'subtitle', defaults.waterfall_section.subtitle),
    page_size: Math.max(4, Math.min(20, Number(next.waterfall_section?.page_size || defaults.waterfall_section.page_size))),
    source_keys: Array.isArray(next.waterfall_section?.source_keys) && next.waterfall_section.source_keys.length
      ? next.waterfall_section.source_keys.filter((item) => ZONE_SOURCE_OPTIONS.some((option) => option.value === item))
      : clonePayload(defaults.waterfall_section.source_keys)
  }
  next.quick_section = {
    enabled: normalizeEnabled(next.quick_section?.enabled, defaults.quick_section.enabled),
    title: fieldOrDefault(next.quick_section, 'title', defaults.quick_section.title),
    subtitle: fieldOrDefault(next.quick_section, 'subtitle', defaults.quick_section.subtitle),
    items: Array.isArray(next.quick_section?.items) && next.quick_section.items.length
      ? next.quick_section.items.map((item) => ({
          ...createQuickItem(),
          ...item,
          enabled: normalizeEnabled(item?.enabled, true)
        }))
      : clonePayload(defaults.quick_section.items)
  }
  return next
}

const presetFactories = {
  default: createDefaultPayload,
  growth: createGrowthPayload,
  localLife: createLocalLifePayload
}
const customBlockTemplateFactories = {
  newcomer: createNewcomerTemplateBlocks,
  campaign: createCampaignTemplateBlocks,
  localLife: createLocalLifeTemplateBlocks
}

const form = reactive(createDefaultPayload())
const announcementLinesText = ref('')
const saving = ref(false)
const exportDialogVisible = ref(false)
const importDialogVisible = ref(false)
const exportJsonText = ref('')
const importJsonText = ref('')
const uploadingImageKey = ref('')
const uploadingSwiperImageKey = ref('')
const collapsedCustomBlocks = ref({})
const dragState = reactive({
  type: '',
  blockId: '',
  from: -1,
  over: -1
})

const customBlockMap = computed(() => {
  const map = {}
  form.custom_blocks.forEach((block) => {
    map[customLayoutKey(block.id)] = block
  })
  return map
})
const zoneSourceOptions = computed(() => ZONE_SOURCE_OPTIONS.map((item) => ({
  ...item,
  label: zoneSourceLabel(item.value)
})))

const previewAnnouncementLines = computed(() => splitLines(announcementLinesText.value))
const previewPromoCards = computed(() => form.promo_section.items.filter((item) => item.enabled !== false && (item.badge || item.title || item.desc)))
const previewZoneItems = computed(() => form.zone_section.items.filter((item) => item.enabled !== false && (item.key || item.title || item.tip || item.icon_url)))
const previewWaterfallSources = computed(() => (form.waterfall_section.source_keys || []).map((item) => zoneSourceLabel(item)).join(' / '))
const previewQuickItems = computed(() => form.quick_section.items.filter((item) => item.enabled !== false && (item.title || item.desc || item.icon_url)))
const previewPrimarySwiperBlock = computed(() => {
  return form.custom_blocks.find((block) => block.type === 'image_swiper' && block.enabled !== false && customSwiperItems(block).length > 0) || null
})
const previewPrimarySwiperItems = computed(() => customSwiperItems(previewPrimarySwiperBlock.value))
const previewPrimarySwiperLayoutKey = computed(() => (previewPrimarySwiperBlock.value ? customLayoutKey(previewPrimarySwiperBlock.value.id) : ''))
const customSectionEnabledMap = computed(() => {
  const map = {}
  form.custom_blocks.forEach((block) => {
    if (block.type === 'grid') {
      map[customLayoutKey(block.id)] = block.enabled !== false && customGridItems(block).length > 0
      return
    }
    if (block.type === 'image_swiper') {
      map[customLayoutKey(block.id)] = block.enabled !== false && customSwiperItems(block).length > 0
      return
    }
    if (block.type === 'mixed_goods') {
      map[customLayoutKey(block.id)] = block.enabled !== false && customMixedGoodsItems(block).length > 0
      return
    }
    if (block.type === 'zone_feed') {
      map[customLayoutKey(block.id)] = block.enabled !== false && (block.title || block.subtitle)
      return
    }
    map[customLayoutKey(block.id)] = block.enabled !== false && (block.title || block.desc || block.badge)
  })
  return map
})
const sectionEnabledMap = computed(() => ({
  announcement: form.announcement.enabled && previewAnnouncementLines.value.length > 0,
  zone_section: form.zone_section.enabled && previewZoneItems.value.length > 0,
  waterfall_section: form.waterfall_section.enabled && (form.waterfall_section.source_keys || []).length > 0,
  package_section: form.package_section.enabled,
  promo_section: form.promo_section.enabled && previewPromoCards.value.length > 0,
  quick_section: form.quick_section.enabled && previewQuickItems.value.length > 0,
  ...customSectionEnabledMap.value
}))
const orderedPreviewKeys = computed(() => form.layout.filter((key) => sectionEnabledMap.value[key] && key !== previewPrimarySwiperLayoutKey.value))

function zoneSourceLabel(key) {
  const zoneItem = form.zone_section?.items?.find((item) => item.key === key && item.title)
  return zoneItem?.title || ZONE_SOURCE_OPTIONS.find((item) => item.value === key)?.label || '专区'
}

function customBlockTypeLabel(type) {
  return {
    banner: '活动横幅',
    grid: '宫格导航',
    coupon_strip: '券权益条',
    zone_feed: '专区商品流',
    image_swiper: '轮播海报',
    mixed_goods: '混合商品'
  }[type] || '自定义模块'
}

function customBlockFromLayout(sectionKey) {
  return customBlockMap.value[sectionKey] || null
}

function isCustomBlockCollapsed(blockId) {
  return !!collapsedCustomBlocks.value[blockId]
}

function customGridItems(block) {
  return (block?.items || []).filter((item) => item.enabled !== false && (item.title || item.desc || item.icon_url))
}

function navItemFallbackText(item, fallback = '入口') {
  const title = String(item?.title || item?.key || fallback).trim()
  return title.slice(0, 2) || fallback
}

function customSwiperItems(block) {
  return (block?.items || []).filter((item) => item.enabled !== false && (item.badge || item.title || item.desc || item.image_url))
}

function previewSwiperStyle(item) {
  const imageUrl = String(item?.image_url || '').trim()
  const imageLayer = imageUrl ? `linear-gradient(180deg, rgba(18, 31, 35, 0.08) 0%, rgba(18, 31, 35, 0.38) 100%), url("${imageUrl}") center / cover no-repeat` : ''
  return {
    background: imageLayer || 'linear-gradient(145deg, #18343b 0%, #275d57 58%, #1f8f64 100%)'
  }
}

function customMixedGoodsItems(block) {
  return (block?.items || []).filter((item) => item.enabled !== false && (item.tag || item.title || item.desc || item.price_text))
}

function sectionLabel(sectionKey) {
  if (SECTION_META[sectionKey]) {
    return SECTION_META[sectionKey].label
  }
  const block = customBlockFromLayout(sectionKey)
  return block?.title || customBlockTypeLabel(block?.type)
}

function sectionHint(sectionKey) {
  if (SECTION_META[sectionKey]) {
    return SECTION_META[sectionKey].hint
  }
  const block = customBlockFromLayout(sectionKey)
  if (!block) {
    return ''
  }
  if (block.type === 'zone_feed') {
    return `使用 ${zoneSourceLabel(block.source_key)} 的真实商品或服务数据`
  }
  if (block.type === 'coupon_strip') {
    return '用于表达领券、满减、会员券等权益转化'
  }
  if (block.type === 'image_swiper') {
    return '用于首页顶部或中部活动轮播位'
  }
  if (block.type === 'mixed_goods') {
    return '用于运营手动编排的商品卡片列表'
  }
  return block.type === 'grid' ? '后台自定义的专题导航模块' : '后台自定义的活动横幅模块'
}

function sectionEnabled(sectionKey) {
  return !!sectionEnabledMap.value[sectionKey]
}

function assignPayload(payload) {
  const next = normalizePayload(payload)
  Object.keys(next).forEach((key) => {
    form[key] = next[key]
  })
  announcementLinesText.value = (next.announcement.lines || []).join('\n')
}

function buildExportCustomBlocks() {
  return buildPayload().custom_blocks
}

function buildPayload() {
  return {
    layout: [...form.layout],
    custom_blocks: form.custom_blocks.map((block) => {
      if (block.type === 'grid') {
        return {
          id: block.id,
          type: block.type,
          enabled: !!block.enabled,
          title: block.title,
          subtitle: block.subtitle,
          items: block.items.map((item) => ({
            enabled: !!item.enabled,
            title: item.title,
            desc: item.desc,
            icon_url: item.icon_url,
            path: item.path,
            open_type: item.open_type
          }))
        }
      }
      if (block.type === 'coupon_strip') {
        return {
          id: block.id,
          type: block.type,
          enabled: !!block.enabled,
          badge: block.badge,
          title: block.title,
          desc: block.desc,
          path: block.path,
          open_type: block.open_type
        }
      }
      if (block.type === 'zone_feed') {
        return {
          id: block.id,
          type: block.type,
          enabled: !!block.enabled,
          title: block.title,
          subtitle: block.subtitle,
          source_key: block.source_key,
          limit: Number(block.limit || 4),
          path: block.path,
          open_type: block.open_type
        }
      }
      if (block.type === 'image_swiper') {
        return {
          id: block.id,
          type: block.type,
          enabled: !!block.enabled,
          title: block.title,
          section_kicker: block.section_kicker,
          count_suffix: block.count_suffix,
          kicker: block.kicker,
          desc: block.desc,
          tags: [...(block.tags || [])],
          slide_tags: [...(block.slide_tags || [])],
          autoplay: !!block.autoplay,
          items: block.items.map((item) => ({
            enabled: !!item.enabled,
            badge: item.badge,
            title: item.title,
            desc: item.desc,
            image_url: item.image_url,
            path: item.path,
            open_type: item.open_type
          }))
        }
      }
      if (block.type === 'mixed_goods') {
        return {
          id: block.id,
          type: block.type,
          enabled: !!block.enabled,
          title: block.title,
          subtitle: block.subtitle,
          items: block.items.map((item) => ({
            enabled: !!item.enabled,
            tag: item.tag,
            title: item.title,
            desc: item.desc,
            price_text: item.price_text,
            path: item.path,
            open_type: item.open_type
          }))
        }
      }
      return {
        id: block.id,
        type: block.type,
        enabled: !!block.enabled,
        badge: block.badge,
        title: block.title,
        desc: block.desc,
        button_text: block.button_text,
        path: block.path,
        open_type: block.open_type
      }
    }),
    announcement: {
      enabled: !!form.announcement.enabled,
      title: form.announcement.title,
      lines: splitLines(announcementLinesText.value)
    },
    package_section: {
      enabled: !!form.package_section.enabled,
      title: form.package_section.title,
      desc: form.package_section.desc,
      limit: Number(form.package_section.limit || 2)
    },
    promo_section: {
      enabled: !!form.promo_section.enabled,
      title: form.promo_section.title,
      subtitle: form.promo_section.subtitle,
      items: form.promo_section.items.map((item) => ({
        enabled: !!item.enabled,
        badge: item.badge,
        title: item.title,
        desc: item.desc,
        path: item.path,
        open_type: item.open_type
      }))
    },
    zone_section: {
      enabled: !!form.zone_section.enabled,
      title: form.zone_section.title,
      subtitle: form.zone_section.subtitle,
      items: form.zone_section.items.map((item) => ({
        enabled: !!item.enabled,
        key: item.key,
        title: item.title,
        tip: item.tip,
        icon_url: item.icon_url,
        link_text: item.link_text,
        show_count: !!item.show_count,
        path: item.path,
        open_type: item.open_type
      }))
    },
    waterfall_section: {
      enabled: !!form.waterfall_section.enabled,
      title: form.waterfall_section.title,
      subtitle: form.waterfall_section.subtitle,
      page_size: Number(form.waterfall_section.page_size || 8),
      source_keys: [...form.waterfall_section.source_keys]
    },
    quick_section: {
      enabled: !!form.quick_section.enabled,
      title: form.quick_section.title,
      subtitle: form.quick_section.subtitle,
      items: form.quick_section.items.map((item) => ({
        enabled: !!item.enabled,
        title: item.title,
        desc: item.desc,
        icon_url: item.icon_url,
        path: item.path,
        open_type: item.open_type
      }))
    }
  }
}

async function loadData() {
  const data = await decorationApi.mobileHome()
  assignPayload(data?.payload || createDefaultPayload())
}

function reorderList(items, from, to) {
  if (from === to || from < 0 || to < 0 || from >= items.length || to >= items.length) {
    return
  }
  const [current] = items.splice(from, 1)
  items.splice(to, 0, current)
}

function moveItem(items, index, offset) {
  const target = index + offset
  if (target < 0 || target >= items.length) {
    return
  }
  const [current] = items.splice(index, 1)
  items.splice(target, 0, current)
}

function moveLayoutSection(index, offset) {
  moveItem(form.layout, index, offset)
}

function isDragActive(type, blockId, index) {
  return dragState.type === type && dragState.blockId === blockId && dragState.over === index
}

function startDrag(type, blockId, index) {
  dragState.type = type
  dragState.blockId = blockId
  dragState.from = index
  dragState.over = index
}

function dragOverDrag(type, blockId, index) {
  if (dragState.type !== type || dragState.blockId !== blockId) {
    return
  }
  dragState.over = index
}

function dropDrag(items, type, blockId, index) {
  if (dragState.type !== type || dragState.blockId !== blockId) {
    return
  }
  reorderList(items, dragState.from, index)
  endDrag()
}

function endDrag() {
  dragState.type = ''
  dragState.blockId = ''
  dragState.from = -1
  dragState.over = -1
}

function addCustomBlock(type) {
  const factoryMap = {
    banner: createCustomBanner,
    grid: createCustomGrid,
    coupon_strip: createCustomCouponStrip,
    zone_feed: createCustomZoneFeed,
    image_swiper: createCustomImageSwiper,
    mixed_goods: createCustomMixedGoods
  }
  const block = (factoryMap[type] || createCustomBanner)()
  form.custom_blocks.push(block)
  form.layout.push(customLayoutKey(block.id))
  collapsedCustomBlocks.value[block.id] = false
}

function appendCustomBlocks(blocks) {
  blocks.forEach((block) => {
    form.custom_blocks.push(block)
    form.layout.push(customLayoutKey(block.id))
    collapsedCustomBlocks.value[block.id] = false
  })
}

function replaceCustomBlocks(blocks) {
  const fixedLayout = form.layout.filter((item) => !String(item).startsWith('custom:'))
  form.custom_blocks.splice(0, form.custom_blocks.length)
  form.layout.splice(0, form.layout.length, ...fixedLayout)
  collapsedCustomBlocks.value = {}
  appendCustomBlocks(blocks)
}

function removeCustomBlock(index) {
  const [current] = form.custom_blocks.splice(index, 1)
  if (!current) {
    return
  }
  const nextLayout = form.layout.filter((item) => item !== customLayoutKey(current.id))
  form.layout.splice(0, form.layout.length, ...nextLayout)
}

function duplicateCustomBlock(block) {
  const duplicated = normalizeCustomBlock(clonePayload(block), form.custom_blocks.length)
  duplicated.id = createBlockId(customBlockIdPrefix(block?.type))
  if (typeof duplicated.title === 'string' && duplicated.title.trim()) {
    duplicated.title = `${duplicated.title} 副本`
  }
  form.custom_blocks.push(duplicated)
  const layoutIndex = form.layout.indexOf(customLayoutKey(block.id))
  const nextKey = customLayoutKey(duplicated.id)
  if (layoutIndex === -1) {
    form.layout.push(nextKey)
  } else {
    form.layout.splice(layoutIndex + 1, 0, nextKey)
  }
  collapsedCustomBlocks.value[duplicated.id] = false
  ElMessage.success('模块已复制')
}

function insertTemplateBlocks(templateKey) {
  const factory = customBlockTemplateFactories[templateKey]
  if (!factory) {
    return
  }
  const blocks = factory()
  appendCustomBlocks(blocks)
  const label = CUSTOM_BLOCK_TEMPLATE_META[templateKey]?.label || '模板'
  ElMessage.success(`${label}已插入`)
}

function openExportDialog() {
  exportJsonText.value = JSON.stringify(
    {
      version: 1,
      custom_blocks: buildExportCustomBlocks()
    },
    null,
    2
  )
  exportDialogVisible.value = true
}

async function copyExportJson() {
  if (!exportJsonText.value) {
    return
  }
  try {
    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(exportJsonText.value)
      ElMessage.success('模块 JSON 已复制')
      return
    }
  } catch (error) {
    console.error(error)
  }
  ElMessage.warning('当前环境不支持直接复制，请手动复制弹窗内容')
}

function normalizeImportedCustomBlocks(source) {
  let rawBlocks = []
  if (Array.isArray(source)) {
    rawBlocks = source
  } else if (Array.isArray(source?.custom_blocks)) {
    rawBlocks = source.custom_blocks
  } else if (source && typeof source === 'object') {
    rawBlocks = [source]
  }
  return rawBlocks.map((block, index) => {
    const normalized = normalizeCustomBlock(block, form.custom_blocks.length + index)
    normalized.id = createBlockId(customBlockIdPrefix(normalized.type))
    return normalized
  })
}

function importCustomBlocks(mode = 'append') {
  try {
    const parsed = JSON.parse(importJsonText.value || '')
    const blocks = normalizeImportedCustomBlocks(parsed)
    if (!blocks.length) {
      ElMessage.warning('没有识别到可导入的模块数据')
      return
    }
    if (mode === 'replace') {
      replaceCustomBlocks(blocks)
    } else {
      appendCustomBlocks(blocks)
    }
    importDialogVisible.value = false
    importJsonText.value = ''
    ElMessage.success(mode === 'replace' ? '模块已替换导入' : '模块已追加导入')
  } catch (error) {
    console.error(error)
    ElMessage.error('JSON 解析失败，请检查格式')
  }
}

function openImportDialog() {
  importJsonText.value = ''
  importDialogVisible.value = true
}

function toggleCustomBlockCollapsed(blockId) {
  collapsedCustomBlocks.value[blockId] = !collapsedCustomBlocks.value[blockId]
}

function collapseAllCustomBlocks() {
  const next = {}
  form.custom_blocks.forEach((block) => {
    next[block.id] = true
  })
  collapsedCustomBlocks.value = next
}

function expandAllCustomBlocks() {
  const next = {}
  form.custom_blocks.forEach((block) => {
    next[block.id] = false
  })
  collapsedCustomBlocks.value = next
}

function duplicateListItem(items, item, suffixField) {
  const duplicated = clonePayload(item)
  if (suffixField && typeof duplicated[suffixField] === 'string' && duplicated[suffixField].trim()) {
    duplicated[suffixField] = `${duplicated[suffixField]} 副本`
  }
  items.push(duplicated)
}

function addGridItem(block) {
  block.items.push(createGridItem())
}

function duplicateGridItem(block, item) {
  duplicateListItem(block.items, item, 'title')
}

function removeGridItem(block, index) {
  block.items.splice(index, 1)
}

function addSwiperItem(block) {
  block.items.push(createSwiperItem())
}

function swiperImageUploadKey(blockId, itemIndex) {
  return `${blockId}:${itemIndex}`
}

function itemImageUploadKey(sectionKey, itemType, itemIndex) {
  return `${sectionKey}:${itemType}:${itemIndex}`
}

async function uploadDecorationItemImage(options, item, uploadKey) {
  const file = options?.file
  if (!file) {
    ElMessage.error('未选择图片文件')
    return
  }
  uploadingImageKey.value = uploadKey
  try {
    const data = await decorationApi.uploadMobileHomeImage(file)
    item.icon_url = data?.url || ''
    ElMessage.success('图标已上传')
    options?.onSuccess?.(data)
  } catch (error) {
    console.error(error)
    options?.onError?.(error)
  } finally {
    uploadingImageKey.value = ''
  }
}

async function uploadSwiperImage(options, block, item, itemIndex) {
  const file = options?.file
  if (!file) {
    ElMessage.error('未选择图片文件')
    return
  }
  const uploadKey = swiperImageUploadKey(block.id, itemIndex)
  uploadingSwiperImageKey.value = uploadKey
  try {
    const data = await decorationApi.uploadMobileHomeImage(file)
    item.image_url = data?.url || ''
    ElMessage.success('轮播图已上传')
    options?.onSuccess?.(data)
  } catch (error) {
    console.error(error)
    options?.onError?.(error)
  } finally {
    uploadingSwiperImageKey.value = ''
  }
}

function duplicateSwiperItem(block, item) {
  duplicateListItem(block.items, item, 'title')
}

function removeSwiperItem(block, index) {
  block.items.splice(index, 1)
}

function addMixedGoodsItem(block) {
  block.items.push(createMixedGoodsItem())
}

function duplicateMixedGoodsItem(block, item) {
  duplicateListItem(block.items, item, 'title')
}

function removeMixedGoodsItem(block, index) {
  block.items.splice(index, 1)
}

function addPromoCard() {
  form.promo_section.items.push(createPromoCard())
}

function duplicatePromoCard(item) {
  duplicateListItem(form.promo_section.items, item, 'title')
}

function removePromoCard(index) {
  form.promo_section.items.splice(index, 1)
}

function addZoneItem() {
  form.zone_section.items.push(createZoneItem())
}

function duplicateZoneItem(item) {
  duplicateListItem(form.zone_section.items, item, 'title')
}

function removeZoneItem(index) {
  form.zone_section.items.splice(index, 1)
}

function addQuickItem() {
  form.quick_section.items.push(createQuickItem())
}

function duplicateQuickItem(item) {
  duplicateListItem(form.quick_section.items, item, 'title')
}

function removeQuickItem(index) {
  form.quick_section.items.splice(index, 1)
}

function applyPreset(type) {
  const factory = presetFactories[type] || createDefaultPayload
  assignPayload(factory())
  ElMessage.success('装修模板已应用，保存后生效')
}

async function saveDecoration() {
  saving.value = true
  try {
    await decorationApi.updateMobileHome(buildPayload())
    ElMessage.success('uni 首页装修已保存')
    await loadData()
  } finally {
    saving.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.toolbar-stack {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
}

.preset-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toolbar-label {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.editor-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  margin-bottom: 18px;
}

.section-panel {
  margin-bottom: 18px;
}

.section-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 14px;
}

.section-title-row.compact {
  margin-bottom: 0;
}

.section-title-row h3 {
  margin: 0;
  font-size: 18px;
}

.section-title-row span {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.section-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-header-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.toolbar-row.wrap {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.nested-actions {
  margin-top: 8px;
}

.section-config-row {
  align-items: end;
  margin-bottom: 16px;
}

.section-tip,
.mini-desc {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.mini-desc {
  margin: 6px 0 0;
}

.empty-inline {
  padding: 18px;
  border-radius: 14px;
  background: rgba(15, 76, 129, 0.04);
  color: var(--el-text-color-secondary);
}

.form-split {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.block-list {
  display: grid;
  gap: 14px;
}

.config-block,
.layout-block,
.sub-block {
  padding: 16px;
  border-radius: 14px;
  background: rgba(15, 76, 129, 0.04);
  border: 1px solid rgba(15, 76, 129, 0.08);
}

.config-block-head,
.layout-block {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.layout-block p {
  margin: 8px 0 0;
  color: var(--el-text-color-secondary);
  line-height: 1.6;
}

.drag-active {
  border-color: rgba(31, 143, 110, 0.35);
  box-shadow: 0 0 0 2px rgba(31, 143, 110, 0.08);
}

.layout-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 72px;
  padding: 6px 10px;
  border-radius: 999px;
  color: #8a6b15;
  background: rgba(201, 155, 73, 0.12);
  font-size: 12px;
}

.layout-status.enabled {
  color: #146a4b;
  background: rgba(31, 143, 110, 0.12);
}

.block-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.drag-handle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 72px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(24, 52, 59, 0.06);
  color: #18343b;
  font-size: 12px;
  cursor: grab;
  user-select: none;
}

.drag-handle:active {
  cursor: grabbing;
}

.preview-shell {
  margin-top: 4px;
}

.preview-heading {
  margin-bottom: 14px;
}

.swiper-upload-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.item-upload-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.swiper-image-preview-shell {
  margin-bottom: 14px;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(24, 52, 59, 0.08);
  background: rgba(24, 52, 59, 0.03);
}

.swiper-image-preview {
  display: block;
  width: 100%;
  max-height: 180px;
  object-fit: cover;
}

.item-image-preview-shell {
  width: 120px;
  margin-bottom: 14px;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(24, 52, 59, 0.08);
  background: rgba(24, 52, 59, 0.03);
}

.item-image-preview {
  display: block;
  width: 100%;
  height: 120px;
  object-fit: cover;
}

.mobile-preview {
  width: 420px;
  max-width: 100%;
  padding: 18px;
  border-radius: 28px;
  background:
    radial-gradient(circle at top right, rgba(200, 155, 73, 0.22), transparent 30%),
    linear-gradient(180deg, #fffdf8 0%, #eef4ef 100%);
  box-shadow: 0 20px 50px rgba(24, 52, 59, 0.12);
}

.preview-card {
  margin-bottom: 14px;
  padding: 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(24, 52, 59, 0.08);
}

.preview-banner-card,
.preview-coupon-card {
  background:
    radial-gradient(circle at top right, rgba(200, 155, 73, 0.16), transparent 34%),
    linear-gradient(180deg, rgba(255, 252, 244, 0.96) 0%, rgba(245, 249, 243, 0.96) 100%);
}

.preview-banner-card p,
.preview-coupon-card p {
  margin: 10px 0 0;
  line-height: 1.7;
}

.preview-badge {
  display: inline-flex;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
  font-size: 12px;
}

.preview-badge.muted {
  background: rgba(24, 52, 59, 0.08);
  color: #18343b;
}

.preview-action {
  display: inline-flex;
  margin-top: 14px;
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(24, 52, 59, 0.08);
  color: #18343b;
  font-size: 12px;
}

.tag-row,
.preview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 14px;
}

.mini-tag {
  padding: 8px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
  text-align: center;
  font-size: 12px;
}

.preview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.preview-head span,
.preview-lines,
.preview-mini-card p,
.preview-empty {
  color: var(--el-text-color-secondary);
}

.preview-lines {
  display: grid;
  gap: 8px;
  line-height: 1.7;
}

.preview-mini-card {
  position: relative;
  overflow: hidden;
  padding: 12px;
  border-radius: 14px;
  background: rgba(24, 52, 59, 0.04);
}

.preview-item-icon {
  width: 44px;
  height: 44px;
  margin-bottom: 10px;
  border-radius: 14px;
  background: linear-gradient(145deg, rgba(24, 52, 59, 0.1), rgba(30, 143, 100, 0.16));
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  color: #18343b;
  font-size: 13px;
  font-weight: 700;
}

.preview-item-icon-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.preview-item-icon-empty {
  width: 16px;
  height: 16px;
  border-radius: 6px;
  background: rgba(24, 52, 59, 0.16);
}

.preview-swiper-strip {
  display: grid;
  gap: 12px;
  margin-bottom: 16px;
}

.preview-swiper-mini-card {
  min-height: 132px;
  background: linear-gradient(145deg, #18343b 0%, #275d57 58%, #1f8f64 100%);
  color: #fff;
}

.preview-swiper-mask {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(11, 22, 27, 0.12) 0%, rgba(11, 22, 27, 0.56) 100%);
}

.preview-swiper-content {
  position: relative;
  z-index: 1;
}

.preview-mini-card strong {
  display: block;
  margin: 8px 0 8px;
}

.preview-mini-card p {
  margin: 0;
  line-height: 1.6;
}

.preview-swiper-mini-card .preview-badge.muted {
  background: rgba(255, 255, 255, 0.16);
  color: #fff;
}

.preview-swiper-mini-card p {
  color: rgba(255, 255, 255, 0.82);
}

.preview-empty {
  padding: 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.72);
  text-align: center;
}

.json-textarea {
  margin-top: 16px;
}

@media (max-width: 1200px) {
  .editor-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .toolbar-stack,
  .preset-row {
    width: 100%;
    align-items: flex-start;
  }

  .form-split {
    grid-template-columns: 1fr;
  }

  .section-header-actions,
  .config-block-head,
  .layout-block {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
