<template>
  <view class="container packages-page">
    <view class="filter-strip">
      <view
        v-for="item in quickFilters"
        :key="item.value"
        class="filter-chip interactive"
        :class="{ active: activeQuickFilter === item.value }"
        @click="selectQuickFilter(item.value)"
      >
        {{ item.label }}
      </view>
    </view>

    <StateView v-if="loading" title="商品加载中..." custom-class="mt-20" />
    <StateView
      v-else-if="failed"
      title="商品加载失败，请重试"
      :show-retry="true"
      custom-class="mt-20"
      @retry="fetchList"
    />
    <StateView
      v-else-if="!filteredGoods.length"
      title="暂无商品"
      description="切换筛选条件后再试试看"
      custom-class="mt-20"
    />

    <view v-else class="goods-grid mt-20">
      <view
        v-for="item in filteredGoods"
        :key="item.id"
        class="goods-card interactive"
        @click="goDetail(item.id)"
      >
        <image v-if="item.image" class="goods-cover" :src="item.image" mode="aspectFill" lazy-load />
        <view v-else class="goods-cover goods-cover-fallback" />

        <view class="goods-body">
          <view class="goods-tag-row">
            <text class="goods-tag">{{ item.tag }}</text>
            <text v-if="item.quickTag" class="goods-quick-tag">{{ item.quickTag }}</text>
          </view>
          <view class="goods-title">{{ item.title }}</view>
          <view class="goods-desc">{{ item.desc }}</view>
          <view class="goods-foot">
            <view class="ecom-price">
              <view class="ecom-price-main">¥{{ item.price }}</view>
              <view class="ecom-price-origin" v-if="item.originPrice">¥{{ item.originPrice }}</view>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import StateView from '@/components/StateView.vue';
import { packageApi } from '@/api/modules';
import { getApiBaseUrl } from '@/config/index';
import { trackEvent, trackPageView } from '@/utils/track';

const LEGACY_FILE_BASE_URL = 'https://file.hoh516.com/huohonghuo';

const quickFilters = [
  { value: 'all', label: '全部商品' },
  { value: 'new', label: '新品优先' },
  { value: 'value', label: '高性价比' },
  { value: 'premium', label: '品质精选' }
];

const loading = ref(false);
const failed = ref(false);
const goods = ref([]);
const activeQuickFilter = ref('all');

const resolveImage = (value) => {
  if (!value) return '';
  if (/^https?:\/\//i.test(value)) return value;
  if (value.startsWith('/profile/')) return `${LEGACY_FILE_BASE_URL}${value}`;
  if (value.startsWith('/')) return `${getApiBaseUrl()}${value}`;
  return value;
};

const filteredGoods = computed(() => {
  const rows = [...goods.value];

  if (activeQuickFilter.value === 'new') {
    return rows.sort((a, b) => b.rank - a.rank);
  }

  if (activeQuickFilter.value === 'value') {
    return rows.sort((a, b) => a.price - b.price);
  }

  if (activeQuickFilter.value === 'premium') {
    return rows.sort((a, b) => b.price - a.price);
  }

  return rows;
});

const normalizeList = (res) => {
  const rows = Array.isArray(res) ? res : res?.items || res?.list || [];
  return rows.map((item, idx) => {
    const price = Number(item.price ?? item.sale_price ?? 0);
    const marketPrice = Number(item.market_price ?? 0);
    const category = item.category_name || item.tag || '精选';
    const rank = Number(item.sort ?? item.rank ?? rows.length - idx);

    return {
      id: item.id || item.product_id || `product-${idx}`,
      title: item.name || item.title || '未命名商品',
      desc: item.description || item.desc || '暂无描述',
      price: Number(price.toFixed(2)),
      originPrice: marketPrice > price ? marketPrice.toFixed(2) : '',
      tag: item.tag || category,
      rank,
      quickTag: price >= 999 ? '甄选' : price <= 99 ? '实惠' : '',
      image: resolveImage(item.image || item.main_image || item.cover || item.gallery?.[0])
    };
  });
};

const fetchList = async () => {
  loading.value = true;
  failed.value = false;
  try {
    const res = await packageApi.list({ page: 1, page_size: 60 });
    goods.value = normalizeList(res);
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
};

const goDetail = (id) => {
  trackEvent('packages_click_item', { id, filter: activeQuickFilter.value });
  uni.navigateTo({ url: `/subpackages/package/detail?id=${id}` });
};

const selectQuickFilter = (value) => {
  if (activeQuickFilter.value === value) return;
  activeQuickFilter.value = value;
  trackEvent('packages_select_filter', { filter: value });
};

onMounted(() => {
  trackPageView('packages_list');
  fetchList();
});
</script>

<style scoped>
@import '@/styles/common.css';

.packages-page {
  padding-bottom: 36rpx;
}

.filter-strip {
  display: flex;
  gap: 12rpx;
  overflow-x: auto;
  padding-bottom: 6rpx;
}

.filter-chip {
  flex-shrink: 0;
  padding: 14rpx 24rpx;
  border-radius: 999rpx;
  background: rgba(255, 249, 242, 0.9);
  color: #8d735a;
  font-size: 24rpx;
  border: 1rpx solid rgba(198, 161, 124, 0.16);
}

.filter-chip.active {
  background: linear-gradient(135deg, rgba(201, 143, 88, 0.18), rgba(191, 127, 66, 0.1));
  color: #a16532;
  border-color: rgba(191, 127, 66, 0.24);
  box-shadow: 0 10rpx 20rpx rgba(167, 109, 54, 0.08);
}

.goods-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18rpx;
}

.goods-card {
  overflow: hidden;
  border-radius: 24rpx;
  background: rgba(255, 255, 255, 0.96);
  border: 1rpx solid rgba(198, 161, 124, 0.14);
  box-shadow: 0 14rpx 28rpx rgba(146, 103, 63, 0.08);
}

.goods-cover {
  width: 100%;
  height: 260rpx;
  display: block;
  background: #f4eadf;
}

.goods-cover-fallback {
  background: linear-gradient(135deg, #f1dec9, #e7c8a4 46%, #d8af83);
}

.goods-body {
  padding: 16rpx 16rpx 18rpx;
}

.goods-tag-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8rpx;
}

.goods-tag,
.goods-quick-tag {
  display: inline-flex;
  align-items: center;
  height: 38rpx;
  padding: 0 12rpx;
  border-radius: 999rpx;
  font-size: 20rpx;
}

.goods-tag {
  color: #9a6333;
  background: rgba(190, 133, 78, 0.12);
}

.goods-quick-tag {
  color: #fffaf4;
  background: #bd7d44;
}

.goods-title {
  margin-top: 12rpx;
  min-height: 76rpx;
  font-size: 28rpx;
  line-height: 1.35;
  font-weight: 700;
  color: #4f321b;
}

.goods-desc {
  margin-top: 8rpx;
  min-height: 64rpx;
  font-size: 22rpx;
  line-height: 1.45;
  color: #856a53;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.goods-foot {
  margin-top: 14rpx;
}

.interactive {
  transition: transform 180ms ease, opacity 180ms ease;
}

.interactive:active {
  transform: scale(0.98);
  opacity: 0.92;
}
</style>
