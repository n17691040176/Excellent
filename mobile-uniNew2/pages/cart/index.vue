<template>
  <view class="cart-page">
    <!-- Header -->
    <view class="page-header">
      <view class="header-content">
        <view class="logo-mark">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
            <path d="M6 2L3 6V20C3 20.5304 3.21071 21.0391 3.58579 21.4142C3.96086 21.7893 4.46957 22 5 22H19C19.5304 22 20.0391 21.7893 20.4142 21.4142C20.7893 21.0391 21 20.5304 21 20V6L18 2H6Z" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M3 6H21" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M16 10C16 11.0609 15.5786 12.0783 14.8284 12.8284C14.0783 13.5786 13.0609 14 12 14C10.9391 14 9.92172 13.5786 9.17157 12.8284C8.42143 12.0783 8 11.0609 8 10" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </view>
        <text class="page-title">购物车</text>
      </view>
      <view v-if="cartItems.length" class="edit-btn" @click="toggleEdit">
        {{ isEditMode ? '完成' : '编辑' }}
      </view>
    </view>

    <!-- Cart Content -->
    <view class="cart-content">
      <!-- Loading State -->
      <view v-if="loading" class="loading-state">
        <view v-for="i in 3" :key="i" class="skeleton-item">
          <view class="skeleton skeleton-check" />
          <view class="skeleton skeleton-img" />
          <view class="skeleton-info">
            <view class="skeleton skeleton-title" />
            <view class="skeleton skeleton-price" />
          </view>
        </view>
      </view>

      <!-- Empty State -->
      <view v-else-if="!cartItems.length" class="empty-state">
        <svg class="empty-icon" width="120" height="120" viewBox="0 0 24 24" fill="none">
          <circle cx="9" cy="21" r="1" fill="currentColor"/>
          <circle cx="20" cy="21" r="1" fill="currentColor"/>
          <path d="M1 1H5L7.68 14.39C7.77144 14.8504 8.02191 15.264 8.38755 15.5583C8.75318 15.8526 9.2107 16.009 9.68 16H19.4C19.8693 16.009 20.3268 15.8526 20.6925 15.5583C21.0581 15.264 21.3086 14.8504 21.4 14.39L23 6H6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <text class="empty-title">购物车是空的</text>
        <text class="empty-desc">去挑选心仪的商品吧</text>
        <view class="empty-btn" @click="goShopping">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M5 12H19M12 5L19 12L12 19" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          去逛逛
        </view>
      </view>

      <!-- Cart List -->
      <view v-else class="cart-list">
        <view
          v-for="item in cartItems"
          :key="item.id"
          class="cart-item"
          :class="{ pressed: pressedId === item.id }"
          @click="goDetail(item)"
          @touchstart="pressedId = item.id"
          @touchend="pressedId = null"
          @touchcancel="pressedId = null"
        >
          <!-- Checkbox -->
          <view
            class="check-wrap"
            :class="{ checked: item.selected }"
            @click.stop="toggleSelect(item)"
          >
            <svg v-if="item.selected" width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M20 6L9 17L4 12" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </view>

          <!-- Item Image -->
          <view class="item-image">
            <image
              v-if="item.image"
              class="image"
              :src="item.image"
              mode="aspectFill"
            />
            <view v-else class="image-placeholder">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
                <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" stroke-width="1.5" opacity="0.3"/>
                <circle cx="8.5" cy="8.5" r="1.5" fill="currentColor" opacity="0.3"/>
                <path d="M21 15L16 10.5V10C16 8.89543 15.1046 8 14 8H10C8.89543 8 8 8.89543 8 10V10.5L3 15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" opacity="0.3"/>
              </svg>
            </view>
          </view>

          <!-- Item Info -->
          <view class="item-info">
            <text class="item-title">{{ item.title }}</text>
            <text class="item-desc">{{ item.spec || '默认规格' }}</text>
            <view class="item-footer">
              <view class="item-price">
                <text class="price-symbol">¥</text>
                <text class="price-value">{{ item.price }}</text>
              </view>
              <view class="quantity-wrap">
                <view
                  class="qty-btn minus"
                  @click.stop="decrease(item)"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M5 12H19" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                  </svg>
                </view>
                <text class="qty-num">{{ item.quantity }}</text>
                <view
                  class="qty-btn plus"
                  @click.stop="increase(item)"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M12 5V19M5 12H19" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                  </svg>
                </view>
              </view>
            </view>
          </view>

          <!-- Delete Button (Edit Mode) -->
          <view
            v-if="isEditMode"
            class="delete-btn"
            @click.stop="removeItem(item)"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M3 6H5H21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M8 6V4C8 3.46957 8.21071 2.96086 8.58579 2.58579C8.96086 2.21071 9.46957 2 10 2H14C14.5304 2 15.0391 2.21071 15.4142 2.58579C15.7893 2.96086 16 3.46957 16 4V6M19 6V20C19 20.5304 18.7893 21.0391 18.4142 21.4142C18.0391 21.7893 17.5304 22 17 22H7C6.46957 22 5.96086 21.7893 5.58579 21.4142C5.21071 21.0391 5 20.5304 5 20V6H19Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </view>
        </view>
      </view>
    </view>

    <!-- Bottom Bar -->
    <view v-if="cartItems.length" class="bottom-bar">
      <view class="bar-content">
        <!-- Select All -->
        <view class="select-all" @click="toggleSelectAll">
          <view class="check-wrap" :class="{ checked: isAllSelected }">
            <svg v-if="isAllSelected" width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M20 6L9 17L4 12" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </view>
          <text class="select-text">全选</text>
        </view>

        <!-- Total -->
        <view class="total-wrap">
          <text class="total-label">合计：</text>
          <text class="total-price">
            <text class="total-symbol">¥</text>
            {{ totalPrice }}
          </text>
        </view>

        <!-- Checkout / Delete Button -->
        <view
          v-if="!isEditMode"
          class="checkout-btn"
          :class="{ disabled: !selectedCount }"
          @click="checkout"
        >
          结算{{ selectedCount ? `(${selectedCount})` : '' }}
        </view>
        <view
          v-else
          class="checkout-btn delete"
          :class="{ disabled: !selectedCount }"
          @click="batchDelete"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M3 6H5H21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M8 6V4C8 3.46957 8.21071 2.96086 8.58579 2.58579C8.96086 2.21071 9.46957 2 10 2H14C14.5304 2 15.0391 2.21071 15.4142 2.58579C15.7893 2.96086 16 3.46957 16 4V6M19 6V20C19 20.5304 18.7893 21.0391 18.4142 21.4142C18.0391 21.7893 17.5304 22 17 22H7C6.46957 22 5.96086 21.7893 5.58579 21.4142C5.21071 21.0391 5 20.5304 5 20V6H19Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          删除
        </view>
      </view>
    </view>

    <view class="bottom-space" />
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import { commerceApi } from '@/api/modules';
import { pickListPayload } from '@/utils/adapters';
import { trackEvent, trackPageView } from '@/utils/track';

const loading = ref(false);
const cartItems = ref([]);
const isEditMode = ref(false);
const pressedId = ref(null);

const toCartView = (item = {}) => ({
  id: item.id || item.cart_item_id,
  productId: item.product_id || item.product?.id,
  title: item.title || item.product?.title || item.product?.name || '未命名商品',
  spec: item.product?.category_name || item.product?.tag || '默认规格',
  price: Number(item.price ?? item.product?.price ?? item.product?.sale_price ?? 0).toFixed(2),
  quantity: Number(item.quantity || 1),
  image: item.image || item.product?.image || item.product?.main_image || item.product?.cover || '',
  selected: Boolean(item.selected)
});

const isAllSelected = computed(() => cartItems.value.length > 0 && cartItems.value.every((item) => item.selected));
const selectedRows = computed(() => cartItems.value.filter((item) => item.selected));
const selectedCount = computed(() => selectedRows.value.length);
const totalPrice = computed(() => selectedRows.value
  .reduce((sum, item) => sum + Number(item.price || 0) * Number(item.quantity || 0), 0)
  .toFixed(2));

async function loadCart() {
  loading.value = true;
  try {
    const rows = pickListPayload(await commerceApi.cart());
    cartItems.value = rows.map(toCartView);
  } catch (error) {
    uni.showToast({ title: '购物车加载失败', icon: 'none' });
  } finally {
    loading.value = false;
  }
}

async function toggleSelect(item) {
  try {
    const updated = await commerceApi.updateCartItem(item.id, { selected: !item.selected });
    Object.assign(item, toCartView(updated));
  } catch (error) {
    uni.showToast({ title: '更新失败', icon: 'none' });
  }
}

async function toggleSelectAll() {
  const selected = !isAllSelected.value;
  try {
    const rows = await Promise.all(cartItems.value.map((item) => commerceApi.updateCartItem(item.id, { selected })));
    cartItems.value = rows.map(toCartView);
  } catch (error) {
    uni.showToast({ title: '全选更新失败', icon: 'none' });
    await loadCart();
  }
}

async function changeQuantity(item, quantity, action) {
  const next = Math.max(1, Number(quantity || 1));
  try {
    const updated = await commerceApi.updateCartItem(item.id, { quantity: next });
    Object.assign(item, toCartView(updated));
    trackEvent('cart_quantity_change', { id: item.id, quantity: next, action });
  } catch (error) {
    uni.showToast({ title: '数量更新失败', icon: 'none' });
  }
}

const increase = (item) => changeQuantity(item, item.quantity + 1, 'increase');
const decrease = (item) => {
  if (item.quantity > 1) changeQuantity(item, item.quantity - 1, 'decrease');
};

async function removeItem(item) {
  try {
    await commerceApi.removeCartItem(item.id);
    cartItems.value = cartItems.value.filter((row) => row.id !== item.id);
    trackEvent('cart_remove_item', { id: item.id });
  } catch (error) {
    uni.showToast({ title: '删除失败', icon: 'none' });
  }
}

async function batchDelete() {
  if (!selectedCount.value) return;
  const ids = selectedRows.value.map((item) => item.id);
  try {
    await Promise.all(ids.map((id) => commerceApi.removeCartItem(id)));
    cartItems.value = cartItems.value.filter((item) => !ids.includes(item.id));
    trackEvent('cart_batch_delete', { count: ids.length });
  } catch (error) {
    uni.showToast({ title: '批量删除失败', icon: 'none' });
    await loadCart();
  }
}

const toggleEdit = () => {
  isEditMode.value = !isEditMode.value;
  trackEvent('cart_toggle_edit', { isEditMode: isEditMode.value });
};

const goShopping = () => {
  trackEvent('cart_go_shopping');
  uni.switchTab({ url: '/pages/packages/list' });
};

const goDetail = (item) => {
  if (isEditMode.value || !item.productId) return;
  trackEvent('cart_item_click', { id: item.productId });
  uni.navigateTo({ url: `/subpackages/package/detail?id=${item.productId}` });
};

const checkout = () => {
  if (!selectedCount.value) return;
  const ids = selectedRows.value.map((item) => item.id).join(',');
  trackEvent('cart_checkout', { count: selectedCount.value, amount: totalPrice.value });
  uni.navigateTo({ url: `/subpackages/order/confirm?cart_item_ids=${encodeURIComponent(ids)}` });
};

onShow(() => {
  trackPageView('cart');
  loadCart();
});
</script>

<style scoped>
@import '@/styles/common.css';

.cart-page {
  min-height: 100vh;
  background: var(--bg);
  padding-bottom: calc(env(safe-area-inset-bottom) + 140rpx);
}

/* ===== Header ===== */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24rpx 32rpx;
  padding-top: calc(24rpx + env(safe-area-inset-top));
  background: var(--card);
  border-bottom: 1rpx solid var(--border);
}

.header-content {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.logo-mark {
  width: 56rpx;
  height: 56rpx;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  display: flex;
  align-items: center;
  justify-content: center;
}

.page-title {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--text);
}

.edit-btn {
  font-size: var(--text-base);
  color: var(--primary);
  font-weight: var(--font-medium);
  padding: 8rpx 16rpx;
  transition: all var(--duration-fast) var(--ease-out);
}

.edit-btn:active {
  opacity: 0.7;
}

/* ===== Content ===== */
.cart-content {
  padding: 24rpx;
}

/* ===== Cart List ===== */
.cart-list {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.cart-item {
  display: flex;
  align-items: flex-start;
  gap: 24rpx;
  padding: 24rpx;
  background: var(--card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  position: relative;
  transition: all var(--duration-fast) var(--ease-out);
}

.cart-item:active,
.cart-item.pressed {
  transform: scale(0.99);
  box-shadow: var(--shadow-xs);
}

/* Checkbox */
.check-wrap {
  width: 44rpx;
  height: 44rpx;
  border-radius: var(--radius-sm);
  border: 2rpx solid var(--border);
  background: var(--card);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 60rpx;
  transition: all var(--duration-fast) var(--ease-out);
}

.check-wrap.checked {
  background: var(--primary);
  border-color: var(--primary);
}

.check-wrap:active {
  transform: scale(0.9);
}

/* Item Image */
.item-image {
  width: 160rpx;
  height: 160rpx;
  border-radius: var(--radius-md);
  overflow: hidden;
  flex-shrink: 0;
}

.image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #E2E8F0 0%, #CBD5E1 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}

/* Item Info */
.item-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.item-title {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 8rpx;
}

.item-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-bottom: 12rpx;
}

.item-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
}

.item-price {
  display: flex;
  align-items: baseline;
  gap: 2rpx;
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

/* Quantity Controls */
.quantity-wrap {
  display: flex;
  align-items: center;
  background: var(--bg);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.qty-btn {
  width: 56rpx;
  height: 56rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--card);
  color: var(--text);
  transition: all var(--duration-fast) var(--ease-out);
}

.qty-btn:active {
  background: var(--border);
}

.qty-btn.minus {
  border-right: 1rpx solid var(--border);
}

.qty-btn.plus {
  border-left: 1rpx solid var(--border);
}

.qty-num {
  width: 64rpx;
  text-align: center;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text);
}

/* Delete Button */
.delete-btn {
  position: absolute;
  right: 24rpx;
  top: 24rpx;
  width: 48rpx;
  height: 48rpx;
  border-radius: 50%;
  background: var(--danger);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast) var(--ease-out);
}

.delete-btn:active {
  transform: scale(0.9);
}

/* ===== Empty State ===== */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64rpx 32rpx;
  margin-top: 120rpx;
}

.empty-icon {
  color: var(--border);
  margin-bottom: 32rpx;
}

.empty-title {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--text);
  margin-bottom: 8rpx;
}

.empty-desc {
  font-size: var(--text-base);
  color: var(--text-muted);
  margin-bottom: 48rpx;
}

.empty-btn {
  display: flex;
  align-items: center;
  gap: 8rpx;
  padding: 16rpx 48rpx;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: white;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  border-radius: var(--radius-full);
  transition: all var(--duration-fast) var(--ease-out);
}

.empty-btn:active {
  transform: scale(0.98);
}

/* ===== Loading State ===== */
.loading-state {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.skeleton-item {
  display: flex;
  align-items: flex-start;
  gap: 24rpx;
  padding: 24rpx;
  background: var(--card);
  border-radius: var(--radius-lg);
}

.skeleton {
  background: linear-gradient(90deg, var(--border-light) 25%, var(--bg) 50%, var(--border-light) 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s infinite;
  border-radius: var(--radius-md);
}

.skeleton-check {
  width: 44rpx;
  height: 44rpx;
  flex-shrink: 0;
  margin-top: 60rpx;
}

.skeleton-img {
  width: 160rpx;
  height: 160rpx;
  flex-shrink: 0;
}

.skeleton-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.skeleton-title {
  height: 36rpx;
  width: 80%;
}

.skeleton-price {
  height: 32rpx;
  width: 40%;
}

@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ===== Bottom Bar ===== */
.bottom-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: calc(100rpx + env(safe-area-inset-bottom));
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-top: 1rpx solid var(--border);
  box-shadow: 0 -4rpx 20rpx rgba(0, 0, 0, 0.04);
}

.bar-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24rpx 32rpx;
  height: 100rpx;
}

.select-all {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.select-text {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.total-wrap {
  display: flex;
  align-items: baseline;
  gap: 4rpx;
}

.total-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.total-price {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--primary);
}

.total-symbol {
  font-size: var(--text-sm);
}

.checkout-btn {
  display: flex;
  align-items: center;
  gap: 8rpx;
  padding: 16rpx 32rpx;
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: white;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  border-radius: var(--radius-full);
  box-shadow: var(--shadow-primary);
  transition: all var(--duration-fast) var(--ease-out);
}

.checkout-btn:active {
  transform: scale(0.95);
}

.checkout-btn.disabled {
  opacity: 0.5;
}

.checkout-btn.delete {
  background: var(--danger);
  box-shadow: 0 8rpx 24rpx rgba(239, 68, 68, 0.25);
}

.bottom-space {
  height: 64rpx;
}

/* ===== Reduced Motion ===== */
@media (prefers-reduced-motion: reduce) {
  .edit-btn,
  .cart-item,
  .check-wrap,
  .qty-btn,
  .delete-btn,
  .empty-btn,
  .checkout-btn {
    transition: none;
  }

  .cart-item:active,
  .cart-item.pressed {
    transform: none;
  }
}
</style>
