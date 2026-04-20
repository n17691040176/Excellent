<template>
  <view class="container profile-page">
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
            <view class="hero-tip">余额、消费金、积分和充电宝，都统一收进我的资产。</view>
          </view>
        </view>
        <view class="hero-settings interactive" @click="go('/subpackages/profile/settings')">设置</view>
      </view>

      <view class="hero-summary mt-20">
        <view
          v-for="item in platformCurrencies"
          :key="item.label"
          class="summary-chip interactive"
          @click="handleAction(item)"
        >
          <view class="summary-chip-label">{{ item.label }}</view>
          <view class="summary-chip-value">{{ item.value }}</view>
          <view class="summary-chip-meta">{{ item.meta }}</view>
        </view>
      </view>

      <view class="notice-bar">
        <view class="notice-left">
          <view class="notice-badge">荐</view>
          <text class="notice-text">{{ noticeText }}</text>
        </view>
        <view class="notice-btn interactive" @click="go(noticePath)">{{ noticeActionText }}</view>
      </view>
    </view>

    <view class="card orders-card mt-20">
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

    <view class="card tool-card mt-20">
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
          <view class="tool-main">
            <view class="tool-icon" :class="item.iconClass">{{ item.icon }}</view>
            <view class="tool-copy">
              <view class="tool-title-row">
                <view class="tool-title">{{ item.title }}</view>
                <view class="tool-chip">{{ item.chip }}</view>
              </view>
              <view class="tool-desc">{{ item.desc }}</view>
            </view>
          </view>
          <view class="tool-foot">
            <view class="tool-note">{{ item.note }}</view>
            <view class="tool-link">{{ item.actionText }}</view>
          </view>
        </view>
      </view>
    </view>

    <view class="mt-24">
      <view class="row-between">
        <view class="section-title slim-title">
          <text class="section-accent">超级 88</text>
          <text> 成长权益</text>
        </view>
        <view class="more-link interactive" @click="go('/subpackages/invite/index')">更多</view>
      </view>

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
          <view class="benefit-desc">{{ item.desc }}</view>
          <view class="benefit-btn">去查看</view>
        </view>
      </view>
    </view>

    <view class="entry-strip mt-24">
      <view
        v-for="item in footerEntries"
        :key="item.title"
        class="entry-bubble interactive"
        @click="handleAction(item)"
      >
        <view class="entry-icon" :class="item.iconClass">{{ item.icon }}</view>
        <view class="entry-text">{{ item.title }}</view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app';
import { assetApi, commissionApi, userApi } from '@/api/modules';
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
    desc: '查看包裹运输与签收进度',
    icon: '递',
    iconClass: 'icon-orange',
    chip: '物流',
    note: '已支付订单可查',
    actionText: '去查看',
    path: '/subpackages/profile/shipping'
  },
  {
    title: '收藏',
    desc: '保存心仪商品，方便随时回看',
    icon: '藏',
    iconClass: 'icon-gold',
    chip: '回看',
    note: '常看的商品都在这里',
    actionText: '去查看',
    path: '/subpackages/profile/favorites'
  },
  {
    title: '购物车',
    desc: '统一管理待下单商品',
    icon: '车',
    iconClass: 'icon-blue',
    chip: '下单',
    note: '支持直接前往结算',
    actionText: '去下单',
    path: '/subpackages/profile/cart'
  },
  {
    title: '足迹',
    desc: '回到最近浏览过的商品',
    icon: '迹',
    iconClass: 'icon-rose',
    chip: '最近',
    note: '继续浏览感兴趣商品',
    actionText: '继续看',
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

const footerEntries = computed(() => {
  const entries = [
    { title: '我的资产', icon: '资', iconClass: 'icon-green', path: buildAssetIndexPath() }
  ];

  if (isLegacyUser.value) {
    entries.push({ title: '佣金', icon: '佣', iconClass: 'icon-orange', path: '/subpackages/commission/index' });
  }

  entries.push({ title: '签到', icon: '签', iconClass: 'icon-red', action: 'toast', name: '每日签到' });

  if (isLegacyUser.value) {
    entries.push({ title: '团队', icon: '团', iconClass: 'icon-purple', path: '/subpackages/team/index' });
  }

  entries.push({ title: '邀请', icon: '邀', iconClass: 'icon-pink', path: '/subpackages/invite/index' });
  return entries;
});

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
    meta: '去提现 · 查看明细',
    path: buildBalanceWithdrawPath()
  },
  {
    label: '消费金',
    value: formatAmount(assetSummary.value.VOUCHER ?? assetSummary.value.voucher),
    meta: '商城抵扣 · 查看明细',
    path: buildAssetIndexPath('voucher')
  },
  {
    label: '积分',
    value: formatAmount(assetSummary.value.POINTS ?? assetSummary.value.points),
    meta: '补贴转赠 · 查看明细',
    path: buildAssetIndexPath('points')
  },
  {
    label: '充电宝',
    value: `${formatCount(assetSummary.value.POWER_BANK ?? assetSummary.value.power_bank ?? assetSummary.value.power_bank_count)}台`,
    meta: '已绑定设备 · 查看明细',
    path: buildAssetIndexPath('power_bank')
  }
]));

const noticePath = computed(() => (inviteCode.value ? '/subpackages/invite/index' : '/pages/packages/list'));
const noticeText = computed(() => (
  inviteCode.value
    ? `邀请码 ${inviteCode.value} 已生成，邀请好友可解锁更多成长权益。`
    : '成长权益持续更新，限定商品与服务专区可用。'
));
const noticeActionText = computed(() => (inviteCode.value ? '去邀请' : '去使用'));

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
  padding-bottom: 44rpx;
}

.hero-card {
  border-radius: 32rpx;
  padding: 26rpx;
  background:
    radial-gradient(circle at 12% 10%, rgba(255, 255, 255, 0.34), transparent 26%),
    radial-gradient(circle at 100% 0%, rgba(255, 224, 187, 0.42), transparent 28%),
    linear-gradient(180deg, #f6c389 0%, #ecab68 42%, #e4964d 100%);
  box-shadow: 0 28rpx 48rpx rgba(170, 97, 28, 0.2);
  color: #fff;
}

.hero-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16rpx;
}

.hero-user {
  flex: 1;
  min-width: 0;
  display: flex;
  gap: 16rpx;
}

.avatar-shell {
  width: 98rpx;
  height: 98rpx;
  border-radius: 50%;
  padding: 4rpx;
  box-sizing: border-box;
  background: rgba(255, 255, 255, 0.28);
  border: 1rpx solid rgba(255, 255, 255, 0.5);
}

.avatar {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.8), rgba(255, 240, 222, 0.92));
  color: #9d5c1d;
  font-size: 28rpx;
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
}

.level-pill {
  display: inline-flex;
  align-items: center;
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  font-size: 20rpx;
  color: #9a4f13;
  background: rgba(255, 245, 231, 0.92);
}

.hero-subline {
  margin-top: 8rpx;
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.92);
}

.hero-tip {
  margin-top: 8rpx;
  font-size: 22rpx;
  color: rgba(255, 247, 239, 0.9);
}

.hero-settings {
  flex-shrink: 0;
  padding: 0 20rpx;
  height: 58rpx;
  line-height: 58rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.18);
  border: 1rpx solid rgba(255, 255, 255, 0.32);
  font-size: 22rpx;
  color: #fff;
}

.hero-summary {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12rpx;
}

.summary-chip {
  border-radius: 22rpx;
  padding: 18rpx 16rpx;
  box-sizing: border-box;
  background: rgba(255, 251, 247, 0.18);
  border: 1rpx solid rgba(255, 255, 255, 0.3);
}

.summary-chip-label {
  font-size: 22rpx;
  color: rgba(255, 244, 236, 0.9);
}

.summary-chip-value {
  margin-top: 10rpx;
  font-size: 28rpx;
  line-height: 1.1;
  font-weight: 800;
  color: #fff;
}

.summary-chip-meta {
  margin-top: 8rpx;
  font-size: 19rpx;
  color: rgba(255, 248, 243, 0.76);
}

.notice-bar {
  margin-top: 16rpx;
  border-radius: 20rpx;
  padding: 14rpx 16rpx;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12rpx;
  background: linear-gradient(180deg, rgba(255, 241, 228, 0.92), rgba(255, 231, 206, 0.92));
  color: #9e5320;
}

.notice-left {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10rpx;
}

.notice-badge {
  width: 34rpx;
  height: 34rpx;
  flex-shrink: 0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, #ff6f53, #ff4233);
  color: #fff;
  font-size: 20rpx;
  font-weight: 700;
}

.notice-text {
  font-size: 22rpx;
  line-height: 1.4;
  color: #9d5b2a;
}

.notice-btn {
  flex-shrink: 0;
  padding: 10rpx 18rpx;
  border-radius: 999rpx;
  background: linear-gradient(120deg, #ff6b33, #ff844b);
  color: #fff;
  font-size: 22rpx;
  font-weight: 700;
}

.orders-card,
.tool-card {
  border-radius: 28rpx;
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
  margin-top: 18rpx;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14rpx;
}

.tool-item {
  padding: 18rpx;
  border-radius: 22rpx;
  background: #fffdf9;
  border: 1rpx solid rgba(198, 161, 124, 0.16);
  box-shadow: 0 10rpx 22rpx rgba(146, 103, 63, 0.06);
}

.tool-main {
  display: flex;
  align-items: center;
  gap: 14rpx;
}

.tool-icon {
  width: 60rpx;
  height: 60rpx;
  border-radius: 18rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 24rpx;
  font-weight: 800;
  flex-shrink: 0;
}

.tool-copy {
  flex: 1;
  min-width: 0;
}

.tool-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10rpx;
}

.tool-title {
  font-size: 26rpx;
  font-weight: 700;
  color: #4f321a;
}

.tool-chip {
  flex-shrink: 0;
  padding: 4rpx 12rpx;
  border-radius: 999rpx;
  background: #f7efe5;
  color: #9a6a3d;
  font-size: 18rpx;
  font-weight: 700;
}

.tool-desc {
  margin-top: 8rpx;
  font-size: 22rpx;
  line-height: 1.4;
  color: #8b7158;
}

.tool-foot {
  margin-top: 16rpx;
  padding-top: 14rpx;
  border-top: 1rpx solid rgba(198, 161, 124, 0.12);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12rpx;
}

.tool-note {
  flex: 1;
  min-width: 0;
  font-size: 20rpx;
  color: #9b8268;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tool-link {
  flex-shrink: 0;
  font-size: 20rpx;
  color: #c96a14;
  font-weight: 700;
}

.section-accent {
  color: #ff4f60;
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

.benefit-desc {
  margin-top: 8rpx;
  font-size: 21rpx;
  line-height: 1.45;
  color: rgba(115, 48, 30, 0.82);
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

.entry-strip {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12rpx;
}

.entry-bubble {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10rpx;
}

.entry-icon {
  width: 76rpx;
  height: 76rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 26rpx;
  font-weight: 800;
  box-shadow: 0 12rpx 20rpx rgba(161, 89, 26, 0.12);
}

.entry-text {
  font-size: 22rpx;
  color: #6a4a31;
}

.icon-orange { background: linear-gradient(180deg, #ff9942, #ff7124); }
.icon-gold { background: linear-gradient(180deg, #f7b84a, #eb8e14); }
.icon-blue { background: linear-gradient(180deg, #60a3ff, #2d73f5); }
.icon-rose { background: linear-gradient(180deg, #ff8c78, #ff5a4b); }
.icon-green { background: linear-gradient(180deg, #4fcf88, #18a85b); }
.icon-red { background: linear-gradient(180deg, #ff7d73, #ff4d43); }
.icon-purple { background: linear-gradient(180deg, #9b86ff, #7158f4); }
.icon-pink { background: linear-gradient(180deg, #ff9dc6, #ff5da5); }

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
