import type { CellValue } from '$lib/utils/grid';
import { normalizeCellValue } from './common';
import type { DatesOnlyEditorState, PlanLike } from './types';

export function datesOnlyEmpty(plan: PlanLike): Record<string, any> {
	const anchorTz = plan.anchor_timezone || 'UTC';
	return {
		type: 'DATES_ONLY',
		anchor_timezone: anchorTz,
		dates: []
	};
}

export function datesOnlyFromAvailability(
	availability: Record<string, any> | null | undefined
): DatesOnlyEditorState {
	const dateValues: Record<string, CellValue> = {};
	if (!availability || availability.type !== 'DATES_ONLY') return { dateValues };
	const dates = Array.isArray(availability.dates) ? availability.dates : [];
	for (const item of dates) {
		if (!item || typeof item !== 'object') continue;
		const dateStr = typeof item.date === 'string' ? item.date : '';
		if (!dateStr) continue;
		const value = normalizeCellValue(item.value);
		if (value === null) continue;
		dateValues[dateStr] = value;
	}
	return { dateValues };
}

export function datesOnlyToAvailability(
	plan: PlanLike,
	state: DatesOnlyEditorState
): Record<string, any> {
	const anchorTz = plan.anchor_timezone || 'UTC';
	const dates = Object.entries(state.dateValues || {})
		.filter(([, value]) => value !== 'UNSET')
		.sort(([a], [b]) => a.localeCompare(b))
		.map(([date, value]) => ({ date, value }));

	return {
		type: 'DATES_ONLY',
		anchor_timezone: anchorTz,
		dates
	};
}
