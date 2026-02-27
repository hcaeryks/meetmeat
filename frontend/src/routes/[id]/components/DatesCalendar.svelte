<script lang="ts">
	import { format, addMonths, startOfMonth, endOfMonth, startOfWeek, endOfWeek, eachDayOfInterval, isSameMonth, isWithinInterval, parseISO } from 'date-fns';
	import type { CellValue } from '$lib/utils/grid';
	import { ChevronLeft, ChevronRight } from 'lucide-svelte';
	import { datesOnlyFromAvailability, datesOnlyToAvailability } from '$lib/availability';
	import type { ChangeHandler } from '$lib/availability';

	interface Props {
		plan: Record<string, any>;
		availability: Record<string, any>;
		onchange: ChangeHandler;
	}

	let { plan, availability = $bindable({}), onchange }: Props = $props();

	const config = $derived(plan.config as Record<string, any>);

	let currentMonth = $state(new Date());
	let dateValues = $state<Record<string, CellValue>>({});
	let lastHydrationKey = '';

	const calendarDays = $derived.by(() => {
		const monthStart = startOfMonth(currentMonth);
		const monthEnd = endOfMonth(currentMonth);
		const calStart = startOfWeek(monthStart);
		const calEnd = endOfWeek(monthEnd);
		return eachDayOfInterval({ start: calStart, end: calEnd });
	});

	const rangeStart = $derived(config.date_start_local ? parseISO(config.date_start_local) : null);
	const rangeEnd = $derived(config.date_end_local ? parseISO(config.date_end_local) : null);

	function hydrationKey(nextAvailability: Record<string, any>): string {
		return JSON.stringify({
			availability: nextAvailability || {},
			rangeStart: config.date_start_local || '',
			rangeEnd: config.date_end_local || ''
		});
	}

	$effect(() => {
		const key = hydrationKey(availability || {});
		if (key === lastHydrationKey) return;
		dateValues = datesOnlyFromAvailability(availability).dateValues;
		lastHydrationKey = key;
	});

	function isInRange(day: Date): boolean {
		if (!rangeStart && !rangeEnd) return true;
		if (rangeStart && rangeEnd) return isWithinInterval(day, { start: rangeStart, end: rangeEnd });
		if (rangeStart) return day >= rangeStart;
		if (rangeEnd) return day <= rangeEnd;
		return true;
	}

	function toggleDate(day: Date) {
		if (!isSameMonth(day, currentMonth)) return;
		if (!isInRange(day)) return;
		const key = format(day, 'yyyy-MM-dd');
		const current = dateValues[key] || 'UNSET';
		const next: CellValue = current === 'UNSET' ? 'IDEAL' : current === 'IDEAL' ? 'OK' : 'UNSET';
		const nextValues = { ...dateValues, [key]: next };
		dateValues = nextValues;
		const nextAvailability = datesOnlyToAvailability(plan, { dateValues: nextValues });
		lastHydrationKey = hydrationKey(nextAvailability);
		availability = nextAvailability;
		queueMicrotask(() => onchange({ immediate: true }));
	}

	function dayClass(day: Date): string {
		const key = format(day, 'yyyy-MM-dd');
		const val = dateValues[key] || 'UNSET';
		const inMonth = isSameMonth(day, currentMonth);
		const inRange = isInRange(day);
		let cls = 'h-10 w-10 flex items-center justify-center rounded-md text-sm cursor-pointer transition-colors ';
		if (!inMonth) cls += 'text-muted-foreground/30 ';
		else if (!inRange) cls += 'text-muted-foreground/50 cursor-not-allowed ';
		else if (val === 'IDEAL') cls += 'bg-ideal-bg text-foreground font-medium ';
		else if (val === 'OK') cls += 'bg-ok-bg text-foreground ';
		else cls += 'hover:bg-accent ';
		return cls;
	}

	function goToPrevMonth() {
		currentMonth = addMonths(currentMonth, -1);
	}

	function goToNextMonth() {
		currentMonth = addMonths(currentMonth, 1);
	}
</script>

<div class="space-y-3">
	<p class="text-xs text-muted-foreground">Click a date to cycle: Ideal → OK → Clear</p>

	<div class="flex items-center justify-between mb-2">
		<button onclick={goToPrevMonth} class="p-1 hover:bg-accent rounded">
			<ChevronLeft class="h-4 w-4" />
		</button>
		<span class="font-medium text-sm">{format(currentMonth, 'MMMM yyyy')}</span>
		<button onclick={goToNextMonth} class="p-1 hover:bg-accent rounded">
			<ChevronRight class="h-4 w-4" />
		</button>
	</div>

	<div class="grid grid-cols-7 gap-1">
		{#each ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'] as d}
			<div class="h-8 flex items-center justify-center text-xs font-medium text-muted-foreground">{d}</div>
		{/each}
		{#each calendarDays as day}
			<button class={dayClass(day)} onclick={() => toggleDate(day)}>
				{format(day, 'd')}
			</button>
		{/each}
	</div>

	<div class="flex items-center gap-3 text-xs text-muted-foreground mt-2">
		<span class="flex items-center gap-1"><span class="w-3 h-3 rounded bg-ideal-bg"></span> Ideal</span>
		<span class="flex items-center gap-1"><span class="w-3 h-3 rounded bg-ok-bg"></span> OK</span>
	</div>
</div>
