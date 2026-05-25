<template>
  <view class="container balance-withdraw-page">
    <StateView v-if="pageLoading" title="加载中..." custom-class="mt-24" />
    <StateView
      v-else-if="pageFailed"
      title="余额提现数据加载失败"
      :show-retry="true"
      custom-class="mt-24"
      @retry="reloadPage"
    />

    <template v-else>
      <view class="card summary-card">
        <view class="summary-tag">余额提现</view>
        <view class="row-between summary-head mt-12">
          <view>
            <view class="section-title slim-title">余额提现</view>
            <view class="muted mt-8">审核通过后，80% 提现到账，20% 自动转入消费金。</view>
          </view>
          <view class="summary-link interactive" @click="goBalanceDetail">余额明细</view>
        </view>

        <view class="stat-grid mt-20">
          <view class="stat-item">
            <view class="stat-label">可提现</view>
            <view class="stat-value">¥{{ money(assetDetail.available_amount) }}</view>
          </view>
          <view class="stat-item">
            <view class="stat-label">累计提现</view>
            <view class="stat-value">¥{{ money(assetDetail.withdrawn_amount) }}</view>
          </view>
        </view>

        <view class="withdraw-input-wrap mt-20">
          <input
            v-model="withdrawAmount"
            class="withdraw-input"
            type="digit"
            placeholder="请输入提现金额"
          />
          <view class="withdraw-shortcut interactive" @click="fillAllWithdraw">全部提现</view>
        </view>

        <view class="withdraw-preview mt-12">
          <view class="preview-item">
            <text class="preview-label">到账</text>
            <text class="preview-value">¥{{ withdrawPreview.netAmount }}</text>
          </view>
          <view class="preview-item">
            <text class="preview-label">转消费金</text>
            <text class="preview-value preview-value-warm">¥{{ withdrawPreview.voucherAmount }}</text>
          </view>
        </view>

        <button class="btn btn-primary mt-16" :loading="withdrawSubmitting" @click="submitBalanceWithdraw">
          申请提现
        </button>
      </view>

      <view class="card mt-24 rule-card">
        <view class="row-between section-row">
          <view>
            <view class="section-title slim-title">提现说明</view>
            <view class="muted">提现规则、审核状态和到账方式统一在这里说明</view>
          </view>
          <view class="badge badge-blue">规则</view>
        </view>

        <view class="tips-list">
          <view v-for="item in withdrawTips" :key="item.title" class="tip-item">
            <view class="tip-index">{{ item.index }}</view>
            <view class="tip-content">
              <view class="tip-title">{{ item.title }}</view>
              <view class="tip-desc">{{ item.desc }}</view>
            </view>
          </view>
        </view>
      </view>

      <view class="card mt-24 record-card">
        <view class="row-between section-row">
          <view>
            <view class="section-title slim-title">提现记录</view>
            <view class="muted">展示最近的余额提现申请、到账金额和转消费金金额</view>
          </view>
          <view class="badge badge-orange">{{ filteredWithdrawRows.length }} 笔</view>
        </view>

        <FilterChips
          :items="recordRangeOptions"
          :model-value="activeRecordRange"
          @change="changeRecordRange"
        />

        <FilterChips
          class="mt-12"
          :items="recordTabs"
          :model-value="activeRecordTab"
          @change="changeRecordTab"
        />

        <StateView
          v-if="recordsLoading"
          title="提现记录加载中..."
          custom-class="asset-empty"
        />
        <StateView
          v-else-if="recordsFailed"
          title="提现记录加载失败"
          :show-retry="true"
          custom-class="asset-empty"
          @retry="reloadPage"
        />
        <StateView
          v-else-if="!filteredWithdrawRows.length"
          title="暂时还没有提现记录"
          description="提交余额提现申请后，这里会展示审核进度、到账金额和转消费金金额。"
          custom-class="asset-empty"
        />

        <view v-else class="withdraw-record-list mt-16">
          <view v-for="item in filteredWithdrawRows" :key="item.id" class="withdraw-record-item">
            <view class="row-between">
              <view class="withdraw-record-title">提现 ¥{{ money(item.amount) }}</view>
              <view class="badge" :class="withdrawStatusClass(item.status)">{{ withdrawStatusLabel(item.status) }}</view>
            </view>
            <view class="withdraw-record-line withdraw-record-copy">
              <text>提现单号 {{ item.source_no || `WD-${item.id}` }}</text>
              <view class="copy-link interactive" @click.stop="copyText(item.source_no || `WD-${item.id}`, '提现单号')">复制</view>
            </view>
            <view class="withdraw-record-line">到账 ¥{{ money(item.net_amount) }}，转消费金 ¥{{ money(item.voucher_amount) }}</view>
            <view v-if="item.remark" class="withdraw-record-line">{{ item.remark }}</view>
            <view class="withdraw-record-time">{{ formatDetailTime(item.created_at || item.time) }}</view>
            <view class="withdraw-record-action">
              <view class="copy-link interactive" @click.stop="toggleRecordExpand(item.id)">
                {{ isRecordExpanded(item.id) ? '收起详情' : '展开详情' }}
              </view>
            </view>
            <DetailInfoPanel
              v-if="isRecordExpanded(item.id)"
              :items="buildWithdrawDetailItems(item)"
              :note="withdrawStatusHint(item)"
            />
          </view>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onLoad, onPullDownRefresh, onShow } from '@dcloudio/uni-app';

import DetailInfoPanel from '@/components/DetailInfoPanel.vue';
import FilterChips from '@/components/FilterChips.vue';
import StateView from '@/components/StateView.vue';
import { assetApi, commissionApi } from '@/api/modules';
import { pickListPayload } from '@/utils/adapters';

const BALANCE_WITHDRAW_VOUCHER_RATE = 0.2;
const WITHDRAW_PAGE_CACHE_KEY = 'asset_withdraw_view_state';
const recordRangeOptions = [
  { value: 7, label: '最近7天' },
  { value: 30, label: '最近30天' },
  { value: 0, label: '全部' }
];

const pageLoading = ref(false);
const pageFailed = ref(false);
const withdrawSubmitting = ref(false);
const recordsLoading = ref(false);
const recordsFailed = ref(false);
const assetDetail = ref({});
const withdrawRows = ref([]);
const withdrawAmount = ref('');
const expandedRecordIds = ref([]);
const activeRecordTab = ref('all');
const activeRecordRange = ref(recordRangeOptions[0].value);
const assetDetailRange = ref(recordRangeOptions[0].value);
const withdrawTips = [
  {
    index: '01',
    title: '提现比例',
    desc: '每笔余额提现审核通过后，80% 按提现到账处理，20% 自动转入消费金账户。'
  },
  {
    index: '02',
    title: '审核状态',
    desc: '待审核表示已提交申请；审核通过表示审核已完成待打款；已打款表示提现已完成。'
  },
  {
    index: '03',
    title: '驳回处理',
    desc: '如果提现被驳回，申请金额会退回余额账户，驳回原因会展示在提现记录里。'
  },
  {
    index: '04',
    title: '查看记录',
    desc: '余额明细里可以查看资产变动，提现记录里可以查看申请进度和消费金转入金额。'
  }
];

const balanceWithdrawRows = computed(() => (
  withdrawRows.value.filter((item) => item.withdraw_type === 'BALANCE')
));
const recordTabs = computed(() => {
  const rows = balanceWithdrawRows.value;
  const countByStatus = rows.reduce((map, item) => {
    const key = normalizeStatus(item.status);
    map[key] = (map[key] || 0) + 1;
    return map;
  }, {});

  return [
    { value: 'all', label: '全部', count: rows.length },
    { value: 'pending', label: '待审核', count: countByStatus.pending || 0 },
    { value: 'approved', label: '审核通过', count: countByStatus.approved || 0 },
    { value: 'paid', label: '已打款', count: countByStatus.paid || 0 },
    { value: 'rejected', label: '已驳回', count: countByStatus.rejected || 0 }
  ];
});
const filteredWithdrawRows = computed(() => {
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

function normalizeRange(value) {
  const num = Number(value);
  return recordRangeOptions.some((item) => item.value === num) ? num : recordRangeOptions[0].value;
}

function normalizeRecordTab(value) {
  const text = String(value || '').trim().toLowerCase();
  return ['all', 'pending', 'approved', 'paid', 'rejected'].includes(text) ? text : 'all';
}

function readPageCache() {
  const cached = uni.getStorageSync(WITHDRAW_PAGE_CACHE_KEY);
  return cached && typeof cached === 'object' ? cached : {};
}

function writePageCache() {
  uni.setStorageSync(WITHDRAW_PAGE_CACHE_KEY, {
    range: activeRecordRange.value,
    status: activeRecordTab.value,
    asset_range: assetDetailRange.value
  });
}

function formatDetailTime(value) {
  if (!value) return '--';
  return String(value).replace('T', ' ').slice(0, 16);
}

function normalizeStatus(status) {
  return String(status || '').trim().toLowerCase();
}

function withdrawStatusLabel(status) {
  return {
    pending: '待审核',
    approved: '审核通过',
    rejected: '已驳回',
    paid: '已打款'
  }[normalizeStatus(status)] || status;
}

function withdrawStatusClass(status) {
  return {
    pending: 'badge-orange',
    approved: 'badge-blue',
    rejected: 'badge-blue',
    paid: 'badge-green'
  }[normalizeStatus(status)] || 'badge-blue';
}

function withdrawStatusHint(item) {
  const status = normalizeStatus(item.status);
  if (status === 'pending') return '当前申请等待审核，审核完成后会进入“审核通过”或“已驳回”状态。';
  if (status === 'approved') return '审核已经通过，当前等待财务或系统完成实际打款处理。';
  if (status === 'paid') return '该笔提现已经完成打款，到账金额和转消费金金额已确认。';
  if (status === 'rejected') return item.remark || '该笔提现已驳回，申请金额通常会退回余额账户。';
  return '可结合申请时间、审核时间和单号继续排查这笔提现记录。';
}

function buildWithdrawDetailItems(item) {
  return [
    { key: 'created', label: '申请时间', value: formatDetailTime(item.created_at || item.time) },
    { key: 'reviewed', label: '审核时间', value: formatDetailTime(item.reviewed_at) },
    { key: 'net', label: '到账金额', value: `¥${money(item.net_amount)}` },
    { key: 'voucher', label: '转消费金', value: `¥${money(item.voucher_amount)}` }
  ];
}

function fillAllWithdraw() {
  withdrawAmount.value = money(assetDetail.value.available_amount);
}

function syncPageOptions() {
  const pages = getCurrentPages();
  const currentPage = pages[pages.length - 1];
  if (!currentPage?.options) return;
  currentPage.options.range = String(activeRecordRange.value);
  currentPage.options.status = activeRecordTab.value;
  currentPage.options.asset_range = String(assetDetailRange.value);
  writePageCache();
}

function changeRecordTab(tab) {
  if (activeRecordTab.value === tab) return;
  activeRecordTab.value = tab;
  syncPageOptions();
}

function changeRecordRange(value) {
  if (activeRecordRange.value === value) return;
  activeRecordRange.value = value;
  syncPageOptions();
  reloadPage();
}

function goBalanceDetail() {
  const pages = getCurrentPages();
  const previousPage = pages[pages.length - 2];
  if (previousPage?.route === 'subpackages/assets/index') {
    uni.navigateBack();
    return;
  }
  uni.navigateTo({ url: `/subpackages/assets/index?tab=balance&range=${assetDetailRange.value}` });
}

function copyText(value, label = '内容') {
  if (!value) return;
  uni.setClipboardData({
    data: String(value),
    success: () => uni.showToast({ title: `已复制${label}`, icon: 'none' })
  });
}

function toggleRecordExpand(id) {
  const key = Number(id);
  if (!key) return;
  if (expandedRecordIds.value.includes(key)) {
    expandedRecordIds.value = expandedRecordIds.value.filter((item) => item !== key);
    return;
  }
  expandedRecordIds.value = [...expandedRecordIds.value, key];
}

function isRecordExpanded(id) {
  return expandedRecordIds.value.includes(Number(id));
}

async function loadPageData() {
  recordsLoading.value = true;
  recordsFailed.value = false;

  const [detailRes, withdrawsRes] = await Promise.allSettled([
    assetApi.detail('balance'),
    commissionApi.withdraws(Number(activeRecordRange.value) > 0 ? { recent_days: Number(activeRecordRange.value) } : {})
  ]);

  if (detailRes.status === 'fulfilled') {
    assetDetail.value = detailRes.value || {};
  }
  if (withdrawsRes.status === 'fulfilled') {
    withdrawRows.value = pickListPayload(withdrawsRes.value);
    expandedRecordIds.value = expandedRecordIds.value.filter((id) => withdrawRows.value.some((item) => Number(item.id) === Number(id)));
  } else {
    recordsFailed.value = true;
  }

  recordsLoading.value = false;

  if (detailRes.status === 'rejected' && withdrawsRes.status === 'rejected') {
    throw new Error('balance_withdraw_load_failed');
  }
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

async function submitBalanceWithdraw() {
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

  withdrawSubmitting.value = true;
  try {
    await commissionApi.createWithdraw({
      withdraw_type: 'BALANCE',
      amount
    });
    uni.showToast({ title: '提现申请已提交', icon: 'none' });
    withdrawAmount.value = '';
    await reloadPage();
  } finally {
    withdrawSubmitting.value = false;
  }
}

onShow(() => {
  reloadPage();
});

onLoad((options = {}) => {
  const cached = readPageCache();
  activeRecordRange.value = normalizeRange(options.range || options.recent_days || cached.range);
  activeRecordTab.value = normalizeRecordTab(options.status || cached.status);
  assetDetailRange.value = normalizeRange(options.asset_range || options.range || cached.asset_range);
  syncPageOptions();
});

onPullDownRefresh(async () => {
  await reloadPage();
  uni.stopPullDownRefresh();
});
</script>

<style scoped>
@import '@/styles/common.css';

.balance-withdraw-page {
  padding-bottom: 36rpx;
}

.summary-card {
  background:
    radial-gradient(circle at 100% 0%, rgba(255, 193, 120, 0.22), transparent 32%),
    radial-gradient(circle at 8% 8%, rgba(255, 255, 255, 0.24), transparent 24%),
    linear-gradient(180deg, #fffaf2 0%, #fff1df 100%);
  border: 1rpx solid rgba(198, 161, 124, 0.16);
  position: relative;
  overflow: hidden;
}
.summary-card::after {
  content: '';
  position: absolute;
  right: -26rpx;
  top: -26rpx;
  width: 140rpx;
  height: 140rpx;
  border-radius: 50%;
  background: rgba(255, 122, 0, 0.08);
}
.summary-tag {
  display: inline-flex;
  align-items: center;
  padding: 6rpx 14rpx;
  border-radius: 999rpx;
  background: rgba(255, 138, 43, 0.12);
  color: #c96a14;
  font-size: 20rpx;
  font-weight: 800;
}
.summary-head {
  align-items: flex-start;
  gap: 20rpx;
}
.summary-link {
  flex-shrink: 0;
  padding: 12rpx 20rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.72);
  color: #c96a14;
  font-size: 22rpx;
  font-weight: 700;
}
.section-row {
  margin-bottom: 16rpx;
}
.tips-list {
  display: grid;
  gap: 16rpx;
}
.tip-item {
  display: flex;
  align-items: flex-start;
  gap: 16rpx;
  padding: 18rpx;
  border-radius: 20rpx;
  background: #fffaf4;
  border: 1rpx solid rgba(198, 161, 124, 0.14);
}
.tip-index {
  flex-shrink: 0;
  min-width: 56rpx;
  height: 56rpx;
  line-height: 56rpx;
  border-radius: 18rpx;
  text-align: center;
  background: rgba(255, 138, 43, 0.12);
  color: #c96a14;
  font-size: 22rpx;
  font-weight: 800;
}
.tip-content {
  min-width: 0;
}
.tip-title {
  font-size: 26rpx;
  font-weight: 700;
  color: #4f321a;
}
.tip-desc {
  margin-top: 8rpx;
  font-size: 22rpx;
  line-height: 1.6;
  color: #8d745d;
}
.slim-title {
  margin-bottom: 0;
}
.stat-grid,
.withdraw-preview,
.withdraw-record-list {
  display: grid;
  gap: 12rpx;
}
.stat-grid,
.withdraw-preview {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.stat-item,
.preview-item {
  padding: 16rpx;
  border-radius: 18rpx;
  background: rgba(255, 255, 255, 0.72);
}
.stat-label,
.preview-label {
  display: block;
  font-size: 20rpx;
  color: #8b7158;
}
.stat-value,
.preview-value {
  display: block;
  margin-top: 8rpx;
  font-size: 32rpx;
  font-weight: 800;
  color: #4f321a;
}
.preview-value-warm {
  color: #c96a14;
}
.withdraw-input-wrap {
  display: flex;
  align-items: center;
  gap: 12rpx;
}
.withdraw-input {
  flex: 1;
  min-width: 0;
  height: 76rpx;
  padding: 0 22rpx;
  border-radius: 18rpx;
  background: #fffdf9;
  border: 1rpx solid rgba(198, 161, 124, 0.18);
  box-sizing: border-box;
  font-size: 26rpx;
  color: #4f321a;
}
.withdraw-shortcut {
  flex-shrink: 0;
  padding: 0 22rpx;
  height: 76rpx;
  line-height: 76rpx;
  border-radius: 18rpx;
  background: #f7efe5;
  color: #c96a14;
  font-size: 24rpx;
  font-weight: 700;
}
.asset-empty {
  padding: 16rpx 0 8rpx;
}
.withdraw-record-item {
  padding: 20rpx;
  border-radius: 24rpx;
  background: #fffdf9;
  border: 1rpx solid rgba(198, 161, 124, 0.16);
}
.withdraw-record-title {
  font-size: 28rpx;
  font-weight: 700;
  color: #4f321a;
}
.withdraw-record-line,
.withdraw-record-time {
  margin-top: 8rpx;
  font-size: 21rpx;
  line-height: 1.5;
  color: #8d745d;
}
.withdraw-record-copy {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12rpx;
  flex-wrap: wrap;
}
.copy-link {
  padding: 4rpx 12rpx;
  border-radius: 999rpx;
  background: rgba(255, 138, 43, 0.12);
  color: #c96a14;
  font-size: 20rpx;
  line-height: 1.4;
}
.withdraw-record-action {
  margin-top: 10rpx;
  display: flex;
  justify-content: flex-end;
}
.interactive {
  transition: transform 180ms ease, opacity 180ms ease;
}
.interactive:active {
  transform: scale(0.98);
  opacity: 0.92;
}
</style>
