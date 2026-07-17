<template>
  <view class="withdraw-page">
    <!-- Header -->
    <view class="page-header">
      <view class="back-btn" @click="goBack">←</view>
      <text class="header-title">余额提现</text>
      <view class="header-spacer" />
    </view>

    <!-- Loading -->
    <view v-if="pageLoading && !assetDetail.available_amount" class="loading-state">
      <view class="skeleton skeleton-card" />
    </view>

    <!-- Error -->
    <view v-else-if="pageFailed && !assetDetail.available_amount" class="error-state">
      <text class="error-icon">⚠</text>
      <text class="error-text">数据加载失败</text>
      <view class="retry-btn" @click="reloadPage">点击重试</view>
    </view>

    <!-- Content -->
    <template v-else>
      <!-- Balance Card -->
      <view class="balance-card">
        <text class="balance-label">可提现金额</text>
        <text class="balance-amount">¥{{ money(assetDetail.available_amount) }}</text>
        <view class="balance-strip">
          <view class="strip-item">
            <text class="strip-label">累计提现</text>
            <text class="strip-value">¥{{ money(assetDetail.withdrawn_amount) }}</text>
          </view>
        </view>
      </view>

      <!-- Withdraw Form -->
      <view class="form-card">
        <text class="form-title">申请提现</text>
        <view class="input-wrap">
          <text class="input-prefix">¥</text>
          <input
            v-model="withdrawAmount"
            class="amount-input"
            type="digit"
            placeholder="0.00"
            placeholder-class="placeholder"
          />
          <view class="input-action" @click="fillAll">全部</view>
        </view>
        <view class="preview-row">
          <view class="preview-item">
            <text class="preview-label">到账</text>
            <text class="preview-value">¥{{ withdrawPreview.netAmount }}</text>
          </view>
          <view class="preview-item">
            <text class="preview-label">转消费金</text>
            <text class="preview-value warm">¥{{ withdrawPreview.voucherAmount }}</text>
          </view>
        </view>
        <view class="submit-btn" :class="{ disabled: submitting }" @click="submitWithdraw">
          {{ submitting ? '提交中...' : '申请提现' }}
        </view>
      </view>

      <!-- Rules -->
      <view class="rules-card">
        <text class="section-title">提现说明</text>
        <view class="rules-list">
          <view v-for="(rule, index) in rules" :key="index" class="rule-item">
            <view class="rule-index">{{ String(index + 1).padStart(2, '0') }}</view>
            <view class="rule-content">
              <text class="rule-title">{{ rule.title }}</text>
              <text class="rule-desc">{{ rule.desc }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- Records -->
      <view class="records-card">
        <view class="records-header">
          <text class="section-title">提现记录</text>
          <text class="records-count">{{ filteredRecords.length }} 笔</text>
        </view>

        <!-- Tabs -->
        <view class="tabs-wrap">
          <view
            v-for="tab in recordTabs"
            :key="tab.value"
            class="tab-item"
            :class="{ active: activeRecordTab === tab.value }"
            @click="changeRecordTab(tab.value)"
          >
            {{ tab.label }}
          </view>
        </view>

        <!-- Loading -->
        <view v-if="recordsLoading && !filteredRecords.length" class="state-loading">
          <view class="loading-spinner" />
          <text>加载中...</text>
        </view>

        <!-- Empty -->
        <view v-else-if="!filteredRecords.length" class="state-empty">
          <view class="empty-icon">◇</view>
          <text class="empty-title">暂无提现记录</text>
        </view>

        <!-- List -->
        <view v-else class="records-list">
          <view v-for="item in filteredRecords" :key="item.id" class="record-item">
            <view class="record-header">
              <text class="record-title">提现 ¥{{ money(item.amount) }}</text>
              <view class="record-status" :class="getStatusClass(item.status)">
                {{ getStatusLabel(item.status) }}
              </view>
            </view>
            <view class="record-detail">
              到账 ¥{{ money(item.net_amount) }} · 转消费金 ¥{{ money(item.voucher_amount) }}
            </view>
            <view class="record-time">{{ formatTime(item.created_at) }}</view>
            <view v-if="item.remark" class="record-remark">{{ item.remark }}</view>
          </view>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app';
import { assetApi, commissionApi } from '@/api/modules';
import { pickListPayload } from '@/utils/adapters';

const BALANCE_WITHDRAW_VOUCHER_RATE = 0.2;

const pageLoading = ref(false);
const pageFailed = ref(false);
const recordsLoading = ref(false);
const submitting = ref(false);
const assetDetail = ref({});
const withdrawRows = ref([]);
const withdrawAmount = ref('');
const activeRecordTab = ref('all');

const recordTabs = [
  { value: 'all', label: '全部' },
  { value: 'pending', label: '待审核' },
  { value: 'approved', label: '审核通过' },
  { value: 'paid', label: '已打款' },
  { value: 'rejected', label: '已驳回' }
];

const rules = [
  { title: '提现比例', desc: '审核通过后，80% 提现到账，20% 自动转入消费金' },
  { title: '审核状态', desc: '待审核 → 审核通过 → 已打款；驳回则金额退回' },
  { title: '到账方式', desc: '审核通过后由财务或系统完成打款处理' }
];

const balanceWithdrawRows = computed(() =>
  withdrawRows.value.filter((item) => item.withdraw_type === 'BALANCE')
);

const filteredRecords = computed(() => {
  if (activeRecordTab.value === 'all') return balanceWithdrawRows.value;
  return balanceWithdrawRows.value.filter((item) => normalizeStatus(item.status) === activeRecordTab.value);
});

const withdrawPreview = computed(() => {
  const gross = Math.max(0, Number(withdrawAmount.value || 0));
  const voucherAmount = gross * BALANCE_WITHDRAW_VOUCHER_RATE;
  const netAmount = Math.max(0, gross - voucherAmount);
  return {
    netAmount: money(netAmount),
    voucherAmount: money(voucherAmount)
  };
});

function money(value) {
  return Number(value || 0).toFixed(2);
}

function normalizeStatus(status) {
  return String(status || '').trim().toLowerCase();
}

function getStatusLabel(status) {
  return {
    pending: '待审核',
    approved: '审核通过',
    rejected: '已驳回',
    paid: '已打款'
  }[normalizeStatus(status)] || status;
}

function getStatusClass(status) {
  return {
    pending: 'status-pending',
    approved: 'status-approved',
    rejected: 'status-rejected',
    paid: 'status-paid'
  }[normalizeStatus(status)] || 'status-pending';
}

function formatTime(value) {
  if (!value) return '--';
  return String(value).replace('T', ' ').slice(0, 16);
}

function goBack() {
  uni.navigateBack();
}

function fillAll() {
  withdrawAmount.value = money(assetDetail.value.available_amount);
}

function changeRecordTab(tab) {
  activeRecordTab.value = tab;
}

async function loadPageData() {
  recordsLoading.value = true;
  const [detailRes, withdrawsRes] = await Promise.allSettled([
    assetApi.detail('balance'),
    commissionApi.withdraws({})
  ]);

  if (detailRes.status === 'fulfilled') {
    assetDetail.value = detailRes.value || {};
  }
  if (withdrawsRes.status === 'fulfilled') {
    withdrawRows.value = pickListPayload(withdrawsRes.value);
  }

  if (detailRes.status === 'rejected' && withdrawsRes.status === 'rejected') {
    throw new Error('balance_withdraw_load_failed');
  }
  recordsLoading.value = false;
}

async function reloadPage() {
  pageLoading.value = true;
  pageFailed.value = false;
  try {
    await loadPageData();
  } catch (error) {
    pageFailed.value = true;
  } finally {
    pageLoading.value = false;
  }
}

async function submitWithdraw() {
  if (submitting.value) return;

  const amount = Number(withdrawAmount.value || 0);
  const available = Number(assetDetail.value.available_amount || 0);

  if (amount <= 0) {
    uni.showToast({ title: '请输入正确的提现金额', icon: 'none' });
    return;
  }
  if (amount > available) {
    uni.showToast({ title: '提现金额不能超过可用余额', icon: 'none' });
    return;
  }

  const confirmed = await new Promise((resolve) => {
    uni.showModal({
      title: '确认提现',
      content: `本次提现 ¥${money(amount)}，预计到账 ¥${withdrawPreview.value.netAmount}，转消费金 ¥${withdrawPreview.value.voucherAmount}。`,
      success: (res) => resolve(Boolean(res.confirm)),
      fail: () => resolve(false)
    });
  });
  if (!confirmed) return;

  submitting.value = true;
  try {
    await commissionApi.createWithdraw({
      withdraw_type: 'BALANCE',
      amount
    });
    uni.showToast({ title: '提现申请已提交', icon: 'none' });
    withdrawAmount.value = '';
    await loadPageData();
  } catch (error) {
    uni.showToast({ title: '提交失败，请重试', icon: 'none' });
  } finally {
    submitting.value = false;
  }
}

onShow(() => {
  reloadPage();
});

onPullDownRefresh(async () => {
  await reloadPage();
  uni.stopPullDownRefresh();
});
</script>

<style scoped>
@import '@/styles/elegant.css';

.withdraw-page {
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
}

.skeleton {
  background: linear-gradient(90deg, var(--border-light) 25%, var(--bg) 50%, var(--border-light) 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s infinite;
  border-radius: var(--radius-xl);
}

.skeleton-card {
  height: 400rpx;
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

.balance-label {
  font-size: 26rpx;
  color: rgba(255, 255, 255, 0.8);
  display: block;
  margin-bottom: 12rpx;
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

.strip-label {
  font-size: 20rpx;
  color: rgba(255, 255, 255, 0.7);
}

.strip-value {
  font-size: 26rpx;
  font-weight: 700;
  color: white;
}

/* Form Card */
.form-card {
  margin: 0 24rpx 24rpx;
  padding: 32rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
}

.form-title {
  font-size: 30rpx;
  font-weight: 700;
  color: var(--text);
  display: block;
  margin-bottom: 24rpx;
}

.input-wrap {
  display: flex;
  align-items: center;
  gap: 12rpx;
  padding: 0 24rpx;
  height: 100rpx;
  background: var(--bg);
  border-radius: var(--radius-lg);
  margin-bottom: 20rpx;
}

.input-prefix {
  font-size: 40rpx;
  font-weight: 700;
  color: var(--text);
}

.amount-input {
  flex: 1;
  font-size: 40rpx;
  font-weight: 700;
  color: var(--text);
}

.placeholder {
  color: var(--border);
}

.input-action {
  padding: 12rpx 24rpx;
  background: var(--primary);
  color: white;
  font-size: 24rpx;
  font-weight: 600;
  border-radius: 16rpx;
}

.preview-row {
  display: flex;
  gap: 16rpx;
  margin-bottom: 24rpx;
}

.preview-item {
  flex: 1;
  padding: 16rpx;
  background: var(--bg);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.preview-label {
  font-size: 20rpx;
  color: var(--text-muted);
}

.preview-value {
  font-size: 28rpx;
  font-weight: 700;
  color: var(--text);
}

.preview-value.warm {
  color: var(--secondary);
}

.submit-btn {
  padding: 28rpx;
  text-align: center;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: white;
  font-size: 30rpx;
  font-weight: 700;
  border-radius: var(--radius-lg);
}

.submit-btn.disabled {
  opacity: 0.6;
}

/* Rules Card */
.rules-card {
  margin: 0 24rpx 24rpx;
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

.rules-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.rule-item {
  display: flex;
  gap: 16rpx;
  padding: 20rpx;
  background: var(--bg);
  border-radius: var(--radius-lg);
}

.rule-index {
  width: 48rpx;
  height: 48rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-bg);
  color: var(--primary);
  font-size: 22rpx;
  font-weight: 700;
  border-radius: var(--radius-md);
  flex-shrink: 0;
}

.rule-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.rule-title {
  font-size: 26rpx;
  font-weight: 600;
  color: var(--text);
}

.rule-desc {
  font-size: 22rpx;
  color: var(--text-muted);
  line-height: 1.5;
}

/* Records Card */
.records-card {
  margin: 0 24rpx;
  padding: 32rpx;
  background: var(--card);
  border-radius: var(--radius-xl);
}

.records-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24rpx;
}

.records-count {
  font-size: 24rpx;
  color: var(--text-muted);
}

/* Tabs */
.tabs-wrap {
  display: flex;
  gap: 8rpx;
  margin-bottom: 24rpx;
  overflow-x: auto;
}

.tab-item {
  padding: 10rpx 18rpx;
  background: var(--bg);
  color: var(--text-muted);
  font-size: 22rpx;
  font-weight: 600;
  border-radius: 16rpx;
  white-space: nowrap;
}

.tab-item.active {
  background: var(--primary);
  color: white;
}

/* States */
.state-loading, .state-empty {
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

.empty-icon {
  font-size: 80rpx;
  color: var(--border);
  margin-bottom: 16rpx;
}

.empty-title {
  font-size: 28rpx;
  color: var(--text-muted);
}

/* Records List */
.records-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.record-item {
  padding: 20rpx;
  background: var(--bg);
  border-radius: var(--radius-lg);
}

.record-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12rpx;
}

.record-title {
  font-size: 28rpx;
  font-weight: 700;
  color: var(--text);
}

.record-status {
  padding: 6rpx 16rpx;
  font-size: 22rpx;
  font-weight: 600;
  border-radius: 16rpx;
}

.status-pending {
  background: var(--secondary-bg);
  color: var(--secondary);
}

.status-approved, .status-rejected {
  background: var(--primary-bg);
  color: var(--primary);
}

.status-paid {
  background: var(--success-bg);
  color: var(--success);
}

.record-detail {
  font-size: 22rpx;
  color: var(--text-muted);
  margin-bottom: 8rpx;
}

.record-time {
  font-size: 20rpx;
  color: var(--text-muted);
}

.record-remark {
  margin-top: 8rpx;
  font-size: 20rpx;
  color: var(--error);
  padding: 12rpx;
  background: var(--bg);
  border-radius: var(--radius-md);
}
</style>
