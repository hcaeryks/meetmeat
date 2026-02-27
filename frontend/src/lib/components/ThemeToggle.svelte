<script lang="ts">
	import { Sun, Moon } from 'lucide-svelte';
	import { theme } from '$lib/stores';
	import { onMount } from 'svelte';

	let isDark = $state(false);

	onMount(() => {
		const stored = localStorage.getItem('theme') as 'dark' | 'light' | 'system' | null;
		if (stored) theme.set(stored);
		applyTheme();
	});

	theme.subscribe(() => applyTheme());

	function applyTheme() {
		const val = $theme;
		if (typeof document === 'undefined') return;
		let dark = false;
		if (val === 'dark') dark = true;
		else if (val === 'system') dark = window.matchMedia('(prefers-color-scheme: dark)').matches;
		isDark = dark;
		document.documentElement.classList.toggle('dark', dark);
	}

	function toggle() {
		const next = isDark ? 'light' : 'dark';
		theme.set(next);
		localStorage.setItem('theme', next);
		applyTheme();
	}
</script>

<button
	onclick={toggle}
	class="inline-flex items-center justify-center rounded-md p-2 hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
	aria-label="Toggle theme"
>
	{#if isDark}
		<Sun class="h-5 w-5" />
	{:else}
		<Moon class="h-5 w-5" />
	{/if}
</button>
