<template>
  <div class="page safe-bottom">
    <van-nav-bar title="地址管理" fixed placeholder left-arrow @click-left="$router.back()" />

    <div class="page-card hero-soft">
      <div class="hero-badge">Address Center</div>
      <h2 class="page-title">把收货地址集中到一个维护入口</h2>
      <p class="page-desc">支持新增、编辑、删除和设为默认地址，用于商城与一件代发履约。</p>
      <div class="metric-grid">
        <div class="metric-card" v-for="item in metrics" :key="item.label">
          <div class="metric-label">{{ item.label }}</div>
          <div class="metric-value">{{ item.value }}</div>
          <div class="metric-meta">{{ item.meta }}</div>
        </div>
      </div>
    </div>

    <div class="page-card">
      <div class="section-head">
        <h3 class="cell-group-title" style="margin: 0;">地址列表</h3>
        <span class="section-link-text" @click="openPopup()">新增地址</span>
      </div>
      <div v-if="loadError" class="state-card">
        <div class="state-title">地址数据加载失败</div>
        <div class="state-desc">{{ loadError }}</div>
        <van-button block round plain type="primary" style="margin-top: 0.18rem;" @click="loadData">重新加载</van-button>
      </div>
      <div v-else-if="loading" class="card-stack">
        <div class="skeleton-card short"></div>
      </div>
      <div v-else class="soft-section">
        <van-address-list
          v-model="chosenId"
          :list="list"
          default-tag-text="默认"
          @add="openPopup()"
          @edit="openPopup"
          @select="handleSelect"
        />
      </div>
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
            <van-button block round type="primary" native-type="submit">{{ saving ? '保存中...' : '保存地址' }}</van-button>
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
import { normalizeLoadError } from '@/utils/ui'

const chosenId = ref('')
const rows = ref([])
const showPopup = ref(false)
const loading = ref(false)
const loadError = ref('')
const saving = ref(false)
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

const metrics = computed(() => [
  { label: '地址数量', value: rows.value.length, meta: '当前已保存地址条数' },
  { label: '默认地址', value: rows.value.filter((item) => item.is_default).length, meta: '结算时优先使用' },
  { label: '已选地址', value: chosenId.value || '--', meta: '当前默认选中的地址 ID' },
  { label: '履约用途', value: '商城', meta: '用于普通商品与代发履约' }
])

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
  loading.value = true
  loadError.value = ''
  try {
    rows.value = await addressApi.list()
    const current = rows.value.find((item) => item.is_default) || rows.value[0]
    chosenId.value = current ? String(current.id) : ''
  } catch (error) {
    loadError.value = normalizeLoadError(error)
  } finally {
    loading.value = false
  }
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
  saving.value = true
  try {
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
  } finally {
    saving.value = false
  }
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
