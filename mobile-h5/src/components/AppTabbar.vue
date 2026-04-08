<template>
  <van-tabbar
    route
    safe-area-inset-bottom
    active-color="#1f8f6e"
    inactive-color="rgba(24, 52, 59, 0.52)"
  >
    <van-tabbar-item replace to="/home" icon="wap-home-o">首页</van-tabbar-item>
    <van-tabbar-item replace to="/categories" icon="apps-o">分类</van-tabbar-item>
    <van-tabbar-item replace to="/orders" icon="orders-o">订单</van-tabbar-item>
    <van-tabbar-item replace to="/profile" icon="contact-o">我的</van-tabbar-item>
  </van-tabbar>
</template>
