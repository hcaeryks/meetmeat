const API_BASE = '/api';

let _passwords: Record<string, string> = {};
let _participantPasswords: Record<string, string> = {};

function _loadFromSession() {
	try {
		const pw = sessionStorage.getItem('_planPasswords');
		if (pw) _passwords = JSON.parse(pw);
		const ppw = sessionStorage.getItem('_participantPasswords');
		if (ppw) _participantPasswords = JSON.parse(ppw);
	} catch {}
}

function _saveToSession() {
	try {
		sessionStorage.setItem('_planPasswords', JSON.stringify(_passwords));
		sessionStorage.setItem('_participantPasswords', JSON.stringify(_participantPasswords));
	} catch {}
}

if (typeof window !== 'undefined') {
	_loadFromSession();
}

export function setPassword(planId: string, password: string) {
	_passwords[planId] = password;
	_saveToSession();
}

export function getPassword(planId: string): string | undefined {
	return _passwords[planId];
}

export function clearPassword(planId: string) {
	delete _passwords[planId];
	_saveToSession();
}

export function setParticipantPassword(participantId: string, password: string) {
	_participantPasswords[participantId] = password;
	_saveToSession();
}

export function getParticipantPassword(participantId: string): string | undefined {
	return _participantPasswords[participantId];
}

export function clearParticipantPassword(participantId: string) {
	delete _participantPasswords[participantId];
	_saveToSession();
}

async function apiFetch<T>(path: string, options: RequestInit = {}, planId?: string, participantId?: string): Promise<T> {
	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
		...(options.headers as Record<string, string> || {})
	};
	if (planId && _passwords[planId]) {
		headers['X-Plan-Password'] = _passwords[planId];
	}
	if (participantId && _participantPasswords[participantId]) {
		headers['X-Participant-Password'] = _participantPasswords[participantId];
	}
	const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
	if (!res.ok) {
		const body = await res.json().catch(() => ({ detail: res.statusText }));
		throw new ApiError(res.status, body.detail || res.statusText);
	}
	return res.json();
}

export class ApiError extends Error {
	constructor(public status: number, message: string) {
		super(message);
	}
}

export async function createPlan(data: {
	title: string;
	mode: string;
	anchor_timezone: string;
	slot_minutes: number;
	require_password: boolean;
	config: Record<string, unknown>;
}) {
	return apiFetch<{ plan_id: string; url_path: string }>('/plans', {
		method: 'POST',
		body: JSON.stringify(data)
	});
}

export async function getPlan(planId: string) {
	return apiFetch<{
		plan_id: string;
		title: string;
		mode: string;
		created_at_utc: string;
		anchor_timezone: string;
		slot_minutes: number;
		require_password: boolean;
		password_hash_exists: boolean;
		config: Record<string, unknown>;
		participants_count: number;
	}>(`/plans/${planId}`, {}, planId);
}

export async function setPlanPassword(planId: string, password: string) {
	return apiFetch<{ ok: boolean }>(`/plans/${planId}/password`, {
		method: 'POST',
		body: JSON.stringify({ password })
	});
}

export async function createParticipant(
	planId: string,
	displayName: string,
	timezone: string,
	password?: string
) {
	const body: Record<string, string> = { display_name: displayName, timezone };
	if (password) body.password = password;
	return apiFetch<{ participant_id: string; display_name: string; timezone: string; has_password: boolean }>(
		`/plans/${planId}/participants`,
		{ method: 'POST', body: JSON.stringify(body) },
		planId
	);
}

export async function submitAvailability(
	planId: string,
	participantId: string,
	availability: Record<string, unknown>
) {
	return apiFetch<{ ok: boolean; updated_at_utc: string }>(
		`/plans/${planId}/submissions/${participantId}`,
		{ method: 'PUT', body: JSON.stringify({ availability }) },
		planId,
		participantId
	);
}

export async function getSubmission(planId: string, participantId: string) {
	return apiFetch<{
		participant_id: string;
		updated_at_utc: string | null;
		availability: Record<string, unknown>;
	}>(
		`/plans/${planId}/submissions/${participantId}`,
		{},
		planId,
		participantId
	);
}

export async function getAggregate(planId: string) {
	return apiFetch<{
		mode: string;
		participants_count: number;
		data: Record<string, unknown>;
	}>(`/plans/${planId}/aggregate`, { cache: 'no-store' }, planId);
}

export async function exportPlan(planId: string, format: 'json' | 'ai' = 'json') {
	return apiFetch<Record<string, unknown>>(
		`/plans/${planId}/export?format=${format}`,
		{},
		planId
	);
}
