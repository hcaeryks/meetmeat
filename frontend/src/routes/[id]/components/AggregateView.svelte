<script lang="ts">
	import { getSlotLabel, slotsPerDay, DOW_LABELS, zonedToUtc } from '$lib/utils/time';
	import { format, addDays, differenceInDays, parseISO } from 'date-fns';
	import { Users, Trophy } from 'lucide-svelte';

	interface Props {
		plan: Record<string, any>;
		aggregate: Record<string, any> | null;
	}

	let { plan, aggregate }: Props = $props();

	const mode = $derived(plan.mode);
	const config = $derived(plan.config as Record<string, any>);
	const slotMinutes = $derived(plan.slot_minutes || 15);
	const totalParticipants = $derived(aggregate?.participants_count ?? 0);

	let tooltipVisible = $state(false);
	let tooltipX = $state(0);
	let tooltipY = $state(0);
	let tooltipIdeal = $state<string[]>([]);
	let tooltipOk = $state<string[]>([]);
	let tooltipUnset = $state<string[]>([]);

	function heatColor(ideal: number, ok: number): string {
		if (ideal === 0 && ok === 0) return '';
		const total = ideal + ok;
		const max = Math.max(totalParticipants, 1);
		const intensity = total / max;
		return `opacity: ${0.3 + intensity * 0.7}`;
	}

	function heatClass(ideal: number, ok: number): string {
		if (ideal === 0 && ok === 0) return '';
		const total = ideal + ok;
		const idealRatio = ideal / Math.max(total, 1);
		return idealRatio > 0.5 ? 'bg-ideal-bg' : 'bg-ok-bg';
	}

	function weeklyGridHeaders(): string[] {
		if (config.scope === 'SPECIFIC_WEEK' && config.week_start_local_date) {
			const start = new Date(config.week_start_local_date + 'T00:00:00');
			return Array.from({ length: 7 }, (_, i) => format(addDays(start, i), 'EEE M/d'));
		}
		return DOW_LABELS;
	}

	const dateTimeDates = $derived.by(() => {
		if (mode !== 'DATE_TIME_WINDOWS') return [];
		if (!config.date_start_local || !config.date_end_local) return [];
		const start = parseISO(config.date_start_local);
		const end = parseISO(config.date_end_local);
		const days = differenceInDays(end, start) + 1;
		return Array.from({ length: Math.min(days, 31) }, (_, i) =>
			format(addDays(start, i), 'yyyy-MM-dd')
		);
	});

	const dateTimeHeaders = $derived(
		dateTimeDates.map((d) => format(parseISO(d), 'MMM d'))
	);

	const durationDates = $derived.by(() => {
		if (mode !== 'DURATION_FINDER') return [];
		if (!config.date_start_local || !config.date_end_local) return [];
		const start = parseISO(config.date_start_local);
		const end = parseISO(config.date_end_local);
		const days = differenceInDays(end, start) + 1;
		return Array.from({ length: Math.min(days, 60) }, (_, i) =>
			format(addDays(start, i), 'yyyy-MM-dd')
		);
	});

	const durationHeaders = $derived(
		durationDates.map((d) => format(parseISO(d), 'MMM d'))
	);

	function showTooltip(e: PointerEvent, participants: { IDEAL: string[]; OK: string[]; UNSET: string[] } | undefined) {
		if (!participants) {
			tooltipVisible = false;
			return;
		}
		tooltipIdeal = participants.IDEAL || [];
		tooltipOk = participants.OK || [];
		tooltipUnset = participants.UNSET || [];
		if (tooltipIdeal.length === 0 && tooltipOk.length === 0 && tooltipUnset.length === 0) {
			tooltipVisible = false;
			return;
		}
		const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
		tooltipX = rect.left + rect.width / 2;
		tooltipY = rect.top - 4;
		tooltipVisible = true;
	}

	function hideTooltip() {
		tooltipVisible = false;
	}
</script>

{#if tooltipVisible}
	<div
		class="fixed z-50 pointer-events-none px-2 py-1.5 rounded-md bg-popover border border-border shadow-lg text-xs max-w-[220px]"
		style="left: {tooltipX}px; top: {tooltipY}px; transform: translate(-50%, -100%);"
	>
		{#if tooltipIdeal.length > 0}
			<div class="text-ideal font-medium">Ideal: {tooltipIdeal.join(', ')}</div>
		{/if}
		{#if tooltipOk.length > 0}
			<div class="text-ok font-medium">OK: {tooltipOk.join(', ')}</div>
		{/if}
		{#if tooltipUnset.length > 0}
			<div class="text-muted-foreground">Unset: {tooltipUnset.join(', ')}</div>
		{/if}
	</div>
{/if}

{#if !aggregate}
	<div class="text-sm text-muted-foreground py-8 text-center">Loading results...</div>
{:else}
	<div class="space-y-4">
		<div class="flex items-center gap-2 text-sm text-muted-foreground">
			<Users class="h-4 w-4" />
			<span>{totalParticipants} participant{totalParticipants !== 1 ? 's' : ''}</span>
		</div>

		{#if mode === 'WEEKLY_GRID'}
			{@const slotCounts = (aggregate.data?.slot_counts || {}) as Record<string, { IDEAL: number; OK: number }>}
			{@const slotParticipants = (aggregate.data?.slot_participants || {}) as Record<string, { IDEAL: string[]; OK: string[]; UNSET: string[] }>}
			{@const rows = slotsPerDay(slotMinutes)}
			{@const headers = weeklyGridHeaders()}
			{@const isAnyWeek = config.scope === 'ANY_WEEK'}

			<div class="overflow-auto">
				<div class="inline-grid gap-px bg-border" style="grid-template-columns: 50px repeat(7, minmax(40px, 1fr));">
					<div class="bg-background"></div>
					{#each headers as h}
						<div class="bg-background text-xs font-medium text-center py-1">{h}</div>
					{/each}
				{#each { length: rows } as _, r}
					{@const isHour = r % (60 / slotMinutes) === 0}
					<div class="bg-background text-xs text-muted-foreground text-right pr-1 leading-none {isHour ? 'self-start -translate-y-1/2' : ''}">
						{#if isHour}
							{getSlotLabel(r, slotMinutes)}
						{/if}
					</div>
					{#each { length: 7 } as _, c}
						{@const key = isAnyWeek
							? `${c}|${getSlotLabel(r, slotMinutes)}|${getSlotLabel(r + 1, slotMinutes)}`
							: (() => {
								if (!config.week_start_local_date) return '';
								const dateStr = format(addDays(new Date(config.week_start_local_date + 'T00:00:00'), c), 'yyyy-MM-dd');
								const sMin = r * slotMinutes;
								const eMin = (r + 1) * slotMinutes;
								const sH = String(Math.floor(sMin / 60)).padStart(2, '0');
								const sMn = String(sMin % 60).padStart(2, '0');
								const eH = String(Math.floor(eMin / 60)).padStart(2, '0');
								const eMn = String(eMin % 60).padStart(2, '0');
								const startUtc = zonedToUtc(new Date(`${dateStr}T${sH}:${sMn}:00`), plan.anchor_timezone);
								const endUtc = zonedToUtc(new Date(`${dateStr}T${eH}:${eMn}:00`), plan.anchor_timezone);
								return `${startUtc}|${endUtc}`;
							})()}
						{@const counts = slotCounts[key] || { IDEAL: 0, OK: 0 }}
						{@const participants = slotParticipants[key]}
						<div
							class="h-3 bg-background {heatClass(counts.IDEAL, counts.OK)} {isHour ? 'border-t border-border' : ''}"
							style={heatColor(counts.IDEAL, counts.OK)}
							role="img"
							aria-label="{counts.IDEAL} ideal, {counts.OK} ok"
							onpointerenter={(e) => showTooltip(e, participants)}
							onpointerleave={hideTooltip}
							title="{counts.IDEAL} ideal, {counts.OK} ok"
						></div>
					{/each}
				{/each}
				</div>
			</div>

		{:else if mode === 'DATES_ONLY'}
			{@const dateCounts = (aggregate.data?.date_counts || {}) as Record<string, { IDEAL: number; OK: number }>}
			{@const dateParticipants = (aggregate.data?.date_participants || {}) as Record<string, { IDEAL: string[]; OK: string[]; UNSET: string[] }>}
			<div class="space-y-2">
				{#each Object.entries(dateCounts).sort(([a], [b]) => a.localeCompare(b)) as [date, counts]}
					{@const participants = dateParticipants[date] || { IDEAL: [], OK: [], UNSET: [] }}
					<details class="p-2 rounded border border-border">
						<summary class="cursor-pointer flex items-center justify-between text-sm">
							<span>{date}</span>
							<span class="text-xs text-muted-foreground">{counts.IDEAL} ideal / {counts.OK} ok</span>
						</summary>
						<div class="mt-2 text-xs space-y-1">
							<div><span class="text-ideal font-medium">Ideal:</span> {participants.IDEAL.join(', ') || 'None'}</div>
							<div><span class="text-ok font-medium">OK:</span> {participants.OK.join(', ') || 'None'}</div>
							<div class="text-muted-foreground"><span class="font-medium">Unset:</span> {participants.UNSET.join(', ') || 'None'}</div>
						</div>
					</details>
				{/each}
				{#if Object.keys(dateCounts).length === 0}
					<p class="text-sm text-muted-foreground">No responses yet.</p>
				{/if}
			</div>

		{:else if mode === 'OPTIONS_POLL'}
			{@const optionCounts = (aggregate.data?.option_counts || {}) as Record<string, { IDEAL: number; OK: number }>}
			{@const optionParticipants = (aggregate.data?.option_participants || {}) as Record<string, { IDEAL: string[]; OK: string[]; UNSET: string[] }>}
			{@const opts = (config.options || []) as Array<{ option_id: string; start_utc: string; duration_minutes: number }>}
			<div class="space-y-2">
				{#each opts as opt}
					{@const counts = optionCounts[opt.option_id] || { IDEAL: 0, OK: 0 }}
					{@const participants = optionParticipants[opt.option_id] || { IDEAL: [], OK: [], UNSET: [] }}
					{@const total = counts.IDEAL + counts.OK}
					{@const pct = totalParticipants > 0 ? Math.round((total / totalParticipants) * 100) : 0}
					<details class="p-2 rounded border border-border">
						<summary class="cursor-pointer">
							<div class="flex justify-between text-sm mb-1">
								<span>{(() => { try { return format(new Date(opt.start_utc), 'EEE, MMM d h:mm a'); } catch { return opt.start_utc; } })()} ({opt.duration_minutes}min)</span>
								<span class="text-muted-foreground">{total}/{totalParticipants}</span>
							</div>
							<div class="h-2 rounded-full bg-muted overflow-hidden">
								<div class="h-full rounded-full bg-ideal" style="width: {pct}%"></div>
							</div>
							<div class="flex gap-2 mt-1 text-xs text-muted-foreground">
								<span>{counts.IDEAL} yes</span>
								<span>{counts.OK} maybe</span>
							</div>
						</summary>
						<div class="mt-2 text-xs space-y-1">
							<div><span class="text-ideal font-medium">Yes:</span> {participants.IDEAL.join(', ') || 'None'}</div>
							<div><span class="text-ok font-medium">Maybe:</span> {participants.OK.join(', ') || 'None'}</div>
							<div class="text-muted-foreground"><span class="font-medium">No/Unset:</span> {participants.UNSET.join(', ') || 'None'}</div>
						</div>
					</details>
				{/each}
			</div>

		{:else if mode === 'DATE_TIME_WINDOWS'}
			{@const slotCounts = (aggregate.data?.slot_counts || {}) as Record<string, { IDEAL: number; OK: number }>}
			{@const slotParticipants = (aggregate.data?.slot_participants || {}) as Record<string, { IDEAL: string[]; OK: string[]; UNSET: string[] }>}
			{@const rows = slotsPerDay(slotMinutes)}
			{@const cols = dateTimeDates.length}

			{#if cols > 0}
			<div class="overflow-x-auto">
				<div class="inline-grid gap-px bg-border" style="grid-template-columns: 50px repeat({cols}, minmax(36px, 1fr));">
					<div class="bg-background"></div>
					{#each dateTimeHeaders as h}
						<div class="bg-background text-xs font-medium text-center py-1 px-0.5 whitespace-nowrap">{h}</div>
					{/each}

					{#each { length: rows } as _, r}
						{@const isHour = r % (60 / slotMinutes) === 0}
						<div class="bg-background text-xs text-muted-foreground text-right pr-1 leading-none {isHour ? 'self-start -translate-y-1/2' : ''}">
							{#if isHour}
								{getSlotLabel(r, slotMinutes)}
							{/if}
						</div>
						{#each { length: cols } as _, c}
							{@const dateStr = dateTimeDates[c]}
							{@const sMin = r * slotMinutes}
							{@const eMin = (r + 1) * slotMinutes}
							{@const sH = String(Math.floor(sMin / 60)).padStart(2, '0')}
							{@const sMn = String(sMin % 60).padStart(2, '0')}
							{@const eH = String(Math.floor(eMin / 60)).padStart(2, '0')}
							{@const eMn = String(eMin % 60).padStart(2, '0')}
							{@const startUtc = zonedToUtc(new Date(`${dateStr}T${sH}:${sMn}:00`), plan.anchor_timezone)}
							{@const endUtc = zonedToUtc(new Date(`${dateStr}T${eH}:${eMn}:00`), plan.anchor_timezone)}
							{@const key = `${startUtc}|${endUtc}`}
							{@const counts = slotCounts[key] || { IDEAL: 0, OK: 0 }}
							{@const participants = slotParticipants[key]}
							<div
								class="h-3 bg-background {heatClass(counts.IDEAL, counts.OK)} {isHour ? 'border-t border-border' : ''}"
								style={heatColor(counts.IDEAL, counts.OK)}
								role="img"
								aria-label="{counts.IDEAL} ideal, {counts.OK} ok"
								onpointerenter={(e) => showTooltip(e, participants)}
								onpointerleave={hideTooltip}
							></div>
						{/each}
					{/each}
				</div>
			</div>
			{:else}
				<p class="text-sm text-muted-foreground">No date range configured.</p>
			{/if}

		{:else if mode === 'DURATION_FINDER'}
			{@const slotCounts = (aggregate.data?.slot_counts || {}) as Record<string, { IDEAL: number; OK: number }>}
			{@const slotParticipants = (aggregate.data?.slot_participants || {}) as Record<string, { IDEAL: string[]; OK: string[]; UNSET: string[] }>}
			{@const topSlots = (aggregate.data?.top_slots || []) as Array<{ start_utc: string; end_utc: string; total: number; ideal: number }>}
			{@const rows = slotsPerDay(slotMinutes)}
			{@const cols = durationDates.length}

			{#if cols > 0}
			<div class="overflow-x-auto">
				<div class="inline-grid gap-px bg-border" style="grid-template-columns: 50px repeat({cols}, minmax(36px, 1fr));">
					<div class="bg-background"></div>
					{#each durationHeaders as h}
						<div class="bg-background text-xs font-medium text-center py-1 px-0.5 whitespace-nowrap">{h}</div>
					{/each}

					{#each { length: rows } as _, r}
						{@const isHour = r % (60 / slotMinutes) === 0}
						<div class="bg-background text-xs text-muted-foreground text-right pr-1 leading-none {isHour ? 'self-start -translate-y-1/2' : ''}">
							{#if isHour}
								{getSlotLabel(r, slotMinutes)}
							{/if}
						</div>
						{#each { length: cols } as _, c}
							{@const dateStr = durationDates[c]}
							{@const sMin = r * slotMinutes}
							{@const hh = String(Math.floor(sMin / 60)).padStart(2, '0')}
							{@const mm = String(sMin % 60).padStart(2, '0')}
							{@const utcIso = zonedToUtc(new Date(`${dateStr}T${hh}:${mm}:00`), plan.anchor_timezone)}
							{@const key = new Date(utcIso).toISOString().replace(/\.\d{3}Z$/, '+00:00')}
							{@const counts = slotCounts[key] || { IDEAL: 0, OK: 0 }}
							{@const participants = slotParticipants[key]}
							<div
								class="h-3 bg-background {heatClass(counts.IDEAL, counts.OK)} {isHour ? 'border-t border-border' : ''}"
								style={heatColor(counts.IDEAL, counts.OK)}
								role="img"
								aria-label="{counts.IDEAL} ideal, {counts.OK} ok"
								onpointerenter={(e) => showTooltip(e, participants)}
								onpointerleave={hideTooltip}
							></div>
						{/each}
					{/each}
				</div>
			</div>
			{:else}
				<p class="text-sm text-muted-foreground">No date range configured.</p>
			{/if}

			{#if topSlots.length > 0}
				<div>
					<h3 class="text-sm font-semibold flex items-center gap-1 mb-2">
						<Trophy class="h-4 w-4 text-ideal" /> Top Slots
					</h3>
					<div class="space-y-2">
						{#each topSlots as slot, i}
							<div class="p-2 rounded border border-border text-sm flex items-center gap-2">
								<span class="font-mono text-xs text-muted-foreground w-5">#{i + 1}</span>
								<div class="flex-1">
									<span>{(() => { try { return format(new Date(slot.start_utc), 'MMM d HH:mm'); } catch { return slot.start_utc; } })()}</span>
									<span class="text-muted-foreground"> &rarr; </span>
									<span>{(() => { try { return format(new Date(slot.end_utc), 'HH:mm'); } catch { return slot.end_utc; } })()}</span>
								</div>
								<span class="text-xs">
									<span class="text-ideal">{slot.ideal} ideal</span>,
									{slot.total} total
								</span>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		{/if}

		<div class="flex items-center gap-3 text-xs text-muted-foreground pt-2 border-t border-border">
			<span class="flex items-center gap-1"><span class="w-3 h-3 rounded bg-ideal-bg"></span> Ideal</span>
			<span class="flex items-center gap-1"><span class="w-3 h-3 rounded bg-ok-bg"></span> OK</span>
		</div>
	</div>
{/if}
