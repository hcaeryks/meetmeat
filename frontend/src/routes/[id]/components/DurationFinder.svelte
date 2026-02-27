<script lang="ts">
	import { getSlotLabel, slotsPerDay } from '$lib/utils/time';
	import { type CellValue, fillRect } from '$lib/utils/grid';
	import { format, parseISO } from 'date-fns';
	import { dateTimeWindowsDates, durationFinderFromAvailability, durationFinderToAvailability } from '$lib/availability';
	import type { ChangeHandler } from '$lib/availability';

	interface Props {
		plan: Record<string, any>;
		availability: Record<string, any>;
		onchange: ChangeHandler;
	}

	let { plan, availability = $bindable({}), onchange }: Props = $props();

	const config = $derived(plan.config as Record<string, any>);
	const slotMinutes = $derived(plan.slot_minutes || 15);
	const rows = $derived(slotsPerDay(slotMinutes));
	const dates = $derived(dateTimeWindowsDates(plan, 60));
	const cols = $derived(dates.length);

	let cells = $state<CellValue[]>([]);
	let brush = $state<CellValue>('IDEAL');
	let activeBrush = $state<CellValue>('IDEAL');
	let dragging = $state(false);
	let anchorRow = $state(-1);
	let anchorCol = $state(-1);
	let previewCells = $state<CellValue[]>([]);
	let lastHydrationKey = '';

	const columnHeaders = $derived(
		dates.map((d) => format(parseISO(d), 'MMM d'))
	);

	function hydrationKey(nextAvailability: Record<string, any>): string {
		return JSON.stringify({
			availability: nextAvailability || {},
			slotMinutes,
			dates
		});
	}

	$effect(() => {
		const key = hydrationKey(availability || {});
		if (dragging || key === lastHydrationKey) return;
		const parsed = durationFinderFromAvailability(plan, availability);
		cells = parsed.cells;
		previewCells = [...parsed.cells];
		lastHydrationKey = key;
	});

	function commitCells(nextCells: CellValue[]) {
		cells = [...nextCells];
		previewCells = [...nextCells];
		const nextAvailability = durationFinderToAvailability(plan, { cells: nextCells });
		lastHydrationKey = hydrationKey(nextAvailability);
		availability = nextAvailability;
		queueMicrotask(() => onchange({ immediate: true }));
	}

	function getCellFromPoint(x: number, y: number): { row: number; col: number } | null {
		const el = document.elementFromPoint(x, y) as HTMLElement | null;
		if (!el?.dataset.row || !el.dataset.col) return null;
		return { row: parseInt(el.dataset.row, 10), col: parseInt(el.dataset.col, 10) };
	}

	function onPointerDown(e: PointerEvent, row: number, col: number) {
		e.preventDefault();
		dragging = true;
		anchorRow = row;
		anchorCol = col;
		activeBrush = brush;
		const next = fillRect([...cells], row, col, row, col, cols, activeBrush);
		previewCells = next;
	}

	function onPointerMove(e: PointerEvent) {
		if (!dragging) return;
		e.preventDefault();
		const cell = getCellFromPoint(e.clientX, e.clientY);
		if (!cell) return;
		previewCells = fillRect([...cells], anchorRow, anchorCol, cell.row, cell.col, cols, activeBrush);
	}

	function onPointerUp() {
		if (!dragging) return;
		dragging = false;
		commitCells(previewCells);
	}

	$effect(() => {
		if (!dragging) return;
		const handlePointerMove = (e: PointerEvent) => onPointerMove(e);
		const handlePointerDone = () => onPointerUp();
		window.addEventListener('pointermove', handlePointerMove);
		window.addEventListener('pointerup', handlePointerDone);
		window.addEventListener('pointercancel', handlePointerDone);
		return () => {
			window.removeEventListener('pointermove', handlePointerMove);
			window.removeEventListener('pointerup', handlePointerDone);
			window.removeEventListener('pointercancel', handlePointerDone);
		};
	});

	function displayCells(): CellValue[] {
		return dragging ? previewCells : cells;
	}

	function cellClass(val: CellValue): string {
		if (val === 'IDEAL') return 'bg-ideal-bg';
		if (val === 'OK') return 'bg-ok-bg';
		return '';
	}
</script>

<div class="space-y-3">
	<p class="text-xs text-muted-foreground">
		Duration: {config.duration_minutes || 60}min &middot; Min attendees: {config.min_attendees || 1}
	</p>

	<div class="flex items-center gap-2 text-sm">
		<span class="text-muted-foreground">Brush:</span>
		<button
			class="px-3 py-1 rounded text-xs font-medium border-2 transition-colors {brush === 'IDEAL' ? 'border-ideal bg-ideal-bg' : 'border-border'}"
			onclick={() => (brush = 'IDEAL')}
		>
			Ideal
		</button>
		<button
			class="px-3 py-1 rounded text-xs font-medium border-2 transition-colors {brush === 'OK' ? 'border-ok bg-ok-bg' : 'border-border'}"
			onclick={() => (brush = 'OK')}
		>
			OK
		</button>
		<button
			class="px-3 py-1 rounded text-xs font-medium border-2 transition-colors {brush === 'UNSET' ? 'border-foreground bg-muted' : 'border-border'}"
			onclick={() => (brush = 'UNSET')}
		>
			Erase
		</button>
	</div>

	{#if cols > 0}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="select-none touch-none overflow-x-auto"
		onpointermove={onPointerMove}
		onpointerup={onPointerUp}
		onpointercancel={onPointerUp}
	>
		<div class="inline-grid gap-px bg-border" style="grid-template-columns: 50px repeat({cols}, minmax(36px, 1fr));">
			<div class="bg-background"></div>
			{#each columnHeaders as h}
				<div class="bg-background text-xs font-medium text-center py-1 px-0.5 whitespace-nowrap">{h}</div>
			{/each}

			{#each { length: rows } as _, r}
				{@const display = displayCells()}
				{@const isHour = r % (60 / slotMinutes) === 0}
				<div class="bg-background text-xs text-muted-foreground text-right pr-1 leading-none {isHour ? 'self-start -translate-y-1/2' : ''}">
					{#if isHour}
						{getSlotLabel(r, slotMinutes)}
					{/if}
				</div>
				{#each { length: cols } as _, c}
					{@const val = display[r * cols + c]}
					<!-- svelte-ignore a11y_interactive_supports_focus -->
					<div
						class="h-3 bg-background cursor-pointer hover:opacity-80 transition-colors {cellClass(val)} {isHour ? 'border-t border-border' : ''}"
						role="gridcell"
						data-row={r}
						data-col={c}
						onpointerdown={(e) => onPointerDown(e, r, c)}
					></div>
				{/each}
			{/each}
		</div>
	</div>
	{:else}
		<p class="text-sm text-muted-foreground">No date range configured.</p>
	{/if}
</div>
