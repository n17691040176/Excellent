<template>
  <view class="packages-page">
    <view class="packages-topbar">
      <view class="brand-wrap">
        <view class="brand-mark">ZK</view>
        <view class="brand-name">ZKMALL</view>
      </view>
      <view class="page-title">分类</view>
      <view class="topbar-spacer" />
    </view>

    <view class="search-shell">
      <view class="search-field">
        <view class="search-icon">搜</view>
        <input
          v-model.trim="searchKeyword"
          class="search-input"
          placeholder="请输入关键词"
          confirm-type="search"
          @confirm="submitSearch"
        />
        <view class="search-btn interactive" @click="submitSearch">搜索</view>
      </view>
    </view>

    <view v-if="loading" class="catalog-shell catalog-shell-state">
      <StateView title="商品加载中..." custom-class="catalog-state-card" />
    </view>
    <view
      v-else-if="failed"
      class="catalog-shell catalog-shell-state"
    >
      <StateView
        title="商品加载失败，请重试"
        :show-retry="true"
        custom-class="catalog-state-card"
        @retry="fetchList"
      />
    </view>
    <view
      v-else-if="!categories.length"
      class="catalog-shell catalog-shell-state"
    >
      <StateView
        title="暂无分类商品"
        description="换个关键词再试试"
        custom-class="catalog-state-card"
      />
    </view>

    <view v-else class="catalog-shell">
      <view class="category-rail">
        <view
          v-for="item in categories"
          :key="item.key"
          class="category-item interactive"
          :class="{ active: item.key === selectedCategory }"
          @click="selectCategory(item.key)"
        >
          <view class="category-item-text">{{ item.label }}</view>
        </view>
      </view>

      <view class="goods-panel">
        <view class="goods-matrix">
          <view
            v-for="item in currentCategoryGoods"
            :key="item.id"
            class="goods-tile interactive"
            @click="goDetail(item.id)"
          >
            <view class="goods-visual">
              <image
                v-if="item.image"
                class="goods-image"
                :src="item.image"
                mode="aspectFit"
                lazy-load
              />
              <view v-else class="goods-image-fallback">{{ item.fallbackLabel }}</view>
            </view>
            <view class="goods-name">{{ item.title }}</view>
          </view>
        </view>

        <view v-if="!currentCategoryGoods.length" class="panel-empty">
          当前分类暂无商品
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import StateView from '@/components/StateView.vue';
import { packageApi } from '@/api/modules';
import { getApiBaseUrl } from '@/config/index';
import { trackEvent, trackPageView } from '@/utils/track';

const LEGACY_FILE_BASE_URL = 'https://file.hoh516.com/huohonghuo';

const loading = ref(false);
const failed = ref(false);
const goods = ref([]);
const selectedCategory = ref('');
const searchKeyword = ref('');

const normalizeText = (value) => String(value ?? '').trim();

const resolveImage = (value) => {
  if (!value) return '';
  if (/^https?:\/\//i.test(value)) return value;
  if (value.startsWith('/profile/')) return `${LEGACY_FILE_BASE_URL}${value}`;
  if (value.startsWith('/')) return `${getApiBaseUrl()}${value}`;
  return value;
};

const normalizeCategory = (value) => {
  const label = normalizeText(value);
  return label || '精选分类';
};

const buildFallbackLabel = (title) => {
  const compact = normalizeText(title).replace(/\s+/g, '');
  return (compact || '商品').slice(0, 2).toUpperCase();
};

const normalizeList = (res) => {
  const rows = Array.isArray(res) ? res : res?.items || res?.list || [];
  return rows.map((item, idx) => {
    const title = normalizeText(item.name || item.title || `商品${idx + 1}`);
    const desc = normalizeText(item.description || item.desc || '');
    const categoryLabel = normalizeCategory(item.category_name || item.tag);

    return {
      id: item.id || item.product_id || `product-${idx}`,
      title,
      desc,
      image: resolveImage(item.image || item.main_image || item.cover || item.gallery?.[0]),
      categoryKey: categoryLabel,
      categoryLabel,
      fallbackLabel: buildFallbackLabel(title),
      searchText: `${title} ${desc} ${categoryLabel}`.toLowerCase(),
    };
  });
};

const filteredGoods = computed(() => {
  const keyword = normalizeText(searchKeyword.value).toLowerCase();
  if (!keyword) return goods.value;
  return goods.value.filter((item) => item.searchText.includes(keyword));
});

const categories = computed(() => {
  const bucket = new Map();
  filteredGoods.value.forEach((item) => {
    if (!bucket.has(item.categoryKey)) {
      bucket.set(item.categoryKey, {
        key: item.categoryKey,
        label: item.categoryLabel,
      });
    }
  });
  return Array.from(bucket.values());
});

watch(
  categories,
  (rows) => {
    if (!rows.length) {
      selectedCategory.value = '';
      return;
    }
    if (!rows.some((item) => item.key === selectedCategory.value)) {
      selectedCategory.value = rows[0].key;
    }
  },
  { immediate: true }
);

const currentCategoryGoods = computed(() => {
  if (!selectedCategory.value) return [];
  return filteredGoods.value.filter((item) => item.categoryKey === selectedCategory.value);
});

const fetchList = async () => {
  loading.value = true;
  failed.value = false;
  try {
    const res = await packageApi.list({ page: 1, page_size: 120 });
    goods.value = normalizeList(res);
  } catch (error) {
    failed.value = true;
  } finally {
    loading.value = false;
  }
};

const goDetail = (id) => {
  trackEvent('packages_click_item', {
    id,
    category: selectedCategory.value,
    keyword: normalizeText(searchKeyword.value),
  });
  uni.navigateTo({ url: `/subpackages/package/detail?id=${id}` });
};

const selectCategory = (key) => {
  if (selectedCategory.value === key) return;
  selectedCategory.value = key;
  trackEvent('packages_select_category', {
    category: key,
    keyword: normalizeText(searchKeyword.value),
  });
};

const submitSearch = () => {
  trackEvent('packages_search', {
    keyword: normalizeText(searchKeyword.value),
    result_count: filteredGoods.value.length,
  });
};

onMounted(() => {
  trackPageView('packages_list');
  fetchList();
});
</script>

<style scoped>
@import '@/styles/common.css';

.packages-page {
  min-height: calc(100vh - 24rpx);
  padding: 16rpx 12rpx 30rpx;
  box-sizing: border-box;
  background:
    radial-gradient(circle at 0% 0%, rgba(255, 184, 125, 0.2), transparent 30%),
    radial-gradient(circle at 100% 0%, rgba(255, 136, 88, 0.14), transparent 26%),
    linear-gradient(180deg, #fff9f3 0%, #fff3e8 46%, #fffaf7 100%);
}

.packages-topbar {
  min-height: 72rpx;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  color: #222733;
}

.brand-wrap {
  display: inline-flex;
  align-items: center;
  gap: 8rpx;
  justify-self: start;
}

.brand-mark {
  width: 40rpx;
  height: 40rpx;
  border-radius: 12rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #fff1e2 0%, #ffe0bf 100%);
  color: #ff7a00;
  font-size: 18rpx;
  font-weight: 900;
  letter-spacing: 0.6rpx;
  box-shadow: inset 0 0 0 1rpx rgba(255, 145, 53, 0.12);
}

.brand-name {
  font-size: 28rpx;
  font-weight: 800;
  letter-spacing: 0.4rpx;
  color: #ff7a00;
}

.page-title {
  justify-self: center;
  font-size: 34rpx;
  font-weight: 800;
  letter-spacing: 1rpx;
}

.topbar-spacer {
  width: 120rpx;
  justify-self: end;
}

.search-shell {
  margin-top: 14rpx;
}

.search-field {
  min-height: 72rpx;
  display: flex;
  align-items: center;
  gap: 10rpx;
  padding: 6rpx 8rpx 6rpx 16rpx;
  border-radius: 999rpx;
  background: transparent;
  border: 1rpx solid rgba(206, 213, 222, 0.92);
  box-shadow: none;
}

.search-icon {
  width: 32rpx;
  height: 32rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #b68866;
  font-size: 18rpx;
  font-weight: 700;
  border: 1rpx solid rgba(192, 155, 123, 0.24);
}

.search-input {
  flex: 1;
  min-width: 0;
  height: 60rpx;
  font-size: 22rpx;
  color: #5c412b;
}

.search-btn {
  flex-shrink: 0;
  min-width: 108rpx;
  height: 56rpx;
  border-radius: 999rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #ff7a00, #ff5f1f);
  color: #fff;
  font-size: 22rpx;
  font-weight: 700;
}

.catalog-shell {
  margin-top: 18rpx;
  display: grid;
  grid-template-columns: 148rpx minmax(0, 1fr);
  min-height: calc(100vh - 250rpx);
  border-radius: 0;
  overflow: visible;
  background: transparent;
  box-shadow: none;
}

.catalog-shell-state {
  display: block;
  min-height: 520rpx;
  padding: 12rpx 0 0;
  box-sizing: border-box;
}

.category-rail {
  padding: 18rpx 0;
  background: linear-gradient(180deg, #f6f1ea 0%, #eee7de 100%);
  border-right: 1rpx solid rgba(210, 186, 164, 0.24);
}

.category-item {
  position: relative;
  min-height: 78rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 14rpx;
  color: #7b6a5d;
}

.category-item.active {
  color: #ff6a00;
  font-weight: 700;
  background: rgba(255, 138, 42, 0.08);
}

.category-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 16rpx;
  bottom: 16rpx;
  width: 6rpx;
  border-radius: 0 999rpx 999rpx 0;
  background: linear-gradient(180deg, #ff8a2a, #ff5f1f);
}

.category-item-text {
  font-size: 24rpx;
  line-height: 1.3;
  text-align: center;
}

.goods-panel {
  padding: 18rpx 16rpx;
  background: transparent;
  box-sizing: border-box;
}

.goods-matrix {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16rpx 12rpx;
}

.goods-tile {
  min-width: 0;
}

.goods-visual {
  height: 118rpx;
  border-radius: 18rpx;
  background: linear-gradient(180deg, #ffffff 0%, #f4f4f4 100%);
  border: 1rpx solid rgba(223, 223, 223, 0.72);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.goods-image {
  width: 100%;
  height: 100%;
}

.goods-image-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #ffd4a6, #ffb566 48%, #ff8a2a);
  color: #fff;
  font-size: 26rpx;
  font-weight: 800;
  letter-spacing: 1rpx;
}

.goods-name {
  margin-top: 10rpx;
  min-height: 56rpx;
  font-size: 22rpx;
  line-height: 1.3;
  color: #5d4633;
  text-align: center;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.panel-empty {
  padding: 120rpx 0;
  text-align: center;
  font-size: 24rpx;
  color: #8e7560;
}

:deep(.catalog-state-card) {
  background: transparent;
  border: 1rpx solid rgba(255, 160, 84, 0.24);
  box-shadow: none;
}

:deep(.catalog-state-card .state-title) {
  color: #4f321a;
}

:deep(.catalog-state-card .state-desc) {
  color: #8e7560;
}

.interactive {
  transition: transform 180ms ease, opacity 180ms ease;
}

.interactive:active {
  transform: scale(0.98);
  opacity: 0.92;
}
</style>
