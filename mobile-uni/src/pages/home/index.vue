<template>
  <view class="page home-page">
    <view class="hero-panel">
      <view class="hero-kicker-row">
        <view class="badge">{{ heroConfig.badge }}</view>
        <view class="hero-refresh">下拉可刷新</view>
      </view>
      <view class="title">{{ heroConfig.title }}</view>
      <view class="desc">{{ heroConfig.desc }}</view>
      <view class="hero-tags">
        <view class="hero-tag" v-for="item in heroConfig.tags" :key="item">{{ item }}</view>
      </view>
    </view>

    <view v-if="heroSwiperItems.length" class="swiper-panel">
      <view class="section-head compact">
        <view class="section-title">{{ primarySwiperBlock?.title || '首页轮播' }}</view>
        <view class="section-link">{{ heroSwiperItems.length }} 张</view>
      </view>
      <swiper
        class="hero-swiper"
        circular
        :autoplay="primarySwiperBlock ? primarySwiperBlock.autoplay !== false : true"
        :indicator-dots="heroSwiperItems.length > 1"
        indicator-active-color="#ffffff"
      >
        <swiper-item v-for="(item, index) in heroSwiperItems" :key="`${item.title}-${index}`">
          <view class="swiper-slide tap-item" @click="openConfiguredLink(item)">
            <view class="slide-badge">{{ item.badge || '精选会场' }}</view>
            <view class="slide-title">{{ item.title || '首页活动' }}</view>
            <view class="slide-desc">{{ item.desc || '请在后台补充轮播文案' }}</view>
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
        <view class="section-head compact">
          <view class="section-title">{{ decoration.announcement.title }}</view>
          <view class="section-link">首页公告</view>
        </view>
        <view class="notice-list">
          <view class="notice-item" v-for="item in announcementLines" :key="item">{{ item }}</view>
        </view>
      </view>

      <view v-else-if="sectionKey === 'zone_section'" class="card">
        <view class="section-head">
          <view class="section-title">{{ decoration.zone_section.title }}</view>
          <view class="section-link">{{ decoration.zone_section.subtitle }}</view>
        </view>
        <view class="zone-grid">
          <view class="zone-nav-card tap-item" v-for="item in zoneItems" :key="item.key || item.title" @click="openZone(item)">
            <view class="zone-card-top">
              <view class="zone-card-title">{{ item.title }}</view>
              <view class="zone-card-count">{{ zoneCount(item.key) }}</view>
            </view>
            <view class="zone-card-tip">{{ item.tip }}</view>
            <view class="zone-card-link">进入专区</view>
          </view>
        </view>
      </view>

      <view v-else-if="sectionKey === 'waterfall_section'" class="card">
        <view class="section-head">
          <view class="section-title">{{ decoration.waterfall_section.title }}</view>
          <view class="section-link">{{ decoration.waterfall_section.subtitle }}</view>
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
              <view class="waterfall-cover" :class="{ tall: item.coverTall }">
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
        <view class="section-head">
          <view class="section-title">{{ decoration.package_section.title }}</view>
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
        <view class="section-head">
          <view class="section-title">{{ decoration.promo_section.title }}</view>
          <view class="section-link">运营精选</view>
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
        <view class="section-head">
          <view class="section-title">{{ decoration.quick_section.title }}</view>
          <view class="section-link" @click="goProfile">{{ decoration.quick_section.subtitle }}</view>
        </view>
        <view class="quick-grid">
          <view class="quick-entry tap-item" v-for="(item, index) in quickItems" :key="`${item.title}-${index}`" @click="openConfiguredLink(item)">
            <view class="quick-entry-title">{{ item.title }}</view>
            <view class="quick-entry-desc">{{ item.desc }}</view>
          </view>
        </view>
      </view>

      <view v-else-if="customBlockFromLayout(sectionKey)?.type === 'banner'" class="card custom-banner-card tap-item" @click="openConfiguredLink(customBlockFromLayout(sectionKey))">
        <view class="promo-badge">{{ customBlockFromLayout(sectionKey)?.badge || '活动横幅' }}</view>
        <view class="promo-title">{{ customBlockFromLayout(sectionKey)?.title || '未命名横幅' }}</view>
        <view class="promo-desc">{{ customBlockFromLayout(sectionKey)?.desc || '请补充活动说明' }}</view>
        <view class="banner-action">{{ customBlockFromLayout(sectionKey)?.button_text || '立即查看' }}</view>
      </view>

      <view v-else-if="customBlockFromLayout(sectionKey)?.type === 'grid'" class="card">
        <view class="section-head">
          <view class="section-title">{{ customBlockFromLayout(sectionKey)?.title || '专题导航' }}</view>
          <view class="section-link">{{ customBlockFromLayout(sectionKey)?.subtitle || '运营专区' }}</view>
        </view>
        <view class="quick-grid">
          <view class="quick-entry tap-item" v-for="(item, index) in customGridItems(customBlockFromLayout(sectionKey))" :key="`${sectionKey}-${index}`" @click="openConfiguredLink(item)">
            <view class="quick-entry-title">{{ item.title }}</view>
            <view class="quick-entry-desc">{{ item.desc }}</view>
          </view>
        </view>
      </view>

      <view v-else-if="customBlockFromLayout(sectionKey)?.type === 'coupon_strip'" class="card coupon-strip-card tap-item" @click="openConfiguredLink(customBlockFromLayout(sectionKey))">
        <view class="section-head">
          <view class="section-title">{{ customBlockFromLayout(sectionKey)?.title || '券权益条' }}</view>
          <view class="section-link">{{ customBlockFromLayout(sectionKey)?.badge || '权益专区' }}</view>
        </view>
        <view class="section-desc">{{ customBlockFromLayout(sectionKey)?.desc }}</view>
      </view>

      <view v-else-if="customBlockFromLayout(sectionKey)?.type === 'zone_feed'" class="card">
        <view class="section-head">
          <view class="section-title">{{ customBlockFromLayout(sectionKey)?.title || '专区商品流' }}</view>
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

      <view v-else-if="customBlockFromLayout(sectionKey)?.type === 'image_swiper'" class="card">
        <view class="section-head">
          <view class="section-title">{{ customBlockFromLayout(sectionKey)?.title || '轮播海报' }}</view>
          <view class="section-link">{{ customBlockFromLayout(sectionKey)?.autoplay ? '自动轮播' : '手动切换' }}</view>
        </view>
        <swiper class="module-swiper" circular :autoplay="customBlockFromLayout(sectionKey)?.autoplay !== false" :indicator-dots="customSwiperItems(customBlockFromLayout(sectionKey)).length > 1">
          <swiper-item v-for="(item, index) in customSwiperItems(customBlockFromLayout(sectionKey))" :key="`${sectionKey}-swiper-${index}`">
            <view class="module-swiper-card tap-item" @click="openConfiguredLink(item)">
              <view class="promo-badge">{{ item.badge || '轮播图' }}</view>
              <view class="promo-title">{{ item.title }}</view>
              <view class="promo-desc">{{ item.desc }}</view>
            </view>
          </swiper-item>
        </swiper>
      </view>

      <view v-else-if="customBlockFromLayout(sectionKey)?.type === 'mixed_goods'" class="card">
        <view class="section-head">
          <view class="section-title">{{ customBlockFromLayout(sectionKey)?.title || '混合商品' }}</view>
          <view class="section-link">{{ customBlockFromLayout(sectionKey)?.subtitle || '人工编排' }}</view>
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
const ZONE_SOURCE_OPTIONS = [
  { value: 'repurchase', label: '复购区' },
  { value: 'selfOperated', label: '自营商城' },
  { value: 'hotSale', label: '爆款区' },
  { value: 'localLife', label: '本地生活' }
]
const TAB_PATHS = new Set([
  '/pages/home/index',
  '/pages/packages/list',
  '/pages/local-life/index',
  '/pages/profile/index'
])

function customLayoutKey(id) {
  return `custom:${id}`
}

function createDefaultHomeSwiper() {
  return {
    id: 'home_swiper_main',
    type: 'image_swiper',
    enabled: true,
    title: '首页轮播',
    autoplay: true,
    items: [
      {
        enabled: true,
        badge: '商城主推',
        title: '热门专区与首单权益一起前置',
        desc: '参考主流电商首页，把主推活动、分区会场和转化入口收进首屏轮播。',
        path: '/pages/packages/list',
        open_type: 'switchTab'
      },
      {
        enabled: true,
        badge: '本地生活',
        title: '到店服务和联盟商家进入底部导航',
        desc: '把本地生活从二级入口抬升到底部栏，门店服务触达更直接。',
        path: '/pages/local-life/index',
        open_type: 'switchTab'
      },
      {
        enabled: true,
        badge: '爆款专区',
        title: '首页下滑直达双列瀑布商品流',
        desc: '支持下拉刷新和继续加载，持续承接爆款、自营和本地生活内容。',
        path: '/pages/packages/list',
        open_type: 'switchTab'
      }
    ]
  }
}

function createDefaultDecoration() {
  const homeSwiper = createDefaultHomeSwiper()
  return {
    hero: {
      badge: 'Excellent Mall',
      title: '把轮播会场、四区导航和商品瀑布流放进统一首页',
      desc: '参考热门电商项目的首页结构，先展示首屏轮播和四区分流，再用可下拉刷新的瀑布流持续承接商城、本地生活和复购内容。',
      tags: ['首页轮播', '四区导航', '瀑布流', '本地生活', '我的订单', '装修配置']
    },
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
        { enabled: true, key: 'repurchase', title: '复购区', tip: '套餐进入，二次复购 4-6 折', path: '/pages/packages/list', open_type: 'switchTab' },
        { enabled: true, key: 'selfOperated', title: '自营商城', tip: '兑换券 5-7 折抵扣，返 AI 券', path: '/pages/packages/list', open_type: 'switchTab' },
        { enabled: true, key: 'hotSale', title: '爆款区', tip: '低价抢购，支持积分或余额', path: '/pages/packages/list', open_type: 'switchTab' },
        { enabled: true, key: 'localLife', title: '本地生活', tip: '联盟商家服务、门店履约与收益联动', path: '/pages/local-life/index', open_type: 'switchTab' }
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
        { enabled: true, title: '套餐中心', desc: '查看入场资格与权益档位', path: '/pages/packages/list', open_type: 'switchTab' },
        { enabled: true, title: '我的团队', desc: '管理归属与成员结构', path: '/subpackages/team/index', open_type: 'navigate' },
        { enabled: true, title: '邀请好友', desc: '分享邀请码完成绑定', path: '/subpackages/invite/index', open_type: 'navigate' },
        { enabled: true, title: '佣金中心', desc: '跟进冻结与可提现状态', path: '/subpackages/commission/index', open_type: 'navigate' },
        { enabled: true, title: '资产中心', desc: '查看余额、积分与券资产', path: '/subpackages/assets/index', open_type: 'navigate' },
        { enabled: true, title: '个人中心', desc: '维护资料、签到和账号设置', path: '/pages/profile/index', open_type: 'switchTab' }
      ]
    }
  }
}

function createFallbackItem(type) {
  if (type === 'promo') {
    return { enabled: true, badge: '', title: '', desc: '', path: '', open_type: 'navigate' }
  }
  if (type === 'zone') {
    return { enabled: true, key: '', title: '', tip: '', path: '', open_type: 'navigate' }
  }
  return { enabled: true, title: '', desc: '', path: '', open_type: 'navigate' }
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
    return {
      id: block?.id || `swiper_${index}`,
      type,
      enabled: normalizeEnabled(block?.enabled, true),
      title: block?.title || '',
      autoplay: normalizeEnabled(block?.autoplay, true),
      items: Array.isArray(block?.items) && block.items.length
        ? block.items.map((item) => ({
            enabled: normalizeEnabled(item?.enabled, true),
            badge: item?.badge || '',
            title: item?.title || '',
            desc: item?.desc || '',
            path: item?.path || '',
            open_type: item?.open_type || 'navigate'
          }))
        : []
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
  const customBlocks = Array.isArray(next.custom_blocks)
    ? next.custom_blocks.map((block, index) => normalizeCustomBlock(block, index))
    : []

  return {
    hero: {
      badge: next.hero?.badge || defaults.hero.badge,
      title: next.hero?.title || defaults.hero.title,
      desc: next.hero?.desc || defaults.hero.desc,
      tags: Array.isArray(next.hero?.tags) && next.hero.tags.length ? next.hero.tags.filter(Boolean) : defaults.hero.tags
    },
    layout: normalizeLayout(next.layout, defaults.layout, customBlocks),
    custom_blocks: customBlocks,
    announcement: {
      enabled: normalizeEnabled(next.announcement?.enabled, defaults.announcement.enabled),
      title: next.announcement?.title || defaults.announcement.title,
      lines: Array.isArray(next.announcement?.lines) && next.announcement.lines.length ? next.announcement.lines.filter(Boolean) : defaults.announcement.lines
    },
    zone_section: {
      enabled: normalizeEnabled(next.zone_section?.enabled, defaults.zone_section.enabled),
      title: next.zone_section?.title || defaults.zone_section.title,
      subtitle: next.zone_section?.subtitle || defaults.zone_section.subtitle,
      items: Array.isArray(next.zone_section?.items) && next.zone_section.items.length
        ? next.zone_section.items.map((item) => ({
            ...createFallbackItem('zone'),
            ...item,
            enabled: normalizeEnabled(item?.enabled, true)
          }))
        : defaults.zone_section.items
    },
    waterfall_section: {
      enabled: normalizeEnabled(next.waterfall_section?.enabled, defaults.waterfall_section.enabled),
      title: next.waterfall_section?.title || defaults.waterfall_section.title,
      subtitle: next.waterfall_section?.subtitle || defaults.waterfall_section.subtitle,
      page_size: Math.max(4, Math.min(20, Number(next.waterfall_section?.page_size || defaults.waterfall_section.page_size))),
      source_keys: Array.isArray(next.waterfall_section?.source_keys) && next.waterfall_section.source_keys.length
        ? next.waterfall_section.source_keys.filter((item) => ZONE_SOURCE_OPTIONS.some((option) => option.value === item))
        : defaults.waterfall_section.source_keys
    },
    package_section: {
      enabled: normalizeEnabled(next.package_section?.enabled, defaults.package_section.enabled),
      title: next.package_section?.title || defaults.package_section.title,
      desc: next.package_section?.desc || defaults.package_section.desc,
      limit: Math.max(1, Math.min(6, Number(next.package_section?.limit || defaults.package_section.limit)))
    },
    promo_section: {
      enabled: normalizeEnabled(next.promo_section?.enabled, defaults.promo_section.enabled),
      title: next.promo_section?.title || defaults.promo_section.title,
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
      title: next.quick_section?.title || defaults.quick_section.title,
      subtitle: next.quick_section?.subtitle || defaults.quick_section.subtitle,
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
const heroConfig = computed(() => decoration.value.hero || createDefaultDecoration().hero)
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
const zoneItems = computed(() => (decoration.value.zone_section?.items || []).filter((item) => item?.enabled !== false && (item?.title || item?.key)))
const quickItems = computed(() => (decoration.value.quick_section?.items || []).filter((item) => item?.enabled !== false && (item?.title || item?.desc)))

function zoneSourceLabel(key) {
  return ZONE_SOURCE_OPTIONS.find((item) => item.value === key)?.label || '专区'
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
  return (block?.items || []).filter((item) => item?.enabled !== false && (item?.title || item?.desc))
}

function customSwiperItems(block) {
  return (block?.items || []).filter((item) => item?.enabled !== false && (item?.badge || item?.title || item?.desc))
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
  waterfall_section: decoration.value.waterfall_section?.enabled !== false && waterfallAllItems.value.length > 0,
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
    const decorationPromise = homeApi.decoration().catch(() => ({ payload: createDefaultDecoration() }))
    const [packageRows, repurchase, selfOperated, hotSale, localLife, decorationRes] = await Promise.all([
      packageApi.list(),
      homeApi.repurchase(),
      homeApi.selfOperated(),
      homeApi.hotSale(),
      localLifeApi.services(),
      decorationPromise
    ])
    const normalizedDecoration = normalizeDecoration(decorationRes?.payload)
    packages.value = packageRows || []
    decorationData.value = normalizedDecoration
    lists.value = {
      repurchase: repurchase || [],
      selfOperated: selfOperated || [],
      hotSale: hotSale || [],
      localLife: localLife || []
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
  background:
    radial-gradient(circle at top right, rgba(209, 163, 79, 0.14), transparent 28%),
    linear-gradient(180deg, #fffaf1 0%, #f5f8f2 32%, #f7f3eb 100%);
}

.hero-panel,
.swiper-panel {
  margin-bottom: 20rpx;
}

.hero-panel {
  padding: 30rpx;
  border-radius: 34rpx;
  background:
    radial-gradient(circle at top right, rgba(208, 163, 80, 0.18), transparent 26%),
    linear-gradient(145deg, #173530 0%, #1f7d5f 100%);
  color: #ffffff;
  box-shadow: 0 24rpx 48rpx rgba(24, 52, 46, 0.18);
}

.hero-kicker-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}

.hero-refresh {
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.78);
}

.hero-tags,
.benefit-row,
.waterfall-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}

.hero-tags {
  margin-top: 22rpx;
}

.hero-tag,
.benefit-pill,
.promo-badge,
.waterfall-chip,
.slide-badge {
  padding: 10rpx 18rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
}

.hero-tag,
.slide-badge {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.14);
}

.swiper-panel {
  padding: 24rpx;
  border-radius: 30rpx;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(8px);
  box-shadow: 0 12rpx 30rpx rgba(24, 52, 46, 0.06);
}

.section-head.compact {
  margin-bottom: 18rpx;
}

.hero-swiper,
.module-swiper {
  height: 260rpx;
}

.swiper-slide,
.module-swiper-card {
  height: 100%;
  padding: 30rpx;
  border-radius: 28rpx;
  box-sizing: border-box;
  background:
    radial-gradient(circle at top right, rgba(208, 163, 80, 0.18), transparent 30%),
    linear-gradient(145deg, #18343b 0%, #275d57 58%, #1f8f64 100%);
  color: #ffffff;
}

.slide-title {
  margin: 18rpx 0 12rpx;
  font-size: 38rpx;
  font-weight: 700;
  line-height: 1.3;
}

.slide-desc {
  font-size: 24rpx;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.82);
}

.notice-card {
  background:
    radial-gradient(circle at top left, rgba(208, 163, 80, 0.1), transparent 30%),
    linear-gradient(180deg, #fffdf8 0%, #f6f8f3 100%);
}

.notice-list,
.package-stack,
.promo-grid,
.feed-list {
  display: grid;
  gap: 16rpx;
}

.notice-item {
  padding: 22rpx 24rpx;
  border-radius: 22rpx;
  background: linear-gradient(180deg, #fcfdfa 0%, #f4f8f3 100%);
  color: #556560;
  line-height: 1.7;
  border: 1rpx solid rgba(21, 55, 45, 0.05);
}

.zone-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
}

.zone-nav-card,
.package-card,
.promo-card,
.custom-banner-card,
.coupon-strip-card,
.feed-card,
.quick-entry,
.waterfall-card {
  background: linear-gradient(180deg, #fcfdfa 0%, #f4f8f3 100%);
  border-radius: 26rpx;
  border: 1rpx solid rgba(21, 55, 45, 0.05);
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
  min-height: 200rpx;
  box-sizing: border-box;
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
  color: #18342e;
  line-height: 1.35;
}

.zone-card-count {
  min-width: 74rpx;
  height: 48rpx;
  padding: 0 14rpx;
  border-radius: 999rpx;
  background: rgba(30, 143, 100, 0.12);
  color: #1e8f64;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 22rpx;
}

.zone-card-tip,
.promo-desc,
.feed-desc,
.waterfall-desc,
.quick-entry-desc {
  font-size: 24rpx;
  line-height: 1.7;
  color: #66756f;
}

.zone-card-link {
  margin-top: 14rpx;
  font-size: 22rpx;
  color: #1e8f64;
}

.waterfall-meta {
  margin-bottom: 18rpx;
}

.waterfall-chip,
.benefit-pill,
.promo-badge {
  color: #1b6f4f;
  background: rgba(231, 246, 239, 0.9);
}

.waterfall-columns {
  display: flex;
  gap: 16rpx;
}

.waterfall-column {
  flex: 1;
  display: grid;
  gap: 16rpx;
}

.waterfall-card {
  overflow: hidden;
}

.waterfall-cover {
  height: 220rpx;
  background:
    radial-gradient(circle at top right, rgba(209, 163, 79, 0.2), transparent 28%),
    linear-gradient(145deg, #203732 0%, #2e6e61 100%);
}

.waterfall-cover.tall {
  height: 280rpx;
}

.waterfall-image {
  width: 100%;
  height: 100%;
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
  color: #1e8f64;
  line-height: 1;
}

.waterfall-market-price {
  font-size: 22rpx;
  color: #9aa7a0;
  text-decoration: line-through;
}

.load-more-btn {
  margin-top: 24rpx;
}

.item-title,
.quick-entry-title {
  font-size: 28rpx;
  font-weight: 700;
  color: #18342e;
}

.item-meta,
.feed-meta {
  margin-top: 10rpx;
  font-size: 22rpx;
  color: #1b6f4f;
}

.promo-card,
.custom-banner-card,
.coupon-strip-card {
  background:
    radial-gradient(circle at top right, rgba(200, 155, 73, 0.14), transparent 30%),
    linear-gradient(180deg, #fffdf9 0%, #f5f7f2 100%);
}

.banner-action {
  display: inline-flex;
  margin-top: 18rpx;
  padding: 10rpx 18rpx;
  border-radius: 999rpx;
  background: rgba(24, 52, 59, 0.08);
  color: #18342e;
  font-size: 22rpx;
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
}

.quick-entry {
  min-height: 152rpx;
  box-sizing: border-box;
}
</style>
