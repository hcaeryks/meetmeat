<script lang="ts">
	import { page } from '$app/state';
	import { onMount, onDestroy } from 'svelte';
	import {
		getPlan,
		setPlanPassword,
		createParticipant,
		setPassword,
		getPassword,
		clearPassword,
		setParticipantPassword,
		clearParticipantPassword,
		getAggregate,
		getSubmission,
		exportPlan,
		ApiError
	} from '$lib/api';
	import { initAutosave, markDirty } from '$lib/stores';
	import { getBrowserTimezone } from '$lib/utils/time';
	import SaveIndicator from '$lib/components/SaveIndicator.svelte';
	import TimezoneSelect from '$lib/components/TimezoneSelect.svelte';
	import WeeklyGrid from './components/WeeklyGrid.svelte';
	import DatesCalendar from './components/DatesCalendar.svelte';
	import DateTimeWindows from './components/DateTimeWindows.svelte';
	import OptionsPoll from './components/OptionsPoll.svelte';
	import DurationFinder from './components/DurationFinder.svelte';
	import AggregateView from './components/AggregateView.svelte';
	import { Loader2, Download, FileText, LogIn, Copy, X } from 'lucide-svelte';
	import type { ChangeMeta } from '$lib/availability';

	const planId = $derived(page.params.id || '');

	let plan = $state<Record<string, any> | null>(null);
	let loading = $state(true);
	let error = $state('');

	let participantId = $state('');
	let displayName = $state('');
	let participantTz = $state(getBrowserTimezone());
	let planPasswordInput = $state('');
	let userPasswordInput = $state('');
	let loginError = $state('');
	let loginLoading = $state(false);
	let userPasswordRequired = $state(false);

	let availability = $state<Record<string, any>>({});
	let aggregate = $state<Record<string, any> | null>(null);
	let editorHydrated = $state(false);
	let aiExportOpen = $state(false);
	let aiExportLoading = $state(false);
	let aiExportText = $state('');
	let aiExportError = $state('');
	let aiCopied = $state(false);

	let pollInterval: ReturnType<typeof setInterval> | null = null;

	const loggedIn = $derived(!!participantId);

	const needsPlanPassword = $derived(
		plan?.require_password === true && plan?.password_hash_exists === true && !getPassword(planId)
	);
	const needsPlanPasswordSetup = $derived(
		plan?.require_password === true && plan?.password_hash_exists === false
	);
	const showPlanPasswordField = $derived(needsPlanPassword || needsPlanPasswordSetup);

	function getAvailability(): Record<string, unknown> {
		return availability;
	}

	function draftKey(pid: string): string {
		return `availability-draft:${planId}:${pid}`;
	}

	function parseTime(value: string | null | undefined): number {
		if (!value) return 0;
		const ts = Date.parse(value);
		return Number.isFinite(ts) ? ts : 0;
	}

	function readDraft(pid: string): { client_updated_at_utc: string; availability: Record<string, any> } | null {
		if (!pid) return null;
		try {
			const raw = localStorage.getItem(draftKey(pid));
			if (!raw) return null;
			const parsed = JSON.parse(raw);
			if (!parsed || typeof parsed !== 'object') return null;
			if (typeof parsed.client_updated_at_utc !== 'string') return null;
			if (!parsed.availability || typeof parsed.availability !== 'object') return null;
			return {
				client_updated_at_utc: parsed.client_updated_at_utc,
				availability: parsed.availability as Record<string, any>
			};
		} catch {
			return null;
		}
	}

	function writeDraft() {
		if (!planId || !participantId) return;
		try {
			localStorage.setItem(
				draftKey(participantId),
				JSON.stringify({
					client_updated_at_utc: new Date().toISOString(),
					availability
				})
			);
		} catch {}
	}

	function clearDraft(pid: string) {
		if (!pid) return;
		try {
			localStorage.removeItem(draftKey(pid));
		} catch {}
	}

	onMount(async () => {
		const stored = localStorage.getItem(`participant:${planId}`);
		if (stored) {
			try {
				const parsed = JSON.parse(stored);
				participantId = parsed.participant_id || '';
				displayName = parsed.display_name || '';
				participantTz = parsed.timezone || getBrowserTimezone();
			} catch {}
		}
		displayName = displayName || localStorage.getItem('display_name') || '';

		await loadPlan();
	});

	onDestroy(() => {
		if (pollInterval) clearInterval(pollInterval);
	});

	async function loadPlan() {
		loading = true;
		error = '';
		if (!planId) {
			error = 'Invalid plan id';
			loading = false;
			return;
		}
		try {
			plan = await getPlan(planId);
			startPolling();
			if (participantId) {
				initAutosave(planId, participantId, getAvailability, handleAuthError, handleSaveSuccess);
				await loadMySubmission();
			} else {
				editorHydrated = false;
			}
			await fetchAggregate();
		} catch (e: any) {
			error = e.message || 'Failed to load plan';
		} finally {
			loading = false;
		}
	}

	function handleSaveSuccess(_updatedAtUtc: string) {
		if (participantId) {
			clearDraft(participantId);
		}
		void fetchAggregate();
	}

	function handleAuthError() {
		const previousParticipantId = participantId;
		participantId = '';
		availability = {};
		editorHydrated = false;
		userPasswordRequired = true;
		loginError = 'Your session expired. Please log in again.';
		localStorage.removeItem(`participant:${planId}`);
		if (previousParticipantId) {
			clearDraft(previousParticipantId);
			clearParticipantPassword(previousParticipantId);
		}
	}

	async function handleLogin() {
		if (!displayName.trim()) return;
		loginLoading = true;
		loginError = '';

		try {
			if (needsPlanPasswordSetup) {
				if (!planPasswordInput) {
					loginError = 'Plan password is required.';
					loginLoading = false;
					return;
				}
				await setPlanPassword(planId, planPasswordInput);
				setPassword(planId, planPasswordInput);
				plan = await getPlan(planId);
			} else if (needsPlanPassword) {
				if (!planPasswordInput) {
					loginError = 'Plan password is required.';
					loginLoading = false;
					return;
				}
				setPassword(planId, planPasswordInput);
			}

			const p = await createParticipant(
				planId,
				displayName.trim(),
				participantTz,
				userPasswordInput || undefined
			);
			participantId = p.participant_id;
			if (userPasswordInput) {
				setParticipantPassword(p.participant_id, userPasswordInput);
			}
			localStorage.setItem(
				`participant:${planId}`,
				JSON.stringify({
					participant_id: p.participant_id,
					display_name: p.display_name,
					timezone: p.timezone
				})
			);
			localStorage.setItem('display_name', displayName.trim());
			userPasswordInput = '';
			planPasswordInput = '';
			userPasswordRequired = false;
			initAutosave(planId, participantId, getAvailability, handleAuthError, handleSaveSuccess);
			await loadMySubmission();
			await fetchAggregate();
		} catch (e: any) {
			if (e instanceof ApiError && e.status === 401) {
				const msg = e.message.toLowerCase();
				if (msg.includes('participant')) {
					userPasswordRequired = true;
					loginError = 'This name is password-protected. Enter your password.';
				} else {
					loginError = 'Invalid plan password.';
					clearPassword(planId);
				}
			} else if (e instanceof ApiError && e.status === 409) {
				loginError = 'Password already set by another user. Reload the page.';
			} else {
				loginError = e.message || 'Failed to join';
			}
		} finally {
			loginLoading = false;
		}
	}

	function handleLogout() {
		const previousParticipantId = participantId;
		participantId = '';
		availability = {};
		editorHydrated = false;
		localStorage.removeItem(`participant:${planId}`);
		if (previousParticipantId) {
			clearDraft(previousParticipantId);
			clearParticipantPassword(previousParticipantId);
		}
	}

	async function loadMySubmission() {
		if (!participantId) return;
		editorHydrated = false;
		try {
			const sub = await getSubmission(planId, participantId);
			const serverAvailability = (sub.availability || {}) as Record<string, any>;
			const serverUpdatedAt = parseTime(sub.updated_at_utc || undefined);
			const draft = readDraft(participantId);
			const draftUpdatedAt = parseTime(draft?.client_updated_at_utc);

			if (draft && draftUpdatedAt > serverUpdatedAt) {
				availability = draft.availability;
				markDirty({ immediate: true });
			} else {
				availability = serverAvailability;
				clearDraft(participantId);
			}
		} catch (e: any) {
			if (e instanceof ApiError && e.status === 401) {
				handleAuthError();
			}
		} finally {
			editorHydrated = true;
		}
	}

	function startPolling() {
		if (pollInterval) clearInterval(pollInterval);
		pollInterval = setInterval(fetchAggregate, 5000);
	}

	async function fetchAggregate() {
		try {
			aggregate = await getAggregate(planId);
		} catch {}
	}

	function onCellChange(meta?: ChangeMeta) {
		writeDraft();
		markDirty(meta);
	}

	async function handleExport(format: 'json' | 'ai') {
		if (format === 'ai') {
			aiExportOpen = true;
			aiExportLoading = true;
			aiExportError = '';
			aiExportText = '';
			aiCopied = false;
			try {
				const data = await exportPlan(planId, 'ai');
				aiExportText = String((data as any).text || '');
			} catch (e: any) {
				aiExportError = e?.message || 'Failed to generate AI text';
			} finally {
				aiExportLoading = false;
			}
			return;
		}

		try {
			const data = await exportPlan(planId, format);
			const text = JSON.stringify(data, null, 2);
			const blob = new Blob([text], { type: 'application/json' });
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `plan-${planId}.json`;
			a.click();
			URL.revokeObjectURL(url);
		} catch {}
	}

	function closeAiExport() {
		aiExportOpen = false;
		aiCopied = false;
	}

	async function copyAiExportText() {
		if (!aiExportText) return;
		try {
			await navigator.clipboard.writeText(aiExportText);
			aiCopied = true;
			setTimeout(() => {
				aiCopied = false;
			}, 1500);
		} catch {
			aiCopied = false;
		}
	}
</script>

<svelte:head>
	<title>{plan?.title || 'Plan'} - meet me at</title>
</svelte:head>

{#if loading}
	<div class="flex items-center justify-center py-20">
		<Loader2 class="h-8 w-8 animate-spin text-muted-foreground" />
	</div>
{:else if error && !plan}
	<div class="max-w-md mx-auto px-4 py-20 text-center">
		<p class="text-destructive mb-4">{error}</p>
		<button onclick={loadPlan} class="text-sm text-primary hover:underline">Retry</button>
	</div>
{:else if plan}
	<div class="px-4 py-4">
		{#if !loggedIn}
			<div class="mb-4 p-4 rounded-lg border border-border bg-card">
				<div class="flex items-center gap-2 mb-3">
					<LogIn class="h-4 w-4 text-muted-foreground" />
					<span class="text-sm font-semibold">Join this plan to mark your availability</span>
				</div>
				{#if loginError}
					<div class="mb-3 p-2 rounded bg-destructive/10 text-destructive text-sm">{loginError}</div>
				{/if}
				<div class="flex flex-wrap gap-3 items-end">
					<div class="flex-1 min-w-[140px]">
						<label for="dn" class="block text-xs font-medium text-muted-foreground mb-1">Your Name</label>
						<input
							id="dn"
							bind:value={displayName}
							placeholder="e.g. Alice"
							onkeydown={(e) => e.key === 'Enter' && handleLogin()}
							class="w-full px-3 py-2 rounded-md border border-input bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
						/>
					</div>
					<div class="min-w-[160px]">
						<span class="block text-xs font-medium text-muted-foreground mb-1">Timezone</span>
						<TimezoneSelect bind:value={participantTz} updateStore={false} />
					</div>
					{#if showPlanPasswordField}
						<div class="min-w-[140px]">
							<label for="ppw" class="block text-xs font-medium text-muted-foreground mb-1">
								{needsPlanPasswordSetup ? 'Set Plan Password' : 'Plan Password'}
							</label>
							<input
								id="ppw"
								type="password"
								bind:value={planPasswordInput}
								placeholder={needsPlanPasswordSetup ? 'Create password' : 'Enter password'}
								onkeydown={(e) => e.key === 'Enter' && handleLogin()}
								class="w-full px-3 py-2 rounded-md border border-input bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
							/>
						</div>
					{/if}
					<div class="min-w-[140px]">
						<label for="upw" class="block text-xs font-medium text-muted-foreground mb-1">
							Your Password {userPasswordRequired ? '' : '(optional)'}
						</label>
						<input
							id="upw"
							type="password"
							bind:value={userPasswordInput}
							placeholder={userPasswordRequired ? 'Required' : 'Protect edits'}
							onkeydown={(e) => e.key === 'Enter' && handleLogin()}
							class="w-full px-3 py-2 rounded-md border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring {userPasswordRequired ? 'border-destructive' : 'border-input'}"
						/>
					</div>
					<button
						onclick={handleLogin}
						disabled={loginLoading || !displayName.trim()}
						class="px-5 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 disabled:opacity-50 inline-flex items-center gap-2 whitespace-nowrap"
					>
						{#if loginLoading}<Loader2 class="h-4 w-4 animate-spin" />{/if}
						Join
					</button>
				</div>
			</div>
		{:else}
			<div class="mb-4 flex items-center justify-between flex-wrap gap-2">
				<div class="flex items-center gap-3">
					<span class="text-sm text-muted-foreground">Logged in as <strong class="text-foreground">{displayName}</strong></span>
					<button
						onclick={handleLogout}
						class="text-xs text-muted-foreground hover:text-foreground underline"
					>
						Switch user
					</button>
				</div>
				<div class="flex items-center gap-3 flex-wrap">
					<SaveIndicator />
					<TimezoneSelect />
					<button
						onclick={() => handleExport('json')}
						class="inline-flex items-center gap-1 text-sm px-2 py-1 rounded border border-border hover:bg-accent transition-colors"
						title="Export JSON"
					>
						<Download class="h-4 w-4" /> JSON
					</button>
					<button
						onclick={() => handleExport('ai')}
						class="inline-flex items-center gap-1 text-sm px-2 py-1 rounded border border-border hover:bg-accent transition-colors"
						title="Export AI text"
					>
						<FileText class="h-4 w-4" /> AI
					</button>
				</div>
			</div>
		{/if}

		<div class="flex items-center justify-between mb-4 flex-wrap gap-2">
			<div>
				<h1 class="text-xl font-bold">{plan.title}</h1>
				<p class="text-sm text-muted-foreground">
					{plan.mode.replace(/_/g, ' ')} &middot; {plan.anchor_timezone} &middot; {plan.slot_minutes}min slots
				</p>
			</div>
		</div>

		<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 {!loggedIn ? 'opacity-40 pointer-events-none select-none' : ''}">
			<div class={loggedIn && !editorHydrated ? 'opacity-60 pointer-events-none select-none' : ''}>
				<h2 class="text-sm font-semibold mb-2 text-muted-foreground uppercase tracking-wide">Your Availability</h2>
				{#if loggedIn && !editorHydrated}
					<div class="mb-2 text-xs text-muted-foreground">Loading your saved availability…</div>
				{/if}
				{#if plan.mode === 'WEEKLY_GRID'}
					<WeeklyGrid {plan} bind:availability onchange={onCellChange} />
				{:else if plan.mode === 'DATES_ONLY'}
					<DatesCalendar {plan} bind:availability onchange={onCellChange} />
				{:else if plan.mode === 'DATE_TIME_WINDOWS'}
					<DateTimeWindows {plan} bind:availability onchange={onCellChange} />
				{:else if plan.mode === 'OPTIONS_POLL'}
					<OptionsPoll {plan} bind:availability onchange={onCellChange} />
				{:else if plan.mode === 'DURATION_FINDER'}
					<DurationFinder {plan} bind:availability onchange={onCellChange} />
				{/if}
			</div>
			<div>
				<h2 class="text-sm font-semibold mb-2 text-muted-foreground uppercase tracking-wide">Group Results</h2>
				<AggregateView {plan} {aggregate} />
			</div>
		</div>
	</div>
{/if}

{#if aiExportOpen}
	<div
		class="fixed inset-0 z-50 bg-black/50 p-4 flex items-center justify-center"
		role="button"
		tabindex="0"
		aria-label="Close AI export modal"
		onclick={(e) => {
			if (e.target === e.currentTarget) closeAiExport();
		}}
		onkeydown={(e) => {
			if ((e.key === 'Escape' || e.key === 'Enter' || e.key === ' ') && e.target === e.currentTarget) {
				e.preventDefault();
				closeAiExport();
			}
		}}
	>
		<div class="w-full max-w-3xl max-h-[85vh] rounded-lg border border-border bg-card shadow-xl flex flex-col">
			<div class="px-4 py-3 border-b border-border flex items-center justify-between">
				<h3 class="text-sm font-semibold">AI Text Export</h3>
				<button
					onclick={closeAiExport}
					class="p-1 rounded hover:bg-accent text-muted-foreground hover:text-foreground"
					title="Close"
				>
					<X class="h-4 w-4" />
				</button>
			</div>
			<div class="p-4 overflow-auto flex-1 min-h-[220px]">
				{#if aiExportLoading}
					<div class="h-full flex items-center justify-center text-muted-foreground text-sm gap-2">
						<Loader2 class="h-4 w-4 animate-spin" />
						Generating AI text...
					</div>
				{:else if aiExportError}
					<div class="text-sm text-destructive">{aiExportError}</div>
				{:else}
					<pre class="text-sm whitespace-pre-wrap break-words font-mono leading-relaxed">{aiExportText}</pre>
				{/if}
			</div>
			<div class="px-4 py-3 border-t border-border flex items-center justify-end gap-2">
				<button
					onclick={closeAiExport}
					class="px-3 py-1.5 rounded border border-border text-sm hover:bg-accent transition-colors"
				>
					Close
				</button>
				<button
					onclick={copyAiExportText}
					disabled={aiExportLoading || !aiExportText}
					class="px-3 py-1.5 rounded bg-primary text-primary-foreground text-sm inline-flex items-center gap-1 hover:opacity-90 disabled:opacity-50"
				>
					<Copy class="h-4 w-4" />
					{aiCopied ? 'Copied' : 'Copy all'}
				</button>
			</div>
		</div>
	</div>
{/if}
