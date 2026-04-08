<template>
  <view class="page home-page">
    <view v-if="heroSwiperItems.length" class="swiper-panel">
      <view v-if="primarySwiperMeta.kicker || primarySwiperMeta.desc || primarySwiperMeta.tags.length" class="visual-strip">
        <view class="visual-copy-block">
          <view v-if="primarySwiperMeta.kicker" class="badge cinematic-badge">{{ primarySwiperMeta.kicker }}</view>
          <view v-if="primarySwiperMeta.desc" class="visual-copy">{{ primarySwiperMeta.desc }}</view>
        </view>
        <view v-if="primarySwiperMeta.tags.length" class="visual-pill-stack">
          <view v-for="item in primarySwiperMeta.tags" :key="item" class="mini-pill">{{ item }}</view>
        </view>
      </view>
      <swiper
        class="hero-swiper"
        circular
        :autoplay="primarySwiperBlock ? primarySwiperBlock.autoplay !== false : true"
        :indicator-dots="heroSwiperItems.length > 1"
        indicator-active-color="#ffffff"
      >
        <swiper-item v-for="(item, index) in heroSwiperItems" :key="`${item.title}-${index}`">
          <view class="swiper-slide tap-item" :class="{ 'with-image': !!item.image_url }" @click="openConfiguredLink(item)">
            <image v-if="item.image_url" class="slide-image" :src="item.image_url" mode="aspectFill" />
            <view class="slide-grid"></view>
            <view class="slide-glow"></view>
            <view class="slide-mask"></view>
            <view class="slide-content">
              <view class="slide-topline">
                <view class="slide-badge">{{ item.badge || '精选会场' }}</view>
                <view class="slide-series">S{{ formatSeriesIndex(index) }}</view>
              </view>
              <view class="slide-title">{{ item.title || '首页活动' }}</view>
              <view class="slide-desc">{{ item.desc || '请在后台补充轮播文案' }}</view>
              <view v-if="primarySwiperMeta.slideTags.length" class="slide-footer">
                <view v-for="tag in primarySwiperMeta.slideTags" :key="tag" class="slide-chip">{{ tag }}</view>
              </view>
            </view>
          </view>
        </swiper-item>
      </swiper>
    </view>

      <view v-if="loadError" class="card status-card">
      <view class="status-title">首页数据加载失败</view>
      <view class="status-desc">{{ loadError }}</view>
      <button class="secondary-btn retry-btn" @click="loadData({ resetWaterfall: true })">重新加载</button>
    </view>

    <block v-for="sectionKey in orderedSectionKeys" :key="sectionKey">
      <view v-if="sectionKey === 'announcement'" class="card notice-card">
        <view v-if="decoration.announcement.title" class="section-head compact">
          <view class="section-title">{{ decoration.announcement.title }}</view>
          <view class="section-link">首页公告</view>
        </view>
        <view class="notice-list">
          <view class="notice-item" v-for="item in announcementLines" :key="item">{{ item }}</view>
        </view>
      </view>

      <view v-else-if="sectionKey === 'zone_section'" class="card">
        <view v-if="decoration.zone_section.title || decoration.zone_section.subtitle" class="section-head">
          <view v-if="decoration.zone_section.title" class="section-title">{{ decoration.zone_section.title }}</view>
          <view v-if="decoration.zone_section.subtitle" class="section-link">{{ decoration.zone_section.subtitle }}</view>
        </view>
        <view class="zone-grid">
          <view class="zone-nav-card tap-item" v-for="item in zoneItems" :key="item.key || item.title" @click="openZone(item)">
            <image v-if="zoneVisualImage(item)" class="zone-card-art" :src="zoneVisualImage(item)" mode="aspectFill" />
            <view class="zone-card-top">
              <view class="zone-card-title">{{ item.title }}</view>
              <view v-if="item.show_count !== false" class="zone-card-count">{{ zoneCount(item.key) }}</view>
            </view>
            <view class="zone-card-tip">{{ item.tip }}</view>
            <view v-if="item.link_text" class="zone-card-link">{{ item.link_text }}</view>
          </view>
        </view>
      </view>

      <view v-else-if="sectionKey === 'waterfall_section'" class="card">
        <view v-if="decoration.waterfall_section.title || decoration.waterfall_section.subtitle" class="section-head">
          <view v-if="decoration.waterfall_section.title" class="section-title">{{ decoration.waterfall_section.title }}</view>
          <view v-if="decoration.waterfall_section.subtitle" class="section-link">{{ decoration.waterfall_section.subtitle }}</view>
        </view>
        <view class="waterfall-meta">
          <view class="waterfall-chip" v-for="item in waterfallSourceLabels" :key="item">{{ item }}</view>
        </view>
        <view v-if="loading && !waterfallVisibleItems.length">
          <view class="skeleton-block"></view>
          <view class="skeleton-block short"></view>
        </view>
        <view v-else-if="waterfallVisibleItems.length" class="waterfall-columns">
          <view class="waterfall-column" v-for="(column, columnIndex) in waterfallColumns" :key="`column-${columnIndex}`">
            <view class="waterfall-card tap-item" v-for="item in column" :key="item.uniqueKey" @click="openWaterfallItem(item)">
              <view class="waterfall-cover" :class="{ tall: item.coverTall, 'with-image': !!item.image }">
                <image v-if="item.image" class="waterfall-image" :src="item.image" mode="aspectFill" />
                <view v-else class="waterfall-cover-fallback">
                  <view class="waterfall-cover-badge">{{ item.badge }}</view>
                  <view class="waterfall-cover-title">{{ item.title }}</view>
                </view>
              </view>
              <view class="waterfall-body">
                <view class="waterfall-title">{{ item.title }}</view>
                <view class="waterfall-desc">{{ item.desc }}</view>
                <view class="waterfall-price-row">
                  <view class="waterfall-price">{{ item.priceText || '查看详情' }}</view>
                  <view v-if="item.marketPriceText" class="waterfall-market-price">{{ item.marketPriceText }}</view>
                </view>
              </view>
            </view>
          </view>
        </view>
        <view v-else class="empty-text">当前来源暂无可展示内容</view>
        <button v-if="canLoadMoreWaterfall" class="secondary-btn load-more-btn" @click="loadMoreWaterfall">继续加载</button>
      </view>

      <view v-else-if="sectionKey === 'package_section'" class="card">
        <view v-if="decoration.package_section.title || packages.length" class="section-head">
          <view v-if="decoration.package_section.title" class="section-title">{{ decoration.package_section.title }}</view>
          <view class="section-link" @click="goPackages">查看全部</view>
        </view>
        <view class="section-desc">{{ decoration.package_section.desc }}</view>
        <view v-if="loading && !packages.length">
          <view class="skeleton-block"></view>
          <view class="skeleton-block short"></view>
        </view>
        <view v-else-if="packages.length" class="package-stack">
          <view class="package-card tap-item" v-for="item in packages.slice(0, packageLimit)" :key="item.id" @click="goPackage(item.id)">
            <view class="package-top">
              <view>
                <view class="item-title">{{ item.package_name }}</view>
                <view class="item-meta">AI 券抵扣上限 {{ item.ai_coupon_max_deduct_rate }}%</view>
              </view>
              <view class="package-price">¥{{ displayAmount(item.package_price) }}</view>
            </view>
            <view class="benefit-row">
              <view class="benefit-pill">购券 {{ item.voucher_reward_rate }}%</view>
              <view class="benefit-pill">推荐赠券 {{ item.referral_voucher_rate }}%</view>
            </view>
          </view>
        </view>
        <view v-else class="empty-text">暂无套餐上架</view>
      </view>

      <view v-else-if="sectionKey === 'promo_section'" class="card">
        <view v-if="decoration.promo_section.title || promoSectionSubtitle" class="section-head">
          <view v-if="decoration.promo_section.title" class="section-title">{{ decoration.promo_section.title }}</view>
          <view v-if="promoSectionSubtitle" class="section-link">{{ promoSectionSubtitle }}</view>
        </view>
        <view class="promo-grid">
          <view class="promo-card tap-item" v-for="(item, index) in promoCards" :key="`${item.title}-${index}`" @click="openConfiguredLink(item)">
            <view class="promo-badge">{{ item.badge || '活动推荐' }}</view>
            <view class="promo-title">{{ item.title }}</view>
            <view class="promo-desc">{{ item.desc }}</view>
          </view>
        </view>
      </view>

      <view v-else-if="sectionKey === 'quick_section'" class="card">
        <view v-if="decoration.quick_section.title || decoration.quick_section.subtitle" class="section-head">
          <view v-if="decoration.quick_section.title" class="section-title">{{ decoration.quick_section.title }}</view>
          <view v-if="decoration.quick_section.subtitle" class="section-link" @click="goProfile">{{ decoration.quick_section.subtitle }}</view>
        </view>
        <view class="quick-grid">
          <view class="quick-entry tap-item" v-for="(item, index) in quickItems" :key="`${item.title}-${index}`" @click="openConfiguredLink(item)">
            <view class="nav-icon-shell quick-icon-shell">
              <image v-if="item.icon_url" class="nav-icon-image" :src="item.icon_url" mode="aspectFill" />
              <view v-else class="nav-icon-text">{{ navItemFallbackText(item, '入口') }}</view>
            </view>
            <view class="quick-entry-title">{{ item.title }}</view>
            <view class="quick-entry-desc">{{ item.desc }}</view>
          </view>
        </view>
      </view>

      <view v-else-if="customBlockFromLayout(sectionKey)?.type === 'banner'" class="card custom-banner-card tap-item" @click="openConfiguredLink(customBlockFromLayout(sectionKey))">
        <view class="promo-badge">{{ customBlockFromLayout(sectionKey)?.badge || '活动横幅' }}</view>
        <view v-if="customBlockFromLayout(sectionKey)?.title" class="promo-title">{{ customBlockFromLayout(sectionKey)?.title }}</view>
        <view class="promo-desc">{{ customBlockFromLayout(sectionKey)?.desc || '请补充活动说明' }}</view>
        <view class="banner-action">{{ customBlockFromLayout(sectionKey)?.button_text || '立即查看' }}</view>
      </view>

      <view v-else-if="customBlockFromLayout(sectionKey)?.type === 'grid'" class="card">
        <view v-if="customBlockFromLayout(sectionKey)?.title || customBlockFromLayout(sectionKey)?.subtitle" class="section-head">
          <view v-if="customBlockFromLayout(sectionKey)?.title" class="section-title">{{ customBlockFromLayout(sectionKey)?.title }}</view>
          <view v-if="customBlockFromLayout(sectionKey)?.subtitle" class="section-link">{{ customBlockFromLayout(sectionKey)?.subtitle }}</view>
        </view>
        <view class="quick-grid">
          <view class="quick-entry tap-item" v-for="(item, index) in customGridItems(customBlockFromLayout(sectionKey))" :key="`${sectionKey}-${index}`" @click="openConfiguredLink(item)">
            <view class="nav-icon-shell quick-icon-shell">
              <image v-if="item.icon_url" class="nav-icon-image" :src="item.icon_url" mode="aspectFill" />
              <view v-else class="nav-icon-text">{{ navItemFallbackText(item, '宫格') }}</view>
            </view>
            <view class="quick-entry-title">{{ item.title }}</view>
            <view class="quick-entry-desc">{{ item.desc }}</view>
          </view>
        </view>
      </view>

      <view v-else-if="customBlockFromLayout(sectionKey)?.type === 'coupon_strip'" class="card coupon-strip-card tap-item" @click="openConfiguredLink(customBlockFromLayout(sectionKey))">
        <view v-if="customBlockFromLayout(sectionKey)?.title || customBlockFromLayout(sectionKey)?.badge" class="section-head">
          <view v-if="customBlockFromLayout(sectionKey)?.title" class="section-title">{{ customBlockFromLayout(sectionKey)?.title }}</view>
          <view v-if="customBlockFromLayout(sectionKey)?.badge" class="section-link">{{ customBlockFromLayout(sectionKey)?.badge }}</view>
        </view>
        <view class="section-desc">{{ customBlockFromLayout(sectionKey)?.desc }}</view>
      </view>

      <view v-else-if="customBlockFromLayout(sectionKey)?.type === 'zone_feed'" class="card">
        <view v-if="customBlockFromLayout(sectionKey)?.title || customBlockFromLayout(sectionKey)?.subtitle || customBlockFromLayout(sectionKey)?.source_key" class="section-head">
          <view v-if="customBlockFromLayout(sectionKey)?.title" class="section-title">{{ customBlockFromLayout(sectionKey)?.title }}</view>
          <view class="section-link" @click="openZoneFeed(customBlockFromLayout(sectionKey))">
            {{ customBlockFromLayout(sectionKey)?.subtitle || zoneSourceLabel(customBlockFromLayout(sectionKey)?.source_key) }}
          </view>
        </view>
        <view class="feed-list">
          <view class="feed-card tap-item" v-for="(item, index) in customZoneFeedItems(customBlockFromLayout(sectionKey))" :key="`${sectionKey}-${item.id || index}`" @click="openZoneFeed(customBlockFromLayout(sectionKey))">
            <view class="feed-title">{{ displayName(item) }}</view>
            <view class="feed-meta">{{ zoneSourceLabel(customBlockFromLayout(sectionKey)?.source_key) }}</view>
            <view class="feed-desc">{{ item.product_desc || item.service_desc || item.package_desc || '运营配置的专区商品流' }}</view>
          </view>
        </view>
      </view>

      <view v-else-if="customBlockFromLayout(sectionKey)?.type === 'image_swiper'" class="image-swiper-module">
        <swiper class="module-swiper" circular :autoplay="customBlockFromLayout(sectionKey)?.autoplay !== false" :indicator-dots="customSwiperItems(customBlockFromLayout(sectionKey)).length > 1">
          <swiper-item v-for="(item, index) in customSwiperItems(customBlockFromLayout(sectionKey))" :key="`${sectionKey}-swiper-${index}`">
            <view class="module-swiper-card tap-item" :class="{ 'with-image': !!item.image_url }" @click="openConfiguredLink(item)">
              <image v-if="item.image_url" class="slide-image" :src="item.image_url" mode="aspectFill" />
              <view class="slide-grid"></view>
              <view class="slide-glow"></view>
              <view class="slide-mask"></view>
              <view class="slide-content">
                <view class="promo-badge">{{ item.badge || '轮播图' }}</view>
                <view class="promo-title">{{ item.title }}</view>
                <view class="promo-desc">{{ item.desc }}</view>
              </view>
            </view>
          </swiper-item>
        </swiper>
      </view>

      <view v-else-if="customBlockFromLayout(sectionKey)?.type === 'mixed_goods'" class="card">
        <view v-if="customBlockFromLayout(sectionKey)?.title || customBlockFromLayout(sectionKey)?.subtitle" class="section-head">
          <view v-if="customBlockFromLayout(sectionKey)?.title" class="section-title">{{ customBlockFromLayout(sectionKey)?.title }}</view>
          <view v-if="customBlockFromLayout(sectionKey)?.subtitle" class="section-link">{{ customBlockFromLayout(sectionKey)?.subtitle }}</view>
        </view>
        <view class="feed-list">
          <view class="feed-card tap-item" v-for="(item, index) in customMixedGoodsItems(customBlockFromLayout(sectionKey))" :key="`${sectionKey}-mixed-${index}`" @click="openConfiguredLink(item)">
            <view class="promo-badge">{{ item.tag || '商品' }}</view>
            <view class="feed-title">{{ item.title }}</view>
            <view class="feed-meta">{{ item.price_text || '运营价' }}</view>
            <view class="feed-desc">{{ item.desc }}</view>
          </view>
        </view>
      </view>
    </block>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onPullDownRefresh, onReachBottom, onShow } from '@dcloudio/uni-app'

import { homeApi, localLifeApi, packageApi } from '../../api/modules'
import { ensureLogin } from '../../utils/guard'
import { normalizeLoadError } from '../../utils/ui'

const SECTION_ORDER = ['announcement', 'zone_section', 'waterfall_section', 'package_section', 'promo_section', 'quick_section']
const ZONE_VISUAL_MAP = Object.freeze({
  repurchase: '/static/zone-posters/zone-repurchase.svg',
  selfOperated: '/static/zone-posters/zone-self-operated.svg',
  hotSale: '/static/zone-posters/zone-hot-sale.svg',
  localLife: '/static/zone-posters/zone-local-life.svg'
})
const ZONE_SOURCE_OPTIONS = [
  { value: 'repurchase', label: '复购来源' },
  { value: 'selfOperated', label: '商城来源' },
  { value: 'hotSale', label: '热卖来源' },
  { value: 'localLife', label: '本地生活' }
]
const TAB_PATHS = new Set([
  '/pages/home/index',
  '/pages/packages/list',
  '/pages/local-life/index',
  '/pages/profile/index'
])

function formatSeriesIndex(index = 0) {
  return String(index + 1).padStart(2, '0')
}

function customLayoutKey(id) {
  return `custom:${id}`
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

function createDefaultDecoration() {
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
    quick_section: {
      enabled: true,
      title: '我的常用',
      subtitle: '个人中心',
      items: [
        { enabled: true, title: '套餐中心', desc: '查看入场资格与权益档位', icon_url: '', path: '/pages/packages/list', open_type: 'switchTab' },
        { enabled: true, title: '我的团队', desc: '管理归属与成员结构', icon_url: '', path: '/subpackages/team/index', open_type: 'navigate' },
        { enabled: true, title: '邀请好友', desc: '分享邀请码完成绑定', icon_url: '', path: '/subpackages/invite/index', open_type: 'navigate' },
        { enabled: true, title: '佣金中心', desc: '跟进冻结与可提现状态', icon_url: '', path: '/subpackages/commission/index', open_type: 'navigate' },
        { enabled: true, title: '资产中心', desc: '查看余额、积分与券资产', icon_url: '', path: '/subpackages/assets/index', open_type: 'navigate' },
        { enabled: true, title: '个人中心', desc: '维护资料、签到和账号设置', icon_url: '', path: '/pages/profile/index', open_type: 'switchTab' }
      ]
    }
  }
}

function createFallbackItem(type) {
  if (type === 'promo') {
    return { enabled: true, badge: '', title: '', desc: '', path: '', open_type: 'navigate' }
  }
  if (type === 'zone') {
    return { enabled: true, key: '', title: '', tip: '', icon_url: '', link_text: '进入专区', show_count: true, path: '', open_type: 'navigate' }
  }
  return { enabled: true, title: '', desc: '', icon_url: '', path: '', open_type: 'navigate' }
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
      id: block?.id || `grid_${index}`,
      type,
      enabled: normalizeEnabled(block?.enabled, true),
      title: block?.title || '',
      subtitle: block?.subtitle || '',
      items: Array.isArray(block?.items) && block.items.length
        ? block.items.map((item) => ({
            ...createFallbackItem('grid'),
            ...item,
            enabled: normalizeEnabled(item?.enabled, true)
          }))
        : []
    }
  }
  if (type === 'coupon_strip') {
    return {
      id: block?.id || `coupon_${index}`,
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
      id: block?.id || `feed_${index}`,
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
      id: block?.id || `swiper_${index}`,
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
            enabled: normalizeEnabled(item?.enabled, true),
            badge: item?.badge || '',
            title: item?.title || '',
            desc: item?.desc || '',
            image_url: item?.image_url || '',
            path: item?.path || '',
            open_type: item?.open_type || 'navigate'
          }))
        : (fallbackBlock.items || [])
    }
  }
  if (type === 'mixed_goods') {
    return {
      id: block?.id || `mixed_${index}`,
      type,
      enabled: normalizeEnabled(block?.enabled, true),
      title: block?.title || '',
      subtitle: block?.subtitle || '',
      items: Array.isArray(block?.items) && block.items.length
        ? block.items.map((item) => ({
            enabled: normalizeEnabled(item?.enabled, true),
            tag: item?.tag || '',
            title: item?.title || '',
            desc: item?.desc || '',
            price_text: item?.price_text || '',
            path: item?.path || '',
            open_type: item?.open_type || 'navigate'
          }))
        : []
    }
  }
  return {
    id: block?.id || `banner_${index}`,
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

function normalizeDecoration(payload) {
  const defaults = createDefaultDecoration()
  const next = payload || {}
  const customBlocksSource = Array.isArray(next.custom_blocks) ? next.custom_blocks : defaults.custom_blocks
  const customBlocks = customBlocksSource.map((block, index) => normalizeCustomBlock(block, index))

  return {
    layout: normalizeLayout(next.layout, defaults.layout, customBlocks),
    custom_blocks: customBlocks,
    announcement: {
      enabled: normalizeEnabled(next.announcement?.enabled, defaults.announcement.enabled),
      title: fieldOrDefault(next.announcement, 'title', defaults.announcement.title),
      lines: Array.isArray(next.announcement?.lines) && next.announcement.lines.length ? next.announcement.lines.filter(Boolean) : defaults.announcement.lines
    },
    zone_section: {
      enabled: normalizeEnabled(next.zone_section?.enabled, defaults.zone_section.enabled),
      title: fieldOrDefault(next.zone_section, 'title', defaults.zone_section.title),
      subtitle: fieldOrDefault(next.zone_section, 'subtitle', defaults.zone_section.subtitle),
      items: Array.isArray(next.zone_section?.items) && next.zone_section.items.length
        ? next.zone_section.items.map((item) => ({
            ...createFallbackItem('zone'),
            ...item,
            enabled: normalizeEnabled(item?.enabled, true),
            link_text: fieldOrDefault(item, 'link_text', '进入专区'),
            show_count: normalizeEnabled(item?.show_count, true)
          }))
        : defaults.zone_section.items
    },
    waterfall_section: {
      enabled: normalizeEnabled(next.waterfall_section?.enabled, defaults.waterfall_section.enabled),
      title: fieldOrDefault(next.waterfall_section, 'title', defaults.waterfall_section.title),
      subtitle: fieldOrDefault(next.waterfall_section, 'subtitle', defaults.waterfall_section.subtitle),
      page_size: Math.max(4, Math.min(20, Number(next.waterfall_section?.page_size || defaults.waterfall_section.page_size))),
      source_keys: Array.isArray(next.waterfall_section?.source_keys) && next.waterfall_section.source_keys.length
        ? next.waterfall_section.source_keys.filter((item) => ZONE_SOURCE_OPTIONS.some((option) => option.value === item))
        : defaults.waterfall_section.source_keys
    },
    package_section: {
      enabled: normalizeEnabled(next.package_section?.enabled, defaults.package_section.enabled),
      title: fieldOrDefault(next.package_section, 'title', defaults.package_section.title),
      desc: next.package_section?.desc || defaults.package_section.desc,
      limit: Math.max(1, Math.min(6, Number(next.package_section?.limit || defaults.package_section.limit)))
    },
    promo_section: {
      enabled: normalizeEnabled(next.promo_section?.enabled, defaults.promo_section.enabled),
      title: fieldOrDefault(next.promo_section, 'title', defaults.promo_section.title),
      subtitle: fieldOrDefault(next.promo_section, 'subtitle', defaults.promo_section.subtitle),
      items: Array.isArray(next.promo_section?.items) && next.promo_section.items.length
        ? next.promo_section.items.map((item) => ({
            ...createFallbackItem('promo'),
            ...item,
            enabled: normalizeEnabled(item?.enabled, true)
          }))
        : defaults.promo_section.items
    },
    quick_section: {
      enabled: normalizeEnabled(next.quick_section?.enabled, defaults.quick_section.enabled),
      title: fieldOrDefault(next.quick_section, 'title', defaults.quick_section.title),
      subtitle: fieldOrDefault(next.quick_section, 'subtitle', defaults.quick_section.subtitle),
      items: Array.isArray(next.quick_section?.items) && next.quick_section.items.length
        ? next.quick_section.items.map((item) => ({
            ...createFallbackItem('quick'),
            ...item,
            enabled: normalizeEnabled(item?.enabled, true)
          }))
        : defaults.quick_section.items
    }
  }
}

const packages = ref([])
const loading = ref(false)
const loadError = ref('')
const decorationData = ref(createDefaultDecoration())
const lists = ref({
  repurchase: [],
  selfOperated: [],
  hotSale: [],
  localLife: []
})
const waterfallVisibleCount = ref(8)

const decoration = computed(() => decorationData.value || createDefaultDecoration())
const customBlockMap = computed(() => {
  const map = {}
  ;(decoration.value.custom_blocks || []).forEach((block) => {
    map[customLayoutKey(block.id)] = block
  })
  return map
})
const announcementLines = computed(() => (decoration.value.announcement?.lines || []).filter(Boolean))
const announcementEnabled = computed(() => decoration.value.announcement?.enabled !== false && announcementLines.value.length > 0)
const packageLimit = computed(() => Math.max(1, Number(decoration.value.package_section?.limit || 2)))
const promoCards = computed(() => (decoration.value.promo_section?.items || []).filter((item) => item?.enabled !== false && (item?.title || item?.desc || item?.badge)))
const promoSectionSubtitle = computed(() => decoration.value.promo_section?.subtitle || '')
const zoneItems = computed(() => (decoration.value.zone_section?.items || []).filter((item) => item?.enabled !== false && (item?.title || item?.key)))
const quickItems = computed(() => (decoration.value.quick_section?.items || []).filter((item) => item?.enabled !== false && (item?.title || item?.desc)))
const zoneLabelMap = computed(() => {
  const map = {}
  ;(decoration.value.zone_section?.items || []).forEach((item) => {
    if (item?.key && item?.title) {
      map[item.key] = item.title
    }
  })
  return map
})

function zoneSourceLabel(key) {
  return zoneLabelMap.value[key] || ZONE_SOURCE_OPTIONS.find((item) => item.value === key)?.label || '专区'
}

const waterfallSourceKeys = computed(() => {
  const rows = decoration.value.waterfall_section?.source_keys || []
  return rows.length ? rows : createDefaultDecoration().waterfall_section.source_keys
})
const waterfallSourceLabels = computed(() => waterfallSourceKeys.value.map((item) => zoneSourceLabel(item)))

function customBlockFromLayout(sectionKey) {
  return customBlockMap.value[sectionKey] || null
}

function customGridItems(block) {
  return (block?.items || []).filter((item) => item?.enabled !== false && (item?.title || item?.desc || item?.icon_url))
}

function navItemFallbackText(item, fallback = '入口') {
  const source = String(item?.title || item?.key || fallback).trim()
  return source.slice(0, 2) || fallback
}

function customSwiperItems(block) {
  return (block?.items || []).filter((item) => item?.enabled !== false && (item?.badge || item?.title || item?.desc || item?.image_url))
}

function customMixedGoodsItems(block) {
  return (block?.items || []).filter((item) => item?.enabled !== false && (item?.tag || item?.title || item?.desc || item?.price_text))
}

function customZoneFeedItems(block) {
  const sourceKey = block?.source_key || 'repurchase'
  const rows = lists.value[sourceKey] || []
  const limit = Math.max(1, Number(block?.limit || 4))
  return rows.slice(0, limit)
}

const primarySwiperBlock = computed(() => {
  return (decoration.value.custom_blocks || []).find((block) => block.type === 'image_swiper' && block.enabled !== false && customSwiperItems(block).length > 0) || null
})
const primarySwiperLayoutKey = computed(() => (primarySwiperBlock.value ? customLayoutKey(primarySwiperBlock.value.id) : ''))
const primarySwiperMeta = computed(() => ({
  sectionKicker: primarySwiperBlock.value?.section_kicker || '',
  countSuffix: primarySwiperBlock.value?.count_suffix || '',
  kicker: primarySwiperBlock.value?.kicker || '',
  desc: primarySwiperBlock.value?.desc || '',
  tags: Array.isArray(primarySwiperBlock.value?.tags) ? primarySwiperBlock.value.tags.filter(Boolean) : [],
  slideTags: Array.isArray(primarySwiperBlock.value?.slide_tags) ? primarySwiperBlock.value.slide_tags.filter(Boolean) : []
}))
const heroSwiperItems = computed(() => {
  if (primarySwiperBlock.value) {
    return customSwiperItems(primarySwiperBlock.value)
  }
  return promoCards.value.slice(0, 3).map((item) => ({
    badge: item.badge || '精选会场',
    title: item.title,
    desc: item.desc,
    path: item.path,
    open_type: item.open_type
  }))
})

function zoneList(key) {
  return lists.value[key] || []
}

function zoneCount(key) {
  return zoneList(key).length
}

function zoneVisualImage(item) {
  if (item?.icon_url) {
    return item.icon_url
  }
  return ZONE_VISUAL_MAP[item?.key] || ''
}

function displayName(item) {
  return item?.product_name || item?.service_name || item?.package_name || `内容 ${item?.id || ''}`
}

function displayAmount(value) {
  const amount = Number(value)
  if (!Number.isFinite(amount)) {
    return '--'
  }
  return amount.toFixed(2).replace(/\.00$/, '')
}

function normalizePath(path) {
  if (path === '/subpackages/life/index') {
    return '/pages/local-life/index'
  }
  return path
}

function openPath(path) {
  const nextPath = normalizePath(path)
  if (!nextPath) {
    return
  }
  if (TAB_PATHS.has(nextPath)) {
    uni.switchTab({ url: nextPath })
    return
  }
  uni.navigateTo({ url: nextPath })
}

function openConfiguredLink(item) {
  openPath(item?.path)
}

function goPackages() {
  openPath('/pages/packages/list')
}

function goProfile() {
  openPath('/pages/profile/index')
}

function goPackage(id) {
  openPath(`/subpackages/package/detail?id=${id}`)
}

function openZone(item) {
  if (item?.path) {
    openConfiguredLink(item)
    return
  }
  if (item?.key === 'localLife') {
    openPath('/pages/local-life/index')
    return
  }
  goPackages()
}

function openZoneFeed(block) {
  if (block?.path) {
    openConfiguredLink(block)
    return
  }
  if (block?.source_key === 'localLife') {
    openPath('/pages/local-life/index')
    return
  }
  goPackages()
}

function normalizeWaterfallItem(item, sourceKey, index) {
  const title = displayName(item)
  const isLocalLife = sourceKey === 'localLife'
  const path = isLocalLife && item?.id ? `/subpackages/life/service-detail?id=${item.id}` : (isLocalLife ? '/pages/local-life/index' : '/pages/packages/list')
  return {
    uniqueKey: `${sourceKey}-${item?.id || index}`,
    title,
    desc: isLocalLife
      ? `${item.service_type || '到店服务'} · ${item.verification_type || '门店核销'}`
      : item.product_desc || item.package_desc || `${zoneSourceLabel(sourceKey)}推荐`,
    priceText: item?.sale_price || item?.package_price ? `¥${displayAmount(item.sale_price || item.package_price)}` : '',
    marketPriceText: item?.market_price ? `¥${displayAmount(item.market_price)}` : '',
    badge: zoneSourceLabel(sourceKey),
    path,
    image: item?.main_image || '',
    coverTall: (index + sourceKey.length) % 3 !== 0
  }
}

function buildWaterfallItems() {
  const buckets = waterfallSourceKeys.value
    .map((key) => ({ key, rows: [...(lists.value[key] || [])] }))
    .filter((bucket) => bucket.rows.length)
  const merged = []
  let pointer = 0
  while (buckets.some((bucket) => bucket.rows.length) && merged.length < 200) {
    const bucket = buckets[pointer % buckets.length]
    if (bucket.rows.length) {
      merged.push(normalizeWaterfallItem(bucket.rows.shift(), bucket.key, merged.length))
    }
    pointer += 1
  }
  return merged
}

const waterfallAllItems = computed(() => buildWaterfallItems())
const waterfallVisibleItems = computed(() => waterfallAllItems.value.slice(0, waterfallVisibleCount.value))
const waterfallColumns = computed(() => {
  const columns = [[], []]
  const heights = [0, 0]
  waterfallVisibleItems.value.forEach((item) => {
    const score = 180 + (item.coverTall ? 44 : 0) + String(item.desc || '').length * 0.6
    const target = heights[0] <= heights[1] ? 0 : 1
    columns[target].push(item)
    heights[target] += score
  })
  return columns
})
const canLoadMoreWaterfall = computed(() => waterfallVisibleCount.value < waterfallAllItems.value.length)

const customSectionEnabledMap = computed(() => {
  const map = {}
  ;(decoration.value.custom_blocks || []).forEach((block) => {
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
      map[customLayoutKey(block.id)] = block.enabled !== false && customZoneFeedItems(block).length > 0
      return
    }
    map[customLayoutKey(block.id)] = block.enabled !== false && (block.title || block.desc || block.badge)
  })
  return map
})

const sectionEnabledMap = computed(() => ({
  announcement: announcementEnabled.value,
  zone_section: decoration.value.zone_section?.enabled !== false && zoneItems.value.length > 0,
  waterfall_section: decoration.value.waterfall_section?.enabled !== false,
  package_section: decoration.value.package_section?.enabled !== false,
  promo_section: decoration.value.promo_section?.enabled !== false && promoCards.value.length > 0,
  quick_section: decoration.value.quick_section?.enabled !== false && quickItems.value.length > 0,
  ...customSectionEnabledMap.value
}))

const orderedSectionKeys = computed(() => {
  const layout = Array.isArray(decoration.value.layout) && decoration.value.layout.length
    ? decoration.value.layout
    : SECTION_ORDER
  return layout.filter((key) => sectionEnabledMap.value[key] && key !== primarySwiperLayoutKey.value)
})

function loadMoreWaterfall() {
  if (!canLoadMoreWaterfall.value) {
    return
  }
  waterfallVisibleCount.value = Math.min(
    waterfallAllItems.value.length,
    waterfallVisibleCount.value + Number(decoration.value.waterfall_section?.page_size || 8)
  )
}

function openWaterfallItem(item) {
  openPath(item?.path)
}

async function loadData({ resetWaterfall = false } = {}) {
  loading.value = true
  loadError.value = ''
  try {
    const results = await Promise.allSettled([
      packageApi.list(),
      homeApi.repurchase(),
      homeApi.selfOperated(),
      homeApi.hotSale(),
      localLifeApi.services(),
      homeApi.decoration()
    ])
    const [packageRows, repurchase, selfOperated, hotSale, localLife, decorationRes] = results
    const normalizedDecoration = normalizeDecoration(decorationRes.status === 'fulfilled' ? decorationRes.value?.payload : createDefaultDecoration())
    packages.value = packageRows.status === 'fulfilled' ? (packageRows.value || []) : []
    decorationData.value = normalizedDecoration
    lists.value = {
      repurchase: repurchase.status === 'fulfilled' ? (repurchase.value || []) : [],
      selfOperated: selfOperated.status === 'fulfilled' ? (selfOperated.value || []) : [],
      hotSale: hotSale.status === 'fulfilled' ? (hotSale.value || []) : [],
      localLife: localLife.status === 'fulfilled' ? (localLife.value || []) : []
    }
    const failedCount = results.filter((item) => item.status === 'rejected').length
    if (failedCount === results.length) {
      throw packageRows.reason || repurchase.reason || selfOperated.reason || hotSale.reason || localLife.reason || decorationRes.reason
    }
    if (resetWaterfall || !waterfallVisibleCount.value) {
      waterfallVisibleCount.value = Number(normalizedDecoration.waterfall_section?.page_size || 8)
    }
  } catch (error) {
    loadError.value = normalizeLoadError(error)
  } finally {
    loading.value = false
  }
}

onShow(() => {
  if (!ensureLogin()) {
    return
  }
  loadData({ resetWaterfall: true })
})

onPullDownRefresh(async () => {
  if (!ensureLogin()) {
    uni.stopPullDownRefresh()
    return
  }
  await loadData({ resetWaterfall: true })
  uni.stopPullDownRefresh()
})

onReachBottom(() => {
  loadMoreWaterfall()
})
</script>

<style scoped>
.home-page {
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(circle at 0% 0%, rgba(233, 176, 120, 0.24), transparent 22%),
    radial-gradient(circle at 100% 8%, rgba(208, 220, 244, 0.82), transparent 24%),
    linear-gradient(180deg, #fbf8f3 0%, #f6f4ef 42%, #f3f1ec 100%);
}

.home-page::before,
.home-page::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.home-page::before {
  background:
    linear-gradient(120deg, rgba(255, 255, 255, 0.62), transparent 18%, transparent 78%, rgba(255, 255, 255, 0.38)),
    linear-gradient(180deg, rgba(255, 255, 255, 0.18), transparent 30%);
}

.home-page::after {
  background:
    radial-gradient(circle at 18% 20%, rgba(255, 255, 255, 0.78), transparent 10%),
    radial-gradient(circle at 78% 12%, rgba(255, 255, 255, 0.68), transparent 12%);
  opacity: 0.72;
}

.card,
.swiper-panel {
  position: relative;
  overflow: hidden;
  margin-bottom: 24rpx;
  border-radius: 30rpx;
  border: 1rpx solid rgba(232, 224, 214, 0.9);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.94) 0%, rgba(252, 250, 246, 0.96) 100%);
  box-shadow:
    0 18rpx 42rpx rgba(136, 124, 107, 0.1),
    inset 0 1rpx 0 rgba(255, 255, 255, 0.75);
}

.card,
.swiper-panel {
  padding: 28rpx;
}

.visual-strip,
.benefit-row,
.waterfall-meta,
.slide-topline,
.slide-footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12rpx;
}

.swiper-panel {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(250, 247, 241, 0.98) 100%);
}

.visual-strip {
  justify-content: space-between;
  margin-bottom: 22rpx;
}

.visual-copy-block {
  max-width: 68%;
}

.cinematic-badge {
  margin-bottom: 12rpx;
  background: linear-gradient(135deg, #efe5d6 0%, #f5efe6 100%);
  color: #8c5a2f;
  border: 1rpx solid rgba(224, 209, 189, 0.9);
}

.visual-copy {
  font-size: 23rpx;
  line-height: 1.7;
  color: #7a726a;
}

.visual-pill-stack {
  display: grid;
  gap: 10rpx;
}

.mini-pill,
.benefit-pill,
.promo-badge,
.waterfall-chip,
.slide-badge,
.slide-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 52rpx;
  padding: 0 18rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
  color: #c86a32;
  background: rgba(210, 108, 50, 0.08);
  border: 1rpx solid rgba(210, 108, 50, 0.12);
}

.visual-head {
  align-items: flex-end;
  padding-top: 8rpx;
  border-top: 1rpx solid rgba(228, 220, 209, 0.9);
}

.section-head.compact {
  margin-bottom: 20rpx;
}

.section-kicker {
  margin-bottom: 10rpx;
  font-size: 20rpx;
  letter-spacing: 3rpx;
  text-transform: uppercase;
  color: #b28d69;
}

.visual-count {
  min-height: 56rpx;
  padding: 0 18rpx;
  border-radius: 999rpx;
  border: 1rpx solid rgba(232, 224, 214, 0.9);
  background: #ffffff;
  color: #27231e;
}

.hero-swiper,
.module-swiper {
  height: 400rpx;
}

.image-swiper-module {
  margin-bottom: 24rpx;
}

.module-swiper {
  height: 300rpx;
}

.swiper-slide,
.module-swiper-card {
  position: relative;
  overflow: hidden;
  height: 100%;
  padding: 34rpx 30rpx 30rpx;
  border-radius: 28rpx;
  box-sizing: border-box;
  background:
    radial-gradient(circle at 84% 16%, rgba(232, 192, 149, 0.45), transparent 24%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.12), transparent 24%, transparent 72%, rgba(255, 255, 255, 0.06)),
    linear-gradient(150deg, #25201b 0%, #3a2d24 50%, #7a5738 100%);
  color: #ffffff;
  border: 1rpx solid rgba(120, 91, 63, 0.18);
  box-shadow:
    0 18rpx 44rpx rgba(111, 84, 58, 0.2),
    inset 0 1rpx 0 rgba(255, 255, 255, 0.1);
}

.slide-image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  transform: scale(1.04);
  filter: saturate(0.94) contrast(1.02) brightness(0.94);
}

.slide-grid,
.slide-glow {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.slide-grid {
  background:
    linear-gradient(90deg, rgba(255, 255, 255, 0.06) 1rpx, transparent 1rpx),
    linear-gradient(180deg, rgba(255, 255, 255, 0.06) 1rpx, transparent 1rpx);
  background-size: 34rpx 34rpx;
  opacity: 0.18;
}

.slide-glow {
  background:
    radial-gradient(circle at 88% 18%, rgba(255, 197, 140, 0.26), transparent 22%),
    radial-gradient(circle at 20% 120%, rgba(255, 255, 255, 0.08), transparent 30%);
}

.slide-mask {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(180deg, rgba(20, 17, 15, 0.12) 0%, rgba(20, 17, 15, 0.28) 40%, rgba(20, 17, 15, 0.68) 100%),
    linear-gradient(135deg, rgba(255, 206, 159, 0.18), transparent 44%);
}

.slide-content {
  position: relative;
  z-index: 1;
}

.slide-topline {
  justify-content: space-between;
}

.slide-series {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 50rpx;
  padding: 0 16rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.82);
  border: 1rpx solid rgba(255, 255, 255, 0.12);
  font-size: 21rpx;
  letter-spacing: 2rpx;
}

.slide-title {
  margin: 26rpx 0 14rpx;
  font-size: 42rpx;
  font-weight: 700;
  line-height: 1.24;
  max-width: 82%;
}

.slide-desc {
  font-size: 24rpx;
  line-height: 1.72;
  color: rgba(255, 255, 255, 0.74);
  max-width: 90%;
}

.slide-footer {
  margin-top: 26rpx;
}

.notice-card {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(250, 247, 241, 0.98) 100%);
}

.notice-list,
.package-stack,
.promo-grid,
.feed-list {
  display: grid;
  gap: 18rpx;
}

.notice-item {
  position: relative;
  padding: 24rpx 26rpx;
  border-radius: 22rpx;
  background: #fbfaf7;
  color: #6e665e;
  line-height: 1.75;
  border: 1rpx solid rgba(238, 230, 220, 0.9);
}

.zone-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18rpx;
}

.zone-nav-card,
.package-card,
.promo-card,
.custom-banner-card,
.coupon-strip-card,
.feed-card,
.quick-entry,
.waterfall-card {
  position: relative;
  overflow: hidden;
  background: linear-gradient(180deg, #ffffff 0%, #faf8f4 100%);
  border-radius: 24rpx;
  border: 1rpx solid rgba(238, 229, 219, 0.9);
  box-shadow:
    0 14rpx 32rpx rgba(145, 131, 112, 0.08),
    inset 0 1rpx 0 rgba(255, 255, 255, 0.82);
}

.zone-nav-card,
.package-card,
.promo-card,
.custom-banner-card,
.coupon-strip-card,
.feed-card,
.quick-entry {
  padding: 24rpx;
}

.zone-nav-card {
  min-height: 308rpx;
  box-sizing: border-box;
}

.zone-card-art {
  width: 100%;
  height: 148rpx;
  margin-bottom: 18rpx;
  border-radius: 18rpx;
  display: block;
  box-shadow:
    0 14rpx 30rpx rgba(145, 131, 112, 0.12),
    inset 0 1rpx 0 rgba(255, 255, 255, 0.36);
}

.nav-icon-shell {
  width: 82rpx;
  height: 82rpx;
  border-radius: 26rpx;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20rpx;
  background: linear-gradient(180deg, #f5efe6 0%, #fffdf8 100%);
  border: 1rpx solid rgba(232, 223, 214, 0.9);
  color: #44372f;
  font-size: 24rpx;
  font-weight: 700;
}

.zone-icon-shell {
  box-shadow: 0 10rpx 22rpx rgba(146, 126, 105, 0.1);
}

.quick-icon-shell {
  width: 72rpx;
  height: 72rpx;
  border-radius: 24rpx;
  margin-bottom: 14rpx;
}

.nav-icon-image {
  width: 100%;
  height: 100%;
}

.nav-icon-text {
  padding: 0 8rpx;
  text-align: center;
}

.nav-icon-empty {
  width: 28rpx;
  height: 28rpx;
  border-radius: 10rpx;
  background: rgba(201, 106, 50, 0.12);
}

.zone-card-top,
.package-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16rpx;
  margin-bottom: 14rpx;
}

.zone-card-title,
.promo-title,
.feed-title,
.waterfall-title {
  font-size: 30rpx;
  font-weight: 700;
  color: #191613;
  line-height: 1.35;
}

.zone-card-count {
  min-width: 74rpx;
  height: 48rpx;
  padding: 0 14rpx;
  border-radius: 999rpx;
  background: #f6ede4;
  color: #c96a32;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 22rpx;
  border: 1rpx solid rgba(214, 176, 143, 0.36);
}

.zone-card-tip,
.promo-desc,
.feed-desc,
.waterfall-desc,
.quick-entry-desc {
  font-size: 24rpx;
  line-height: 1.75;
  color: #7a726a;
}

.zone-card-link {
  margin-top: 14rpx;
  font-size: 22rpx;
  color: #c96a32;
}

.waterfall-meta {
  margin-bottom: 18rpx;
}

.waterfall-columns {
  display: flex;
  gap: 18rpx;
}

.waterfall-column {
  flex: 1;
  display: grid;
  gap: 18rpx;
}

.waterfall-card {
  overflow: hidden;
}

.waterfall-cover {
  height: 220rpx;
  background:
    radial-gradient(circle at top right, rgba(245, 205, 169, 0.36), transparent 28%),
    linear-gradient(150deg, #2a241f 0%, #513d2f 56%, #8a6448 100%);
}

.waterfall-cover.tall {
  height: 300rpx;
}

.waterfall-image {
  width: 100%;
  height: 100%;
  transform: scale(1.04);
  filter: saturate(0.94) contrast(1.02) brightness(0.94);
}

.waterfall-cover-fallback {
  height: 100%;
  padding: 22rpx;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  color: #ffffff;
}

.waterfall-cover-badge {
  display: inline-flex;
  align-self: flex-start;
  padding: 8rpx 16rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.16);
  font-size: 22rpx;
  border: 1rpx solid rgba(255, 255, 255, 0.08);
}

.waterfall-cover-title {
  font-size: 32rpx;
  font-weight: 700;
  line-height: 1.35;
}

.waterfall-body {
  padding: 20rpx 22rpx 24rpx;
}

.waterfall-title {
  margin-bottom: 8rpx;
}

.waterfall-price-row {
  display: flex;
  align-items: baseline;
  gap: 10rpx;
  margin-top: 14rpx;
}

.waterfall-price,
.package-price {
  font-size: 38rpx;
  font-weight: 700;
  color: #c96a32;
  line-height: 1;
}

.waterfall-market-price {
  font-size: 22rpx;
  color: #aea59b;
  text-decoration: line-through;
}

.load-more-btn {
  margin-top: 24rpx;
}

.item-title,
.quick-entry-title {
  font-size: 28rpx;
  font-weight: 700;
  color: #191613;
}

.item-meta,
.feed-meta {
  margin-top: 10rpx;
  font-size: 22rpx;
  color: #c96a32;
}

.banner-action {
  display: inline-flex;
  margin-top: 18rpx;
  padding: 10rpx 18rpx;
  border-radius: 999rpx;
  background: #f4ece4;
  color: #7d5633;
  font-size: 22rpx;
  border: 1rpx solid rgba(230, 215, 198, 0.9);
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18rpx;
}

.quick-entry {
  min-height: 172rpx;
  box-sizing: border-box;
}

.section-head {
  margin-bottom: 18rpx;
}

.section-title,
.title {
  color: #181512;
}

.section-link {
  color: #b86f39;
}

.section-desc,
.desc,
.empty-text,
.status-desc {
  color: #7a726a;
}

.status-card {
  background: linear-gradient(180deg, #ffffff 0%, #faf7f2 100%);
  border: 1rpx solid rgba(235, 226, 216, 0.92);
}

.status-title {
  color: #181512;
}

.secondary-btn {
  background: linear-gradient(180deg, #ffffff 0%, #f7f2eb 100%);
  color: #3b3129;
  border: 1rpx solid rgba(232, 222, 212, 0.92);
  box-shadow: 0 8rpx 20rpx rgba(145, 131, 112, 0.08);
}

.retry-btn,
.load-more-btn {
  position: relative;
  z-index: 1;
}
</style>
