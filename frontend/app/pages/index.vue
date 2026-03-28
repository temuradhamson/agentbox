<script setup lang="ts">
definePageMeta({ middleware: 'auth' })
const auth = useAuthStore()
onMounted(() => {
  if (auth.isAuthenticated) navigateTo('/chat')
  else navigateTo('/login')
})
</script>

<template>
  <div />
</template>
