<template>
  <view class="page">
    <view class="header">
      <AppBackButton @click="goBack" />
      <text class="title">银行卡</text>
      <view class="add" @click="addCard">新增</view>
    </view>

    <view v-if="loading" class="state">银行卡加载中...</view>
    <view v-else-if="!cards.length" class="state">
      <text>暂未绑定银行卡</text>
      <button class="primary" @click="addCard">添加银行卡</button>
    </view>
    <view v-else class="list">
      <view v-for="item in cards" :key="item.id" class="bank-card">
        <view class="card-head">
          <view>
            <text class="bank-name">{{ item.bank_name }}</text>
            <text class="holder">{{ item.holder_name }}</text>
          </view>
          <text v-if="item.is_default" class="default-tag">默认</text>
        </view>
        <text class="card-number">{{ item.masked_card_number }}</text>
        <text v-if="item.branch_name" class="branch">{{ item.branch_name }}</text>
        <view class="actions">
          <text v-if="!item.is_default" @click="setDefault(item)">设为默认</text>
          <text @click="editCard(item)">编辑</text>
          <text class="danger" @click="removeCard(item)">删除</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import { bankCardApi } from '@/api/modules';
import { pickListPayload } from '@/utils/adapters';

const loading = ref(false);
const cards = ref([]);

async function loadCards() {
  loading.value = true;
  try {
    cards.value = pickListPayload(await bankCardApi.list());
  } finally {
    loading.value = false;
  }
}

function goBack() { uni.navigateBack(); }
function addCard() { uni.navigateTo({ url: '/subpackages/profile/bank-edit' }); }
function editCard(item) { uni.navigateTo({ url: `/subpackages/profile/bank-edit?id=${item.id}` }); }

async function setDefault(item) {
  await bankCardApi.setDefault(item.id);
  await loadCards();
  uni.showToast({ title: '默认银行卡已更新', icon: 'success' });
}

function removeCard(item) {
  uni.showModal({
    title: '删除银行卡',
    content: `确认删除尾号 ${item.card_last_four} 的银行卡吗？`,
    success: async ({ confirm }) => {
      if (!confirm) return;
      await bankCardApi.remove(item.id);
      await loadCards();
      uni.showToast({ title: '银行卡已删除', icon: 'success' });
    }
  });
}

onShow(loadCards);
</script>

<style scoped>
@import '@/styles/elegant.css';
.page { min-height: 100vh; background: var(--bg); }
.header { display: flex; align-items: center; justify-content: space-between; padding: 24rpx 32rpx; padding-top: calc(24rpx + env(safe-area-inset-top)); background: var(--card); border-bottom: 1rpx solid var(--border-light); }
.title { font-size: 32rpx; font-weight: 700; color: var(--text); }
.add { width: 88rpx; text-align: right; color: var(--primary); }
.state { margin: 24rpx; padding: 48rpx 28rpx; text-align: center; color: var(--text-muted); background: var(--card); border: 1rpx solid var(--border-light); border-radius: var(--radius-lg); }
.primary { margin-top: 24rpx; color: #fff; background: var(--primary); }
.list { padding: 24rpx; }
.bank-card { margin-bottom: 20rpx; padding: 28rpx; color: var(--text); background: var(--card); border: 1rpx solid var(--border-light); border-radius: var(--radius-lg); }
.card-head { display: flex; justify-content: space-between; align-items: flex-start; }
.bank-name, .holder, .card-number, .branch { display: block; }
.bank-name { font-size: 30rpx; font-weight: 700; }
.holder { margin-top: 8rpx; color: var(--text-muted); font-size: 24rpx; }
.default-tag { padding: 4rpx 12rpx; color: var(--primary); background: var(--primary-bg); border-radius: 6rpx; font-size: 20rpx; }
.card-number { margin-top: 32rpx; font-size: 34rpx; font-weight: 600; }
.branch { margin-top: 10rpx; color: var(--text-muted); font-size: 22rpx; }
.actions { display: flex; justify-content: flex-end; gap: 28rpx; margin-top: 24rpx; padding-top: 20rpx; border-top: 1rpx solid var(--border-light); color: var(--primary); font-size: 24rpx; }
.danger { color: var(--error); }
</style>

