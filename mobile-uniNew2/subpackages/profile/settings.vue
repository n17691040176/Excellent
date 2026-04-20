<template>
  <view class="container settings-page">
    <view class="card">
      <view class="section-title">账号设置</view>
      <view class="muted">管理资料、安全与偏好配置</view>

      <view class="setting-item interactive" v-for="item in items" :key="item.title" @click="preview(item.title)">
        <view>
          <view class="item-title">{{ item.title }}</view>
          <view class="item-desc">{{ item.desc }}</view>
        </view>
        <view class="arrow">查看</view>
      </view>
    </view>

    <button class="btn btn-ghost mt-24" @click="logout">退出登录</button>
  </view>
</template>

<script setup>
import { clearAuth } from '@/utils/auth';

const items = [
  { title: '个人资料', desc: '头像、昵称和联系方式' },
  { title: '账号安全', desc: '修改手机号与登录验证' },
  { title: '隐私设置', desc: '授权范围与数据管理' }
];

const logout = () => {
  clearAuth();
  uni.reLaunch({ url: '/pages/login/index' });
};

const preview = (title) => {
  uni.showToast({ title: `${title}即将开放`, icon: 'none' });
};
</script>

<style scoped>
@import '@/styles/common.css';
.settings-page { padding-bottom: 36rpx; }
.setting-item {
  padding: 22rpx 0;
  border-bottom: 1rpx solid #ebf2ef;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.setting-item:last-child { border-bottom: none; }
.item-title { font-size: 28rpx; color: #1f4032; }
.item-desc { margin-top: 6rpx; font-size: 22rpx; color: #7a8d84; }
.arrow { font-size: 22rpx; color: #b27a46; font-weight: 700; }
.interactive { transition: transform 180ms ease, opacity 180ms ease; }
.interactive:active { transform: scale(0.99); opacity: 0.92; }
</style>
