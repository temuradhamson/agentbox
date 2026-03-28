<script setup lang="ts">
const auth = useAuthStore()
const login = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  if (!login.value || !password.value) return
  loading.value = true
  error.value = ''
  try {
    await auth.login(login.value, password.value)
    navigateTo('/chat')
  } catch (e: any) {
    error.value = e.message || 'Login failed'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (auth.isAuthenticated) navigateTo('/chat')
})
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-surface-950">
    <div class="bg-surface-900 border border-surface-700 rounded-2xl p-8 w-[360px] shadow-2xl animate-fade-in">
      <div class="text-center mb-8">
        <div class="text-4xl mb-3">🤖</div>
        <h1 class="text-xl font-bold text-white">Agent Hub</h1>
        <p class="text-sm text-surface-500 mt-1">AI Agent Control Panel</p>
      </div>

      <form @submit.prevent="submit" class="space-y-4">
        <div>
          <label class="block text-xs font-medium text-surface-500 mb-1.5">Login</label>
          <input v-model="login" type="text" autocomplete="username" placeholder="admin"
            class="focus-ring w-full bg-surface-800 border border-surface-600 rounded-lg px-3 py-2.5 text-sm text-white placeholder-surface-600 transition hover:border-surface-500" />
        </div>
        <div>
          <label class="block text-xs font-medium text-surface-500 mb-1.5">Password</label>
          <input v-model="password" type="password" autocomplete="current-password" placeholder="••••••••"
            @keydown.enter="submit"
            class="focus-ring w-full bg-surface-800 border border-surface-600 rounded-lg px-3 py-2.5 text-sm text-white placeholder-surface-600 transition hover:border-surface-500" />
        </div>

        <p v-if="error" class="text-xs text-danger text-center">{{ error }}</p>

        <button type="submit" :disabled="loading"
          class="w-full h-10 rounded-lg text-sm font-semibold text-white bg-accent hover:bg-accent-hover transition shadow-[0_0_16px_var(--color-accent-glow)] disabled:opacity-50">
          {{ loading ? 'Connecting...' : 'Sign In' }}
        </button>
      </form>
    </div>
  </div>
</template>
