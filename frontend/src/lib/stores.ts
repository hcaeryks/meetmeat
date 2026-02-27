import { writable, get } from 'svelte/store';
import { submitAvailability, ApiError } from './api';

export type SaveState = 'idle' | 'countdown' | 'saving' | 'saved' | 'error';

export interface MarkDirtyMeta {
	immediate?: boolean;
}

export const saveState = writable<SaveState>('idle');
export const saveProgress = writable(0);
export const saveError = writable('');

let _countdownTimer: ReturnType<typeof setTimeout> | null = null;
let _rafId: number | null = null;
let _countdownStart = 0;
const COUNTDOWN_MS = 1200;
const SAVED_DISPLAY_MS = 1200;

let _planId = '';
let _participantId = '';
let _getAvailability: (() => Record<string, unknown>) | null = null;
let _onAuthError: (() => void) | null = null;
let _onSaveSuccess: ((updatedAtUtc: string) => void) | null = null;

let _saveInFlight = false;
let _queuedAfterSave = false;
let _savedTimeout: ReturnType<typeof setTimeout> | null = null;

export function initAutosave(
	planId: string,
	participantId: string,
	getAvailability: () => Record<string, unknown>,
	onAuthError?: () => void,
	onSaveSuccess?: (updatedAtUtc: string) => void
) {
	_planId = planId;
	_participantId = participantId;
	_getAvailability = getAvailability;
	_onAuthError = onAuthError || null;
	_onSaveSuccess = onSaveSuccess || null;
	resetAutosaveRuntime();
}

function resetAutosaveRuntime() {
	if (_countdownTimer) {
		clearTimeout(_countdownTimer);
		_countdownTimer = null;
	}
	if (_savedTimeout) {
		clearTimeout(_savedTimeout);
		_savedTimeout = null;
	}
	if (_rafId) {
		cancelAnimationFrame(_rafId);
		_rafId = null;
	}
	_countdownStart = 0;
	_saveInFlight = false;
	_queuedAfterSave = false;
	saveProgress.set(0);
	saveError.set('');
	saveState.set('idle');
}

function animateProgress() {
	const elapsed = performance.now() - _countdownStart;
	const p = Math.min(elapsed / COUNTDOWN_MS, 1);
	saveProgress.set(p);
	if (p < 1) {
		_rafId = requestAnimationFrame(animateProgress);
	}
}

function startCountdown() {
	if (_saveInFlight) {
		_queuedAfterSave = true;
		return;
	}
	if (_countdownTimer) clearTimeout(_countdownTimer);
	if (_rafId) cancelAnimationFrame(_rafId);
	if (_savedTimeout) {
		clearTimeout(_savedTimeout);
		_savedTimeout = null;
	}

	saveState.set('countdown');
	saveProgress.set(0);
	_countdownStart = performance.now();
	_rafId = requestAnimationFrame(animateProgress);
	_countdownTimer = setTimeout(() => {
		_countdownTimer = null;
		void doSave();
	}, COUNTDOWN_MS);
}

export function markDirty(meta?: MarkDirtyMeta) {
	if (meta?.immediate) {
		if (_saveInFlight) {
			_queuedAfterSave = true;
			return;
		}
		if (_countdownTimer) {
			clearTimeout(_countdownTimer);
			_countdownTimer = null;
		}
		if (_rafId) {
			cancelAnimationFrame(_rafId);
			_rafId = null;
		}
		void doSave();
		return;
	}

	startCountdown();
}

async function doSave() {
	if (_saveInFlight) {
		_queuedAfterSave = true;
		return;
	}
	if (_rafId) {
		cancelAnimationFrame(_rafId);
		_rafId = null;
	}
	saveProgress.set(1);
	saveState.set('saving');

	if (!_getAvailability || !_planId || !_participantId) {
		saveState.set('error');
		saveError.set('Not initialized');
		return;
	}

	_saveInFlight = true;
	let saveSucceeded = false;
	try {
		const res = await submitAvailability(_planId, _participantId, _getAvailability());
		_onSaveSuccess?.(res.updated_at_utc);
		saveSucceeded = true;

		saveState.set('saved');
		if (_savedTimeout) clearTimeout(_savedTimeout);
		_savedTimeout = setTimeout(() => {
			if (get(saveState) === 'saved') saveState.set('idle');
		}, SAVED_DISPLAY_MS);
	} catch (e: any) {
		if (e instanceof ApiError && e.status === 401 && _onAuthError) {
			_onAuthError();
		}
		saveState.set('error');
		saveError.set(e.message || 'Save failed');
	} finally {
		_saveInFlight = false;
		if (_queuedAfterSave) {
			_queuedAfterSave = false;
			if (saveSucceeded) saveState.set('saving');
			void doSave();
		}
	}
}

export function retrySave() {
	void doSave();
}

export const theme = writable<'light' | 'dark' | 'system'>('system');
export const viewerTimezone = writable('UTC');
