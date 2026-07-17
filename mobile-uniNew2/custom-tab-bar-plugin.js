// 自定义 tabBar 插件 - 确保在所有页面之前加载
import CustomTabBar from './custom-tab-bar/index.vue'

export default {
  install(app) {
    app.component('CustomTabBar', CustomTabBar)
  }
}