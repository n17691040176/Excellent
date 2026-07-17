<template>
  <div class="page-header">
    <div class="page-header__left">
      <div class="page-header__title-row">
        <h1 class="page-header__title">{{ title }}</h1>
        <span v-if="badge" class="page-header__badge">{{ badge }}</span>
      </div>
      <p v-if="description" class="page-header__desc">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="page-header__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
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
  align-items: flex-start;
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

.page-header__desc {
  margin: var(--space-2) 0 0;
  font-size: var(--text-sm);
  color: var(--text-muted);
  line-height: var(--leading-normal);
}

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