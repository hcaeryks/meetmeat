<script lang="ts">
	import { goto } from '$app/navigation';
	import { createPlan } from '$lib/api';
	import { getBrowserTimezone, ianaTimezones } from '$lib/utils/time';
	import {
		Calendar,
		BarChart3,
		Clock,
		Vote,
		Users,
		ChevronRight,
		ChevronLeft,
		Loader2
	} from 'lucide-svelte';

	const MODES = [
		{ id: 'WEEKLY_GRID', label: 'Weekly Grid', desc: 'Paint a 7-day time grid', icon: Calendar },
		{ id: 'DATES_ONLY', label: 'Dates Only', desc: 'Pick dates on a calendar', icon: BarChart3 },
		{
			id: 'DATE_TIME_WINDOWS',
			label: 'Date + Time',
			desc: 'Dates with time slots',
			icon: Clock
		},
		{ id: 'OPTIONS_POLL', label: 'Options Poll', desc: 'Vote on specific options', icon: Vote },
		{
			id: 'DURATION_FINDER',
			label: 'Duration Finder',
			desc: 'Find overlapping windows',
			icon: Users
		}
	] as const;

	let step = $state(1);
	let title = $state('');
	let mode = $state<string>('WEEKLY_GRID');
	let anchorTimezone = $state(getBrowserTimezone());
	let slotMinutes = $state(15);
	let requirePassword = $state(false);
	let submitting = $state(false);
	let error = $state('');

	let scope = $state<'SPECIFIC_WEEK' | 'ANY_WEEK'>('ANY_WEEK');
	let weekStartDate = $state('');
	let dateStart = $state('');
	let dateEnd = $state('');
	let durationMinutes = $state(60);
	let minAttendees = $state(2);
	let options = $state<Array<{ start: string; duration: number }>>([
		{ start: '', duration: 60 }
	]);

	const zones = ianaTimezones();

	function addOption() {
		options = [...options, { start: '', duration: 60 }];
	}

	function removeOption(idx: number) {
		options = options.filter((_, i) => i !== idx);
	}

	function buildConfig(): Record<string, unknown> {
		switch (mode) {
			case 'WEEKLY_GRID':
				return {
					scope,
					...(scope === 'SPECIFIC_WEEK' ? { week_start_local_date: weekStartDate } : {}),
					slot_minutes: slotMinutes
				};
			case 'DATES_ONLY':
				return {
					date_start_local: dateStart || null,
					date_end_local: dateEnd || null
				};
			case 'DATE_TIME_WINDOWS':
				return {
					date_start_local: dateStart,
					date_end_local: dateEnd,
					slot_minutes: slotMinutes
				};
			case 'OPTIONS_POLL':
				return {
					options: options.map((o, i) => ({
						option_id: `o${i + 1}`,
						start_utc: o.start ? new Date(o.start).toISOString() : '',
						duration_minutes: o.duration
					}))
				};
			case 'DURATION_FINDER':
				return {
					date_start_local: dateStart,
					date_end_local: dateEnd,
					slot_minutes: slotMinutes,
					duration_minutes: durationMinutes,
					min_attendees: minAttendees
				};
			default:
				return {};
		}
	}

	async function submit() {
		if (!title.trim()) {
			error = 'Please enter a title';
			return;
		}
		submitting = true;
		error = '';
		try {
			const res = await createPlan({
				title: title.trim(),
				mode,
				anchor_timezone: anchorTimezone,
				slot_minutes: slotMinutes,
				require_password: requirePassword,
				config: buildConfig()
			});
			goto(res.url_path);
		} catch (e: any) {
			error = e.message || 'Failed to create plan';
			submitting = false;
		}
	}
</script>

<svelte:head>
	<title>Create Plan - meet me at</title>
</svelte:head>

<div class="max-w-2xl mx-auto px-4 py-8">
	<h1 class="text-2xl font-bold mb-6">Create a Scheduling Plan</h1>

	{#if error}
		<div class="mb-4 p-3 rounded-md bg-destructive/10 text-destructive text-sm">{error}</div>
	{/if}

	{#if step === 1}
		<div class="space-y-6">
			<div>
				<label for="title" class="block text-sm font-medium mb-1">Plan Title</label>
				<input
					id="title"
					bind:value={title}
					placeholder="e.g. Team weekly sync"
					class="w-full px-3 py-2 rounded-md border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
				/>
			</div>

			<div>
				<p class="block text-sm font-medium mb-2">Scheduling Mode</p>
				<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
					{#each MODES as m}
						<button
							onclick={() => (mode = m.id)}
							class="text-left p-4 rounded-lg border-2 transition-colors {mode === m.id
								? 'border-primary bg-primary/5'
								: 'border-border hover:border-primary/50'}"
						>
							<div class="flex items-center gap-2 mb-1">
								<m.icon class="h-4 w-4" />
								<span class="font-medium text-sm">{m.label}</span>
							</div>
							<p class="text-xs text-muted-foreground">{m.desc}</p>
						</button>
					{/each}
				</div>
			</div>

			<div>
				<label for="tz" class="block text-sm font-medium mb-1">Anchor Timezone</label>
				<select
					id="tz"
					bind:value={anchorTimezone}
					class="w-full px-3 py-2 rounded-md border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
				>
					{#each zones as tz}
						<option value={tz}>{tz}</option>
					{/each}
				</select>
			</div>

			<button
				onclick={() => (step = 2)}
				disabled={!title.trim()}
				class="inline-flex items-center gap-1 px-4 py-2 rounded-md bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-opacity"
			>
				Next <ChevronRight class="h-4 w-4" />
			</button>
		</div>
	{:else if step === 2}
		<div class="space-y-6">
			<h2 class="text-lg font-semibold">Configure: {MODES.find((m) => m.id === mode)?.label}</h2>

			{#if mode === 'WEEKLY_GRID'}
				<div>
					<p class="block text-sm font-medium mb-2">Scope</p>
					<div class="flex gap-4">
						<label class="flex items-center gap-2 text-sm">
							<input type="radio" bind:group={scope} value="ANY_WEEK" class="accent-primary" />
							Any Week (recurring)
						</label>
						<label class="flex items-center gap-2 text-sm">
							<input
								type="radio"
								bind:group={scope}
								value="SPECIFIC_WEEK"
								class="accent-primary"
							/>
							Specific Week
						</label>
					</div>
				</div>
				{#if scope === 'SPECIFIC_WEEK'}
					<div>
						<label for="ws" class="block text-sm font-medium mb-1">Week Start Date (Sunday)</label>
						<input
							id="ws"
							type="date"
							bind:value={weekStartDate}
							class="px-3 py-2 rounded-md border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
						/>
					</div>
				{/if}
				<div>
					<label for="slot" class="block text-sm font-medium mb-1">Slot Duration (minutes)</label>
					<select
						id="slot"
						bind:value={slotMinutes}
						class="px-3 py-2 rounded-md border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
					>
						<option value={15}>15 min</option>
						<option value={30}>30 min</option>
						<option value={60}>60 min</option>
					</select>
				</div>
			{:else if mode === 'DATES_ONLY'}
				<div class="grid grid-cols-2 gap-4">
					<div>
						<label for="ds" class="block text-sm font-medium mb-1">Start Date (optional)</label>
						<input
							id="ds"
							type="date"
							bind:value={dateStart}
							class="w-full px-3 py-2 rounded-md border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
						/>
					</div>
					<div>
						<label for="de" class="block text-sm font-medium mb-1">End Date (optional)</label>
						<input
							id="de"
							type="date"
							bind:value={dateEnd}
							class="w-full px-3 py-2 rounded-md border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
						/>
					</div>
				</div>
			{:else if mode === 'DATE_TIME_WINDOWS'}
				<div class="grid grid-cols-2 gap-4">
					<div>
						<label for="ds2" class="block text-sm font-medium mb-1">Start Date</label>
						<input
							id="ds2"
							type="date"
							bind:value={dateStart}
							class="w-full px-3 py-2 rounded-md border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
						/>
					</div>
					<div>
						<label for="de2" class="block text-sm font-medium mb-1">End Date</label>
						<input
							id="de2"
							type="date"
							bind:value={dateEnd}
							class="w-full px-3 py-2 rounded-md border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
						/>
					</div>
				</div>
				<div>
					<label for="slot2" class="block text-sm font-medium mb-1">Slot Duration</label>
					<select
						id="slot2"
						bind:value={slotMinutes}
						class="px-3 py-2 rounded-md border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
					>
						<option value={15}>15 min</option>
						<option value={30}>30 min</option>
						<option value={60}>60 min</option>
					</select>
				</div>
			{:else if mode === 'OPTIONS_POLL'}
				<div class="space-y-3">
					{#each options as opt, i}
						<div class="flex items-end gap-2">
							<div class="flex-1">
								<label for={`opt-start-${i}`} class="block text-sm font-medium mb-1">Option {i + 1} - Date/Time</label>
								<input
									id={`opt-start-${i}`}
									type="datetime-local"
									bind:value={opt.start}
									class="w-full px-3 py-2 rounded-md border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
								/>
							</div>
							<div class="w-28">
								<label for={`opt-duration-${i}`} class="block text-sm font-medium mb-1">Duration (min)</label>
								<input
									id={`opt-duration-${i}`}
									type="number"
									bind:value={opt.duration}
									min="15"
									step="15"
									class="w-full px-3 py-2 rounded-md border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
								/>
							</div>
							{#if options.length > 1}
								<button
									onclick={() => removeOption(i)}
									class="px-2 py-2 text-sm text-destructive hover:text-destructive/80"
								>
									Remove
								</button>
							{/if}
						</div>
					{/each}
					<button
						onclick={addOption}
						class="text-sm text-primary hover:underline"
					>
						+ Add option
					</button>
				</div>
			{:else if mode === 'DURATION_FINDER'}
				<div class="grid grid-cols-2 gap-4">
					<div>
						<label for="ds3" class="block text-sm font-medium mb-1">Start Date</label>
						<input
							id="ds3"
							type="date"
							bind:value={dateStart}
							class="w-full px-3 py-2 rounded-md border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
						/>
					</div>
					<div>
						<label for="de3" class="block text-sm font-medium mb-1">End Date</label>
						<input
							id="de3"
							type="date"
							bind:value={dateEnd}
							class="w-full px-3 py-2 rounded-md border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
						/>
					</div>
				</div>
				<div class="grid grid-cols-3 gap-4">
					<div>
						<label for="dur" class="block text-sm font-medium mb-1">Duration (min)</label>
						<input
							id="dur"
							type="number"
							bind:value={durationMinutes}
							min="15"
							step="15"
							class="w-full px-3 py-2 rounded-md border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
						/>
					</div>
					<div>
						<label for="mina" class="block text-sm font-medium mb-1">Min Attendees</label>
						<input
							id="mina"
							type="number"
							bind:value={minAttendees}
							min="1"
							class="w-full px-3 py-2 rounded-md border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
						/>
					</div>
					<div>
						<label for="slot3" class="block text-sm font-medium mb-1">Slot (min)</label>
						<select
							id="slot3"
							bind:value={slotMinutes}
							class="w-full px-3 py-2 rounded-md border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
						>
							<option value={15}>15</option>
							<option value={30}>30</option>
							<option value={60}>60</option>
						</select>
					</div>
				</div>
			{/if}

			<div>
				<label class="flex items-center gap-2 text-sm">
					<input type="checkbox" bind:checked={requirePassword} class="accent-primary" />
					Require password to access this plan
				</label>
			</div>

			<div class="flex items-center gap-3">
				<button
					onclick={() => (step = 1)}
					class="inline-flex items-center gap-1 px-4 py-2 rounded-md border border-border hover:bg-accent transition-colors"
				>
					<ChevronLeft class="h-4 w-4" /> Back
				</button>
				<button
					onclick={submit}
					disabled={submitting}
					class="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-opacity"
				>
					{#if submitting}
						<Loader2 class="h-4 w-4 animate-spin" />
					{/if}
					Create Plan
				</button>
			</div>
		</div>
	{/if}
</div>
