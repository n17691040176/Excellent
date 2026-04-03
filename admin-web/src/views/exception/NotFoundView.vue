<template>
  <div class="exception-shell page-shell">
    <div class="panel-card exception-card">
      <div class="exception-code">404</div>
      <h1>页面不存在</h1>
      <p>访问的路由未配置或已失效，请从左侧菜单重新进入业务模块。</p>
      <div class="exception-actions">
        <el-button type="primary" @click="$router.push('/dashboard')">回到首页</el-button>
        <el-button plain @click="$router.push('/login')">重新登录</el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.exception-shell {
  display: grid;
  place-items: center;
  padding: 24px;
}

.exception-card {
  width: min(560px, 100%);
  padding: 48px 32px;
  text-align: center;
}

.exception-code {
  font-size: 88px;
  font-weight: 800;
  line-height: 1;
  color: var(--brand-teal);
}

h1 {
  margin: 22px 0 12px;
  color: var(--brand-deep);
}

p {
  margin: 0;
  line-height: 1.8;
  color: rgba(15, 47, 47, 0.64);
}

.exception-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 28px;
}
</style>
