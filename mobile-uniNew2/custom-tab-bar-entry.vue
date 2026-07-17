<!-- 自定义 tabBar 组件入口 -->
<!-- 这个文件确保自定义 tabBar 组件被编译 -->
<template>
  <custom-tab-bar />
</template>

<script>
import CustomTabBar from './custom-tab-bar/index.vue'

export default {
  components: {
    CustomTabBar
  }
}
</script>
