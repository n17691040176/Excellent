<template>
  <view class="profile-page">
    <view class="hero-card">
      <view class="hero-top">
        <view class="hero-user">
          <view class="avatar-shell">
            <view class="avatar">{{ initials }}</view>
          </view>
          <view class="hero-copy">
            <view class="nickname-row">
              <text class="nickname">{{ overview.nickname }}</text>
              <text class="level-pill">{{ overview.levelText }}</text>
            </view>
            <view class="hero-subline">{{ heroSubline }}</view>
          </view>
        </view>
        <view class="hero-settings interactive" @click="go('/subpackages/profile/settings')">设置</view>
      </view>

      <view class="hero-summary">
        <view
          v-for="item in platformCurrencies"
          :key="item.label"
          class="summary-chip interactive"
          @click="handleAction(item)"
        >
          <view class="summary-chip-value">{{ item.value }}</view>
          <view class="summary-chip-label">{{ item.label }}</view>
        </view>
      </view>
    </view>

    <view class="section-card orders-card mt-20">
      <view class="row-between">
        <view class="section-title slim-title">我的订单</view>
        <view class="more-link interactive" @click="go('/pages/orders/list')">全部</view>
      </view>
      <view class="order-grid">
        <view
          v-for="item in orderEntries"
          :key="item.title"
          class="order-entry interactive"
          @click="go(item.path)"
        >
          <view class="order-icon">
            {{ item.icon }}
            <view v-if="item.badge" class="order-badge">{{ item.badge }}</view>
          </view>
          <view class="order-title">{{ item.title }}</view>
        </view>
      </view>
    </view>

    <view class="section-card tool-card mt-20">
      <view class="row-between">
        <view class="section-title slim-title">常用工具</view>
        <view class="more-link interactive" @click="go('/pages/home/index')">更多</view>
      </view>
      <view class="tool-grid">
        <view
          v-for="item in commonTools"
          :key="item.title"
          class="tool-item interactive"
          @click="handleAction(item)"
        >
          <view class="tool-title-row">
            <view class="tool-icon">{{ item.icon }}</view>
            <view class="tool-title">{{ item.title }}</view>
          </view>
          <view class="tool-note">{{ item.note }}</view>
          <view class="tool-preview" :class="item.previewClass">
            <view class="tool-preview-mark">{{ item.previewMark }}</view>
          </view>
          <view class="tool-link">{{ item.actionText }}</view>
        </view>
      </view>
    </view>

    <view class="section-card power-card mt-20 interactive" @click="openPowerBank">
      <view class="power-top">
        <view>
          <view class="section-title slim-title">共享充电宝</view>
          <view class="power-desc">进入内置小程序，按配置好的 appId 和 path 打开</view>
        </view>
        <view class="power-chip">小程序</view>
      </view>
      <view class="power-meta">支持 App 内打开小程序；若当前环境不支持，会自动走兜底页。</view>
    </view>

    <view class="section-card benefit-section mt-20">
      <view class="benefit-grid">
        <view
          v-for="item in benefitEntries"
          :key="item.title"
          class="benefit-card interactive"
          :class="item.cardClass"
          @click="go(item.path)"
        >
          <view class="benefit-amount">{{ item.amount }}</view>
          <view class="benefit-title">{{ item.title }}</view>
          <view class="benefit-btn">去查看</view>
        </view>
      </view>
    </view>

  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app';
import { assetApi, commissionApi, userApi } from '@/api/modules';
import { openPowerBankMiniApp } from '@/utils/miniapp';
import { toProfileOverview } from '@/utils/adapters';
import { trackEvent, trackPageView } from '@/utils/track';

const TAB_PAGES = new Set([
  '/pages/home/index',
  '/pages/packages/list',
  '/pages/local-life/index',
  '/pages/profile/index'
]);

const overview = ref({
  nickname: 'Excellent 用户',
  userId: '--',
  levelText: '成长型合伙人',
  totalAsset: '0.00',
  withdrawableCommission: '0.00',
  teamMembers: 0
});
const profileInfo = ref({});
const inviteCode = ref('');
const assetSummary = ref({});
const isLegacyUser = computed(() => Boolean(profileInfo.value.is_legacy_user || profileInfo.value.is_legacy_imported));

const orderEntries = [
  { title: '待付款', icon: '付', badge: '', path: '/pages/orders/list' },
  { title: '待发货', icon: '发', badge: '', path: '/pages/orders/list' },
  { title: '待收货', icon: '收', badge: '', path: '/pages/orders/list' },
  { title: '待评价', icon: '评', path: '/pages/orders/list' },
  { title: '退款/售后', icon: '退', path: '/pages/orders/list' }
];

const commonTools = [
  {
    title: '快递',
    icon: '递',
    note: '1件待发货',
    previewMark: '箱',
    previewClass: 'preview-orange',
    actionText: '去查看',
    path: '/subpackages/profile/shipping'
  },
  {
    title: '收藏',
    icon: '藏',
    note: '收藏的宝贝',
    previewMark: '夹',
    previewClass: 'preview-gold',
    actionText: '逛更多宝贝',
    path: '/subpackages/profile/favorites'
  },
  {
    title: '购物车',
    icon: '车',
    note: '待下单商品',
    previewMark: '袋',
    previewClass: 'preview-mint',
    actionText: '去查看',
    path: '/subpackages/profile/cart'
  },
  {
    title: '足迹',
    icon: '迹',
    note: '看过的内容',
    previewMark: '钟',
    previewClass: 'preview-amber',
    actionText: '逛更多宝贝',
    path: '/subpackages/profile/footprints'
  }
];

function buildAssetIndexPath(tab = '', range = null) {
  const query = [];
  if (tab) query.push(`tab=${tab}`);
  if (range !== null && range !== undefined) query.push(`range=${range}`);
  return `/subpackages/assets/index${query.length ? `?${query.join('&')}` : ''}`;
}

function buildBalanceWithdrawPath(range = null) {
  const query = [];
  if (range !== null && range !== undefined) {
    query.push(`range=${range}`);
    query.push(`asset_range=${range}`);
  }
  return `/subpackages/assets/withdraw${query.length ? `?${query.join('&')}` : ''}`;
}

async function openPowerBank() {
  trackEvent('profile_click_power_bank');
  try {
    await openPowerBankMiniApp({
      userId: overview.value.userId,
      inviteCode: inviteCode.value
    });
  } catch (error) {
    uni.showToast({ title: '打开失败，请检查配置', icon: 'none' });
  }
}

const initials = computed(() => String(overview.value.nickname || 'EX').slice(0, 2).toUpperCase());

const heroSubline = computed(() => {
  const maskedPhone = maskPhone(profileInfo.value.phone);
  if (inviteCode.value) return `ID ${overview.value.userId} · 邀请码 ${inviteCode.value}`;
  if (maskedPhone) return `ID ${overview.value.userId} · 手机号 ${maskedPhone}`;
  return `ID ${overview.value.userId} · ${overview.value.levelText}`;
});

const platformCurrencies = computed(() => ([
  {
    label: '余额',
    value: formatAmount(assetSummary.value.BALANCE ?? assetSummary.value.balance),
    path: buildBalanceWithdrawPath()
  },
  {
    label: '消费金',
    value: formatAmount(assetSummary.value.VOUCHER ?? assetSummary.value.voucher),
    path: buildAssetIndexPath('voucher')
  },
  {
    label: '积分',
    value: formatAmount(assetSummary.value.POINTS ?? assetSummary.value.points),
    path: buildAssetIndexPath('points')
  },
  {
    label: '充电宝',
    value: `${formatCount(assetSummary.value.POWER_BANK ?? assetSummary.value.power_bank ?? assetSummary.value.power_bank_count)}台`,
    path: buildAssetIndexPath('power_bank')
  }
]));

const benefitEntries = computed(() => {
  const entries = [
    {
      title: '我的资产',
      amount: `¥${overview.value.totalAsset}`,
      desc: '余额、消费金、积分和充电宝统一查看明细',
      path: buildAssetIndexPath(),
      cardClass: 'benefit-orange'
    }
  ];

  if (isLegacyUser.value) {
    entries.push(
      {
        title: '佣金中心',
        amount: `¥${overview.value.withdrawableCommission}`,
        desc: '提现进度与收益明细随时看',
        path: '/subpackages/commission/index',
        cardClass: 'benefit-pink'
      },
      {
        title: '我的团队',
        amount: `${overview.value.teamMembers}人`,
        desc: '查看成员活跃和成交贡献',
        path: '/subpackages/team/index',
        cardClass: 'benefit-gold'
      }
    );
  }

  entries.push({
    title: '邀请有礼',
    amount: inviteCode.value || '去解锁',
    desc: '分享邀请码，承接转化关系',
    path: '/subpackages/invite/index',
    cardClass: 'benefit-red'
  });

  return entries;
});

function maskPhone(phone) {
  const raw = String(phone || '');
  if (raw.length < 7) return raw;
  return `${raw.slice(0, 3)}****${raw.slice(-4)}`;
}

function formatAmount(value) {
  return Number(value || 0).toFixed(2);
}

function formatCount(value) {
  const num = Number(value || 0);
  if (Number.isNaN(num)) return '0';
  if (Math.abs(num - Math.round(num)) < 0.000001) {
    return String(Math.round(num));
  }
  return num.toFixed(2).replace(/\.?0+$/, '');
}

const loadProfile = async () => {
  try {
    const [profileRes, teamRes, assetRes, commissionRes, inviteCodeRes] = await Promise.allSettled([
      userApi.profile(),
      userApi.teamSummary(),
      assetApi.summary(),
      commissionApi.summary(),
      userApi.inviteCode()
    ]);

    if (profileRes.status === 'fulfilled') {
      profileInfo.value = profileRes.value || {};
    }
    if (assetRes.status === 'fulfilled') {
      assetSummary.value = assetRes.value || {};
    }

    overview.value = toProfileOverview(
      profileRes.status === 'fulfilled' ? profileRes.value : {},
      teamRes.status === 'fulfilled' ? teamRes.value : {},
      assetRes.status === 'fulfilled' ? assetRes.value : {},
      commissionRes.status === 'fulfilled' ? commissionRes.value : {}
    );

    if (inviteCodeRes.status === 'fulfilled') {
      inviteCode.value = inviteCodeRes.value?.invite_code || inviteCodeRes.value?.code || '';
    }
  } catch (error) {
    // Request layer handles the toast.
  }
};

const go = (path) => {
  trackEvent('profile_click_entry', { path });
  if (TAB_PAGES.has(path)) {
    uni.switchTab({ url: path });
    return;
  }
  uni.navigateTo({ url: path });
};

const showComingSoon = (name) => {
  uni.showToast({ title: `${name}功能建设中`, icon: 'none' });
};

const handleAction = (item) => {
  if (item.path) {
    go(item.path);
    return;
  }
  showComingSoon(item.name || item.title);
};

onShow(() => {
  trackPageView('profile');
  loadProfile();
});

onPullDownRefresh(async () => {
  await loadProfile();
  uni.stopPullDownRefresh();
});
</script>

<style scoped>
@import '@/styles/common.css';

.profile-page {
  padding: 18rpx 18rpx 44rpx;
  box-sizing: border-box;
}

.hero-card {
  border-radius: 24rpx;
  padding: 36rpx 14rpx 8rpx;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  background: transparent;
  border: none;
  box-shadow: none;
  color: #4f321b;
}

.hero-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18rpx;
}

.hero-user {
  flex: 1;
  min-width: 0;
  display: flex;
  gap: 16rpx;
}

.avatar-shell {
  width: 84rpx;
  height: 84rpx;
}

.avatar {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #ff9a3d, #ff6a00);
  color: #fff;
  font-size: 26rpx;
  font-weight: 800;
  letter-spacing: 1rpx;
}

.hero-copy {
  flex: 1;
  min-width: 0;
  padding-top: 4rpx;
}

.nickname-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10rpx;
}

.nickname {
  font-size: 36rpx;
  font-weight: 800;
  letter-spacing: 0.4rpx;
  color: #4a2b13;
}

.level-pill {
  display: inline-flex;
  align-items: center;
  padding: 0;
  border-radius: 0;
  font-size: 20rpx;
  color: #c18347;
  background: transparent;
}

.hero-subline {
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #8d745d;
}

.hero-settings {
  flex-shrink: 0;
  padding: 4rpx 0 4rpx 12rpx;
  border-radius: 0;
  background: transparent;
  color: #6b5545;
  font-size: 22rpx;
  font-weight: 700;
  border: none;
}

.hero-summary {
  margin-top: 76rpx;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8rpx;
}

.summary-chip {
  min-width: 0;
  padding: 0;
  text-align: center;
  background: transparent;
  border: none;
  border-radius: 0;
}

.summary-chip-label {
  margin-top: 6rpx;
  font-size: 20rpx;
  line-height: 1.3;
  color: #8f765f;
}

.summary-chip-value {
  font-size: 34rpx;
  line-height: 1.1;
  font-weight: 800;
  color: #4a2b13;
}

.section-card {
  padding: 18rpx 16rpx;
  border-radius: 22rpx;
  background: linear-gradient(180deg, #ffffff 0%, #fffdf9 100%);
  border: 1rpx solid rgba(210, 186, 164, 0.18);
  box-shadow: none;
}

.orders-card {
  background: linear-gradient(180deg, #ffffff 0%, #fbf7f3 100%);
}

.tool-card,
.benefit-section {
  background: linear-gradient(180deg, #fbf9f7 0%, #f7f2ed 100%);
}

.slim-title {
  margin-bottom: 0;
}

.more-link {
  font-size: 24rpx;
  color: #9b7858;
  font-weight: 600;
}

.order-grid {
  margin-top: 18rpx;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10rpx;
}

.order-entry {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10rpx;
}

.order-icon {
  position: relative;
  width: 68rpx;
  height: 68rpx;
  border-radius: 22rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, #fff3e2, #ffe6cc);
  color: #b5692d;
  font-size: 28rpx;
  font-weight: 800;
  box-shadow: inset 0 1rpx 0 rgba(255, 255, 255, 0.8);
}

.order-badge {
  position: absolute;
  top: -4rpx;
  right: -8rpx;
  min-width: 30rpx;
  height: 30rpx;
  padding: 0 8rpx;
  border-radius: 999rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, #ff6d52, #ff4938);
  color: #fff;
  font-size: 18rpx;
  font-weight: 700;
  box-sizing: border-box;
  border: 2rpx solid #fff;
}

.order-title {
  font-size: 22rpx;
  color: #60422a;
  text-align: center;
  line-height: 1.3;
}

.tool-grid {
  margin-top: 16rpx;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10rpx;
}

.tool-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 14rpx 8rpx 12rpx;
  border-radius: 18rpx;
  background: #fffdf9;
  border: 1rpx solid rgba(198, 161, 124, 0.12);
}

.tool-icon {
  width: 32rpx;
  height: 32rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #695446;
  font-size: 18rpx;
  font-weight: 700;
  flex-shrink: 0;
  border: 1rpx solid rgba(105, 84, 70, 0.24);
}

.tool-title-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6rpx;
  width: 100%;
}

.tool-title {
  font-size: 24rpx;
  font-weight: 700;
  color: #4f321a;
  line-height: 1.2;
  text-align: center;
}

.tool-note {
  margin-top: 8rpx;
  min-height: 40rpx;
  font-size: 18rpx;
  line-height: 1.2;
  color: #9b8268;
  text-align: center;
}

.tool-preview {
  width: 100%;
  height: 88rpx;
  margin-top: 10rpx;
  border-radius: 18rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.tool-preview-mark {
  font-size: 44rpx;
  line-height: 1;
  font-weight: 800;
}

.tool-link {
  margin-top: 10rpx;
  font-size: 20rpx;
  line-height: 1.2;
  color: #ff7a00;
  font-weight: 700;
  text-align: center;
}

.preview-orange {
  background: linear-gradient(180deg, #fff1df 0%, #ffd4a6 100%);
}

.preview-orange .tool-preview-mark {
  color: #ff7a00;
}

.preview-gold {
  background: linear-gradient(180deg, #fff6e5 0%, #ffe39f 100%);
}

.preview-gold .tool-preview-mark {
  color: #f2a100;
}

.preview-mint {
  background: linear-gradient(180deg, #eef6ef 0%, #cfe7d1 100%);
}

.preview-mint .tool-preview-mark {
  color: #6a8d6d;
}

.preview-amber {
  background: linear-gradient(180deg, #fff3dc 0%, #ffd49d 100%);
}

.preview-amber .tool-preview-mark {
  color: #d78b1f;
}

.power-card {
  border: 1rpx solid rgba(255, 154, 106, 0.16);
  background: linear-gradient(180deg, #fff8f1 0%, #fff0e4 100%);
  box-shadow: 0 14rpx 28rpx rgba(175, 90, 39, 0.08);
}
.power-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16rpx;
}
.power-desc {
  margin-top: 8rpx;
  font-size: 22rpx;
  line-height: 1.45;
  color: #8f765f;
}
.power-chip {
  flex-shrink: 0;
  padding: 8rpx 14rpx;
  border-radius: 999rpx;
  background: rgba(255, 122, 0, 0.12);
  color: #ff6a00;
  font-size: 20rpx;
  font-weight: 800;
}
.power-meta {
  margin-top: 14rpx;
  padding-top: 14rpx;
  border-top: 1rpx solid rgba(255, 154, 106, 0.14);
  font-size: 22rpx;
  line-height: 1.45;
  color: #9b8268;
}

.benefit-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14rpx;
}

.benefit-card {
  padding: 18rpx;
  border-radius: 24rpx;
  box-sizing: border-box;
  min-height: 184rpx;
  color: #7d3120;
  box-shadow: 0 14rpx 28rpx rgba(175, 90, 39, 0.08);
}

.benefit-amount {
  font-size: 38rpx;
  line-height: 1.05;
  font-weight: 800;
}

.benefit-title {
  margin-top: 10rpx;
  font-size: 25rpx;
  font-weight: 700;
}

.benefit-btn {
  margin-top: 14rpx;
  width: 110rpx;
  height: 42rpx;
  line-height: 42rpx;
  text-align: center;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.92);
  color: #e4503d;
  font-size: 20rpx;
  font-weight: 700;
}

.benefit-orange {
  background: linear-gradient(180deg, #fff0e3 0%, #ffd9bd 100%);
}

.benefit-pink {
  background: linear-gradient(180deg, #ffe7ef 0%, #ffc7d9 100%);
}

.benefit-gold {
  background: linear-gradient(180deg, #fff1d3 0%, #ffd997 100%);
}

.benefit-red {
  background: linear-gradient(180deg, #ffe4e0 0%, #ffbeb5 100%);
}

.interactive {
  transition: transform 180ms ease, opacity 180ms ease;
}

.interactive:active {
  transform: scale(0.98);
  opacity: 0.92;
}
</style>
