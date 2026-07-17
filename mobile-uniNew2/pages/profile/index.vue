<template>
  <view class="profile-page">
    <!-- User Header -->
    <view class="user-header">
      <view class="user-info" @click="goLogin">
        <view class="avatar-wrap">
          <image v-if="avatarUrl" class="avatar-img" :src="avatarUrl" mode="aspectFill" />
          <view v-else class="avatar-placeholder">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
              <path d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 5.17157 16.1716C4.42143 16.9217 4 17.9391 4 19V21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <circle cx="12" cy="7" r="4" stroke="currentColor" stroke-width="2"/>
            </svg>
          </view>
        </view>
        <view class="user-text">
          <text class="user-name">{{ nickname }}</text>
          <view v-if="isLogin" class="user-id">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <rect x="2" y="5" width="20" height="14" rx="2" stroke="currentColor" stroke-width="2"/>
              <path d="M2 10H22" stroke="currentColor" stroke-width="2"/>
            </svg>
            ID {{ userId }}
          </view>
        </view>
      </view>
      <view v-if="isLogin" class="vip-tag" :class="{ active: isVip }">
        <svg v-if="isVip" width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        {{ isVip ? 'VIP会员' : '普通用户' }}
      </view>
    </view>

    <!-- Asset Summary -->
    <view class="asset-card">
      <view
        v-for="(asset, index) in assets"
        :key="asset.label"
        class="asset-item"
        :class="{ clickable: isLogin }"
        @click="go(asset.path)"
      >
        <view v-if="index > 0" class="asset-divider" />
        <text class="asset-value">{{ asset.value }}</text>
        <text class="asset-label">{{ asset.label }}</text>
      </view>
    </view>

    <!-- Orders -->
    <view class="section-card">
      <view class="card-header">
        <text class="card-title">我的订单</text>
        <view class="card-more" @click="go('/pages/orders/list')">
          <text>全部订单</text>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M9 18L15 12L9 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </view>
      </view>
      <view class="order-grid">
        <view
          v-for="item in orderTypes"
          :key="item.type"
          class="order-item"
          @click="go(item.path)"
        >
          <view class="order-icon" :style="{ background: item.bg }">
            <svg v-if="item.type === 'pending'" width="32" height="32" viewBox="0 0 24 24" fill="none">
              <rect x="2" y="5" width="20" height="14" rx="2" stroke="currentColor" stroke-width="2"/>
              <path d="M2 10H22" stroke="currentColor" stroke-width="2"/>
            </svg>
            <svg v-else-if="item.type === 'ship'" width="32" height="32" viewBox="0 0 24 24" fill="none">
              <path d="M21 10H3M21 10V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V10M21 10L19 4H5L3 10M21 10H3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg v-else-if="item.type === 'shipped'" width="32" height="32" viewBox="0 0 24 24" fill="none">
              <path d="M9 11L12 14L22 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M21 12V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg v-else-if="item.type === 'review'" width="32" height="32" viewBox="0 0 24 24" fill="none">
              <path d="M21 15C21 15.5304 20.7893 16.0391 20.4142 16.4142C20.0391 16.7893 19.5304 17 19 17H6L2 21V5C2 4.46957 2.21071 3.96086 2.58579 3.58579C2.96086 3.21071 3.46957 3 4 3H19C19.5304 3 20.0391 3.21071 20.4142 3.58579C20.7893 3.96086 21 4.46957 21 5V15Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg v-else width="32" height="32" viewBox="0 0 24 24" fill="none">
              <path d="M3 6H21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M19 6V20C19 20.5304 18.7893 21.0391 18.4142 21.4142C18.0391 21.7893 17.5304 22 17 22H7C6.46957 22 5.96086 21.7893 5.58579 21.4142C5.21071 21.0391 5 20.5304 5 20V6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M8 6V4C8 3.46957 8.21071 2.96086 8.58579 2.58579C8.96086 2.21071 9.46957 2 10 2H14C14.5304 2 15.0391 2.21071 15.4142 2.58579C15.7893 2.96086 16 3.46957 16 4V6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <view v-if="item.badge" class="badge">{{ item.badge }}</view>
          </view>
          <text class="order-label">{{ item.label }}</text>
        </view>
      </view>
    </view>

    <!-- Tools Grid -->
    <view class="section-card">
      <view class="card-header">
        <text class="card-title">常用服务</text>
      </view>
      <view class="tools-grid">
        <view
          v-for="tool in tools"
          :key="tool.label"
          class="tool-item"
          @click="go(tool.path)"
        >
          <view class="tool-icon" :style="{ background: tool.bg }">
            <svg v-if="tool.label === '我的快递'" width="28" height="28" viewBox="0 0 24 24" fill="none">
              <path d="M21 10H3M21 10V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V10M21 10L19 4H5L3 10M21 10H3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg v-else-if="tool.label === '我的收藏'" width="28" height="28" viewBox="0 0 24 24" fill="none">
              <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg v-else-if="tool.label === '购物车'" width="28" height="28" viewBox="0 0 24 24" fill="none">
              <path d="M6 2L3 6V20C3 20.5304 3.21071 21.0391 3.58579 21.4142C3.96086 21.7893 4.46957 22 5 22H19C19.5304 22 20.0391 21.7893 20.4142 21.4142C20.7893 21.0391 21 20.5304 21 20V6L18 2H6Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M3 6H21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M16 10C16 11.0609 15.5786 12.0783 14.8284 12.8284C14.0783 13.5786 13.0609 14 12 14C10.9391 14 9.92172 13.5786 9.17157 12.8284C8.42143 12.0783 8 11.0609 8 10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg v-else-if="tool.label === '我的足迹'" width="28" height="28" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
              <path d="M12 6V12L16 14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <view v-if="tool.tag" class="tool-badge">{{ tool.tag }}</view>
          </view>
          <text class="tool-label">{{ tool.label }}</text>
        </view>
      </view>
    </view>

    <!-- Menu List -->
    <view class="menu-card">
      <view
        v-for="(item, index) in menuItems"
        :key="item.label"
        class="menu-item"
        :class="{ last: index === menuItems.length - 1 }"
        @click="handleMenu(item)"
      >
        <view class="menu-icon-wrap" :style="{ background: item.iconBg }">
          <svg v-if="item.label === '邀请有礼'" width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M16 21V19C16 17.9391 15.5786 16.9217 14.8284 16.1716C14.0783 15.4214 13.0609 15 12 15C10.9391 15 9.92172 15.4214 9.17157 16.1716C8.42143 16.9217 8 17.9391 8 19V21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M12 15C14.2091 15 16 13.2091 16 11C16 8.79086 14.2091 7 12 7C9.79086 7 8 8.79086 8 11C8 13.2091 9.79086 15 12 15Z" stroke="currentColor" stroke-width="2"/>
            <path d="M20 8V14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <path d="M17 11H23" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
          <svg v-else-if="item.label === '我的团队'" width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M17 21V19C17 17.9391 16.5786 16.9217 15.8284 16.1716C15.0783 15.4214 14.0609 15 13 15H5C3.93913 15 2.92172 15.4214 2.17157 16.1716C1.42143 16.9217 1 17.9391 1 19V21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="9" cy="7" r="4" stroke="currentColor" stroke-width="2"/>
            <path d="M23 21V19C23 17.5 22 16.5 20.5 16.5C19 16.5 18 17.5 18 19V21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M16 3.13C17.7699 3.58304 19.0078 5.17816 19.0078 7C19.0078 8.82184 17.7699 10.417 16 10.87" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <svg v-else-if="item.label === '银行卡'" width="20" height="20" viewBox="0 0 24 24" fill="none">
            <rect x="1" y="4" width="22" height="16" rx="2" stroke="currentColor" stroke-width="2"/>
            <path d="M1 10H23" stroke="currentColor" stroke-width="2"/>
          </svg>
          <svg v-else-if="item.label === '消息通知'" width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M18 8C18 6.4087 17.3679 4.88258 16.2426 3.75736C15.1174 2.63214 13.5913 2 12 2C10.4087 2 8.88258 2.63214 7.75736 3.75736C6.63214 4.88258 6 6.4087 6 8C6 15 3 17 3 17H21C21 17 18 15 18 8Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M13.73 21C13.5542 21.3031 13.3019 21.5547 12.9982 21.7295C12.6946 21.9044 12.3504 21.9965 12 21.9965C11.6496 21.9965 11.3054 21.9044 11.0018 21.7295C10.6982 21.5547 10.4458 21.3031 10.27 21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <svg v-else-if="item.label === '账号安全'" width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M12 22C12 22 20 18 20 12V5L12 2L4 5V12C4 18 12 22 12 22Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M9 12L11 14L15 10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M21 15C21 15.5304 20.7893 16.0391 20.4142 16.4142C20.0391 16.7893 19.5304 17 19 17H5L2 21V5C2 4.46957 2.21071 3.96086 2.58579 3.58579C2.96086 3.21071 3.46957 3 4 3H19C19.5304 3 20.0391 3.21071 20.4142 3.58579C20.7893 3.96086 21 4.46957 21 5V15Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </view>
        <text class="menu-label">{{ item.label }}</text>
        <text v-if="item.value" class="menu-value">{{ item.value }}</text>
        <svg v-if="item.path" class="menu-arrow" width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M9 18L15 12L9 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </view>
    </view>

    <view class="bottom-space" />
  </view>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue';
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app';
import { assetApi, commissionApi, userApi, commerceApi, orderApi } from '@/api/modules';
import { pickListPayload, toProfileOverview } from '@/utils/adapters';
import { trackEvent, trackPageView } from '@/utils/track';

const TAB_PAGES = new Set([
  '/pages/home/index',
  '/pages/packages/list',
  '/pages/cart/index',
  '/pages/profile/index'
]);

// User state
const profileInfo = ref({});
const assetSummary = ref({});
const overview = ref({
  nickname: '点击登录',
  userId: '--',
  level: 1,
  withdrawableCommission: '0.00'
});
const inviteCode = ref('');

// Computed
const isLogin = computed(() => !!profileInfo.value?.id);
const avatarUrl = computed(() => profileInfo.value?.avatar || '');
const nickname = computed(() => overview.value.nickname || '点击登录');
const userId = computed(() => overview.value.userId || '--');
const level = computed(() => overview.value.level || 1);
const isVip = computed(() => level.value > 1);

// Assets
const assets = computed(() => [
  { label: '余额', value: formatAmount(assetSummary.value.BALANCE ?? assetSummary.value.balance), path: '/subpackages/assets/index' },
  { label: '积分', value: formatAmount(assetSummary.value.POINTS ?? assetSummary.value.points), path: '/subpackages/assets/index' },
  { label: '佣金', value: formatAmount(overview.value.withdrawableCommission), path: '/subpackages/commission/index' },
  { label: '优惠券', value: '0', path: '/subpackages/coupon/list' }
]);

// Order counts
const pendingCount = ref('');
const pendingShipCount = ref('');
const shippedCount = ref('');
const reviewCount = ref('');
const refundCount = ref('');

const orderTypes = computed(() => [
  { type: 'pending', label: '待付款', bg: 'var(--primary-bg)', path: '/pages/orders/list?status=待支付', badge: pendingCount.value },
  { type: 'ship', label: '待发货', bg: 'var(--accent-bg)', path: '/pages/orders/list?status=待发货', badge: pendingShipCount.value },
  { type: 'shipped', label: '已发货', bg: 'var(--success-bg)', path: '/pages/orders/list?status=已发货', badge: shippedCount.value },
  { type: 'review', label: '已完成', bg: '#FCE7F3', path: '/pages/orders/list?status=已完成', badge: reviewCount.value },
  { type: 'refund', label: '取消/退款', bg: 'var(--danger-bg)', path: '/pages/orders/list?status=取消/退款', badge: refundCount.value }
]);

// Tools counts
const shippingCount = ref('');
const favoritesCount = ref('');
const cartCount = ref('');
const footprintsCount = ref('');

const tools = computed(() => [
  { label: '我的快递', bg: 'linear-gradient(135deg, var(--primary), var(--primary-dark))', tag: shippingCount.value, path: '/subpackages/profile/shipping' },
  { label: '我的收藏', bg: 'linear-gradient(135deg, #0EA5E9, #0284C7)', tag: favoritesCount.value, path: '/subpackages/profile/favorites' },
  { label: '购物车', bg: 'linear-gradient(135deg, #F97316, #EA580C)', tag: cartCount.value, path: '/pages/cart/index' },
  { label: '我的足迹', bg: 'linear-gradient(135deg, #6366F1, #4F46E5)', tag: footprintsCount.value, path: '/subpackages/profile/footprints' }
]);

// Menu
const DEV_MENU_LABELS = ['银行卡', '消息通知', '账号安全', '联系客服'];

const menuItems = computed(() => [
  { icon: 'invite', iconBg: 'linear-gradient(135deg, var(--success), #16A34A)', label: '邀请有礼', value: inviteCode.value || '', path: '/subpackages/invite/index' },
  { icon: 'team', iconBg: 'linear-gradient(135deg, #0EA5E9, #0284C7)', label: '我的团队', value: '', path: '/subpackages/team/index' },
  { icon: 'security', iconBg: 'linear-gradient(135deg, #10B981, #059669)', label: '收货地址', value: '', path: '/subpackages/profile/addresses' },
  { icon: 'bank', iconBg: 'linear-gradient(135deg, #6366F1, #4F46E5)', label: '银行卡', value: '', path: '/subpackages/profile/bank' },
  { icon: 'notify', iconBg: 'linear-gradient(135deg, var(--accent), var(--accent-dark))', label: '消息通知', value: '', path: '/subpackages/notification/list' },
  { icon: 'security', iconBg: 'linear-gradient(135deg, #EC4899, #DB2777)', label: '账号安全', value: '', path: '/subpackages/profile/security' },
  { icon: 'service', iconBg: 'linear-gradient(135deg, var(--text-muted), #475569)', label: '联系客服', value: '', path: '' }
]);

// Helpers
const formatAmount = (value) => {
  const num = Number(value || 0);
  return num.toFixed(2);
};

const goLogin = () => {
  if (!isLogin.value) {
    uni.navigateTo({ url: '/pages/login/index' });
  }
};

const loadProfile = async () => {
  try {
    const [profileRes, teamRes, assetRes, commissionRes, inviteRes, favoritesRes, cartRes, footprintsRes, shipmentsRes, ordersRes] = await Promise.allSettled([
      userApi.profile(),
      userApi.teamSummary(),
      assetApi.summary(),
      commissionApi.summary(),
      userApi.inviteCode(),
      commerceApi.favorites({ page: 1, page_size: 100 }),
      commerceApi.cart(),
      commerceApi.footprints({ page: 1, page_size: 100 }),
      commerceApi.shipments(),
      orderApi.list({ page: 1, page_size: 100 })
    ]);

    if (profileRes.status === 'fulfilled') {
      profileInfo.value = profileRes.value || {};
    }
    if (assetRes.status === 'fulfilled') {
      assetSummary.value = assetRes.value || {};
    }
    if (inviteRes.status === 'fulfilled') {
      inviteCode.value = inviteRes.value?.invite_code || inviteRes.value?.code || '';
    }

    if (favoritesRes.status === 'fulfilled') {
      const total = pickListPayload(favoritesRes.value).length;
      favoritesCount.value = total > 0 ? String(total) : '';
    }
    if (cartRes.status === 'fulfilled') {
      const items = pickListPayload(cartRes.value);
      const total = items.reduce((sum, item) => sum + (item.quantity || 0), 0);
      cartCount.value = total > 0 ? String(total) : '';
    }
    if (footprintsRes.status === 'fulfilled') {
      const total = pickListPayload(footprintsRes.value).length;
      footprintsCount.value = total > 0 ? String(total) : '';
    }
    if (shipmentsRes.status === 'fulfilled') {
      const shipments = pickListPayload(shipmentsRes.value);
      shippingCount.value = shipments.length > 0 ? String(shipments.length) : '';
    }

    if (ordersRes.status === 'fulfilled') {
      const orders = pickListPayload(ordersRes.value);
      const countByStatus = (status) => orders.filter(o => (o.status_text || o.status) === status).length;
      pendingCount.value = countByStatus('待支付') > 0 ? String(countByStatus('待支付')) : '';
      pendingShipCount.value = countByStatus('待发货') > 0 ? String(countByStatus('待发货')) : '';
      shippedCount.value = countByStatus('已发货') > 0 ? String(countByStatus('已发货')) : '';
      reviewCount.value = countByStatus('已完成') > 0 ? String(countByStatus('已完成')) : '';
      const refundTotal = countByStatus('已取消') + countByStatus('已退款');
      refundCount.value = refundTotal > 0 ? String(refundTotal) : '';
    }

    overview.value = toProfileOverview(
      profileRes.status === 'fulfilled' ? profileRes.value : {},
      teamRes.status === 'fulfilled' ? teamRes.value : {},
      assetRes.status === 'fulfilled' ? assetRes.value : {},
      commissionRes.status === 'fulfilled' ? commissionRes.value : {}
    );
  } catch (error) {
    console.error('加载失败', error);
  } finally {
    uni.stopPullDownRefresh?.();
  }
};

const go = (path) => {
  if (!path) return;
  trackEvent('profile_click', { path });
  if (TAB_PAGES.has(path)) {
    uni.switchTab({ url: path });
  } else {
    uni.navigateTo({ url: path });
  }
};

const handleMenu = (item) => {
  trackEvent('profile_menu', { label: item.label });
  if (DEV_MENU_LABELS.includes(item.label)) {
    uni.showToast({ title: `${item.label}开发中`, icon: 'none' });
    return;
  }
  if (item.path) {
    go(item.path);
  }
};

onShow(() => {
  trackPageView('profile');
  loadProfile();
});

onMounted(() => {
  loadProfile();
});

onPullDownRefresh(async () => {
  await loadProfile();
});
</script>

<style scoped>
@import '@/styles/common.css';

.profile-page {
  min-height: 100vh;
  background: var(--bg);
  padding: 24rpx 32rpx;
  padding-top: calc(24rpx + env(safe-area-inset-top));
  padding-bottom: calc(env(safe-area-inset-bottom) + 160rpx);
}

/* ===== User Header ===== */
.user-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 36rpx;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 28rpx;
}

.avatar-wrap {
  width: 132rpx;
  height: 132rpx;
  border-radius: var(--radius-full);
  overflow: hidden;
  box-shadow: var(--shadow-lg);
  border: 5rpx solid var(--card);
}

.avatar-img {
  width: 100%;
  height: 100%;
}

.avatar-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.user-text {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}

.user-name {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--text);
}

.user-id {
  display: flex;
  align-items: center;
  gap: 8rpx;
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.vip-tag {
  display: flex;
  align-items: center;
  gap: 8rpx;
  padding: 12rpx 24rpx;
  background: var(--bg);
  color: var(--text-muted);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  border-radius: var(--radius-full);
  border: 1rpx solid var(--border);
}

.vip-tag.active {
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
  color: white;
  border-color: transparent;
  box-shadow: var(--shadow-primary);
}

/* ===== Asset Card ===== */
.asset-card {
  display: flex;
  background: var(--card);
  border-radius: var(--radius-xl);
  padding: 36rpx 0;
  margin-bottom: 28rpx;
  box-shadow: var(--shadow);
}

.asset-item {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10rpx;
}

.asset-item.clickable:active {
  transform: scale(0.95);
}

.asset-divider {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 1rpx;
  height: 56rpx;
  background: var(--border-light);
}

.asset-value {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--primary);
}

.asset-label {
  font-size: var(--text-sm);
  color: var(--text-muted);
}

/* ===== Section Card ===== */
.section-card {
  background: var(--card);
  border-radius: var(--radius-xl);
  padding: 36rpx;
  margin-bottom: 28rpx;
  box-shadow: var(--shadow);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 32rpx;
}

.card-title {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--text);
}

.card-more {
  display: flex;
  align-items: center;
  gap: 6rpx;
  font-size: var(--text-sm);
  color: var(--text-muted);
  transition: color var(--duration-fast) var(--ease-out);
}

.card-more:active {
  color: var(--primary);
}

/* ===== Order Grid ===== */
.order-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12rpx;
}

.order-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14rpx;
}

.order-item:active {
  transform: scale(0.95);
}

.order-icon {
  position: relative;
  width: 88rpx;
  height: 88rpx;
  border-radius: var(--radius-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary);
  background: var(--primary-bg);
  transition: transform var(--duration-fast) var(--ease-out);
}

.order-item:active .order-icon {
  transform: scale(0.9);
  background: var(--primary-surface);
}

.badge {
  position: absolute;
  top: -10rpx;
  right: -10rpx;
  min-width: 40rpx;
  height: 40rpx;
  padding: 0 12rpx;
  background: linear-gradient(135deg, var(--danger) 0%, #F87171 100%);
  color: white;
  font-size: 22rpx;
  font-weight: var(--font-bold);
  border-radius: 20rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2rpx 8rpx rgba(239, 68, 68, 0.3);
}

.order-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  font-weight: var(--font-medium);
}

/* ===== Tools Grid ===== */
.tools-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 28rpx;
}

.tool-item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14rpx;
}

.tool-item:active {
  transform: scale(0.95);
}

.tool-icon {
  position: relative;
  width: 96rpx;
  height: 96rpx;
  border-radius: var(--radius-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: var(--shadow);
  transition: transform var(--duration-fast) var(--ease-out);
}

.tool-item:active .tool-icon {
  transform: scale(0.9);
  box-shadow: var(--shadow-sm);
}

.tool-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  font-weight: var(--font-medium);
}

.tool-badge {
  position: absolute;
  top: -10rpx;
  right: 4rpx;
  min-width: 36rpx;
  height: 36rpx;
  padding: 0 10rpx;
  background: linear-gradient(135deg, var(--danger) 0%, #F87171 100%);
  color: white;
  font-size: 22rpx;
  font-weight: var(--font-bold);
  border-radius: 18rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2rpx 8rpx rgba(239, 68, 68, 0.3);
}

/* ===== Menu Card ===== */
.menu-card {
  background: var(--card);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow);
}

.menu-item {
  display: flex;
  align-items: center;
  padding: 32rpx 36rpx;
  border-bottom: 1rpx solid var(--border-light);
  transition: background var(--duration-fast) var(--ease-out);
}

.menu-item:active {
  background: var(--bg);
}

.menu-item.last {
  border-bottom: none;
}

.menu-icon-wrap {
  width: 64rpx;
  height: 64rpx;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  margin-right: 24rpx;
  flex-shrink: 0;
  box-shadow: var(--shadow-sm);
}

.menu-label {
  flex: 1;
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text);
}

.menu-value {
  font-size: var(--text-sm);
  color: var(--text-muted);
  margin-right: 20rpx;
  max-width: 200rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.menu-arrow {
  color: var(--text-muted);
  flex-shrink: 0;
}

/* Bottom Space */
.bottom-space {
  height: 64rpx;
}

/* ===== Reduced Motion ===== */
@media (prefers-reduced-motion: reduce) {
  .asset-item,
  .order-item,
  .tool-item,
  .menu-item,
  .card-more {
    transition: none;
  }

  .asset-item:active,
  .order-item:active,
  .tool-item:active {
    transform: none;
  }
}
</style>
