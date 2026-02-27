<script lang="ts">
	import { getSlotLabel, slotsPerDay } from '$lib/utils/time';
	import { type CellValue } from '$lib/utils/grid';
	import { dateTimeWindowsDates, dateTimeWindowsFromAvailability, dateTimeWindowsToAvailability } from '$lib/availability';
	import type { ChangeHandler } from '$lib/availability';

	interface Props {
		plan: Record<string, any>;
		availability: Record<string, any>;
		onchange: ChangeHandler;
	}

	let { plan, availability = $bindable({}), onchange }: Props = $props();

	const slotMinutes = $derived(plan.slot_minutes || 15);
	const rows = $derived(slotsPerDay(slotMinutes));
	const dates = $derived(dateTimeWindowsDates(plan, 31));

	let selectedDate = $state('');
	let dateCells = $state<Record<string, CellValue[]>>({});
	let brush = $state<CellValue>('IDEAL');
	let activeBrush = $state<CellValue>('IDEAL');
	let dragging = $state(false);
	let anchorRow = $state(-1);
	let previewCells = $state<CellValue[]>([]);
	let lastHydrationKey = '';

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
		const parsed = dateTimeWindowsFromAvailability(plan, availability);
		dateCells = parsed.dateCells;
		const initialDate = dates[0] || '';
		if (!selectedDate || !dateCells[selectedDate]) {
			selectedDate = initialDate;
		}
		previewCells = dateCells[selectedDate] ? [...dateCells[selectedDate]] : new Array(rows).fill('UNSET');
		lastHydrationKey = key;
	});

	$effect(() => {
		if (dragging) return;
		if (!selectedDate || !dateCells[selectedDate]) {
			selectedDate = dates[0] || '';
		}
		previewCells = dateCells[selectedDate] ? [...dateCells[selectedDate]] : new Array(rows).fill('UNSET');
	});

	function getCells(dateKey = selectedDate): CellValue[] {
		return dateCells[dateKey] ? [...dateCells[dateKey]] : new Array(rows).fill('UNSET');
	}

	function commitDateCells(nextDateCells: Record<string, CellValue[]>) {
		dateCells = nextDateCells;
		previewCells = nextDateCells[selectedDate] ? [...nextDateCells[selectedDate]] : new Array(rows).fill('UNSET');
		const nextAvailability = dateTimeWindowsToAvailability(plan, { dateCells: nextDateCells });
		lastHydrationKey = hydrationKey(nextAvailability);
		availability = nextAvailability;
		queueMicrotask(() => onchange({ immediate: true }));
	}

	function getRowFromPoint(x: number, y: number): number | null {
		const el = document.elementFromPoint(x, y) as HTMLElement | null;
		if (!el?.dataset.row) return null;
		return parseInt(el.dataset.row, 10);
	}

	function onPointerDown(e: PointerEvent, row: number) {
		e.preventDefault();
		dragging = true;
		anchorRow = row;
		activeBrush = brush;
		const current = getCells();
		const updated = [...current];
		updated[row] = activeBrush;
		previewCells = updated;
	}

	function onPointerMove(e: PointerEvent) {
		if (!dragging) return;
		e.preventDefault();
		const row = getRowFromPoint(e.clientX, e.clientY);
		if (row === null) return;
		const base = getCells();
		const updated = [...base];
		const minR = Math.min(anchorRow, row);
		const maxR = Math.max(anchorRow, row);
		for (let r = minR; r <= maxR; r++) updated[r] = activeBrush;
		previewCells = updated;
	}

	function onPointerUp() {
		if (!dragging) return;
		dragging = false;
		const nextDateCells = {
			...dateCells,
			[selectedDate]: [...previewCells]
		};
		commitDateCells(nextDateCells);
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
		return dragging ? previewCells : getCells();
	}

	function cellClass(val: CellValue): string {
		if (val === 'IDEAL') return 'bg-ideal-bg';
		if (val === 'OK') return 'bg-ok-bg';
		return '';
	}
</script>

<div class="space-y-3">
	<div class="flex items-center gap-2 flex-wrap">
		<span class="text-sm text-muted-foreground">Date:</span>
		<select
			bind:value={selectedDate}
			class="text-sm px-2 py-1 rounded border border-input bg-background text-foreground"
		>
			{#each dates as d}
				<option value={d}>{d}</option>
			{/each}
		</select>
		<span class="text-sm text-muted-foreground ml-2">Brush:</span>
		<button
			class="px-2 py-0.5 rounded text-xs font-medium border-2 {brush === 'IDEAL' ? 'border-ideal bg-ideal-bg' : 'border-border'}"
			onclick={() => (brush = 'IDEAL')}
		>Ideal</button>
		<button
			class="px-2 py-0.5 rounded text-xs font-medium border-2 {brush === 'OK' ? 'border-ok bg-ok-bg' : 'border-border'}"
			onclick={() => (brush = 'OK')}
		>OK</button>
		<button
			class="px-2 py-0.5 rounded text-xs font-medium border-2 {brush === 'UNSET' ? 'border-foreground bg-muted' : 'border-border'}"
			onclick={() => (brush = 'UNSET')}
		>Erase</button>
	</div>

	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="select-none touch-none"
		onpointermove={onPointerMove}
		onpointerup={onPointerUp}
		onpointercancel={onPointerUp}
	>
		<div class="inline-grid gap-px bg-border" style="grid-template-columns: 50px 60px;">
		{#each { length: rows } as _, r}
			{@const display = displayCells()}
			{@const isHour = r % (60 / slotMinutes) === 0}
			<div class="bg-background text-xs text-muted-foreground text-right pr-1 leading-none {isHour ? 'self-start -translate-y-1/2' : ''}">
				{#if isHour}
					{getSlotLabel(r, slotMinutes)}
				{/if}
			</div>
		<!-- svelte-ignore a11y_interactive_supports_focus -->
		<div
			class="h-3 bg-background cursor-pointer hover:opacity-80 {cellClass(display[r])} {isHour ? 'border-t border-border' : ''}"
			role="gridcell"
			data-row={r}
			onpointerdown={(e) => onPointerDown(e, r)}
		></div>
		{/each}
		</div>
	</div>
</div>
