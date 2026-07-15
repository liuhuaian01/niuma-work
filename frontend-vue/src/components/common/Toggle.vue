<template>
  <button class="toggle-switch" :class="{ on: modelValue }" type="button" role="switch" :aria-checked="modelValue" @click="$emit('update:modelValue', !modelValue)"></button>
</template>

<script setup lang="ts">
defineProps<{ modelValue: boolean }>()
defineEmits<{ 'update:modelValue': [val: boolean] }>()
</script>

<style scoped>
.toggle-switch { width: 38px; height: 22px; border-radius: 11px; border: 1px solid var(--border-default); background: var(--bg-overlay); cursor: pointer; transition: all .25s var(--ease-spring); position: relative; }
.toggle-switch::after { content: ''; position: absolute; top: 1px; left: 1px; width: 18px; height: 18px; border-radius: 50%; background: var(--text-tertiary); transition: all .25s var(--ease-spring); }
.toggle-switch.on { background: var(--brand); border-color: var(--brand); }
.toggle-switch.on::after { left: 17px; background: #fff; }
</style>
