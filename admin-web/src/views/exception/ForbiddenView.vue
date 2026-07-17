<template>
  <div class="exception-shell page-shell">
    <div class="panel-card exception-card">
      <div class="exception-code">403</div>
      <h1>当前账号无权访问此页面</h1>
      <p>请确认你的后台角色是否具备访问权限，普通用户不会开放后台入口。</p>
      <div class="exception-actions">
        <el-button type="primary" @click="$router.push('/dashboard')">返回首页</el-button>
        <el-button plain @click="$router.push('/profile')">查看个人中心</el-button>
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
  color: var(--accent);
}

h1 {
  margin: 22px 0 12px;
  color: var(--text-primary);
}

p {
  margin: 0;
  line-height: 1.8;
  color: var(--text-secondary);
}

.exception-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 28px;
}
</style>
