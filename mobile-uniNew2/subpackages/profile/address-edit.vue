<template>
  <view class="edit-page">
    <view class="page-header">
      <AppBackButton @click="goBack" />
      <text class="header-title">{{ id ? '编辑地址' : '新增地址' }}</text>
      <view class="header-spacer" />
    </view>

    <view class="form-card">
      <view class="form-row"><text>收货人</text><input v-model="form.receiver_name" placeholder="请输入收货人" /></view>
      <view class="form-row"><text>手机号</text><input v-model="form.receiver_phone" type="number" placeholder="请输入手机号" /></view>
      <picker
        class="region-picker"
        mode="multiSelector"
        :range="regionRange"
        :value="regionIndex"
        @columnchange="onRegionColumnChange"
        @change="onRegionChange"
      >
        <view class="form-row picker-row">
          <text>省市区/县</text>
          <view class="picker-value" :class="{ placeholder: !hasRegion }">{{ regionText }}</view>
        </view>
      </picker>
      <view class="form-row detail-row"><text>详细地址</text><textarea v-model="form.detail_address" placeholder="街道、小区、门牌号" /></view>
      <view class="default-row" @click="form.is_default = !form.is_default">
        <text>设为默认地址</text>
        <switch :checked="form.is_default" color="#10B981" @change="form.is_default = $event.detail.value" />
      </view>
    </view>
    <button class="save-btn" :disabled="saving" @click="save">{{ saving ? '保存中...' : '保存地址' }}</button>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
import rawRegions from 'province-city-china/dist/level.json';
import { addressApi } from '@/api/modules';
import { pickListPayload } from '@/utils/adapters';

const id = ref('');
const saving = ref(false);
const form = reactive({
  receiver_name: '',
  receiver_phone: '',
  province: '',
  city: '',
  district: '',
  detail_address: '',
  is_default: false
});

const regionTree = rawRegions.map((province) => {
  const children = Array.isArray(province.children) ? province.children : [];
  const hasCityLevel = children.some((city) => Array.isArray(city.children) && city.children.length);
  const cities = hasCityLevel
    ? children.map((city) => ({
        name: city.name,
        children: Array.isArray(city.children) && city.children.length ? city.children : [city]
      }))
    : [{ name: province.name, children: children.length ? children : [province] }];
  return { name: province.name, children: cities };
});

const regionIndex = ref([0, 0, 0]);
const hasRegion = computed(() => [form.province, form.city, form.district].every((item) => item.trim()));
const regionText = computed(() => (hasRegion.value ? [form.province, form.city, form.district].join(' / ') : '请选择省市区/县'));
const currentProvince = computed(() => regionTree[regionIndex.value[0]] || regionTree[0]);
const currentCities = computed(() => currentProvince.value?.children || []);
const currentCity = computed(() => currentCities.value[regionIndex.value[1]] || currentCities.value[0]);
const currentDistricts = computed(() => currentCity.value?.children || []);
const regionRange = computed(() => [
  regionTree.map((item) => item.name),
  currentCities.value.map((item) => item.name),
  currentDistricts.value.map((item) => item.name)
]);

function goBack() {
  uni.navigateBack();
}

function onRegionColumnChange(event) {
  const { column, value } = event.detail;
  const nextIndex = [...regionIndex.value];
  nextIndex[column] = value;
  if (column === 0) {
    nextIndex[1] = 0;
    nextIndex[2] = 0;
  }
  if (column === 1) {
    nextIndex[2] = 0;
  }
  regionIndex.value = normalizeRegionIndex(nextIndex);
}

function onRegionChange(event) {
  regionIndex.value = normalizeRegionIndex(event.detail.value || regionIndex.value);
  applySelectedRegion();
}

function normalizeRegionIndex(index) {
  const provinceIndex = clampIndex(index[0], regionTree.length);
  const cities = regionTree[provinceIndex]?.children || [];
  const cityIndex = clampIndex(index[1], cities.length);
  const districts = cities[cityIndex]?.children || [];
  return [provinceIndex, cityIndex, clampIndex(index[2], districts.length)];
}

function clampIndex(value, length) {
  if (!length) return 0;
  return Math.min(Math.max(Number(value) || 0, 0), length - 1);
}

function applySelectedRegion() {
  const [provinceIndex, cityIndex, districtIndex] = regionIndex.value;
  const province = regionTree[provinceIndex];
  const city = province?.children?.[cityIndex];
  const district = city?.children?.[districtIndex];
  form.province = province?.name || '';
  form.city = city?.name || '';
  form.district = district?.name || '';
}

function syncRegionIndexByForm() {
  const provinceIndex = Math.max(regionTree.findIndex((item) => item.name === form.province), 0);
  const cities = regionTree[provinceIndex]?.children || [];
  const cityIndex = Math.max(cities.findIndex((item) => item.name === form.city), 0);
  const districts = cities[cityIndex]?.children || [];
  const districtIndex = Math.max(districts.findIndex((item) => item.name === form.district), 0);
  regionIndex.value = normalizeRegionIndex([provinceIndex, cityIndex, districtIndex]);
}

function validate() {
  if (!form.receiver_name.trim()) return '请输入收货人';
  if (!/^1\d{10}$/.test(form.receiver_phone.trim())) return '请输入正确的手机号';
  if (![form.province, form.city, form.district, form.detail_address].every((item) => item.trim())) return '请完善收货地址';
  return '';
}

async function save() {
  const message = validate();
  if (message) {
    uni.showToast({ title: message, icon: 'none' });
    return;
  }
  saving.value = true;
  try {
    const payload = { ...form };
    if (id.value) await addressApi.update(id.value, payload);
    else await addressApi.create(payload);
    uni.showToast({ title: '地址已保存', icon: 'success' });
    setTimeout(() => uni.navigateBack(), 300);
  } finally {
    saving.value = false;
  }
}

onLoad(async (query) => {
  id.value = query?.id || '';
  if (!id.value) return;
  const rows = pickListPayload(await addressApi.list());
  const current = rows.find((item) => Number(item.id) === Number(id.value));
  if (current) {
    Object.assign(form, current);
    syncRegionIndexByForm();
  }
});
</script>

<style scoped>
@import '@/styles/elegant.css';

.edit-page { min-height: 100vh; background: var(--bg); }
.page-header { display: flex; align-items: center; justify-content: space-between; padding: 24rpx 32rpx; padding-top: calc(24rpx + env(safe-area-inset-top)); background: var(--card); border-bottom: 1rpx solid var(--border-light); }
.back-btn, .header-spacer { width: 64rpx; color: var(--primary); }
.header-title { color: var(--text); font-size: 32rpx; font-weight: 700; }
.form-card { margin: 24rpx; padding: 0 28rpx; background: var(--card); border: 1rpx solid var(--border-light); border-radius: var(--radius-xl); }
.form-row, .default-row { display: flex; align-items: center; gap: 24rpx; min-height: 96rpx; border-bottom: 1rpx solid var(--border-light); color: var(--text); }
.form-row > text { width: 150rpx; flex-shrink: 0; }
.form-row input, .form-row textarea { flex: 1; text-align: right; }
.region-picker { display: block; }
.picker-row { justify-content: space-between; }
.picker-value { flex: 1; min-width: 0; color: var(--text); text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.picker-value.placeholder { color: var(--text-muted); }
.detail-row { align-items: flex-start; padding: 24rpx 0; }
.detail-row textarea { min-height: 120rpx; text-align: left; }
.default-row { justify-content: space-between; border-bottom: 0; }
.save-btn { margin: 36rpx 24rpx; color: white; background: var(--primary); border-radius: 999rpx; }
</style>
