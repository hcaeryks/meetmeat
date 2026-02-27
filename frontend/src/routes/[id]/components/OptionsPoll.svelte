<script lang="ts">
	import { format } from 'date-fns';
	import type { CellValue } from '$lib/utils/grid';
	import { optionsPollFromAvailability, optionsPollToAvailability } from '$lib/availability';
	import type { ChangeHandler } from '$lib/availability';

	interface Props {
		plan: Record<string, any>;
		availability: Record<string, any>;
		onchange: ChangeHandler;
	}

	let { plan, availability = $bindable({}), onchange }: Props = $props();

	const config = $derived(plan.config as Record<string, any>);
	const options = $derived((config.options || []) as Array<{ option_id: string; start_utc: string; duration_minutes: number }>);

	let votes = $state<Record<string, CellValue>>({});
	let lastHydrationKey = '';

	function hydrationKey(nextAvailability: Record<string, any>): string {
		return JSON.stringify({
			availability: nextAvailability || {},
			optionIds: options.map((o) => o.option_id)
		});
	}

	$effect(() => {
		const key = hydrationKey(availability || {});
		if (key === lastHydrationKey) return;
		votes = optionsPollFromAvailability(plan, availability).votes;
		lastHydrationKey = key;
	});

	function setVote(optionId: string, value: CellValue) {
		const nextVotes = { ...votes, [optionId]: value };
		votes = nextVotes;
		const nextAvailability = optionsPollToAvailability(plan, { votes: nextVotes });
		lastHydrationKey = hydrationKey(nextAvailability);
		availability = nextAvailability;
		queueMicrotask(() => onchange({ immediate: true }));
	}

	function formatOption(opt: { start_utc: string; duration_minutes: number }): string {
		try {
			const d = new Date(opt.start_utc);
			return `${format(d, 'EEE, MMM d, yyyy h:mm a')} (${opt.duration_minutes}min)`;
		} catch {
			return opt.start_utc;
		}
	}

	function btnClass(optionId: string, value: CellValue): string {
		const current = votes[optionId] || 'UNSET';
		const base = 'px-3 py-1 rounded text-xs font-medium border-2 transition-colors ';
		if (current === value) {
			if (value === 'IDEAL') return base + 'border-ideal bg-ideal-bg';
			if (value === 'OK') return base + 'border-ok bg-ok-bg';
			return base + 'border-destructive bg-destructive/10';
		}
		return base + 'border-border hover:border-muted-foreground';
	}
</script>

<div class="space-y-3">
	{#each options as opt}
		<div class="p-3 rounded-lg border border-border flex flex-col sm:flex-row sm:items-center gap-2 justify-between">
			<span class="text-sm">{formatOption(opt)}</span>
			<div class="flex gap-2">
				<button class={btnClass(opt.option_id, 'IDEAL')} onclick={() => setVote(opt.option_id, 'IDEAL')}>
					Yes
				</button>
				<button class={btnClass(opt.option_id, 'OK')} onclick={() => setVote(opt.option_id, 'OK')}>
					Maybe
				</button>
				<button class={btnClass(opt.option_id, 'UNSET')} onclick={() => setVote(opt.option_id, 'UNSET')}>
					No
				</button>
			</div>
		</div>
	{/each}
</div>
