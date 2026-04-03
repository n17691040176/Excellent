<template>
  <div>
    <div class="page-heading">
      <div>
        <h2>权限管理</h2>
        <p>展示系统角色、后台菜单边界与按钮级权限矩阵。</p>
      </div>
    </div>

    <div class="metric-grid">
      <div v-for="item in metrics" :key="item.label" class="metric-card">
        <div class="label">{{ item.label }}</div>
        <div class="value">{{ item.value }}</div>
        <div class="subtext">{{ item.subtext }}</div>
      </div>
    </div>

    <div class="split-grid" style="margin-top: 18px;">
      <div class="panel-card data-card">
        <div class="section-title">
          <div>
            <h3>角色定义</h3>
            <p>当前系统采用全局角色控制后台访问边界。</p>
          </div>
        </div>
        <el-table :data="roles" border>
          <el-table-column prop="code" label="角色编码" width="160" />
          <el-table-column prop="name" label="角色名称" width="140" />
          <el-table-column prop="scope" label="可见范围" min-width="180" />
          <el-table-column prop="description" label="说明" min-width="240" />
        </el-table>
      </div>

      <div class="panel-card data-card">
        <div class="section-title">
          <div>
            <h3>权限说明</h3>
            <p>路由、菜单和按钮权限统一依赖 JWT 身份与角色矩阵拦截。</p>
          </div>
        </div>
        <div class="notice-list">
          <div class="notice-item">
            <strong>超级管理员</strong>
            拥有全局权限，可查看账号管理与权限管理，并执行高风险状态变更。
          </div>
          <div class="notice-item">
            <strong>团队管理员</strong>
            可管理团队业务数据、提现审核与本地生活核销，不可查看系统账号和角色配置。
          </div>
          <div class="notice-item">
            <strong>普通用户</strong>
            只能进入用户端 APP，无后台访问权限，进入后台即跳转 403。
          </div>
        </div>
      </div>
    </div>

    <div class="panel-card data-card" style="margin-top: 18px;">
      <div class="section-title">
        <div>
          <h3>权限矩阵</h3>
          <p>按钮级权限按最小必要原则划分，避免团队管理员越权操作。</p>
        </div>
      </div>
      <el-table :data="permissionRows" border>
        <el-table-column prop="permission" label="权限标识" min-width="220" />
        <el-table-column prop="label" label="权限说明" min-width="220" />
        <el-table-column label="超级管理员" width="120">
          <template #default>
            <el-tag type="success">允许</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="团队管理员" width="120">
          <template #default="scope">
            <el-tag :type="scope.row.teamAdmin ? 'success' : 'info'">{{ scope.row.teamAdmin ? '允许' : '禁止' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="普通用户" width="110">
          <template #default>
            <el-tag type="info">禁止</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

import { PERMISSION_MATRIX, ROLE_LABELS } from '@/utils/permission'

const roles = [
  { code: 'SUPER_ADMIN', name: ROLE_LABELS.SUPER_ADMIN, scope: '全平台', description: '拥有系统级配置、账号、审核和经营数据全量权限。' },
  { code: 'TEAM_ADMIN', name: ROLE_LABELS.TEAM_ADMIN, scope: '所属团队', description: '管理团队业务数据、提现审核与本地生活核销，不可查看系统配置。' },
  { code: 'USER', name: ROLE_LABELS.USER, scope: '用户端 APP', description: '仅参与商城、团队、邀请和资产业务，不开放后台入口。' }
]

const permissionLabels = {
  'dashboard:view': '查看首页经营概览',
  'users:view': '查看用户列表与邀请关系',
  'users:status': '启用或禁用用户账号',
  'teams:view': '查看团队与成员信息',
  'teams:edit': '编辑团队基础信息',
  'packages:view': '查看套餐与资格',
  'packages:create': '新增套餐',
  'packages:edit': '编辑或删除套餐',
  'packages:shelf': '执行套餐上架与下架',
  'products:view': '查看专区商品与专区规则',
  'products:create': '新增专区商品',
  'products:edit': '编辑或删除专区商品',
  'products:submit-review': '提交商品审核',
  'products:shelf': '执行商品上架与下架',
  'commission:view': '查看佣金配置与返现流水',
  'withdraws:view': '查看提现申请列表',
  'withdraws:review': '审核提现申请',
  'suppliers:view': '查看招商与供应商数据',
  'assets:view': '查看资产中心',
  'local-life:view': '查看本地生活经营数据',
  'local-life:create': '新增本地生活商家、门店、服务和规则',
  'local-life:edit': '编辑或删除本地生活经营数据',
  'local-life:verify': '执行本地生活核销',
  'profile:view': '查看个人中心',
  'profile:edit': '编辑个人资料',
  'profile:password': '修改登录密码'
}

const permissionRows = Object.entries(permissionLabels).map(([permission, label]) => ({
  permission,
  label,
  teamAdmin: (PERMISSION_MATRIX.TEAM_ADMIN || []).includes(permission)
}))

const metrics = computed(() => [
  { label: '系统角色数', value: roles.length, subtext: '超级管理员、团队管理员、普通用户' },
  { label: '超级管理员权限', value: 'ALL', subtext: '使用全权限通配处理' },
  { label: '团队管理员权限数', value: PERMISSION_MATRIX.TEAM_ADMIN.length, subtext: '仅覆盖业务管理必要动作' },
  { label: '普通用户后台权限', value: 0, subtext: '直接禁止后台访问' }
])
</script>
