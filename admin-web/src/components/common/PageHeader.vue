<template>
  <div class="page-header">
    <div class="page-header__left">
      <div class="page-header__title-row">
        <h1 class="page-header__title">{{ title }}</h1>
        <span v-if="badge" class="page-header__badge">{{ badge }}</span>
        <el-popover v-if="description" trigger="click" placement="bottom-start" :width="320" :content="description">
          <template #reference>
            <button class="page-header__help" type="button" :aria-label="`${title}说明`"><el-icon><InfoFilled /></el-icon></button>
          </template>
        </el-popover>
      </div>
    </div>
    <div v-if="$slots.actions" class="page-header__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
import { InfoFilled } from '@element-plus/icons-vue'
defineProps({
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    default: ''
  },
  badge: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
@import '@/styles/variables.css';

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-6);
  padding: var(--space-6);
  background: var(--bg-surface);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
}

.page-header__left {
  flex: 1;
  min-width: 0;
}

.page-header__title-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.page-header__title {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  line-height: var(--leading-tight);
  letter-spacing: -0.01em;
}

.page-header__badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--accent-dark);
  background: rgba(212, 168, 83, 0.12);
  border: 1px solid rgba(212, 168, 83, 0.25);
  border-radius: var(--radius-full);
}

.page-header__help {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 0;
  background: transparent;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  cursor: pointer;
}
.page-header__help:hover, .page-header__help:focus-visible { background: var(--bg-muted); color: var(--primary-deep); }

.page-header__actions {
  display: flex;
  gap: var(--space-3);
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: var(--space-4);
    padding: var(--space-4);
  }

  .page-header__actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .page-header__title {
    font-size: var(--text-xl);
  }
}
</style>
