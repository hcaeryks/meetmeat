<script lang="ts">
	import { saveState, saveProgress, saveError, retrySave } from '$lib/stores';
	import { Check, Loader2, AlertCircle } from 'lucide-svelte';

	const CIRCUMFERENCE = 2 * Math.PI * 10;
</script>

{#if $saveState !== 'idle'}
	<div class="flex items-center gap-2 text-sm">
		{#if $saveState === 'countdown' || $saveState === 'saving'}
			<svg width="24" height="24" viewBox="0 0 24 24" class="text-muted-foreground">
				<circle
					cx="12"
					cy="12"
					r="10"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					opacity="0.2"
				/>
				<circle
					cx="12"
					cy="12"
					r="10"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-dasharray={CIRCUMFERENCE}
					stroke-dashoffset={CIRCUMFERENCE * (1 - $saveProgress)}
					transform="rotate(-90 12 12)"
					class="transition-[stroke-dashoffset] duration-100"
				/>
			</svg>
				<span class="text-muted-foreground">
					{$saveState === 'saving' ? 'Saving…' : 'Saving soon…'}
				</span>
		{:else if $saveState === 'saved'}
			<Check class="h-5 w-5 text-ideal" />
			<span class="text-ideal">Saved</span>
		{:else if $saveState === 'error'}
			<AlertCircle class="h-5 w-5 text-destructive" />
			<span class="text-destructive">{$saveError}</span>
			<button
				class="text-xs underline text-destructive hover:text-destructive/80"
				onclick={() => retrySave()}
			>
				Retry
			</button>
		{/if}
	</div>
{/if}
