export const menuSections = [
  {
    title: '总览',
    items: [
      {
        path: '/dashboard',
        name: 'Dashboard',
        title: '首页概览',
        icon: 'DataAnalysis',
        roles: ['SUPER_ADMIN', 'TEAM_ADMIN'],
        permission: 'dashboard:view'
      },
      {
        path: '/decorations/home',
        name: 'DecorationHome',
        title: '移动端装修',
        icon: 'MagicStick',
        roles: ['SUPER_ADMIN', 'TEAM_ADMIN'],
        permission: 'decoration:view'
      }
    ]
  },
  {
    title: '用户增长',
    items: [
      {
        path: '/users',
        name: 'Users',
        title: '用户管理',
        icon: 'User',
        roles: ['SUPER_ADMIN', 'TEAM_ADMIN'],
        permission: 'users:view'
      },
      {
        path: '/teams',
        name: 'Teams',
        title: '团队管理',
        icon: 'Avatar',
        roles: ['SUPER_ADMIN', 'TEAM_ADMIN'],
        permission: 'teams:view'
      },
      {
        path: '/invites',
        name: 'Invites',
        title: '邀请裂变',
        icon: 'Share',
        roles: ['SUPER_ADMIN', 'TEAM_ADMIN'],
        permission: 'invites:view'
      }
    ]
  },
  {
    title: '商品交易',
    items: [
      {
        path: '/products',
        name: 'Products',
        title: '商品管理',
        icon: 'Goods',
        roles: ['SUPER_ADMIN', 'TEAM_ADMIN'],
        permission: 'products:view'
      },
      {
        path: '/categories',
        name: 'Categories',
        title: '商品分类',
        icon: 'Grid',
        roles: ['SUPER_ADMIN', 'TEAM_ADMIN'],
        permission: 'products:view'
      },
      {
        path: '/orders',
        name: 'Orders',
        title: '订单管理',
        icon: 'Memo',
        roles: ['SUPER_ADMIN', 'TEAM_ADMIN'],
        permission: 'orders:view'
      },
      {
        path: '/shipments',
        name: 'Shipments',
        title: '快递物流',
        icon: 'Van',
        roles: ['SUPER_ADMIN', 'TEAM_ADMIN'],
        permission: 'shipments:view'
      },
      {
        path: '/region-stats',
        name: 'RegionStats',
        title: '区域订单奖励',
        icon: 'MapLocation',
        roles: ['SUPER_ADMIN', 'TEAM_ADMIN'],
        permission: 'region:view'
      }
    ]
  },
  {
    title: '服务与收益',
    items: [
      {
        path: '/local-life',
        name: 'LocalLife',
        title: '本地生活',
        icon: 'Location',
        roles: ['SUPER_ADMIN', 'TEAM_ADMIN'],
        permission: 'local-life:view'
      },
      {
        path: '/commission',
        name: 'Commission',
        title: '返现管理',
        icon: 'Coin',
        roles: ['SUPER_ADMIN', 'TEAM_ADMIN'],
        permission: 'commission:view'
      },
      {
        path: '/withdraws',
        name: 'Withdraws',
        title: '提现管理',
        icon: 'Wallet',
        roles: ['SUPER_ADMIN', 'TEAM_ADMIN'],
        permission: 'withdraws:view'
      },
      {
        path: '/system/earning-rules',
        name: 'EarningRules',
        title: '收益规则',
        icon: 'Setting',
        roles: ['SUPER_ADMIN', 'TEAM_ADMIN'],
        permission: 'earning-rules:view'
      }
    ]
  },
  {
    title: '系统管理',
    items: [
      {
        path: '/system/admins',
        name: 'AdminAccounts',
        title: '管理员管理',
        icon: 'UserFilled',
        roles: ['SUPER_ADMIN', 'TEAM_ADMIN'],
        permission: 'admins:view'
      },
      {
        path: '/system/roles',
        name: 'AdminRoles',
        title: '角色管理',
        icon: 'Lock',
        roles: ['SUPER_ADMIN', 'TEAM_ADMIN'],
        permission: 'roles:view'
      }
    ]
  }
]

export const menuItems = menuSections.flatMap((section) => section.items)
