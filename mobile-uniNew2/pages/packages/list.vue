<template>
  <view class="packages-page">
    <!-- Header -->
    <view class="page-header">
      <view class="header-content">
        <view class="logo-mark">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <path d="M14 3L3 9V19L14 25L25 19V9L14 3Z" stroke="white" stroke-width="2" stroke-linejoin="round"/>
            <path d="M14 3V25M3 9L25 19M25 9L3 19" stroke="white" stroke-width="2" stroke-linejoin="round"/>
          </svg>
        </view>
        <text class="page-title">商品分类</text>
      </view>
    </view>

    <!-- Search -->
    <view class="search-section">
      <view class="search-bar">
        <svg class="search-icon" width="36" height="36" viewBox="0 0 24 24" fill="none">
          <circle cx="11" cy="11" r="8" stroke="currentColor" stroke-width="2"/>
          <path d="M21 21L16.65 16.65" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        <input
          v-model.trim="searchKeyword"
          class="search-input"
          placeholder="搜索商品..."
          confirm-type="search"
          @confirm="submitSearch"
        />
        <view class="search-btn" @click="submitSearch">搜索</view>
      </view>
    </view>

    <!-- Content -->
    <view class="content-area">
      <!-- Category Sidebar -->
      <scroll-view class="category-sidebar" scroll-y enhanced show-scrollbar="false">
        <view
          class="category-item"
          :class="{ active: selectedCategory === '' }"
          @click="selectCategory('')"
        >
          <text class="tab-label">全部</text>
          <text class="tab-count">{{ filteredGoods.length }}</text>
        </view>
        <view
          v-for="cat in categories"
          :key="cat.key"
          class="category-item"
          :class="{ active: selectedCategory === cat.key }"
          @click="selectCategory(cat.key)"
        >
          <text class="tab-label">{{ cat.label }}</text>
          <text class="tab-count">{{ cat.count || 0 }}</text>
        </view>
      </scroll-view>

      <view class="goods-content">
        <!-- Loading State -->
        <view v-if="loading" class="loading-state">
          <view v-for="i in 6" :key="i" class="skeleton-card">
            <view class="skeleton skeleton-image" />
            <view class="skeleton-content">
              <view class="skeleton skeleton-title" />
              <view class="skeleton-footer">
                <view class="skeleton skeleton-price" />
              </view>
            </view>
          </view>
        </view>

        <!-- Error State -->
        <view v-else-if="failed" class="state-view">
          <svg class="state-icon error" width="120" height="120" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5"/>
            <path d="M12 8V12M12 16H12.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
          <text class="state-title">加载失败</text>
          <text class="state-desc">网络连接异常，请检查后重试</text>
          <view class="state-action" @click="fetchList">
            <text>重新加载</text>
          </view>
        </view>

        <!-- Empty State -->
        <view v-else-if="!currentGoods.length" class="state-view">
          <svg class="state-icon" width="120" height="120" viewBox="0 0 24 24" fill="none">
            <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" stroke-width="1.5"/>
            <path d="M3 9H21" stroke="currentColor" stroke-width="1.5"/>
            <path d="M9 21V9" stroke="currentColor" stroke-width="1.5"/>
          </svg>
          <text class="state-title">暂无商品</text>
          <text class="state-desc">该分类下还没有商品</text>
        </view>

        <!-- Product Grid -->
        <scroll-view v-else class="goods-panel" scroll-y enhanced>
          <view class="goods-grid">
            <view
              v-for="item in currentGoods"
              :key="item.id"
              class="goods-card"
              :class="{ pressed: pressedId === item.id }"
              @click="goDetail(item.id)"
              @touchstart="pressedId = item.id"
              @touchend="pressedId = null"
              @touchcancel="pressedId = null"
            >
              <view class="goods-image-wrap">
                <image
                  v-if="item.image"
                  class="goods-image"
                  :src="item.image"
                  mode="aspectFill"
                />
                <view v-else class="goods-placeholder">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
                    <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" stroke-width="1.5" opacity="0.3"/>
                    <circle cx="8.5" cy="8.5" r="1.5" fill="currentColor" opacity="0.3"/>
                    <path d="M21 15L16 10.5V10C16 8.89543 15.1046 8 14 8H10C8.89543 8 8 8.89543 8 10V10.5L3 15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" opacity="0.3"/>
                  </svg>
                </view>
              </view>
              <view class="goods-info">
                <text class="goods-title">{{ item.title }}</text>
                <view class="goods-footer">
                  <view class="goods-price">
                    <text class="price-symbol">¥</text>
                    <text class="price-value">{{ item.price }}</text>
                    <text class="price-original" v-if="item.originalPrice">¥{{ item.originalPrice }}</text>
                  </view>
                  <view class="goods-buy">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                      <path d="M12 5V19M5 12H19" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                  </view>
                </view>
              </view>
            </view>
          </view>
          <view class="list-bottom">
            <text v-if="currentGoods.length >= 20">—— 已加载全部 {{ currentGoods.length }} 件商品 ——</text>
          </view>
        </scroll-view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { packageApi, categoryApi } from '@/api/modules';
import { getApiBaseUrl } from '@/config/index';
import { trackEvent, trackPageView } from '@/utils/track';

const BASE_URL = 'https://file.h516.com/huohonghuo';

const loading = ref(false);
const failed = ref(false);
const goods = ref([]);
const categoryList = ref([]);
const selectedCategory = ref('');
const searchKeyword = ref('');
const pressedId = ref(null);

const normalizeText = (value) => String(value ?? '').trim();

const resolveImage = (value) => {
  if (!value) return '';
  if (/^https?:\/\//i.test(value)) return value;
  if (value.startsWith('/profile/')) return `${BASE_URL}${value}`;
  if (value.startsWith('/')) return `${getApiBaseUrl()}${value}`;
  return value;
};

const normalizeList = (res) => {
  const rows = Array.isArray(res) ? res : res?.items || res?.list || [];
  return rows.map((item, idx) => {
    const title = normalizeText(item.name || item.title || `商品${idx + 1}`);
    const price = Number(item.price ?? item.sale_price ?? 0);
    const originalPrice = Number(item.original_price ?? item.market_price ?? 0);
    const categoryId = String(item.category_id ?? '');
    const categoryName = normalizeText(item.category_name || item.category || '');

    return {
      id: item.id || item.product_id || `product-${idx}`,
      title,
      price: price.toFixed(2),
      originalPrice: originalPrice > price ? originalPrice.toFixed(2) : null,
      image: resolveImage(item.image || item.main_image || item.cover || item.gallery?.[0]),
      categoryId,
      categoryKey: categoryId || 'other',
      categoryLabel: categoryName || '其他',
      searchText: title.toLowerCase(),
    };
  });
};

const filteredGoods = computed(() => {
  const keyword = normalizeText(searchKeyword.value).toLowerCase();
  if (!keyword) return goods.value;
  return goods.value.filter((item) => item.searchText.includes(keyword));
});

const categories = computed(() => {
  const counts = filteredGoods.value.reduce((bucket, item) => {
    bucket.set(item.categoryKey, (bucket.get(item.categoryKey) || 0) + 1);
    return bucket;
  }, new Map());
  const activeCats = categoryList.value.filter((c) => c.status === 'active');
  if (activeCats.length) {
    return activeCats.map((c) => ({
      key: String(c.id),
      label: c.name,
      count: counts.get(String(c.id)) || 0,
    }));
  }
  const bucket = new Map();
  filteredGoods.value.forEach((item) => {
    if (!item.categoryKey || item.categoryKey === 'other') return;
    const existing = bucket.get(item.categoryKey);
    if (existing) {
      existing.count++;
    } else {
      bucket.set(item.categoryKey, {
        key: item.categoryKey,
        label: item.categoryLabel,
        count: 1,
      });
    }
  });
  return Array.from(bucket.values()).sort((a, b) => b.count - a.count);
});

watch(
  categories,
  (rows) => {
    if (!rows.length) {
      selectedCategory.value = '';
      return;
    }
    if (!rows.some((item) => item.key === selectedCategory.value)) {
      selectedCategory.value = '';
    }
  },
  { immediate: true }
);

const currentGoods = computed(() => {
  if (!selectedCategory.value) return filteredGoods.value;
  return filteredGoods.value.filter((item) => item.categoryKey === selectedCategory.value);
});

const fetchCategories = async () => {
  try {
    const res = await categoryApi.list();
    categoryList.value = Array.isArray(res) ? res : res?.data || res?.list || [];
  } catch (error) {
    categoryList.value = [];
  }
};

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
  trackEvent('packages_click_item', { id, category: selectedCategory.value });
  uni.navigateTo({ url: `/subpackages/package/detail?id=${id}` });
};

const selectCategory = (key) => {
  if (selectedCategory.value === key) return;
  selectedCategory.value = key;
  trackEvent('packages_select_category', { category: key || 'all' });
};

const submitSearch = () => {
  trackEvent('packages_search', { keyword: searchKeyword.value, result_count: filteredGoods.value.length });
};

onMounted(() => {
  trackPageView('packages_list');
  fetchCategories();
  fetchList();
});
</script>

<style scoped>
@import '@/styles/common.css';

.packages-page {
  min-height: 100vh;
  background: var(--bg);
  display: flex;
  flex-direction: column;
}

/* ===== Header ===== */
.page-header {
  padding: 28rpx 32rpx;
  padding-top: calc(28rpx + env(safe-area-inset-top));
  background: var(--card);
  border-bottom: 1rpx solid var(--border-light);
}

.header-content {
  display: flex;
  align-items: center;
  gap: 20rpx;
}

.logo-mark {
  width: 64rpx;
  height: 64rpx;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-primary);
}

.page-title {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--text);
}

/* ===== Search ===== */
.search-section {
  padding: 24rpx 32rpx;
  background: var(--card);
}

.search-bar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 88rpx;
  padding: 0 28rpx;
  background: var(--bg);
  border-radius: var(--radius-full);
  box-shadow: var(--shadow-sm);
}

.search-icon {
  color: var(--text-muted);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  height: 100%;
  font-size: var(--text-base);
  color: var(--text);
}

.search-input::placeholder {
  color: var(--text-muted);
}

.search-btn {
  padding: 12rpx 32rpx;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: white;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  border-radius: var(--radius-full);
  flex-shrink: 0;
  box-shadow: var(--shadow-primary);
}

/* ===== Content ===== */
.content-area {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-height: 0;
}

.category-sidebar {
  width: 176rpx;
  flex-shrink: 0;
  background: var(--card);
  border-right: 1rpx solid var(--border-light);
  -webkit-overflow-scrolling: touch;
}

.category-item {
  min-height: 104rpx;
  padding: 22rpx 18rpx;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8rpx;
  position: relative;
  color: var(--text-muted);
  transition: all var(--duration-fast) var(--ease-out);
}

.category-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 24rpx;
  bottom: 24rpx;
  width: 6rpx;
  border-radius: 0 var(--radius-full) var(--radius-full) 0;
  background: transparent;
}

.category-item.active {
  background: var(--bg);
}

.category-item.active::before {
  background: var(--primary);
}

.tab-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: currentColor;
  line-height: 1.35;
  word-break: break-word;
}

.tab-count {
  font-size: 22rpx;
  color: var(--text-muted);
}

.category-item.active .tab-label {
  color: var(--primary);
  font-weight: var(--font-semibold);
}

.goods-content {
  flex: 1;
  min-width: 0;
  display: flex;
  overflow: hidden;
}

/* ===== Loading State ===== */
.loading-state {
  flex: 1;
  padding: 24rpx;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24rpx;
  align-content: start;
}

.skeleton-card {
  background: var(--card);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.skeleton-image {
  width: 100%;
  height: 340rpx;
}

.skeleton-content {
  padding: 24rpx;
}

.skeleton-title {
  height: 32rpx;
  margin-bottom: 20rpx;
}

.skeleton-footer {
  display: flex;
  align-items: center;
}

.skeleton-price {
  width: 120rpx;
  height: 36rpx;
}

/* ===== State View (Empty/Error) ===== */
.state-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64rpx;
}

.state-icon {
  color: var(--border);
  margin-bottom: 32rpx;
}

.state-icon.error {
  color: var(--error);
}

.state-title {
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--text);
  margin-bottom: 12rpx;
}

.state-desc {
  font-size: var(--text-base);
  color: var(--text-muted);
  margin-bottom: 40rpx;
}

.state-action {
  display: flex;
  align-items: center;
  gap: 12rpx;
  padding: 20rpx 40rpx;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: white;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  border-radius: var(--radius-full);
}

.state-action:active {
  opacity: 0.9;
  transform: scale(0.98);
}

/* ===== Goods Panel ===== */
.goods-panel {
  flex: 1;
  height: 100%;
  padding: 20rpx;
  box-sizing: border-box;
  -webkit-overflow-scrolling: touch;
}

.goods-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20rpx;
}

.goods-card {
  background: var(--card);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow);
  transition: all var(--duration-normal) var(--ease-out);
}

.goods-card:active,
.goods-card.pressed {
  transform: scale(0.97);
  box-shadow: var(--shadow-sm);
}

.goods-image-wrap {
  width: 100%;
  aspect-ratio: 1;
  overflow: hidden;
}

.goods-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.goods-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #E2E8F0 0%, #CBD5E1 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}

.goods-info {
  padding: 20rpx;
}

.goods-title {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text);
  line-height: 1.5;
  margin-bottom: 16rpx;
  min-height: 2.4em;
}

.goods-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.goods-price {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 4rpx;
}

.price-symbol {
  font-size: var(--text-sm);
  color: var(--primary);
  font-weight: var(--font-semibold);
}

.price-value {
  font-size: var(--text-lg);
  color: var(--primary);
  font-weight: var(--font-bold);
}

.price-original {
  font-size: 22rpx;
  color: var(--text-muted);
  text-decoration: line-through;
  margin-left: 8rpx;
}

.goods-buy {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 60rpx;
  height: 60rpx;
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
  color: white;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-primary);
  transition: all var(--duration-fast) var(--ease-out);
}

.goods-buy:active {
  transform: scale(0.9);
  box-shadow: var(--shadow-sm);
}

/* ===== List Bottom ===== */
.list-bottom {
  text-align: center;
  padding: 48rpx 0;
}

.list-bottom text {
  font-size: var(--text-sm);
  color: var(--text-muted);
}

/* ===== Reduced Motion ===== */
@media (prefers-reduced-motion: reduce) {
  .goods-card,
  .state-action,
  .goods-buy,
  .category-item {
    transition: none;
  }

  .goods-card:active,
  .goods-card.pressed {
    transform: none;
  }
}
</style>
