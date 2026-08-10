<template>
  <view class="page">
    <view class="header">
      <AppBackButton @click="goBack" />
      <text class="title">{{ id ? '编辑银行卡' : '添加银行卡' }}</text>
      <view class="spacer" />
    </view>
    <view class="form-card">
      <view class="row"><text>持卡人</text><input v-model="form.holder_name" placeholder="请输入持卡人姓名" /></view>
      <view class="row"><text>银行名称</text><input v-model="form.bank_name" placeholder="例如：中国工商银行" /></view>
      <view class="row"><text>开户支行</text><input v-model="form.branch_name" placeholder="选填" /></view>
      <view class="row"><text>银行卡号</text><input v-model="form.card_number" type="number" :placeholder="id ? '不修改可留空' : '请输入银行卡号'" /></view>
      <view class="default-row">
        <text>设为默认银行卡</text>
        <switch :checked="form.is_default" color="#10B981" @change="form.is_default = $event.detail.value" />
      </view>
    </view>
    <button class="save" :disabled="saving" @click="save">{{ saving ? '保存中...' : '保存银行卡' }}</button>
  </view>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
import { bankCardApi } from '@/api/modules';
import { pickListPayload } from '@/utils/adapters';

const id = ref('');
const saving = ref(false);
const form = reactive({ holder_name: '', bank_name: '', branch_name: '', card_number: '', is_default: false });

function goBack() { uni.navigateBack(); }
function validate() {
  if (form.holder_name.trim().length < 2) return '请输入持卡人姓名';
  if (form.bank_name.trim().length < 2) return '请输入银行名称';
  if (!id.value && !/^\d{12,30}$/.test(form.card_number.replace(/\s/g, ''))) return '请输入正确的银行卡号';
  if (form.card_number && !/^\d{12,30}$/.test(form.card_number.replace(/\s/g, ''))) return '请输入正确的银行卡号';
  return '';
}

async function save() {
  const message = validate();
  if (message) return uni.showToast({ title: message, icon: 'none' });
  saving.value = true;
  try {
    const payload = { ...form };
    if (!payload.card_number) delete payload.card_number;
    if (id.value) await bankCardApi.update(id.value, payload);
    else await bankCardApi.create(payload);
    uni.showToast({ title: '银行卡已保存', icon: 'success' });
    setTimeout(() => uni.navigateBack(), 300);
  } finally {
    saving.value = false;
  }
}

onLoad(async (query) => {
  id.value = query?.id || '';
  if (!id.value) return;
  const card = pickListPayload(await bankCardApi.list()).find((item) => Number(item.id) === Number(id.value));
  if (card) Object.assign(form, { ...card, card_number: '' });
});
</script>

<style scoped>
@import '@/styles/elegant.css';
.page { min-height: 100vh; background: var(--bg); }
.header { display: flex; align-items: center; justify-content: space-between; padding: 24rpx 32rpx; padding-top: calc(24rpx + env(safe-area-inset-top)); background: var(--card); border-bottom: 1rpx solid var(--border-light); }
.title { font-size: 32rpx; font-weight: 700; color: var(--text); }
.spacer { width: 64rpx; }
.form-card { margin: 24rpx; padding: 0 28rpx; background: var(--card); border: 1rpx solid var(--border-light); border-radius: var(--radius-lg); }
.row, .default-row { display: flex; align-items: center; min-height: 100rpx; border-bottom: 1rpx solid var(--border-light); }
.row > text { width: 150rpx; color: var(--text); flex-shrink: 0; }
.row input { flex: 1; text-align: right; }
.default-row { justify-content: space-between; border-bottom: 0; color: var(--text); }
.save { height: 88rpx; margin: 36rpx 24rpx; color: #fff; background: var(--primary); border-radius: var(--radius-full); font-weight: 600; }
.save[disabled] { opacity: .55; }
</style>

