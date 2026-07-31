<template>
  <div class="user-list-view">
    <!-- 统一页面头部 -->
    <PageHeader title="用户管理" :description="scopeHint">
      <template #actions>
        <el-button type="primary" @click="fetchUsers(1)">刷新列表</el-button>
      </template>
    </PageHeader>

    <!-- 数据卡片 -->
    <div class="panel-card data-card">
      <!-- 筛选栏 -->
      <FilterBar
        :fields="filterFields"
        v-model="filters"
        @search="handleSearch"
        @reset="handleReset"
      />

      <!-- 数据表格 -->
      <el-table :data="users" border>
        <el-table-column prop="id" label="用户 ID" width="90" />
        <el-table-column label="来源" width="130">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_legacy_imported ? 'warning' : 'info'">
              {{ row.is_legacy_imported ? '历史导入' : '当前用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="用户信息" min-width="200">
          <template #default="{ row }">
            <div class="cell-title">{{ row.nickname || `ID: ${row.id}` }}</div>
            <div class="cell-meta">{{ row.phone || '--' }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="invite_code" label="邀请码" min-width="120" />
        <el-table-column label="系统角色" width="130">
          <template #default="{ row }">
            <el-tag size="small">{{ roleLabel(row.global_role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="会员等级" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="memberLevelTag(row.member_level)">
              {{ memberLevelLabel(row.member_level) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <StatusTag :type="row.status === 'ENABLED' ? 'success' : 'danger'" size="small">
              {{ row.status === 'ENABLED' ? '正常' : '已禁用' }}
            </StatusTag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <div class="action-group">
              <el-button link type="primary" @click="openUserDetail(row)">详情</el-button>
              <el-button link type="default" @click="openInviteTree(row)">邀请关系</el-button>
              <el-button
                v-if="canChangeMemberLevel"
                link
                type="primary"
                @click="openMemberLevelDialog(row)"
              >调整等级</el-button>
              <el-dropdown trigger="click" @command="(cmd) => handleMoreAction(cmd, row)">
                <el-button link>
                  更多
                  <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="legacy" :disabled="!row.is_legacy_imported">
                      历史资料
                    </el-dropdown-item>
                    <el-dropdown-item
                      v-if="canChangeUserStatus"
                      command="toggle"
                      :divided="true"
                    >
                      {{ row.status === 'ENABLED' ? '禁用用户' : '启用用户' }}
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        class="table-pagination"
        layout="total, sizes, prev, pager, next"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        @size-change="handlePageSizeChange"
        @current-change="fetchUsers"
      />
    </div>

    <el-dialog v-model="memberLevelDialogVisible" title="调整会员等级" width="420px" destroy-on-close>
      <el-form label-width="90px">
        <el-form-item label="会员">
          <span>{{ currentLevelUser?.nickname || currentLevelUser?.phone || '--' }}</span>
        </el-form-item>
        <el-form-item label="会员等级">
          <el-select v-model="memberLevelForm.member_level" style="width: 100%">
            <el-option
              v-for="item in memberLevelOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="memberLevelDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="memberLevelSubmitting" @click="submitMemberLevel">保存</el-button>
      </template>
    </el-dialog>

    <!-- 用户详情抽屉 -->
    <el-drawer v-model="detailDrawerVisible" title="用户详情" size="960px">
      <div class="detail-content" v-loading="detailLoading">
        <template v-if="userDetail">
          <!-- 基础信息卡片 -->
          <section class="detail-section">
            <h4 class="section-title">
              <span class="section-icon"><el-icon><Document /></el-icon></span>
              基础信息
            </h4>
            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">用户 ID</span>
                <span class="info-value">{{ userDetail.id }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">来源</span>
                <el-tag size="small" :type="userDetail.is_legacy_imported ? 'warning' : 'info'">
                  {{ userDetail.is_legacy_imported ? '历史导入' : '当前用户' }}
                </el-tag>
              </div>
              <div class="info-item">
                <span class="info-label">历史 ID</span>
                <span class="info-value">{{ userDetail.legacy_user_id ?? '--' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">手机号</span>
                <span class="info-value">{{ userDetail.phone || '--' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">昵称</span>
                <span class="info-value">{{ userDetail.nickname || '--' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">邀请码</span>
                <span class="info-value">{{ userDetail.invite_code || '--' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">系统角色</span>
                <el-tag size="small">{{ roleLabel(userDetail.global_role) }}</el-tag>
              </div>
              <div class="info-item">
                <span class="info-label">会员等级</span>
                <el-tag size="small" :type="memberLevelTag(userDetail.member_level)">
                  {{ memberLevelLabel(userDetail.member_level) }}
                </el-tag>
              </div>
              <div class="info-item">
                <span class="info-label">状态</span>
                <StatusTag :type="userDetail.status === 'ENABLED' ? 'success' : 'danger'" size="small">
                  {{ userDetail.status === 'ENABLED' ? '正常' : '已禁用' }}
                </StatusTag>
              </div>
              <div class="info-item">
                <span class="info-label">团队</span>
                <span class="info-value">{{ userDetail.team_id ?? '--' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">上级</span>
                <span class="info-value">{{ userDetail.parent_id ?? '--' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">上上级</span>
                <span class="info-value">{{ userDetail.grandparent_id ?? '--' }}</span>
              </div>
            </div>
          </section>

          <!-- 标签页区 -->
          <section class="detail-section detail-tabs">
            <el-tabs v-model="activeTab" class="detail-tabs-inner">
              <!-- 邀请统计 -->
              <el-tab-pane label="邀请统计" name="invite">
                <div class="tiny-stat-grid">
                  <div class="tiny-stat">
                    <div class="title">一级邀请</div>
                    <div class="number">{{ userDetail.invite_summary?.level1_count ?? 0 }}</div>
                  </div>
                  <div class="tiny-stat">
                    <div class="title">二级邀请</div>
                    <div class="number">{{ userDetail.invite_summary?.level2_count ?? 0 }}</div>
                  </div>
                  <div class="tiny-stat">
                    <div class="title">邀请总数</div>
                    <div class="number">{{ userDetail.invite_summary?.total_count ?? 0 }}</div>
                  </div>
                </div>
              </el-tab-pane>

              <!-- 资产摘要 -->
              <el-tab-pane label="资产摘要" name="asset">
                <el-table :data="assetRows" size="small" border>
                  <el-table-column prop="assetType" label="资产类型" min-width="120" />
                  <el-table-column prop="availableAmount" label="可用" min-width="100" />
                  <el-table-column prop="totalAmount" label="累计" min-width="100" />
                  <el-table-column prop="frozenAmount" label="冻结" min-width="100" />
                  <el-table-column prop="consumedAmount" label="已消耗" min-width="100" />
                  <el-table-column prop="withdrawnAmount" label="已提现" min-width="100" />
                </el-table>
              </el-tab-pane>

              <!-- 充电宝绑定 -->
              <el-tab-pane label="充电宝绑定" name="powerbank">
                <div class="powerbank-form">
                  <el-input v-model="powerBankForm.device_code" placeholder="设备编号" />
                  <el-input v-model="powerBankForm.device_name" placeholder="设备名称" />
                  <el-input v-model="powerBankForm.remark" placeholder="备注" />
                  <el-button type="primary" :loading="powerBankSubmitting" @click="submitPowerBank">
                    添加
                  </el-button>
                </div>
                <el-table :data="powerBankRows" size="small" border>
                  <el-table-column prop="device_code" label="设备编号" min-width="160" />
                  <el-table-column prop="device_name" label="设备名称" min-width="140" />
                  <el-table-column label="状态" width="100">
                    <template #default="{ row }">
                      <StatusTag :type="row.status === 'ACTIVE' ? 'success' : 'default'" size="small">
                        {{ row.status === 'ACTIVE' ? '生效中' : '已停用' }}
                      </StatusTag>
                    </template>
                  </el-table-column>
                  <el-table-column label="累计收益" min-width="110">
                    <template #default="{ row }">{{ formatAmount(row.total_income_amount) }}</template>
                  </el-table-column>
                  <el-table-column label="推荐奖累计" min-width="110">
                    <template #default="{ row }">{{ formatAmount(row.total_referral_income_amount) }}</template>
                  </el-table-column>
                  <el-table-column label="最近结算日" min-width="120">
                    <template #default="{ row }">{{ row.last_income_date || '--' }}</template>
                  </el-table-column>
                  <el-table-column label="操作" width="100">
                    <template #default="{ row }">
                      <el-button link type="primary" @click="togglePowerBankStatus(row)">
                        {{ row.status === 'ACTIVE' ? '停用' : '启用' }}
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <!-- 资产流水 -->
              <el-tab-pane label="资产流水" name="ledger">
                <el-table :data="userDetail.recent_asset_ledgers || []" size="small" border>
                  <el-table-column prop="id" label="ID" width="90" />
                  <el-table-column prop="asset_type" label="资产类型" min-width="110" />
                  <el-table-column prop="direction" label="方向" width="90" />
                  <el-table-column label="变动" min-width="100">
                    <template #default="{ row }">{{ formatAmount(row.change_amount) }}</template>
                  </el-table-column>
                  <el-table-column prop="business_type" label="业务类型" min-width="160" />
                  <el-table-column label="变动后" min-width="100">
                    <template #default="{ row }">{{ formatAmount(row.after_amount) }}</template>
                  </el-table-column>
                  <el-table-column label="时间" min-width="160">
                    <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <!-- 订单记录 -->
              <el-tab-pane label="订单记录" name="order">
                <el-table :data="userDetail.recent_orders || []" size="small" border>
                  <el-table-column prop="id" label="ID" width="90" />
                  <el-table-column prop="order_no" label="订单号" min-width="180" />
                  <el-table-column prop="order_type" label="订单类型" min-width="140" />
                  <el-table-column prop="order_status" label="订单状态" min-width="110" />
                  <el-table-column prop="pay_status" label="支付状态" min-width="110" />
                  <el-table-column label="应付金额" min-width="100">
                    <template #default="{ row }">{{ formatAmount(row.payable_amount) }}</template>
                  </el-table-column>
                  <el-table-column label="创建时间" min-width="160">
                    <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <!-- 收货地址 -->
              <el-tab-pane label="收货地址" name="address">
                <div class="section-toolbar">
                  <el-button type="primary" plain size="small" @click="openAddressCreate">
                    新增地址
                  </el-button>
                </div>
                <el-table :data="addressRows" size="small" border>
                  <el-table-column prop="receiver_name" label="收货人" min-width="120" />
                  <el-table-column prop="receiver_phone" label="手机号" min-width="140" />
                  <el-table-column label="地址" min-width="200">
                    <template #default="{ row }">{{ row.full_address || '--' }}</template>
                  </el-table-column>
                  <el-table-column label="默认" width="80">
                    <template #default="{ row }">
                      <StatusTag :type="row.is_default ? 'success' : 'default'" size="small">
                        {{ row.is_default ? '是' : '否' }}
                      </StatusTag>
                    </template>
                  </el-table-column>
                  <el-table-column label="更新时间" min-width="160">
                    <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
                  </el-table-column>
                  <el-table-column label="操作" width="180">
                    <template #default="{ row }">
                      <el-button link type="primary" :disabled="row.is_default" @click="setDefaultAddress(row)">
                        设默认
                      </el-button>
                      <el-button link type="primary" @click="openAddressEdit(row)">编辑</el-button>
                      <el-button link type="danger" @click="deleteAddress(row)">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <!-- 商城行为 -->
              <el-tab-pane label="商城行为" name="commerce">
                <div class="tiny-stat-grid">
                  <div class="tiny-stat">
                    <div class="title">收货地址</div>
                    <div class="number">{{ commerceSummary.address_count ?? 0 }}</div>
                  </div>
                  <div class="tiny-stat">
                    <div class="title">默认地址</div>
                    <div class="number">{{ commerceSummary.default_address_count ?? 0 }}</div>
                  </div>
                  <div class="tiny-stat">
                    <div class="title">收藏商品</div>
                    <div class="number">{{ commerceSummary.favorite_count ?? 0 }}</div>
                  </div>
                  <div class="tiny-stat">
                    <div class="title">浏览足迹</div>
                    <div class="number">{{ commerceSummary.footprint_count ?? 0 }}</div>
                  </div>
                  <div class="tiny-stat">
                    <div class="title">购物车</div>
                    <div class="number">{{ commerceSummary.cart_item_count ?? 0 }}</div>
                  </div>
                </div>
              </el-tab-pane>

              <!-- 购物车 -->
              <el-tab-pane label="购物车" name="cart">
                <el-table :data="cartRows" size="small" border>
                  <el-table-column label="商品" min-width="200">
                    <template #default="{ row }">
                      <div>{{ row.title || '--' }}</div>
                      <div class="cell-meta">{{ zoneLabel(row.zone_type) }} / {{ row.product?.status || '--' }}</div>
                    </template>
                  </el-table-column>
                  <el-table-column prop="quantity" label="数量" width="80" />
                  <el-table-column label="已选" width="80">
                    <template #default="{ row }">
                      <StatusTag :type="row.selected ? 'success' : 'default'" size="small">
                        {{ row.selected ? '是' : '否' }}
                      </StatusTag>
                    </template>
                  </el-table-column>
                  <el-table-column label="单价" min-width="100">
                    <template #default="{ row }">{{ formatAmount(row.price) }}</template>
                  </el-table-column>
                  <el-table-column label="小计" min-width="100">
                    <template #default="{ row }">{{ formatAmount(row.subtotal_amount) }}</template>
                  </el-table-column>
                  <el-table-column label="更新时间" min-width="160">
                    <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
                  </el-table-column>
                  <el-table-column label="操作" width="80">
                    <template #default="{ row }">
                      <el-button link type="danger" @click="deleteCartItem(row)">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>

              <!-- 收藏足迹 -->
              <el-tab-pane label="收藏足迹" name="favorite">
                <el-table :data="favoriteRows" size="small" border>
                  <el-table-column label="商品" min-width="200">
                    <template #default="{ row }">
                      <div>{{ row.title || '--' }}</div>
                      <div class="cell-meta">{{ zoneLabel(row.zone_type) }} / {{ row.status || '--' }}</div>
                    </template>
                  </el-table-column>
                  <el-table-column label="售价" min-width="100">
                    <template #default="{ row }">{{ formatAmount(row.sale_price) }}</template>
                  </el-table-column>
                  <el-table-column label="收藏时间" min-width="160">
                    <template #default="{ row }">{{ formatDate(row.favorited_at) }}</template>
                  </el-table-column>
                  <el-table-column label="操作" width="80">
                    <template #default="{ row }">
                      <el-button link type="danger" @click="deleteFavorite(row)">移除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>
            </el-tabs>
          </section>
        </template>
      </div>
    </el-drawer>

    <!-- 邀请关系抽屉 -->
    <el-drawer v-model="drawerVisible" title="邀请关系" size="520px">
      <div class="panel-card data-card">
        <div class="invite-header">
          <div class="invite-user">
            <span class="invite-label">用户 ID</span>
            <span class="invite-value">{{ inviteTree.user_id || '--' }}</span>
          </div>
          <div class="invite-user">
            <span class="invite-label">手机号</span>
            <span class="invite-value">{{ inviteTree.phone || '--' }}</span>
          </div>
        </div>
        <el-divider content-position="left">一级邀请</el-divider>
        <el-table :data="inviteTree.level1 || []" size="small" border>
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="phone" label="手机号" />
          <el-table-column prop="nickname" label="昵称" />
        </el-table>
        <el-divider content-position="left">二级邀请</el-divider>
        <el-table :data="inviteTree.level2 || []" size="small" border>
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="phone" label="手机号" />
          <el-table-column prop="nickname" label="昵称" />
        </el-table>
      </div>
    </el-drawer>

    <!-- 历史资料抽屉 -->
    <el-drawer v-model="legacyDrawerVisible" title="历史资料" size="720px">
      <div class="panel-card data-card" v-loading="legacyLoading">
        <template v-if="legacyProfile">
          <section class="detail-section">
            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">用户 ID</span>
                <span class="info-value">{{ legacyProfile.user.id }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">来源</span>
                <el-tag size="small" :type="legacyProfile.user.is_legacy_imported ? 'warning' : 'info'">
                  {{ legacyProfile.user.is_legacy_imported ? '历史导入' : '当前用户' }}
                </el-tag>
              </div>
              <div class="info-item">
                <span class="info-label">历史 ID</span>
                <span class="info-value">{{ legacyProfile.user.legacy_user_id ?? '--' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">手机号</span>
                <span class="info-value">{{ legacyProfile.user.phone || '--' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">昵称</span>
                <span class="info-value">{{ legacyProfile.user.nickname || '--' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">邀请码</span>
                <span class="info-value">{{ legacyProfile.user.invite_code || '--' }}</span>
              </div>
            </div>
          </section>
          <section class="detail-section">
            <h4 class="section-title">
              <span class="section-icon"><el-icon><Document /></el-icon></span>
              历史原始字段
            </h4>
            <div class="info-grid">
              <div v-for="item in legacyFields" :key="item.key" class="info-item">
                <span class="info-label">{{ item.key }}</span>
                <span class="info-value">{{ item.value }}</span>
              </div>
            </div>
          </section>
        </template>
      </div>
    </el-drawer>

    <!-- 地址编辑对话框 -->
    <el-dialog
      v-model="addressDialogVisible"
      :title="addressDialogTitle"
      width="560px"
      append-to-body
      destroy-on-close
    >
      <el-form label-width="84px">
        <el-form-item label="收货人">
          <el-input v-model="addressForm.receiver_name" maxlength="32" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="addressForm.receiver_phone" maxlength="20" />
        </el-form-item>
        <el-form-item label="省份">
          <el-input v-model="addressForm.province" maxlength="32" />
        </el-form-item>
        <el-form-item label="城市">
          <el-input v-model="addressForm.city" maxlength="32" />
        </el-form-item>
        <el-form-item label="区县">
          <el-input v-model="addressForm.district" maxlength="32" />
        </el-form-item>
        <el-form-item label="详细地址">
          <el-input v-model="addressForm.detail_address" type="textarea" :rows="3" maxlength="120" show-word-limit />
        </el-form-item>
        <el-form-item label="默认地址">
          <el-switch v-model="addressForm.is_default" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addressDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="addressSubmitting" @click="submitAddress">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown, Document } from '@element-plus/icons-vue'

import { userApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'
import { hasPermission } from '@/utils/permission'
import { PageHeader, FilterBar, StatusTag } from '@/components/common'

const userStore = useUserStore()
const canChangeUserStatus = computed(() => hasPermission(userStore.role, 'users:status', userStore.permissions))
const canChangeMemberLevel = computed(() => hasPermission(userStore.role, 'users:member-level', userStore.permissions))

const users = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

// 筛选表单
const filters = ref({
  keyword: '',
  source: '',
  role: '',
  member_level: ''
})

const memberLevelDialogVisible = ref(false)
const memberLevelSubmitting = ref(false)
const currentLevelUser = ref(null)
const memberLevelForm = ref({ member_level: 'NORMAL_MEMBER' })

// 抽屉状态
const drawerVisible = ref(false)
const inviteTree = ref({})
const legacyDrawerVisible = ref(false)
const legacyLoading = ref(false)
const legacyProfile = ref(null)
const detailDrawerVisible = ref(false)
const detailLoading = ref(false)
const userDetail = ref(null)
const activeTab = ref('invite')

// 充电宝表单
const powerBankSubmitting = ref(false)
const powerBankForm = ref({
  device_code: '',
  device_name: '',
  remark: ''
})

// 地址对话框
const addressDialogVisible = ref(false)
const addressSubmitting = ref(false)
const addressDialogMode = ref('create')
const editingAddressId = ref(null)
const addressForm = ref(createEmptyAddressForm())

const sourceOptions = [
  { label: '仅历史导入', value: 'legacy' },
  { label: '仅当前用户', value: 'native' }
]

const roleOptions = [
  { label: '超级管理员', value: 'SUPER_ADMIN' },
  { label: '团队管理员', value: 'TEAM_ADMIN' },
  { label: '普通用户', value: 'USER' }
]

const memberLevelOptions = [
  { label: '普通会员', value: 'NORMAL_MEMBER' },
  { label: '经销商', value: 'DEALER' },
  { label: '区代理', value: 'COUNTY_AGENT' },
  { label: '市代理', value: 'CITY_AGENT' }
]

const filterFields = [
  { key: 'keyword', type: 'input', placeholder: '搜索手机号、昵称、邀请码', width: 240 },
  { key: 'source', type: 'select', label: '来源', options: sourceOptions, width: 140 },
  { key: 'role', type: 'select', label: '角色', options: roleOptions, width: 160 },
  { key: 'member_level', type: 'select', label: '会员等级', options: memberLevelOptions, width: 140 }
]

const scopeHint = computed(() =>
  userStore.role === 'TEAM_ADMIN'
    ? '仅查看当前团队用户，支持按来源和角色筛选。'
    : '查看全平台用户，支持筛选历史导入与当前注册用户。'
)

const addressDialogTitle = computed(() => (addressDialogMode.value === 'edit' ? '编辑地址' : '新增地址'))

const legacyFields = computed(() => {
  const payload = legacyProfile.value?.legacy_profile || {}
  return Object.entries(payload).map(([key, value]) => ({
    key,
    value: value === null || value === '' ? '--' : String(value)
  }))
})

const assetRows = computed(() => {
  const summary = userDetail.value?.asset_summary || {}
  return Object.entries(summary).map(([assetType, item]) => ({
    assetType,
    availableAmount: formatAmount(item.available_amount),
    totalAmount: formatAmount(item.total_amount),
    frozenAmount: formatAmount(item.frozen_amount),
    consumedAmount: formatAmount(item.consumed_amount),
    withdrawnAmount: formatAmount(item.withdrawn_amount)
  }))
})

const powerBankRows = computed(() => userDetail.value?.power_banks || [])
const commerceSummary = computed(() => userDetail.value?.commerce_summary || {})
const addressRows = computed(() => userDetail.value?.addresses || [])
const favoriteRows = computed(() => userDetail.value?.favorites || [])
const cartRows = computed(() => userDetail.value?.cart_items || [])

function roleLabel(role) {
  return roleOptions.find((item) => item.value === role)?.label || role || '--'
}

function memberLevelLabel(level) {
  return memberLevelOptions.find((item) => item.value === level)?.label || level || '--'
}

function memberLevelTag(level) {
  return {
    NORMAL_MEMBER: 'info',
    DEALER: 'success',
    COUNTY_AGENT: 'warning',
    CITY_AGENT: 'danger'
  }[level] || 'info'
}

function formatAmount(value) {
  return value == null ? '--' : Number(value).toFixed(2)
}

function formatDate(value) {
  if (!value) return '--'
  return String(value).replace('T', ' ').slice(0, 19)
}

function zoneLabel(value) {
  return {
    REPURCHASE: '复购区',
    SELF_OPERATED: '自营商城',
    HOT_SALE: '爆款区',
    LOCAL_LIFE: '本地生活'
  }[value] || value || '--'
}

function createEmptyAddressForm() {
  return {
    receiver_name: '',
    receiver_phone: '',
    province: '',
    city: '',
    district: '',
    detail_address: '',
    is_default: false
  }
}

function resetPowerBankForm() {
  powerBankForm.value = {
    device_code: '',
    device_name: '',
    remark: ''
  }
}

function resetAddressForm() {
  addressDialogMode.value = 'create'
  editingAddressId.value = null
  addressForm.value = createEmptyAddressForm()
}

function fillAddressForm(row) {
  addressForm.value = {
    receiver_name: row.receiver_name || '',
    receiver_phone: row.receiver_phone || '',
    province: row.province || '',
    city: row.city || '',
    district: row.district || '',
    detail_address: row.detail_address || '',
    is_default: Boolean(row.is_default)
  }
}

function validateAddressForm() {
  const requiredFields = [
    ['receiver_name', '收货人'],
    ['receiver_phone', '手机号'],
    ['province', '省份'],
    ['city', '城市'],
    ['district', '区县'],
    ['detail_address', '详细地址']
  ]
  for (const [field, label] of requiredFields) {
    if (!String(addressForm.value[field] || '').trim()) {
      ElMessage.warning(`请输入${label}`)
      return false
    }
  }
  return true
}

async function fetchUsers(nextPage = page.value) {
  page.value = nextPage
  const data = await userApi.list({
    page: page.value,
    page_size: pageSize.value,
    keyword: filters.value.keyword || undefined,
    role: filters.value.role || undefined,
    member_level: filters.value.member_level || undefined,
    source: filters.value.source || undefined
  })
  users.value = data.items || []
  total.value = data.total || 0
}

async function loadUserDetail(userId) {
  userDetail.value = await userApi.detail(userId)
}

async function refreshUserDetail() {
  if (!userDetail.value?.id) return
  detailLoading.value = true
  try {
    await loadUserDetail(userDetail.value.id)
  } finally {
    detailLoading.value = false
  }
}

async function openUserDetail(row) {
  detailLoading.value = true
  detailDrawerVisible.value = true
  activeTab.value = 'invite'
  try {
    await loadUserDetail(row.id)
  } finally {
    detailLoading.value = false
  }
}

function openMemberLevelDialog(row) {
  currentLevelUser.value = row
  memberLevelForm.value = { member_level: row.member_level || 'NORMAL_MEMBER' }
  memberLevelDialogVisible.value = true
}

async function submitMemberLevel() {
  if (!currentLevelUser.value?.id) return
  memberLevelSubmitting.value = true
  try {
    await userApi.updateMemberLevel(currentLevelUser.value.id, memberLevelForm.value)
    ElMessage.success('会员等级已更新')
    memberLevelDialogVisible.value = false
    await fetchUsers()
    if (userDetail.value?.id === currentLevelUser.value.id) await refreshUserDetail()
  } finally {
    memberLevelSubmitting.value = false
  }
}

async function openInviteTree(row) {
  inviteTree.value = await userApi.inviteTree(row.id)
  drawerVisible.value = true
}

async function openLegacyProfile(row) {
  if (!row.is_legacy_imported) return
  legacyLoading.value = true
  legacyDrawerVisible.value = true
  try {
    legacyProfile.value = await userApi.legacyProfile(row.id)
  } finally {
    legacyLoading.value = false
  }
}

function handleMoreAction(cmd, row) {
  switch (cmd) {
    case 'legacy':
      openLegacyProfile(row)
      break
    case 'toggle':
      toggleStatus(row)
      break
  }
}

function openAddressCreate() {
  resetAddressForm()
  addressDialogVisible.value = true
}

function openAddressEdit(row) {
  addressDialogMode.value = 'edit'
  editingAddressId.value = row.id
  fillAddressForm(row)
  addressDialogVisible.value = true
}

async function submitAddress() {
  if (!userDetail.value?.id || !validateAddressForm()) return
  addressSubmitting.value = true
  try {
    const payload = {
      receiver_name: addressForm.value.receiver_name.trim(),
      receiver_phone: addressForm.value.receiver_phone.trim(),
      province: addressForm.value.province.trim(),
      city: addressForm.value.city.trim(),
      district: addressForm.value.district.trim(),
      detail_address: addressForm.value.detail_address.trim(),
      is_default: Boolean(addressForm.value.is_default)
    }
    if (addressDialogMode.value === 'edit' && editingAddressId.value) {
      await userApi.updateAddress(userDetail.value.id, editingAddressId.value, payload)
      ElMessage.success('地址已更新')
    } else {
      await userApi.createAddress(userDetail.value.id, payload)
      ElMessage.success('地址已新增')
    }
    addressDialogVisible.value = false
    resetAddressForm()
    await refreshUserDetail()
  } finally {
    addressSubmitting.value = false
  }
}

async function setDefaultAddress(row) {
  if (!userDetail.value?.id || !row?.id || row.is_default) return
  await userApi.setDefaultAddress(userDetail.value.id, row.id)
  ElMessage.success('默认地址已更新')
  await refreshUserDetail()
}

async function deleteAddress(row) {
  if (!userDetail.value?.id || !row?.id) return
  await ElMessageBox.confirm('确认删除该收货地址吗？', '删除地址', {
    type: 'warning'
  })
  await userApi.deleteAddress(userDetail.value.id, row.id)
  ElMessage.success('地址已删除')
  await refreshUserDetail()
}

async function deleteCartItem(row) {
  if (!userDetail.value?.id || !row?.id) return
  await ElMessageBox.confirm('确认删除该购物车商品吗？', '删除购物车商品', {
    type: 'warning'
  })
  await userApi.deleteCartItem(userDetail.value.id, row.id)
  ElMessage.success('购物车商品已删除')
  await refreshUserDetail()
}

async function deleteFavorite(row) {
  if (!userDetail.value?.id || !row?.product_id) return
  await ElMessageBox.confirm('确认移除该收藏商品吗？', '移除收藏', {
    type: 'warning'
  })
  await userApi.deleteFavorite(userDetail.value.id, row.product_id)
  ElMessage.success('收藏商品已移除')
  await refreshUserDetail()
}

async function submitPowerBank() {
  if (!userDetail.value?.id) return
  if (!String(powerBankForm.value.device_code || '').trim()) {
    ElMessage.warning('请输入设备编号')
    return
  }
  powerBankSubmitting.value = true
  try {
    await userApi.bindPowerBank(userDetail.value.id, powerBankForm.value)
    ElMessage.success('充电宝已绑定')
    resetPowerBankForm()
    await refreshUserDetail()
  } finally {
    powerBankSubmitting.value = false
  }
}

async function togglePowerBankStatus(row) {
  if (!userDetail.value?.id || !row?.id) return
  const nextStatus = row.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE'
  await ElMessageBox.confirm(`确认将该充电宝状态调整为 ${nextStatus} 吗？`, '充电宝状态变更', {
    type: 'warning'
  })
  await userApi.updatePowerBank(userDetail.value.id, row.id, { status: nextStatus })
  ElMessage.success('充电宝状态已更新')
  await refreshUserDetail()
}

async function toggleStatus(row) {
  const nextStatus = row.status === 'ENABLED' ? 'DISABLED' : 'ENABLED'
  await ElMessageBox.confirm(`确认将该用户状态调整为 ${nextStatus} 吗？`, '状态变更', {
    type: 'warning'
  })
  await userApi.updateStatus(row.id, { status: nextStatus })
  ElMessage.success('用户状态已更新')
  await fetchUsers()
}

function handleSearch() {
  fetchUsers(1)
}

function handleReset() {
  filters.value = {
    keyword: '',
    source: '',
    role: '',
    member_level: ''
  }
  fetchUsers(1)
}

function handlePageSizeChange() {
  fetchUsers(1)
}

onMounted(fetchUsers)
</script>

<style scoped>
@import '@/styles/variables.css';

.user-list-view {
  display: grid;
  gap: var(--space-4);
}

.data-card {
  padding: var(--space-5);
}

.cell-title {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

.cell-meta {
  margin-top: 4px;
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.action-group {
  display: flex;
  gap: var(--space-1);
}

.table-pagination {
  margin-top: var(--space-5);
  justify-content: flex-end;
}

/* 详情抽屉 */
.detail-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.detail-section {
  padding: var(--space-4) 0;
  border-bottom: 1px solid var(--border-light);
}

.detail-section:last-child {
  border-bottom: none;
}

.section-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0 0 var(--space-4);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.section-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-md);
  background: var(--primary-50);
  color: var(--primary-deep);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.info-item:first-child:nth-last-child(odd) {
  grid-column: span 2;
}

.info-label {
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.info-value {
  font-size: var(--text-base);
  color: var(--text-primary);
}

/* 标签页 */
.detail-tabs {
  padding-top: 0;
}

.detail-tabs :deep(.el-tabs__header) {
  margin-bottom: var(--space-4);
}

.detail-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
}

.detail-tabs :deep(.el-tabs__item) {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
}

.detail-tabs :deep(.el-tabs__item.is-active) {
  color: var(--primary-deep);
}

.detail-tabs :deep(.el-tabs__active-bar) {
  background-color: var(--primary-mid);
}

/* 统计网格 */
.tiny-stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: var(--space-3);
}

.tiny-stat {
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-light);
  background: var(--surface-secondary);
  text-align: center;
}

.tiny-stat .title {
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.tiny-stat .number {
  margin-top: var(--space-2);
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}

/* 充电宝表单 */
.powerbank-form {
  display: flex;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.powerbank-form .el-input {
  flex: 1;
}

/* 邀请关系 */
.invite-header {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.invite-user {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--surface-secondary);
}

.invite-label {
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.invite-value {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

/* 响应式 */
@media (max-width: 768px) {
  .info-grid {
    grid-template-columns: 1fr;
  }

  .info-item:first-child:nth-last-child(odd) {
    grid-column: span 1;
  }

  .powerbank-form {
    flex-direction: column;
  }

  .action-group {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
