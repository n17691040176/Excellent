<template>
  <view class="tabbar-shell" :class="{ compact: isCompact, dark: isDark }" :style="{ opacity: barOpacity }">
    <view class="tabbar-inner">
      <view
        v-for="(item, index) in list"
        :key="item.pagePath"
        class="tab-item"
        :class="{
          active: selected === index,
          pressing: pressIndex === index
        }"
        @touchstart="onPressStart(index)"
        @touchend="onPressEnd(index)"
        @touchcancel="onPressEnd(index)"
        @click="switchTab(index)"
      >
        <view class="tab-item-bg" />
        <view class="tab-icon-wrap" :class="{ active: selected === index }">
          <image
            class="tab-icon"
            :class="{ fx: iconFxIndex === index }"
            :src="selected === index ? item.selectedIconPath : item.iconPath"
            mode="aspectFit"
          />
        </view>
        <text class="tab-text">{{ item.text }}</text>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  data() {
    return {
      selected: 0,
      iconFxIndex: -1,
      pressIndex: -1,
      isCompact: false,
      isDark: false,
      barOpacity: 0.98,
      list: [
        {
          pagePath: '/pages/home/index',
          text: '首页',
          iconPath: '/static/tabbar/home.svg',
          selectedIconPath: '/static/tabbar/home-active.svg'
        },
        {
          pagePath: '/pages/packages/list',
          text: '分类',
          iconPath: '/static/tabbar/packages.svg',
          selectedIconPath: '/static/tabbar/packages-active.svg'
        },
        {
          pagePath: '/pages/local-life/index',
          text: '生活',
          iconPath: '/static/tabbar/life.svg',
          selectedIconPath: '/static/tabbar/life-active.svg'
        },
        {
          pagePath: '/pages/profile/index',
          text: '我的',
          iconPath: '/static/tabbar/profile.svg',
          selectedIconPath: '/static/tabbar/profile-active.svg'
        }
      ]
    };
  },
  attached() {
    this.syncSelected();
    this.syncTheme();
    uni.onThemeChange?.(({ theme }) => {
      this.isDark = theme === 'dark';
    });
    uni.$on('excellent:tabbar-scroll', this.onScrollState);
  },
  detached() {
    uni.$off('excellent:tabbar-scroll', this.onScrollState);
  },
  pageLifetimes: {
    show() {
      this.syncSelected();
    }
  },
  methods: {
    syncTheme() {
      const appBase = uni.getAppBaseInfo?.();
      const theme = appBase?.theme || uni.getSystemInfoSync?.().theme;
      this.isDark = theme === 'dark';
    },
    onScrollState(payload = {}) {
      this.isCompact = Boolean(payload.compact);
      const nextOpacity = Number(payload.opacity);
      this.barOpacity = Number.isFinite(nextOpacity) ? Math.min(1, Math.max(0.84, nextOpacity)) : 0.98;
    },
    onPressStart(index) {
      this.pressIndex = index;
    },
    onPressEnd(index) {
      if (this.pressIndex === index) {
        this.pressIndex = -1;
      }
    },
    triggerIconFx(index) {
      this.iconFxIndex = index;
      setTimeout(() => {
        if (this.iconFxIndex === index) {
          this.iconFxIndex = -1;
        }
      }, 220);
    },
    switchTab(index) {
      const target = this.list[index];
      if (!target) return;

      this.triggerIconFx(index);
      if (this.selected === index) return;

      this.selected = index;
      uni.switchTab({ url: target.pagePath });
    },
    syncSelected() {
      const pages = getCurrentPages();
      const current = pages[pages.length - 1];
      const route = current?.route ? `/${current.route}` : '';
      const matched = this.list.findIndex((item) => item.pagePath === route);
      this.selected = matched >= 0 ? matched : 0;
    }
  }
};
</script>

<style scoped>
.tabbar-shell {
  position: fixed;
  left: 12rpx;
  right: 12rpx;
  bottom: calc(env(safe-area-inset-bottom) + 4rpx);
  z-index: 999;
  transform: translateY(0) scale(1);
  transition: transform 0.24s ease, opacity 0.24s ease;
}

.tabbar-shell.compact {
  transform: translateY(4rpx) scale(0.988);
}

.tabbar-inner {
  position: relative;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10rpx;
  padding: 12rpx;
  border-radius: 30rpx;
  background:
    linear-gradient(180deg, rgba(255, 249, 244, 0.78) 0%, rgba(255, 244, 234, 0.74) 100%);
  box-shadow:
    0 6rpx 14rpx rgba(117, 74, 34, 0.045),
    0 2rpx 3rpx rgba(117, 74, 34, 0.015);
  backdrop-filter: blur(20px);
  overflow: hidden;
}

.tabbar-shell.dark .tabbar-inner {
  background: rgba(36, 30, 26, 0.92);
  box-shadow:
    0 12rpx 24rpx rgba(0, 0, 0, 0.22),
    0 2rpx 6rpx rgba(0, 0, 0, 0.1);
}

.tab-item {
  position: relative;
  min-height: 88rpx;
  border-radius: 24rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6rpx;
  transform: translateY(0);
  transition: transform 0.22s ease, opacity 0.22s ease;
  overflow: hidden;
}

.tab-item-bg {
  position: absolute;
  inset: 0;
  border-radius: 24rpx;
  background: transparent;
  transition: background 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;
  border: 1rpx solid transparent;
}

.tab-item.active {
  transform: translateY(-1rpx);
}

.tab-item.active .tab-item-bg {
  background: linear-gradient(180deg, rgba(255, 245, 235, 0.34) 0%, rgba(252, 239, 225, 0.28) 100%);
  border-color: rgba(201, 125, 46, 0.04);
  box-shadow:
    inset 0 1rpx 0 rgba(255, 255, 255, 0.22),
    0 4rpx 8rpx rgba(191, 119, 49, 0.025);
}

.tabbar-shell.dark .tab-item.active .tab-item-bg {
  background: linear-gradient(180deg, rgba(92, 62, 38, 0.56) 0%, rgba(79, 52, 31, 0.48) 100%);
  border-color: rgba(255, 161, 77, 0.2);
}

.tab-item.pressing {
  transform: scale(0.97);
}

.tab-icon-wrap {
  position: relative;
  z-index: 1;
  width: 52rpx;
  height: 52rpx;
  border-radius: 18rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.22s ease, background 0.22s ease, box-shadow 0.22s ease;
}

.tab-icon-wrap.active {
  background: linear-gradient(160deg, rgba(255, 151, 61, 0.05), rgba(214, 110, 18, 0.06));
  box-shadow:
    0 4rpx 8rpx rgba(183, 107, 41, 0.03),
    inset 0 1rpx 0 rgba(255,255,255,0.16);
}

.tab-icon {
  position: relative;
  z-index: 1;
  width: 36rpx;
  height: 36rpx;
  opacity: 1;
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.tab-icon.fx {
  animation: icon-fade-zoom 0.22s ease;
}

.tab-text {
  position: relative;
  z-index: 1;
  font-size: 20rpx;
  line-height: 1;
  color: #9f8d7d;
  letter-spacing: 0.2rpx;
  transition: color 0.22s ease, font-weight 0.22s ease;
}

.tab-item.active .tab-text {
  color: #b56a28;
  font-weight: 600;
  letter-spacing: 0.2rpx;
}

.tabbar-shell.dark .tab-text {
  color: #b7aaa0;
}

.tabbar-shell.dark .tab-item.active .tab-text {
  color: #ffae63;
}

@keyframes icon-fade-zoom {
  0% { opacity: 0.72; transform: scale(0.9); }
  60% { opacity: 1; transform: scale(1.08); }
  100% { opacity: 1; transform: scale(1); }
}
</style>
