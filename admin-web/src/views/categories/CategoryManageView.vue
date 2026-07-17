<template>
  <div class="category-view">
    <PageHeader title="商品分类管理" description="管理移动端商品分类，支持添加、编辑、删除分类，设置分类排序。">
      <template #actions>
        <el-button type="primary" @click="openCreate">新增分类</el-button>
      </template>
    </PageHeader>

    <!-- 分类列表 -->
    <div class="panel-card">
      <div class="category-header">
        <span class="col-name">分类名称</span>
        <span class="col-slug">标识</span>
        <span class="col-sort">排序</span>
        <span class="col-count">商品数</span>
        <span class="col-status">状态</span>
        <span class="col-actions">操作</span>
      </div>

      <div v-loading="loading" class="category-list">
        <div
          v-for="item in categories"
          :key="item.id"
          class="category-row"
          :class="{ 'is-disabled': item.status === 'disabled' }"
        >
          <div class="col-name">
            <span class="category-name">{{ item.name }}</span>
          </div>
          <div class="col-slug">
            <code>{{ item.slug }}</code>
          </div>
          <div class="col-sort">
            <el-input-number
              v-model="item.sort_order"
              :min="0"
              :max="9999"
              size="small"
              controls-position="right"
              @change="updateSort(item)"
            />
          </div>
          <div class="col-count">
            <span class="count-badge">{{ item.product_count || 0 }}</span>
          </div>
          <div class="col-status">
            <el-switch
              v-model="item.status"
              active-value="active"
              inactive-value="disabled"
              @change="updateStatus(item)"
            />
          </div>
          <div class="col-actions">
            <el-button link type="primary" @click="openEdit(item)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(item)">删除</el-button>
          </div>
        </div>

        <div v-if="!loading && !categories.length" class="empty-state">
          <el-empty description="暂无商品分类">
            <el-button type="primary" @click="openCreate">新增分类</el-button>
          </el-empty>
        </div>
      </div>
    </div>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="500px"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="分类名称" prop="name">
          <el-input v-model="form.name" placeholder="例如：数码产品、家居用品" maxlength="20" show-word-limit />
        </el-form-item>
        <el-form-item label="分类标识" prop="slug">
          <el-input v-model="form.slug" placeholder="英文标识，如：digital、home" :disabled="!!editingId">
            <template #append>
              <el-button @click="generateSlug">自动生成</el-button>
            </template>
          </el-input>
          <div class="form-tip">用于移动端 API 接口，建议使用英文小写</div>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" :max="9999" controls-position="right" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.status" active-value="active" inactive-value="disabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { categoryApi } from '@/api/modules'
import { PageHeader } from '@/components/common'

const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingId = ref(null)
const categories = ref([])
const formRef = ref(null)

const form = reactive({
  name: '',
  slug: '',
  sort_order: 0,
  status: 'active'
})

const rules = {
  name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }],
  slug: [
    { required: true, message: '请输入分类标识', trigger: 'blur' },
    { pattern: /^[a-z0-9-_]+$/, message: '只能包含小写字母、数字、短横线和下划线', trigger: 'blur' }
  ]
}

const dialogTitle = computed(() => editingId.value ? '编辑分类' : '新增分类')

const generateSlug = () => {
  if (form.name) {
    form.slug = form.name
      .toLowerCase()
      .replace(/[一-龥]/g, '')
      .replace(/\s+/g, '-')
      .replace(/[^a-z0-9-_]/g, '')
      .substring(0, 30)
  }
}

const loadCategories = async () => {
  loading.value = true
  try {
    const res = await categoryApi.list()
    categories.value = Array.isArray(res) ? res : res?.data || res?.list || []
  } catch (error) {
    console.error('加载分类失败', error)
    ElMessage.error('加载分类失败')
  } finally {
    loading.value = false
  }
}

const openCreate = () => {
  editingId.value = null
  dialogVisible.value = true
}

const openEdit = (item) => {
  editingId.value = item.id
  form.name = item.name
  form.slug = item.slug
  form.sort_order = item.sort_order
  form.status = item.status
  dialogVisible.value = true
}

const resetForm = () => {
  form.name = ''
  form.slug = ''
  form.sort_order = 0
  form.status = 'active'
  editingId.value = null
}

const handleSave = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    if (editingId.value) {
      await categoryApi.update(editingId.value, {
        name: form.name,
        sort_order: form.sort_order,
        status: form.status
      })
      ElMessage.success('分类已更新')
    } else {
      await categoryApi.create(form)
      ElMessage.success('分类已创建')
    }
    dialogVisible.value = false
    loadCategories()
  } catch (error) {
    console.error('保存失败', error)
    ElMessage.error(error?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const updateSort = async (item) => {
  try {
    await categoryApi.update(item.id, { sort_order: item.sort_order })
    ElMessage.success('排序已更新')
  } catch (error) {
    ElMessage.error('更新排序失败')
    loadCategories()
  }
}

const updateStatus = async (item) => {
  try {
    await categoryApi.updateStatus(item.id, { status: item.status })
    ElMessage.success(`分类已${item.status === 'active' ? '启用' : '禁用'}`)
  } catch (error) {
    ElMessage.error('更新状态失败')
    loadCategories()
  }
}

const handleDelete = async (item) => {
  if (item.product_count > 0) {
    ElMessage.warning(`该分类下有 ${item.product_count} 个商品，请先转移或删除商品`)
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除分类「${item.name}」吗？此操作不可恢复。`,
      '删除确认',
      { type: 'warning' }
    )
    await categoryApi.delete(item.id)
    ElMessage.success('分类已删除')
    loadCategories()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadCategories()
})
</script>

<style scoped>
.category-view {
  padding: 24px;
}

.category-header {
  display: grid;
  grid-template-columns: 2fr 1.5fr 100px 80px 80px 120px;
  gap: 16px;
  padding: 12px 16px;
  background: var(--bg-100);
  border-radius: 8px 8px 0 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}

.category-list {
  min-height: 200px;
}

.category-row {
  display: grid;
  grid-template-columns: 2fr 1.5fr 100px 80px 80px 120px;
  gap: 16px;
  padding: 16px;
  border-bottom: 1px solid var(--border-200);
  align-items: center;
  transition: background-color 0.2s;
}

.category-row:hover {
  background: var(--bg-50);
}

.category-row.is-disabled {
  opacity: 0.6;
}

.category-row:last-child {
  border-bottom: none;
}

.category-name {
  font-weight: 500;
  color: var(--text-primary);
}

.col-slug code {
  font-family: 'SF Mono', Monaco, Consolas, monospace;
  font-size: 12px;
  padding: 2px 8px;
  background: var(--bg-100);
  border-radius: 4px;
  color: var(--primary-600);
}

.count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  padding: 4px 12px;
  background: var(--bg-100);
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
}

.col-actions {
  display: flex;
  gap: 8px;
}

.empty-state {
  padding: 48px;
}

.form-tip {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

@media (max-width: 900px) {
  .category-header,
  .category-row {
    grid-template-columns: 1fr 100px 80px 120px;
  }

  .col-slug,
  .col-count {
    display: none;
  }
}
</style>
