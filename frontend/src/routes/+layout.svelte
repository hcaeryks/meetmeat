<script lang="ts">
	import '../app.css';
	import ThemeToggle from '$lib/components/ThemeToggle.svelte';
	import { Calendar } from 'lucide-svelte';

	let { children } = $props();
</script>

<div class="min-h-screen flex flex-col bg-background text-foreground">
	<header class="border-b border-border px-4 py-3 flex items-center justify-between">
		<a href="/" class="flex items-center gap-2 font-semibold text-lg hover:opacity-80 transition-opacity">
			<Calendar class="h-5 w-5" />
			<span>meet me at</span>
		</a>
		<div class="flex items-center gap-2">
			<a
				href="/create"
				class="text-sm px-3 py-1.5 rounded-md bg-primary text-primary-foreground hover:opacity-90 transition-opacity"
			>
				New Plan
			</a>
			<ThemeToggle />
		</div>
	</header>

	<main class="flex-1">
		{@render children()}
	</main>
</div>
