<template>
  <div class="page safe-bottom">
    <van-nav-bar title="地址管理" fixed placeholder left-arrow @click-left="$router.back()" />

    <div class="page-card">
      <h2 class="page-title">收货地址</h2>
      <p class="page-desc">支持新增、编辑、删除和设为默认地址，用于商城与一件代发履约。</p>
      <van-button round block type="primary" @click="openPopup()">新增地址</van-button>
    </div>

    <div class="page-card">
      <van-address-list
        v-model="chosenId"
        :list="list"
        default-tag-text="默认"
        @add="openPopup()"
        @edit="openPopup"
        @select="handleSelect"
      />
    </div>

    <van-popup v-model:show="showPopup" position="bottom" round :style="{ height: '78%' }">
      <div class="page" style="padding-bottom: 0.4rem;">
        <h3 class="cell-group-title">{{ form.id ? '编辑地址' : '新增地址' }}</h3>
        <van-form @submit="submitForm">
          <van-field v-model="form.name" label="收货人" placeholder="请输入收货人" />
          <van-field v-model="form.phone" label="手机号" placeholder="请输入手机号" />
          <van-field v-model="form.province" label="省份" placeholder="请输入省份" />
          <van-field v-model="form.city" label="城市" placeholder="请输入城市" />
          <van-field v-model="form.district" label="区县" placeholder="请输入区县" />
          <van-field v-model="form.detail_address" label="详细地址" placeholder="请输入详细地址" />
          <van-switch-cell v-model="form.is_default" title="设为默认地址" />
          <div class="inline-actions submit-bar">
            <van-button v-if="form.id" block round plain type="danger" @click="removeAddress">删除</van-button>
            <van-button block round type="primary" native-type="submit">保存地址</van-button>
          </div>
        </van-form>
      </div>
    </van-popup>

    <AppTabbar />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { showConfirmDialog, showSuccessToast } from 'vant'

import AppTabbar from '@/components/AppTabbar.vue'
import { addressApi } from '@/api/modules'

const chosenId = ref('')
const rows = ref([])
const showPopup = ref(false)
const form = reactive({
  id: null,
  name: '',
  phone: '',
  province: '',
  city: '',
  district: '',
  detail_address: '',
  is_default: false
})

const list = computed(() => rows.value.map((item) => ({
  id: String(item.id),
  name: item.name,
  tel: item.phone,
  address: [item.province, item.city, item.district, item.detail_address].filter(Boolean).join(' '),
  isDefault: !!item.is_default
})))

function resetForm() {
  Object.assign(form, {
    id: null,
    name: '',
    phone: '',
    province: '',
    city: '',
    district: '',
    detail_address: '',
    is_default: false
  })
}

async function loadData() {
  rows.value = await addressApi.list()
  const current = rows.value.find((item) => item.is_default) || rows.value[0]
  chosenId.value = current ? String(current.id) : ''
}

function openPopup(item) {
  resetForm()
  if (item) {
    const raw = rows.value.find((row) => String(row.id) === String(item.id))
    if (raw) Object.assign(form, raw)
  }
  showPopup.value = true
}

async function submitForm() {
  const payload = {
    name: form.name,
    phone: form.phone,
    province: form.province,
    city: form.city,
    district: form.district,
    detail_address: form.detail_address,
    is_default: form.is_default
  }
  if (form.id) {
    await addressApi.update(form.id, payload)
  } else {
    await addressApi.create(payload)
  }
  if (form.is_default && form.id) {
    await addressApi.setDefault(form.id)
  }
  showPopup.value = false
  showSuccessToast('地址已保存')
  await loadData()
}

async function removeAddress() {
  await showConfirmDialog({ title: '提示', message: '确认删除该地址吗？' })
  await addressApi.remove(form.id)
  showPopup.value = false
  showSuccessToast('地址已删除')
  await loadData()
}

async function handleSelect(item) {
  await addressApi.setDefault(item.id)
  showSuccessToast('已设为默认地址')
  await loadData()
}

onMounted(loadData)
</script>
