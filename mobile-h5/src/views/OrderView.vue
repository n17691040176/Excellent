<template>
  <div class="page safe-bottom">
    <van-nav-bar title="我的订单" fixed placeholder left-arrow @click-left="$router.back()" />

    <div class="page-card">
      <h2 class="page-title">订单列表</h2>
      <p class="page-desc">展示套餐、商城和本地生活订单；支付后进入待确认或待核销状态，完成后驱动返现结算。</p>
      <van-tabs v-model:active="activeStatus">
        <van-tab title="全部" name="all" />
        <van-tab title="待支付" name="CREATED" />
        <van-tab title="待完成" name="PAID" />
        <van-tab title="已完成" name="CONFIRMED" />
        <van-tab title="已关闭" name="CLOSED" />
      </van-tabs>
    </div>

    <div class="page-card">
      <van-cell-group inset>
        <van-cell
          v-for="item in filteredRows"
          :key="item.id"
          is-link
          @click="goDetail(item.id)"
          :title="item.order_no"
          :label="`${item.order_type} / ${item.zone_type || '--'}`"
        >
          <template #value>
            <div>{{ item.payable_amount }}</div>
            <div>{{ item.order_status }}</div>
            <div class="inline-actions" style="margin-top: 0.12rem; justify-content: flex-end;">
              <van-button size="mini" plain type="primary" @click.stop="payDemo(item)" v-if="item.order_status === 'CREATED'">演示支付</van-button>
              <van-button size="mini" plain type="success" @click.stop="confirmOrder(item)" v-if="canConfirm(item)">确认完成</van-button>
              <van-button size="mini" plain type="danger" @click.stop="cancelOrder(item)" v-if="item.order_status === 'CREATED'">取消订单</van-button>
            </div>
          </template>
        </van-cell>
      </van-cell-group>
      <van-empty v-if="!filteredRows.length" image="search" description="暂无订单记录" />
    </div>

    <AppTabbar />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showConfirmDialog, showSuccessToast } from 'vant'

import AppTabbar from '@/components/AppTabbar.vue'
import { orderApi } from '@/api/modules'

const router = useRouter()
const rows = ref([])
const activeStatus = ref('all')

const filteredRows = computed(() => {
  if (activeStatus.value === 'all') return rows.value
  return rows.value.filter((item) => item.order_status === activeStatus.value)
})

function canConfirm(item) {
  return item.order_status === 'PAID' && item.order_type !== 'LOCAL_LIFE_ORDER'
}

function goDetail(id) {
  router.push(`/orders/${id}`)
}

async function loadData() {
  rows.value = await orderApi.list()
}

async function payDemo(item) {
  await showConfirmDialog({ title: '提示', message: `确认对订单 ${item.order_no} 执行演示支付吗？` })
  await orderApi.payDemo(item.id)
  showSuccessToast('订单已进入已支付状态')
  await loadData()
}

async function confirmOrder(item) {
  await showConfirmDialog({ title: '提示', message: `确认订单 ${item.order_no} 已完成吗？` })
  await orderApi.confirm(item.id)
  showSuccessToast('订单已确认完成')
  await loadData()
}

async function cancelOrder(item) {
  await showConfirmDialog({ title: '提示', message: `确认取消订单 ${item.order_no} 吗？` })
  await orderApi.cancel(item.id)
  showSuccessToast('订单已取消')
  await loadData()
}

onMounted(loadData)
</script>
