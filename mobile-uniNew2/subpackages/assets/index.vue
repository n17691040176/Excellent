<template>
  <view class="assets-page">
    <!-- Header -->
    <view class="page-header">
      <AppBackButton @click="goBack" />
      <text class="header-title">我的资产</text>
      <view class="header-spacer" />
    </view>

    <!-- Loading -->
    <view v-if="pageLoading && !summary.total" class="loading-state">
      <view class="skeleton skeleton-hero" />
      <view v-for="i in 3" :key="i" class="skeleton skeleton-card" />
    </view>

    <!-- Error -->
    <view v-else-if="pageFailed && !summary.total" class="error-state">
      <text class="error-icon">⚠</text>
      <text class="error-text">资产数据加载失败</text>
      <view class="retry-btn" @click="reloadPage">点击重试</view>
    </view>

    <!-- Content -->
    <template v-else>
      <!-- Balance Card -->
      <view class="balance-card">
        <view class="balance-header">
          <text class="balance-label">账户余额</text>
          <view v-if="activeAssetType === 'balance'" class="withdraw-btn" @click="goWithdraw">提现</view>
        </view>
        <text class="balance-amount">¥{{ money(activeBalance) }}</text>
        <view class="balance-strip">
          <view class="strip-item">
            <text class="strip-label">可提现</text>
            <text class="strip-value">¥{{ money(activeAvailable) }}</text>
          </view>
          <view class="strip-divider" />
          <view class="strip-item">
            <text class="strip-label">累计提现</text>
            <text class="strip-value">¥{{ money(activeWithdrawn) }}</text>
          </view>
        </view>
      </view>

      <!-- Asset Tabs -->
      <view class="tabs-wrap">
        <view
          v-for="tab in assetTabs"
          :key="tab.value"
          class="tab-item"
          :class="{ active: activeAssetType === tab.value }"
          @click="changeAssetType(tab.value)"
        >
          {{ tab.label }}
        </view>
      </view>

      <!-- Detail Card -->
      <view class="detail-card">
        <!-- Stats Grid -->
        <view class="stats-grid">
          <view v-for="item in detailCards" :key="item.key" class="stat-cell">
            <text class="stat-label">{{ item.label }}</text>
            <text class="stat-value">{{ item.value }}</text>
          </view>
        </view>

        <!-- Loading More -->
        <view v-if="detailLoading && !detailRows.length" class="state-loading">
          <view class="loading-spinner" />
          <text>加载中...</text>
        </view>

        <!-- Error -->
        <view v-else-if="detailFailed && !detailRows.length" class="state-error">
          <text>明细加载失败</text>
          <text class="retry-link" @click="reloadAssetDetail">重试</text>
        </view>

        <!-- Empty -->
        <view v-else-if="!detailRows.length" class="state-empty">
          <view class="empty-icon">◇</view>
          <text class="empty-title">暂无明细记录</text>
        </view>

        <!-- List -->
        <view v-else class="detail-list">
          <view v-for="item in detailRows" :key="item.id" class="detail-item">
            <view class="detail-top">
              <view class="detail-info">
                <text class="detail-name">{{ item.name }}</text>
                <text class="detail-time">{{ item.time }}</text>
              </view>
              <text class="detail-amount" :class="item.type === 'in' ? 'amount-in' : 'amount-out'">
                {{ item.type === 'in' ? '+' : '-' }}{{ item.amountText }}
              </text>
            </view>
            <view class="detail-summary">{{ item.summaryText }}</view>
          </view>

          <view v-if="hasMore" class="load-more" @click="loadMoreDetail">
            {{ detailLoading ? '加载中...' : '加载更多' }}
          </view>
          <view v-else class="load-more done">— 没有更多了 —</view>
        </view>
      </view>

      <!-- Power Bank Section -->
      <view v-if="isPowerBankTab" class="power-card">
        <text class="section-title">充电宝设备</text>
        <view v-if="!powerBanks.length" class="state-empty">
          <view class="empty-icon">◇</view>
          <text class="empty-title">暂无绑定设备</text>
        </view>
        <view v-else class="power-list">
          <view v-for="item in powerBanks" :key="item.id" class="power-item">
            <view class="power-header">
              <text class="power-name">{{ item.device_name || item.device_code }}</text>
              <view class="power-status" :class="item.status === 'ACTIVE' ? 'status-active' : 'status-disabled'">
                {{ item.status === 'ACTIVE' ? '生效中' : '已停用' }}
              </view>
            </view>
            <view class="power-meta">
              <text>编号：{{ item.device_code }}</text>
              <text>累计收益 ¥{{ money(item.total_income_amount) }}</text>
            </view>
          </view>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onPullDownRefresh, onReachBottom, onShow } from '@dcloudio/uni-app';
import { assetApi } from '@/api/modules';
import { pickListPayload } from '@/utils/adapters';
import { formatDateTime as formatDetailTime } from '@/utils/format';

const DETAIL_PAGE_SIZE = 12;

const assetTabs = [
  { value: 'balance', label: '余额' },
  { value: 'voucher', label: '消费金' },
  { value: 'points', label: '积分' },
  { value: 'power_bank', label: '充电宝' }
];

const pageLoading = ref(false);
const pageFailed = ref(false);
const detailLoading = ref(false);
const detailFailed = ref(false);
const summary = ref({});
const powerBanks = ref([]);
const activeAssetType = ref('balance');
const assetDetail = ref({});
const detailRows = ref([]);
const detailPage = ref(1);
const detailHasMore = ref(true);

const isPowerBankTab = computed(() => activeAssetType.value === 'power_bank');

const activeBalance = computed(() => assetDetail.value.available_amount || 0);
const activeAvailable = computed(() => assetDetail.value.available_amount || 0);
const activeWithdrawn = computed(() => assetDetail.value.withdrawn_amount || 0);

const detailCards = computed(() => {
  if (isPowerBankTab.value) {
    const activeCount = powerBanks.value.filter((item) => item.status === 'ACTIVE').length;
    return [
      { key: 'active', label: '当前生效', value: `${activeCount} 台` },
      { key: 'total', label: '累计绑定', value: `${powerBanks.value.length} 台` }
    ];
  }

  const available = assetDetail.value.available_amount || 0;
  const consumed = assetDetail.value.consumed_amount || 0;

  return [
    { key: 'available', label: '当前可用', value: `¥${money(available)}` },
    { key: 'consumed', label: activeAssetType.value === 'balance' ? '累计提现' : '累计使用', value: `¥${money(consumed)}` }
  ];
});

const hasMore = computed(() => detailHasMore.value);

function money(value) {
  return Number(value || 0).toFixed(2);
}

function goBack() {
  uni.navigateBack();
}

function goWithdraw() {
  uni.navigateTo({ url: '/subpackages/assets/withdraw' });
}

function formatLedgerBizName(item) {
  const businessType = String(item.business_type || '').trim().toUpperCase();
  const names = {
    DAILY_SIGNIN: '每日签到奖励',
    POINTS_TRANSFER_OUT: '积分转出',
    POINTS_TRANSFER_IN: '积分转入',
    BALANCE_WITHDRAW_APPLY: '余额提现申请',
    BALANCE_WITHDRAW_APPROVE: '余额提现到账',
    BALANCE_WITHDRAW_REJECT: '余额提现退回',
    BALANCE_WITHDRAW_VOUCHER: '余额提现转消费金',
    POINTS_WITHDRAW_APPLY: '积分提现申请',
    POINTS_WITHDRAW_APPROVE: '积分提现到账',
    POINTS_WITHDRAW_REJECT: '积分提现退回',
    POWER_BANK_BIND: '充电宝绑定',
    POWER_BANK_ENABLE: '充电宝启用',
    POWER_BANK_DISABLE: '充电宝停用',
    POWER_BANK_DAILY_INCOME: '充电宝每日收益',
    POWER_BANK_REFERRAL_INCOME: '充电宝推荐收益',
    ORDER_DEDUCT: '下单抵扣',
    SELF_OPERATED_REWARD: '自营专区奖励'
  };
  return names[businessType] || item.biz_name || businessType || '资产变动';
}

function buildDetailRows(rows = []) {
  return rows.map((item, index) => {
    const amount = Number(item.amount ?? item.change_amount ?? 0);
    const type = amount >= 0 ? 'in' : 'out';
    return {
      id: item.id || `${activeAssetType.value}-${index}`,
      name: formatLedgerBizName(item),
      amountText: `¥${money(Math.abs(amount))}`,
      type,
      summaryText: item.remark || formatLedgerBizName(item),
      time: formatDetailTime(item.created_at || item.time)
    };
  });
}

async function loadOverview() {
  const [summaryRes, powerBanksRes] = await Promise.allSettled([
    assetApi.summary(),
    assetApi.powerBanks()
  ]);

  if (summaryRes.status === 'fulfilled') {
    summary.value = summaryRes.value || {};
  }
  if (powerBanksRes.status === 'fulfilled') {
    powerBanks.value = pickListPayload(powerBanksRes.value);
  }

  if (summaryRes.status === 'rejected' && powerBanksRes.status === 'rejected') {
    throw new Error('overview_load_failed');
  }
}

async function loadAssetDetail({ reset = false } = {}) {
  if (detailLoading.value && !reset) return;
  if (!reset && !detailHasMore.value) return;

  if (reset) {
    detailRows.value = [];
    detailPage.value = 1;
    detailHasMore.value = true;
  }
  detailLoading.value = true;
  detailFailed.value = false;
  const targetPage = reset ? 1 : detailPage.value;

  try {
    let detailRes = {};
    const ledgerParams = { page: targetPage, page_size: DETAIL_PAGE_SIZE };

    if (reset) {
      const [accountRes, ledgerRes] = await Promise.all([
        assetApi.detail(activeAssetType.value),
        assetApi.ledgers(activeAssetType.value, ledgerParams)
      ]);
      detailRes = accountRes || {};
      assetDetail.value = detailRes;
      const rows = buildDetailRows(pickListPayload(ledgerRes));
      detailRows.value = rows;
      detailHasMore.value = rows.length >= DETAIL_PAGE_SIZE;
      detailPage.value = targetPage + 1;
      return;
    }

    const ledgerRes = await assetApi.ledgers(activeAssetType.value, ledgerParams);
    detailRes = assetDetail.value || {};
    const rows = buildDetailRows(pickListPayload(ledgerRes));
    detailRows.value = [...detailRows.value, ...rows];
    detailHasMore.value = rows.length >= DETAIL_PAGE_SIZE;
    detailPage.value = targetPage + 1;
  } catch (error) {
    detailFailed.value = true;
  } finally {
    detailLoading.value = false;
  }
}

function reloadAssetDetail() {
  loadAssetDetail({ reset: true });
}

async function reloadPage() {
  pageLoading.value = true;
  pageFailed.value = false;
  try {
    await loadOverview();
    await reloadAssetDetail();
  } catch (error) {
    pageFailed.value = true;
  } finally {
    pageLoading.value = false;
  }
}

function changeAssetType(type) {
  if (activeAssetType.value === type) return;
  activeAssetType.value = type;
  reloadAssetDetail();
}

function loadMoreDetail() {
  loadAssetDetail();
}

onShow(() => {
  reloadPage();
});

onPullDownRefresh(async () => {
  await reloadPage();
  uni.stopPullDownRefresh();
});

onReachBottom(() => {
  loadMoreDetail();
});
</script>

<style scoped>
@import '@/styles/elegant.css';

.assets-page {
  min-height: 100vh;
  background: var(--bg);
  padding-bottom: 48rpx;
}

/* Header */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24rpx 32rpx;
  padding-top: calc(24rpx + env(safe-area-inset-top));
  background: var(--card);
  border-bottom: 1rpx solid var(--border-light);
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
}

.back-btn, .header-spacer {
  width: 64rpx;
  height: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32rpx;
  color: var(--text);
}

.header-title {
  font-size: 32rpx;
  font-weight: 700;
  color: var(--text);
}

/* Loading */
.loading-state {
  padding: 24rpx;
  margin-top: 120rpx;
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.skeleton {
  background: linear-gradient(90deg, var(--border-light) 25%, var(--bg) 50%, var(--border-light) 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s infinite;
  border-radius: var(--radius-xl);
}

.skeleton-hero {
  height: 320rpx;
}

.skeleton-card {
  height: 200rpx;
}

@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Error */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin-top: 200rpx;
  gap: 16rpx;
}

.error-icon {
  font-size: 80rpx;
  color: var(--error);
}

.error-text {
  font-size: 28rpx;
  color: var(--text-muted);
}

.retry-btn {
  padding: 16rpx 40rpx;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: white;
  font-size: 26rpx;
  font-weight: 600;
  border-radius: 40rpx;
  margin-top: 16rpx;
}

/* Balance Card */
.balance-card {
  margin: 120rpx 24rpx 24rpx;
  padding: 40rpx 32rpx;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  border-radius: var(--radius-xl);
  box-shadow: 0 12rpx 32rpx rgba(16, 185, 129, 0.25);
}

.balance-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16rpx;
}

.balance-label {
  font-size: 26rpx;
  color: rgba(255, 255, 255, 0.8);
}

.withdraw-btn {
  padding: 10rpx 24rpx;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  font-size: 24rpx;
  font-weight: 600;
  border-radius: 20rpx;
}

.balance-amount {
  font-size: 64rpx;
  font-weight: 800;
  color: white;
  display: block;
  margin-bottom: 24rpx;
}

.balance-strip {
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-lg);
  padding: 20rpx;
}

.strip-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6rpx;
}

.strip-divider {
  width: 1rpx;
  height: 40rpx;
  background: rgba(255, 255, 255, 0.2);
}

.strip-label {
  font-size: 20rpx;
  color: rgba(255, 255, 255, 0.7);
}

.strip-value {
  font-size: 26rpx;
  font-weight: 700;
  color: white;
}

/* Tabs */
.tabs-wrap {
  display: flex;
  gap: 12rpx;
  padding: 0 24rpx;
  margin-bottom: 24rpx;
}

.tab-item {
  padding: 12rpx 24rpx;
  background: var(--card);
  color: var(--text-muted);
  font-size: 26rpx;
  font-weight: 600;
  border-radius: 24rpx;
  border: 1rpx solid var(--border-light);
}

.tab-item.active {
  background: var(--primary);
  color: white;
  border-color: transparent;
}

/* Detail Card */
.detail-card {
  margin: 0 24rpx;
  padding: 32rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
  margin-bottom: 24rpx;
}

.stat-cell {
  padding: 20rpx;
  background: var(--bg);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.stat-label {
  font-size: 20rpx;
  color: var(--text-muted);
}

.stat-value {
  font-size: 28rpx;
  font-weight: 700;
  color: var(--text);
}

/* States */
.state-loading, .state-error, .state-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60rpx 0;
  gap: 12rpx;
}

.loading-spinner {
  width: 40rpx;
  height: 40rpx;
  border: 3rpx solid var(--border-light);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.state-loading {
  font-size: 24rpx;
  color: var(--text-muted);
}

.state-error {
  font-size: 24rpx;
  color: var(--error);
}

.retry-link {
  color: var(--primary);
  margin-top: 8rpx;
}

.empty-icon {
  font-size: 80rpx;
  color: var(--border);
  margin-bottom: 16rpx;
}

.empty-title {
  font-size: 28rpx;
  color: var(--text-muted);
}

/* Detail List */
.detail-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.detail-item {
  padding: 20rpx;
  background: var(--bg);
  border-radius: var(--radius-lg);
}

.detail-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 8rpx;
}

.detail-info {
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.detail-name {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--text);
}

.detail-time {
  font-size: 20rpx;
  color: var(--text-muted);
}

.detail-amount {
  font-size: 28rpx;
  font-weight: 700;
}

.amount-in {
  color: var(--success);
}

.amount-out {
  color: var(--text-muted);
}

.detail-summary {
  font-size: 22rpx;
  color: var(--text-muted);
}

.load-more {
  text-align: center;
  padding: 24rpx;
  font-size: 24rpx;
  color: var(--text-muted);
}

.load-more.done {
  color: var(--border);
}

/* Power Card */
.power-card {
  margin: 24rpx;
  padding: 32rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
}

.section-title {
  font-size: 30rpx;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 24rpx;
}

.power-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.power-item {
  padding: 20rpx;
  background: var(--bg);
  border-radius: var(--radius-lg);
}

.power-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12rpx;
}

.power-name {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--text);
}

.power-status {
  padding: 6rpx 16rpx;
  font-size: 22rpx;
  font-weight: 600;
  border-radius: 16rpx;
}

.status-active {
  background: var(--success-bg);
  color: var(--success);
}

.status-disabled {
  background: var(--bg);
  color: var(--text-muted);
}

.power-meta {
  display: flex;
  flex-direction: column;
  gap: 6rpx;
  font-size: 22rpx;
  color: var(--text-muted);
}
</style>
