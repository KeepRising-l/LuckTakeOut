<script setup lang="ts">
/**
 * 餐饮主题线性图标（内联 SVG，stroke 1.7 / round / currentColor，24×24）
 * 依据设计规范 §5：分类入口禁用 emoji，统一使用本组件。
 */
withDefaults(defineProps<{ name: IconName; size?: number | string }>(), { size: 24 })

type IconName = 'noodle' | 'milkTea' | 'burger' | 'skewer' | 'watermelon' | 'cake' | 'egg' | 'moon'
</script>

<template>
  <svg
    v-if="name === 'noodle'"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path d="M3.5 11.5h17c0 4.4-3.8 8-8.5 8s-8.5-3.6-8.5-8Z" />
    <path d="M9.5 3.5c-1.1 1.1-1.1 2.2 0 3.3" />
    <path d="M14.5 3.5c-1.1 1.1-1.1 2.2 0 3.3" />
    <path d="M6.5 6.5 19 17" />
  </svg>

  <svg
    v-else-if="name === 'milkTea'"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path d="M8 9.5 9.3 20a1.6 1.6 0 0 0 1.6 1.5h2.2a1.6 1.6 0 0 0 1.6-1.5L16 9.5Z" />
    <path d="M7 9.5h10" />
    <path d="M13 3.5 11.8 8" />
    <path d="M10.2 18.2h.01" />
    <path d="M13.8 18.2h.01" />
  </svg>

  <svg
    v-else-if="name === 'burger'"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path d="M5 10c0-3.1 3.1-4.7 7-4.7S19 6.9 19 10Z" />
    <path d="M5 12.5h14" />
    <path d="M6.5 15h11c0 2-1.6 3.6-5.5 3.6S6.5 17 6.5 15Z" />
  </svg>

  <svg
    v-else-if="name === 'skewer'"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path d="M4.5 19.5 19.5 4.5" />
    <circle cx="8" cy="16" r="1.7" />
    <circle cx="12" cy="12" r="1.7" />
    <circle cx="16" cy="8" r="1.7" />
  </svg>

  <svg
    v-else-if="name === 'watermelon'"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path d="M4 15.5a8 8 0 0 1 16 0Z" />
    <path d="M6.8 15.5a5.2 5.2 0 0 1 10.4 0" />
    <path d="M10 13.2h.01" />
    <path d="M12.8 11.6h.01" />
    <path d="M15.4 13.2h.01" />
  </svg>

  <svg
    v-else-if="name === 'cake'"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path d="M5 20h14" />
    <path d="M6.5 20v-6.5c0-.8.6-1.5 1.4-1.5h8.2c.8 0 1.4.7 1.4 1.5V20" />
    <path d="M6.5 15.5c1.2-1.2 2.6-1.2 3.8 0s2.6 1.2 3.8 0 2.4-1.2 3.4 0" />
    <path d="M12 6.2V8" />
    <circle cx="12" cy="4.8" r="1.3" />
  </svg>

  <svg
    v-else-if="name === 'egg'"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path d="M12 3.5c3.6 0 6.8 3 6.8 6.9 0 4-3 7.6-6.8 7.6s-6.8-3.6-6.8-7.6c0-3.9 3.2-6.9 6.8-6.9Z" />
    <circle cx="10.2" cy="10.6" r="1.9" />
  </svg>

  <svg
    v-else
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path d="M19.5 14.5A8 8 0 0 1 9.5 4.5a8 8 0 1 0 10 10Z" />
    <path d="M17 4.5h.01" />
    <path d="M18.8 7.8h.01" />
  </svg>
</template>
