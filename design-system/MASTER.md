# Excellent 电商 - 设计系统

> 完整的设计系统参考文档，供所有页面开发使用

## 项目信息
- **项目名称:** Excellent 电商
- **产品类型:** E-commerce / Marketplace
- **目标用户:** C端消费者
- **技术栈:** 移动端 (uni-app / Vue)

---

## 设计风格

### 主风格: Vibrant & Block-based

| 属性 | 值 |
|------|-----|
| **风格名称** | Vibrant & Block-based |
| **关键词** | Bold, energetic, playful, block layout, geometric shapes, high color contrast, duotone, modern |
| **最佳场景** | Startups, 电商, 娱乐, 消费品, 社交媒体 |
| **模式支持** | ✅ Light 完整支持 / ✅ Dark 完整支持 |

### 风格特点
- 大区块布局，分组清晰
- 高对比度色彩
- 几何形状装饰
- 动态感和活力感
- 200-300ms 过渡动画

### 避免事项
- ❌ 扁平设计缺乏层次
- ❌ 文字过重的页面

---

## 色彩系统

### 调色板

| 角色 | Hex | CSS 变量 | 用途 |
|------|-----|----------|------|
| Primary | `#059669` | `--color-primary` | 主按钮、主要操作 |
| On Primary | `#FFFFFF` | `--color-on-primary` | Primary 上的文字 |
| Secondary | `#10B981` | `--color-secondary` | 次要元素、hover 状态 |
| Accent/CTA | `#D97706` | `--color-accent` | 强调、促销、热点标签 |
| On Accent | `#FFFFFF` | `--color-on-accent` | Accent 上的文字 |
| Background | `#F8FAFC` | `--color-background` | 页面背景 |
| Foreground | `#0F172A` | `--color-foreground` | 主要文字 |
| Card | `#FFFFFF` | `--color-card` | 卡片背景 |
| Card Foreground | `#0F172A` | `--color-card-foreground` | 卡片文字 |
| Muted | `#F1F5F9` | `--color-muted` | 次要背景 |
| Muted Foreground | `#64748B` | `--color-muted-foreground` | 次要文字 |
| Border | `#E2E8F0` | `--color-border` | 边框、分割线 |
| Destructive | `#DC2626` | `--color-destructive` | 危险操作、错误 |
| On Destructive | `#FFFFFF` | `--color-on-destructive` | Destructive 上的文字 |
| Success | `#22C55E` | `--color-success` | 成功状态 |
| Warning | `#F59E0B` | `--color-warning` | 警告状态 |

### 深色模式变体

| 角色 | Hex | CSS 变量 |
|------|-----|----------|
| Background | `#0F172A` | `--color-background-dark` |
| Card | `#1E293B` | `--color-card-dark` |
| Foreground | `#F8FAFC` | `--color-foreground-dark` |
| Border | `#334155` | `--color-border-dark` |
| Muted | `#1E293B` | `--color-muted-dark` |

### 使用原则
1. **对比度**: 文字与背景 ≥ 4.5:1 (普通文字), ≥ 3:1 (大文字)
2. **语义化**: 使用变量而非硬编码 Hex
3. **颜色含义**: 红色=危险/错误, 绿色=成功, 橙色=警告/促销

---

## 字体系统

### 字体选择

| 类型 | 字体 | 用途 |
|------|------|------|
| **Heading** | Rubik | 标题、导航、按钮 |
| **Body** | Nunito Sans | 正文、描述文字 |

### Google Fonts 导入
```css
@import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@300;400;500;600;700&family=Rubik:wght@300;400;500;600;700&display=swap');
```

### 字号系统

| 级别 | 字号 | 行高 | 字重 | 用途 |
|------|------|------|------|------|
| xs | 12px | 1.4 | 400 | 辅助文字 |
| sm | 14px | 1.5 | 400 | 次要文字 |
| base | 16px | 1.5 | 400 | 正文（最小 16px 避免 iOS 缩放）|
| lg | 18px | 1.5 | 500 | 大正文 |
| xl | 20px | 1.4 | 600 | 小标题 |
| 2xl | 24px | 1.3 | 600 | 卡片标题 |
| 3xl | 30px | 1.2 | 700 | 页面标题 |
| 4xl | 36px | 1.1 | 700 | Hero 标题 |

### 字重层级
- **700**: 主要标题、价格
- **600**: 副标题、按钮文字
- **500**: 标签文字
- **400**: 正文

---

## 间距系统

### 基础单位: 4px / 8px

| 名称 | 值 | 用途 |
|------|-----|------|
| 0 | 0px | - |
| 1 | 4px | 紧凑间距 |
| 2 | 8px | 元素内间距 |
| 3 | 12px | 小组件内间距 |
| 4 | 16px | 常规间距 |
| 5 | 20px | 区块内间距 |
| 6 | 24px | 卡片内间距 |
| 8 | 32px | 区块间距 |
| 10 | 40px | 大区块间距 |
| 12 | 48px | 页面区块间距 |
| 16 | 64px | 页面边距 |

### 布局间距
- **小节内间距**: 16px
- **卡片内边距**: 16px
- **卡片间距**: 12-16px
- **区块间距**: 24-32px

---

## 圆角系统

| 名称 | 值 | 用途 |
|------|-----|------|
| none | 0px | - |
| sm | 4px | 小元素 |
| md | 8px | 按钮、输入框 |
| lg | 12px | 卡片 |
| xl | 16px | 大卡片 |
| 2xl | 20px | Modal |
| full | 9999px | 胶囊按钮、头像 |

---

## 阴影系统

| 名称 | 值 | 用途 |
|------|-----|------|
| sm | `0 1px 2px rgba(0,0,0,0.05)` | 轻微浮动 |
| md | `0 4px 6px -1px rgba(0,0,0,0.1)` | 卡片 |
| lg | `0 10px 15px -3px rgba(0,0,0,0.1)` | Modal |
| xl | `0 20px 25px -5px rgba(0,0,0,0.15)` | 大 Modal |

---

## 图标规范

### 图标库
- **推荐**: Lucide Icons / Heroicons
- **格式**: SVG (矢量)
- **描边宽度**: 2px
- **尺寸**: 20px (小), 24px (标准), 32px (大)

### 规范
| 规则 | 说明 |
|------|------|
| ✅ 使用 | SVG 矢量图标 |
| ❌ 禁止 | Emoji 作为结构图标 |
| ✅ 风格 | 统一描边或统一填充 |
| ✅ 触控区域 | ≥44×44px (iOS) |

---

## 组件规范

### 按钮

#### 主按钮
```css
background: var(--color-primary);
color: var(--color-on-primary);
border-radius: 8px;
padding: 12px 24px;
font-weight: 600;
transition: all 150ms ease;
```

#### 次要按钮
```css
background: transparent;
color: var(--color-primary);
border: 1.5px solid var(--color-primary);
border-radius: 8px;
padding: 12px 24px;
font-weight: 600;
```

#### 按钮状态
| 状态 | 变化 |
|------|------|
| Hover | 背景加深 10%, scale(1.02) |
| Active/Press | 背景加深 15%, scale(0.98) |
| Disabled | opacity: 0.5, cursor: not-allowed |
| Loading | 显示 spinner, 禁用点击 |

### 卡片

#### 商品卡片
```css
background: var(--color-card);
border-radius: 12px;
padding: 0; /* 图片撑满顶部 */
overflow: hidden;
box-shadow: 0 2px 8px rgba(0,0,0,0.06);
```

#### 信息卡片
```css
background: var(--color-card);
border-radius: 12px;
padding: 16px;
box-shadow: 0 2px 8px rgba(0,0,0,0.06);
```

### 输入框

```css
border: 1.5px solid var(--color-border);
border-radius: 8px;
padding: 12px 16px;
font-size: 16px;
transition: border-color 150ms ease;
```

### 触控规范
| 要求 | 最小值 |
|------|--------|
| 触控区域 | 44×44px |
| 间距 | ≥8px |
| 按钮内边距 | ≥12px |

---

## 动画规范

### 时长
| 类型 | 时长 |
|------|------|
| 微交互 | 150ms |
| 状态切换 | 200-300ms |
| 页面过渡 | 300-400ms |
| Modal | 250ms |
| 避免 | >500ms |

### 缓动函数
| 类型 | 函数 |
|------|------|
| 进入 | ease-out |
| 退出 | ease-in |
| 状态变化 | ease-in-out |
| 弹性 | cubic-bezier(0.34, 1.56, 0.64, 1) |

### 动画原则
1. ✅ 动画传达因果关系
2. ✅ 退出动画快于进入 (~60-70%)
3. ✅ 支持 prefers-reduced-motion
4. ✅ 可中断动画
5. ❌ 禁止阻塞用户交互的动画

---

## 页面布局

### 移动端结构

```
┌─────────────────────┐
│     Status Bar      │  20-44px
├─────────────────────┤
│      Header         │  44-56px
│  (标题 / 导航 / 搜索)  │
├─────────────────────┤
│                     │
│                     │
│     Main Content    │  flex: 1
│     (可滚动区域)      │
│                     │
│                     │
├─────────────────────┤
│     Bottom Tab      │  50-60px
│     Bar (5项)       │  + Safe Area
└─────────────────────┘
```

### 安全区域
- **iOS 刘海屏**: 确保内容不被刘海遮挡
- **底部手势区**: Tab Bar 下方预留 34px Safe Area
- **状态栏**: 预留 20-44px 高度

### 断点
| 设备 | 宽度 |
|------|------|
| 小手机 | 320px |
| 标准手机 | 375px |
| 大手机 | 414px |
| 平板竖屏 | 768px |
| 平板横屏 | 1024px |

---

## 电商特定规范

### 搜索体验
- ✅ 自动补全 (输入时显示建议)
- ✅ 热门搜索展示
- ✅ 无结果时显示替代建议
- ✅ 搜索历史

### 商品列表
- ✅ 网格/列表视图切换
- ✅ 筛选器 (价格、品牌、分类)
- ✅ 排序选项
- ✅ 下拉刷新 + 上拉加载
- ✅ 图片懒加载

### 商品详情
- ✅ 图片轮播 (支持缩放)
- ✅ 价格醒目展示
- ✅ 规格选择
- ✅ 加入购物车/立即购买
- ✅ 相似推荐

### 购物车
- ✅ 商品数量调整
- ✅ 删除商品
- ✅ 价格汇总
- ✅ 结算按钮醒目

### 结账流程
- ✅ 地址管理
- ✅ 支付方式选择
- ✅ 订单确认
- ✅ 支付状态反馈

---

## 交付前检查清单

### 视觉
- [ ] 无 Emoji 作为图标
- [ ] 图标来自统一图标库
- [ ] 按钮有 hover/press 反馈
- [ ] 卡片有适当圆角和阴影
- [ ] 文字对比度 ≥ 4.5:1

### 交互
- [ ] 触控区域 ≥44×44px
- [ ] 动画时长 150-300ms
- [ ] 禁用状态有明确视觉
- [ ] 表单有错误提示

### 布局
- [ ] 安全区域正确处理
- [ ] 375px 测试通过
- [ ] 无横向滚动
- [ ] 固定元素有内容占位

### 无障碍
- [ ] 支持系统字体缩放
- [ ] 支持深色模式
- [ ] 支持减弱动画
- [ ] 关键按钮有焦点指示

---

## 相关资源

- **Google Fonts**: https://fonts.google.com/specimen/Rubik
- **Nunito Sans**: https://fonts.google.com/specimen/Nunito+Sans
- **Lucide Icons**: https://lucide.dev/
- **Heroicons**: https://heroicons.com/
