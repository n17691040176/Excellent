<template>
  <view class="container life-page">
    <view class="card hero">
      <view class="row-between">
        <view>
          <view class="section-title">本地生活</view>
          <view class="muted">到店与上门服务一站预约，价格和排期清晰可见</view>
        </view>
        <view class="badge badge-blue">附近推荐</view>
      </view>
      <view class="hero-banner mt-20" />
    </view>

    <view class="entry-grid mt-20">
      <view class="entry-item interactive" v-for="item in quickEntries" :key="item.title" @click="go(item.path)">
        <view class="entry-icon">{{ item.icon }}</view>
        <view class="entry-title">{{ item.title }}</view>
      </view>
    </view>

    <view class="benefit-strip mt-20">
      <view class="benefit-item" v-for="item in benefitEntries" :key="item.title">
        <view class="benefit-title">{{ item.title }}</view>
        <view class="benefit-desc">{{ item.desc }}</view>
      </view>
    </view>

    <view class="grid-2 mt-24">
      <view class="card scene-card interactive" v-for="scene in scenes" :key="scene.title" @click="go(scene.path)">
        <view class="scene-title">{{ scene.title }}</view>
        <view class="scene-desc">{{ scene.desc }}</view>
        <view class="scene-link">{{ scene.cta }}</view>
      </view>
    </view>

    <view class="mt-24">
      <view class="section-title">精选服务</view>
      <StateView v-if="loading" title="加载中..." custom-class="mt-16" />
      <StateView v-else-if="failed" title="服务加载失败" :show-retry="true" custom-class="mt-16" @retry="fetchServices" />
      <StateView v-else-if="!services.length" title="当前暂无服务" custom-class="mt-16" />

      <view
        v-else
        v-for="item in services"
        :key="item.id"
        class="card service-card interactive"
        @click="go(`/subpackages/life/service-detail?id=${item.id}`)"
      >
        <view class="service-cover" />
        <view class="row-between mt-12">
          <view class="service-title">{{ item.title }}</view>
          <view class="badge badge-orange">{{ item.tag }}</view>
        </view>
        <view class="service-desc">{{ item.desc }}</view>
        <view class="row-between mt-16">
          <view class="ecom-price">
            <text class="ecom-price-main">¥{{ item.price }}</text>
            <text class="ecom-price-origin">¥{{ Number(item.price || 0) + 38 }}</text>
          </view>
          <view class="service-link">查看详情</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import { onPullDownRefresh, onReachBottom } from '@dcloudio/uni-app';
import StateView from '@/components/StateView.vue';
import { localLifeApi } from '@/api/modules';
import { trackEvent, trackPageView } from '@/utils/track';

const loading = ref(false);
const failed = ref(false);
const page = ref(1);
const services = ref([]);

const quickEntries = ref([
  { title: '到店', icon: '店', path: '/subpackages/life/index' },
  { title: '上门', icon: '门', path: '/subpackages/life/index' },
  { title: '急速约', icon: '急', path: '/subpackages/life/index' },
  { title: '评价榜', icon: '榜', path: '/subpackages/life/index' }
]);

const benefitEntries = ref([
  { title: '新人礼包', desc: '首单至高立减 30 元' },
  { title: '周末特惠', desc: '热门项目低至 7 折起' },
  { title: '同城热榜', desc: '附近高人气商家推荐' }
]);

const scenes = ref([
  { title: '服务大厅', desc: '浏览全部本地服务与上门项目，快速挑选适合你的方案。', cta: '去逛服务', path: '/subpackages/life/index' },
  { title: '生活订单', desc: '统一查看预约、上门、完成等状态，售后进度也能同步跟进。', cta: '查看订单', path: '/subpackages/life/orders' }
]);

const normalizeRows = (res) => {
  const rows = Array.isArray(res) ? res : res?.items || res?.list || [];
  return rows.map((item, idx) => ({
    id: item.id || `s-${idx}`,
    title: item.name || item.title || '未命名服务',
    desc: item.description || item.desc || '暂无描述',
    price: item.price ?? item.sale_price ?? 0,
    tag: item.tag || '推荐'
  }));
};

const fetchServices = async (reset = true) => {
  loading.value = true;
  failed.value = false;
  try {
    const currentPage = reset ? 1 : page.value;
    const res = await localLifeApi.services({ page: currentPage, page_size: 10 });
    const rows = normalizeRows(res);
    services.value = reset ? rows : [...services.value, ...rows];
    page.value = currentPage + 1;
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  trackPageView('local_life_home');
  fetchServices(true);
});

onPullDownRefresh(async () => {
  await fetchServices(true);
  uni.stopPullDownRefresh();
});

onReachBottom(() => {
  trackEvent('local_life_load_more', { page: page.value });
  fetchServices(false);
});

const go = (path) => {
  if (path.includes('/subpackages/life/service-detail')) {
    trackEvent('local_life_click_service', { path });
  } else {
    trackEvent('local_life_click_scene', { path });
  }
  uni.navigateTo({ url: path });
};
</script>

<style scoped>
@import '@/styles/common.css';

.life-page { padding-bottom: 36rpx; }
.hero { background: radial-gradient(circle at 95% 12%, rgba(207,171,132,.2), transparent 42%), #fff; border: 1rpx solid rgba(198,161,124,.2); }
.hero-banner { height: 150rpx; border-radius: 18rpx; background: linear-gradient(120deg, #ebd8c2, #d7b28b); border: 1rpx solid rgba(198,161,124,.2); }
.entry-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10rpx; }
.entry-item { border-radius: 14rpx; padding: 14rpx 8rpx; text-align: center; background: #faf4ec; border: 1rpx solid rgba(196,159,120,.16); }
.entry-icon { width: 42rpx; height: 42rpx; border-radius: 50%; margin: 0 auto 8rpx; background: #bf8650; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 20rpx; box-shadow: 0 8rpx 14rpx rgba(130, 88, 50, 0.2); }
.entry-title { font-size: 21rpx; color: #6d5138; font-weight: 700; letter-spacing: 0.3rpx; }
.benefit-strip { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10rpx; }
.benefit-item { border-radius: 14rpx; padding: 12rpx; background: linear-gradient(145deg, #fffefd, #fbf4ec); border: 1rpx solid rgba(196,159,120,.16); }
.benefit-title { font-size: 22rpx; font-weight: 700; color: #65492f; }
.benefit-desc { margin-top: 4rpx; font-size: 20rpx; color: #8d745d; }
.scene-card { min-height: 180rpx; background: linear-gradient(180deg, #ffffff 0%, #fbf6ef 100%); border: 1rpx solid rgba(198,161,124,.18); box-shadow: 0 12rpx 28rpx rgba(141,100,60,.08); border-radius: 20rpx; }
.scene-title { margin-top: 6rpx; font-size: 30rpx; font-weight: 700; color: #503522; letter-spacing: 0.4rpx; }
.scene-desc { margin-top: 10rpx; color: #7d6753; font-size: 23rpx; line-height: 1.5; }
.scene-link { margin-top: 12rpx; color: #9f6736; font-weight: 700; font-size: 23rpx; }
.service-card { margin-bottom: 16rpx; border: 1rpx solid rgba(198,161,124,.18); box-shadow: 0 12rpx 28rpx rgba(141,100,60,.08); border-radius: 20rpx; }
.service-cover { height: 170rpx; border-radius: 16rpx; background: linear-gradient(130deg, #f0e2d1, #e3c8aa 44%, #d5aa7f); }
.service-title { font-size: 30rpx; font-weight: 700; color: #503522; letter-spacing: 0.4rpx; }
.service-desc { margin-top: 10rpx; color: #7d6753; font-size: 24rpx; line-height: 1.55; }
.service-link { color: #9f6736; font-size: 24rpx; font-weight: 700; }

.interactive { transition: transform 180ms ease, opacity 180ms ease; }
.interactive:active { transform: scale(0.98); opacity: 0.92; }
</style>
