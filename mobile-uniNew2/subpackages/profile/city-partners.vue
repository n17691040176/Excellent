<template>
  <view class="seat-page">
    <view class="page-header">
      <AppBackButton @click="goBack" />
      <text class="header-title">{{ enabled ? '城市合伙人' : '' }}</text>
      <button v-if="enabled" class="header-action" @click="showRules">规则</button>
    </view>
    <view v-if="!enabled" class="state-card">暂未开放</view>
    <template v-else>
    <view class="seat-toolbar">
      <view class="seat-tabs">
        <button :class="{ active: !mineOnly }" @click="mineOnly = false">全部城市</button>
        <button :class="{ active: mineOnly }" @click="mineOnly = true">我的城市</button>
      </view>
      <view class="region-heading">
        <button v-if="province" class="region-back" @click="selectProvince('')">‹ 全部省份</button>
        <text class="region-title">{{ province || '选择省份' }}</text>
      </view>
      <input :key="province" v-model="keyword" class="city-search" :placeholder="province ? '搜索省内城市' : '搜索省份'" confirm-type="search" />
    </view>
    <view v-if="loading" class="state-card">加载中...</view>
    <view v-else-if="failed" class="state-card"><text>加载失败</text><button class="retry-button" @click="load">重试</button></view>
    <template v-else-if="!province">
      <view v-if="provinces.length" class="province-grid">
        <button v-for="item in provinces" :key="item.name" class="province-card" @click="selectProvince(item.name)">
          <text class="province-name">{{ item.name }}</text>
          <view class="province-footer"><text>{{ item.count }} 个城市</text><text class="province-arrow">›</text></view>
        </button>
      </view>
      <view v-else class="state-card">{{ keyword.trim() ? '未找到该省份' : mineOnly ? '暂无持有城市' : '暂无城市席位' }}</view>
    </template>
    <view v-else-if="!visibleSeats.length" class="state-card">{{ keyword.trim() ? '未找到该城市' : mineOnly ? '该省暂无持有城市' : '暂无城市席位' }}</view>
    <view v-else class="seat-list">
      <view v-for="seat in visibleSeats" :key="seat.id" class="seat-card">
        <view class="seat-heading"><text class="seat-title">{{ seat.city }}</text><text v-if="seat.is_current_holder" class="seat-owned">已持有</text></view>
        <view class="seat-holder"><text>当前合伙人</text><text>{{ seat.current_user_nickname || '空缺' }}</text></view>
        <view class="seat-footer">
          <text class="seat-price">¥{{ Number(seat.current_price).toFixed(2) }}</text>
          <button class="buy-button" :disabled="buying || !seat.purchasable" @click="buy(seat)">{{ seat.is_current_holder ? '已持有' : seat.purchasable ? '购买席位' : '暂不可购买' }}</button>
        </view>
      </view>
    </view>
    </template>
  </view>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue';
import { cityPartnerApi } from '@/api/modules';
import { useCityPartnerAvailability } from '@/composables/useCityPartnerAvailability';
const { enabled, refresh } = useCityPartnerAvailability();
const seats = ref([]);
const loading = ref(false);
const failed = ref(false);
const buying = ref(false);
const keyword = ref('');
const mineOnly = ref(false);
const province = ref('');
const scopedSeats = computed(() => seats.value.filter(seat => !mineOnly.value || seat.is_current_holder));
const provinces = computed(() => {
  const groups = new Map();
  for (const seat of scopedSeats.value) groups.set(seat.province, (groups.get(seat.province) || 0) + 1);
  return Array.from(groups, ([name, count]) => ({ name, count }))
    .filter(item => item.name.includes(keyword.value.trim()));
});
const visibleSeats = computed(() => scopedSeats.value.filter(seat => seat.province === province.value && seat.city.includes(keyword.value.trim())));
function selectProvince(value) {
  province.value = value;
  keyword.value = '';
  nextTick(() => uni.pageScrollTo({ scrollTop: 0, duration: 0 }));
}
watch(mineOnly, () => selectProvince(''));
let loadVersion = 0;
function goBack() {
  if (province.value) { selectProvince(''); return; }
  if (getCurrentPages().length > 1) uni.navigateBack();
  else uni.switchTab({ url: '/pages/profile/index' });
}
function showRules() {
  uni.showModal({ title: '城市合伙人规则', content: '每个城市仅一名合伙人，不可自己接替自己。成交后按该城市涨幅调整价格，达到上限后停止接替。城市合伙人订单不支持退款。', showCancel: false });
}
async function load() {
  const version = ++loadVersion;
  loading.value = true;
  failed.value = false;
  try {
    const result = await cityPartnerApi.seats();
    if (version !== loadVersion || !enabled.value) return;
    if (result.enabled === false) enabled.value = false;
    seats.value = enabled.value ? result.items || [] : [];
    if (province.value && !seats.value.some(seat => seat.province === province.value)) selectProvince('');
  }
  catch { if (version === loadVersion) failed.value = true; }
  finally { if (version === loadVersion) loading.value = false; }
}
async function buy(seat) {
  if (buying.value || !seat.purchasable || !(await refresh())) return;
  uni.showModal({
    title: '确认购买',
    content: `${seat.city} ¥${Number(seat.current_price).toFixed(2)}。成交后涨幅 ${Number(seat.price_growth_rate)}%，${seat.price_cap ? `上限 ¥${Number(seat.price_cap).toFixed(2)}` : '不设上限'}。城市合伙人订单不支持退款。`,
    success: async ({ confirm }) => {
      if (!confirm || buying.value) return;
      buying.value = true;
      try {
        const order = await cityPartnerApi.createOrder(seat.id, seat.price_version);
        uni.navigateTo({ url: `/subpackages/order/detail?id=${order.id}` });
      } catch {
        await load();
      } finally { buying.value = false; }
    }
  });
}
watch(enabled, (value) => {
  loadVersion++;
  seats.value = [];
  loading.value = false;
  if (value) load();
});
</script>

<style scoped>
@import '@/styles/elegant.css';
.seat-page { min-height: 100vh; padding-bottom: calc(24rpx + env(safe-area-inset-bottom)); background: var(--bg); color: var(--text); }
.page-header { position: sticky; top: 0; z-index: 10; display: flex; align-items: center; justify-content: space-between; padding: 24rpx 32rpx; padding-top: calc(24rpx + env(safe-area-inset-top)); background: var(--card); border-bottom: 1rpx solid var(--border-light); }
.header-title { font-size: 32rpx; font-weight: 700; }
.header-action { width: 64rpx; margin: 0; padding: 0; background: transparent; color: var(--primary); font-size: 28rpx; line-height: 64rpx; }
button::after { border: 0; }
.seat-toolbar { padding: 24rpx; }
.region-heading { display: flex; flex-direction: column; align-items: flex-start; gap: 20rpx; margin-bottom: 24rpx; }
.region-title { font-size: 34rpx; font-weight: 700; line-height: 1.5; overflow-wrap: anywhere; }
.region-back { margin: 0; padding: 0; background: transparent; color: var(--primary); font-size: 28rpx; line-height: 64rpx; }
.province-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20rpx; padding: 0 24rpx; }
.province-card { display: flex; flex-direction: column; justify-content: space-between; width: 100%; min-width: 0; min-height: 180rpx; margin: 0; padding: 28rpx; text-align: left; background: var(--card); border: 1rpx solid var(--border-light); border-radius: var(--radius-xl); line-height: 1.5; }
.province-card:active { background: var(--primary-bg); }
.province-name { font-size: 30rpx; font-weight: 600; color: var(--text); overflow-wrap: anywhere; }
.province-footer { display: flex; align-items: center; justify-content: space-between; gap: 12rpx; margin-top: 20rpx; color: var(--text-muted); font-size: 26rpx; }
.province-arrow { display: flex; align-items: center; justify-content: center; width: 44rpx; height: 44rpx; border-radius: 50%; background: var(--primary-bg); color: var(--primary); font-size: 32rpx; }
.seat-tabs { display: flex; gap: 32rpx; margin-bottom: 24rpx; }
.seat-tabs button { padding: 8rpx 0; margin: 0; border-radius: 0; background: transparent; color: var(--text-muted); font-size: 28rpx; line-height: 1.8; border-bottom: 4rpx solid transparent; }
.seat-tabs button.active { color: var(--primary); font-weight: 600; border-color: var(--primary); }
.city-search { height: 80rpx; box-sizing: border-box; padding: 0 24rpx; border: 1rpx solid var(--border-light); border-radius: var(--radius-lg); background: var(--card); font-size: 28rpx; }
.seat-list { padding: 0 24rpx; }
.seat-card { margin-bottom: 24rpx; padding: 28rpx; border: 1rpx solid var(--border-light); border-radius: var(--radius-xl); background: var(--card); }
.seat-heading, .seat-holder, .seat-footer { display: flex; align-items: center; justify-content: space-between; gap: 20rpx; }
.seat-heading { align-items: baseline; }
.seat-title { font-size: 32rpx; font-weight: 700; overflow-wrap: anywhere; }
.seat-owned { flex-shrink: 0; padding: 6rpx 16rpx; border-radius: var(--radius-full); font-size: 26rpx; color: var(--primary); background: var(--primary-bg); }
.seat-holder { margin-top: 24rpx; font-size: 26rpx; color: var(--text-muted); }
.seat-holder text:last-child { color: var(--text); text-align: right; overflow-wrap: anywhere; }
.seat-footer { margin-top: 24rpx; padding-top: 24rpx; border-top: 1rpx solid var(--border-light); flex-wrap: wrap; }
.seat-price { font-size: 38rpx; color: var(--primary); font-weight: 700; }
.buy-button { min-width: 184rpx; margin: 0 0 0 auto; padding: 0 28rpx; line-height: 76rpx; background: var(--primary); color: #fff; border-radius: var(--radius-full); font-size: 28rpx; }
.buy-button[disabled] { background: var(--border-light); color: var(--text-muted); }
.state-card { margin: 0 24rpx; padding: 64rpx 28rpx; border-radius: var(--radius-xl); background: var(--card); text-align: center; color: var(--text-muted); font-size: 28rpx; }
.retry-button { margin-top: 24rpx; color: var(--primary); background: var(--primary-bg); }
</style>
