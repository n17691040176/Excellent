<template>
  <view class="tabbar-wrap">
    <view class="tabbar" :class="{ 'safe-area': hasSafeArea }">
      <view
        v-for="(item, index) in tabs"
        :key="item.pagePath"
        class="tab-item"
        :class="{ active: selected === index }"
        @click="switchTab(index)"
      >
        <!-- Tab Icon (Image) -->
        <image
          class="tab-icon-img"
          :src="selected === index ? item.activeIcon : item.icon"
          mode="aspectFit"
        />
        <!-- Tab Label -->
        <text class="tab-label">{{ item.text }}</text>
        <!-- Active Indicator -->
        <view v-if="selected === index" class="tab-indicator" />
        <!-- Badge (for cart) -->
        <view v-if="item.badge && item.badge > 0" class="tab-badge">
          <text>{{ item.badge > 99 ? '99+' : item.badge }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  data() {
    return {
      selected: 0,
      hasSafeArea: true,
      tabs: [
        {
          pagePath: '/pages/home/index',
          text: '首页',
          icon: '/static/tabbar/home.png',
          activeIcon: '/static/tabbar/home-active.png'
        },
        {
          pagePath: '/pages/packages/list',
          text: '分类',
          icon: '/static/tabbar/packages.png',
          activeIcon: '/static/tabbar/packages-active.png'
        },
        {
          pagePath: '/pages/cart/index',
          text: '购物车',
          icon: '/static/tabbar/life.png',
          activeIcon: '/static/tabbar/life-active.png',
          badge: 0
        },
        {
          pagePath: '/pages/profile/index',
          text: '我的',
          icon: '/static/tabbar/profile.png',
          activeIcon: '/static/tabbar/profile-active.png'
        }
      ]
    };
  },
  attached() {
    this.syncSelected();
    this.checkSafeArea();
  },
  pageLifetimes: {
    show() {
      this.syncSelected();
    }
  },
  methods: {
    checkSafeArea() {
      const systemInfo = uni.getSystemInfoSync();
      this.hasSafeArea = systemInfo.safeAreaInsets?.bottom > 0;
    },
    syncSelected() {
      const pages = getCurrentPages();
      const current = pages[pages.length - 1];
      const route = current?.route ? `/${current.route}` : '';
      const matched = this.tabs.findIndex(tab => tab.pagePath === route);
      this.selected = matched >= 0 ? matched : 0;
    },
    switchTab(index) {
      if (this.selected === index) return;
      this.selected = index;
      const target = this.tabs[index];
      if (target) {
        uni.switchTab({ url: target.pagePath });
      }
    }
  }
};
</script>

<style scoped>
.tabbar-wrap {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: var(--z-fixed);
  padding: 0 var(--space-4);
  padding-bottom: env(safe-area-inset-bottom);
}

.tabbar {
  display: flex;
  align-items: center;
  justify-content: space-around;
  height: 100rpx;
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  box-shadow: 0 -4rpx 24rpx rgba(0, 0, 0, 0.04);
  border-top: 1px solid var(--border);
}

.tab-item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  height: 100%;
  padding: var(--space-2) 0;
  transition: all var(--duration-fast) var(--ease-out);
  cursor: pointer;
}

.tab-icon {
  width: 48rpx;
  height: 48rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 4rpx;
  transition: transform var(--duration-fast) var(--ease-spring);
}

.tab-icon-img {
  width: 48rpx;
  height: 48rpx;
  display: block;
  transition: transform var(--duration-fast) var(--ease-spring);
}

.tab-icon-text {
  font-size: 40rpx;
  line-height: 1;
  color: var(--text-muted);
  font-weight: 500;
  display: block;
  text-align: center;
}

.tab-item.active .tab-icon-text {
  color: var(--primary);
  font-weight: 700;
}

.tab-item.active .tab-icon {
  transform: scale(1.1);
}

.tab-item.active .tab-icon-img {
  transform: scale(1.1);
}

.tab-label {
  font-size: 22rpx;
  font-weight: var(--font-medium);
  color: var(--text-muted);
  transition: all var(--duration-fast) var(--ease-out);
}

.tab-item.active .tab-label {
  color: var(--primary);
  font-weight: var(--font-semibold);
}

.tab-indicator {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 40rpx;
  height: 6rpx;
  background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
  border-radius: 0 0 var(--radius-sm) var(--radius-sm);
}

.tab-badge {
  position: absolute;
  top: 6rpx;
  right: calc(50% - 36rpx);
  min-width: 32rpx;
  height: 32rpx;
  padding: 0 8rpx;
  background: var(--danger);
  color: #FFFFFF;
  font-size: 18rpx;
  font-weight: var(--font-semibold);
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Active state press effect */
.tab-item:active {
  opacity: 0.8;
}

/* Badge pulse animation */
.tab-badge {
  animation: badge-pulse 2s ease-in-out infinite;
}

@keyframes badge-pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

/* Safe area padding when no system safe area */
.tabbar.safe-area {
  padding-bottom: calc(env(safe-area-inset-bottom) + 8rpx);
}
</style>
