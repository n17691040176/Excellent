<template>
  <view class="page">
    <view class="header">
      <AppBackButton @click="goBack" />
      <text class="title">佣金提现</text>
      <view class="spacer" />
    </view>
    <view class="balance-card">
      <text class="label">可提现佣金</text>
      <text class="balance">¥{{ money(summary.available_amount) }}</text>
      <text class="range">单笔 ¥{{ money(config.min_amount) }} - ¥{{ money(config.max_amount) }}</text>
    </view>
    <view class="form-card">
      <text class="section-title">提现金额</text>
      <view class="amount-row"><text>¥</text><input v-model="amount" type="digit" placeholder="0.00" /><text class="all" @click="fillAll">全部</text></view>
      <view class="preview">
        <view><text>手续费</text><text>¥{{ feeAmount }}</text></view>
        <view><text>实际到账</text><text class="net">¥{{ netAmount }}</text></view>
      </view>
    </view>
    <view class="form-card">
      <view class="section-head"><text class="section-title">收款银行卡</text><text class="manage" @click="manageCards">管理</text></view>
      <view v-if="!cards.length" class="empty-card" @click="addCard">请先添加银行卡</view>
      <view v-for="item in cards" :key="item.id" class="card-option" :class="{ active: selectedCardId === item.id }" @click="selectedCardId = item.id">
        <view><text class="bank">{{ item.bank_name }}</text><text class="number">{{ item.masked_card_number }}</text></view>
        <text class="radio">{{ selectedCardId === item.id ? '●' : '○' }}</text>
      </view>
    </view>
    <button class="submit" :disabled="submitting" @click="submit">{{ submitting ? '提交中...' : '提交提现申请' }}</button>
    <view class="records">
      <text class="section-title">提现记录</text>
      <view v-if="!records.length" class="empty-record">暂无提现记录</view>
      <view v-for="item in records" :key="item.id" class="record">
        <view><text class="record-amount">¥{{ money(item.net_amount) }}</text><text class="record-bank">{{ item.bank_name }} {{ item.masked_bank_card_number }}</text></view>
        <view class="record-right"><text>{{ statusText(item.status) }}</text><text>{{ formatTime(item.created_at) }}</text></view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import { bankCardApi, commissionApi } from '@/api/modules';
import { pickListPayload } from '@/utils/adapters';

const summary = ref({});
const config = ref({ fee_rate: 0, min_amount: 1, max_amount: 50000 });
const cards = ref([]);
const records = ref([]);
const amount = ref('');
const selectedCardId = ref(null);
const submitting = ref(false);
const feeAmount = computed(() => money((Number(amount.value) || 0) * Number(config.value.fee_rate || 0) / 100));
const netAmount = computed(() => money(Math.max((Number(amount.value) || 0) - Number(feeAmount.value), 0)));

function money(value) { return Number(value || 0).toFixed(2); }
function goBack() { uni.navigateBack(); }
function fillAll() { amount.value = money(summary.value.available_amount); }
function manageCards() { uni.navigateTo({ url: '/subpackages/profile/bank' }); }
function addCard() { uni.navigateTo({ url: '/subpackages/profile/bank-edit' }); }
function statusText(status) { return ({ PENDING: '待审核', APPROVED: '待打款', REJECTED: '已驳回', PAID: '已打款' })[status] || status; }
function formatTime(value) { return value ? String(value).replace('T', ' ').slice(0, 16) : ''; }

async function loadData() {
  const [summaryData, configData, cardData, recordData] = await Promise.all([
    commissionApi.summary(), commissionApi.withdrawConfig(), bankCardApi.list(), commissionApi.withdraws({})
  ]);
  summary.value = summaryData || {};
  config.value = configData || config.value;
  cards.value = pickListPayload(cardData);
  records.value = pickListPayload(recordData).filter((item) => item.withdraw_type === 'COMMISSION');
  if (!cards.value.some((item) => item.id === selectedCardId.value)) {
    selectedCardId.value = cards.value.find((item) => item.is_default)?.id || cards.value[0]?.id || null;
  }
}

async function submit() {
  const value = Number(amount.value || 0);
  if (value < Number(config.value.min_amount) || value > Number(config.value.max_amount)) return uni.showToast({ title: '提现金额不在允许范围内', icon: 'none' });
  if (value > Number(summary.value.available_amount || 0)) return uni.showToast({ title: '可提现佣金不足', icon: 'none' });
  if (!selectedCardId.value) return uni.showToast({ title: '请选择收款银行卡', icon: 'none' });
  const confirmed = await new Promise((resolve) => uni.showModal({ title: '确认提现', content: `申请 ¥${money(value)}，手续费 ¥${feeAmount.value}，实际到账 ¥${netAmount.value}`, success: ({ confirm }) => resolve(confirm), fail: () => resolve(false) }));
  if (!confirmed) return;
  submitting.value = true;
  try {
    await commissionApi.createWithdraw({ withdraw_type: 'COMMISSION', amount: value, bank_card_id: selectedCardId.value });
    amount.value = '';
    await loadData();
    uni.showToast({ title: '提现申请已提交', icon: 'success' });
  } finally { submitting.value = false; }
}

onShow(loadData);
</script>

<style scoped>
@import '@/styles/elegant.css';
.page { min-height: 100vh; padding-bottom: calc(48rpx + env(safe-area-inset-bottom)); background: var(--bg); }
.header { display: flex; align-items: center; justify-content: space-between; padding: 24rpx 32rpx; padding-top: calc(24rpx + env(safe-area-inset-top)); background: var(--card); border-bottom: 1rpx solid var(--border-light); }
.title { font-size: 32rpx; font-weight: 700; color: var(--text); }.spacer { width: 64rpx; }
.balance-card, .form-card, .records { margin: 24rpx; padding: 28rpx; background: var(--card); border: 1rpx solid var(--border-light); border-radius: var(--radius-lg); }
.label, .range, .number, .record-bank, .record-right text:last-child { display: block; color: var(--text-muted); font-size: 22rpx; }.balance { display: block; margin: 12rpx 0; font-size: 52rpx; font-weight: 700; color: var(--text); }
.section-title { color: var(--text); font-size: 28rpx; font-weight: 700; }.section-head { display: flex; justify-content: space-between; }.manage, .all { color: var(--primary); }
.amount-row { display: flex; align-items: center; gap: 16rpx; height: 96rpx; margin-top: 12rpx; border-bottom: 1rpx solid var(--border-light); font-size: 36rpx; }.amount-row input { flex: 1; font-size: 40rpx; }
.preview { padding-top: 20rpx; }.preview view { display: flex; justify-content: space-between; margin-top: 12rpx; color: var(--text-muted); }.preview .net { color: var(--primary); font-weight: 700; }
.empty-card, .empty-record { padding: 28rpx 0; text-align: center; color: var(--text-muted); }
.card-option { display: flex; align-items: center; justify-content: space-between; margin-top: 18rpx; padding: 22rpx; border: 1rpx solid var(--border-light); border-radius: var(--radius-md); }.card-option.active { border-color: var(--primary); background: var(--primary-bg); }.bank, .number { display: block; }.bank { color: var(--text); font-weight: 600; }.number { margin-top: 6rpx; }.radio { color: var(--primary); font-size: 30rpx; }
.submit { height: 88rpx; margin: 32rpx 24rpx; color: #fff; background: var(--primary); border-radius: var(--radius-full); font-weight: 600; }.submit[disabled] { opacity: .55; }
.record { display: flex; justify-content: space-between; padding: 22rpx 0; border-bottom: 1rpx solid var(--border-light); }.record:last-child { border-bottom: 0; }.record-amount, .record-bank { display: block; }.record-amount { color: var(--text); font-weight: 700; }.record-bank { margin-top: 6rpx; }.record-right { text-align: right; color: var(--primary); }.record-right text { display: block; }.record-right text:last-child { margin-top: 6rpx; }
</style>
