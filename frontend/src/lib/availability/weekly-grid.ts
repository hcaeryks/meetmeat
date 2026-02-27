import { addDays, format } from 'date-fns';
import { intervalsToWeekly, type CellValue } from '$lib/utils/grid';
import { rowsFromSlotMinutes, emptyCells, normalizeCellValue, parseClockToMinutes, sortByDateTimeAsc } from './common';
import { utcToZoned, zonedToUtc } from '$lib/utils/time';
import type { PlanLike, WeeklyGridEditorState } from './types';

const COLS = 7;

function scopeFromPlan(plan: PlanLike): 'ANY_WEEK' | 'SPECIFIC_WEEK' {
	const scope = (plan.config?.scope || 'ANY_WEEK') as string;
	return scope === 'SPECIFIC_WEEK' ? 'SPECIFIC_WEEK' : 'ANY_WEEK';
}

export function weeklyGridEmpty(plan: PlanLike): Record<string, any> {
	const scope = scopeFromPlan(plan);
	const anchorTz = plan.anchor_timezone || 'UTC';
	if (scope === 'ANY_WEEK') {
		return {
			type: 'WEEKLY_GRID',
			scope: 'ANY_WEEK',
			anchor_timezone: anchorTz,
			weekly: []
		};
	}
	return {
		type: 'WEEKLY_GRID',
		scope: 'SPECIFIC_WEEK',
		intervals_utc: []
	};
}

export function weeklyGridFromAvailability(
	plan: PlanLike,
	availability: Record<string, any> | null | undefined
): WeeklyGridEditorState {
	const anchorTz = plan.anchor_timezone || 'UTC';
	const slotMinutes = plan.slot_minutes || 15;
	const rows = rowsFromSlotMinutes(slotMinutes);
	const scope = scopeFromPlan(plan);
	const cells = emptyCells(rows * COLS);
	if (!availability || availability.type !== 'WEEKLY_GRID') {
		return { cells };
	}

	if (scope === 'ANY_WEEK') {
		const weekly = Array.isArray(availability.weekly) ? availability.weekly : [];
		for (const entry of weekly) {
			const col = Number(entry?.dow);
			const value = normalizeCellValue(entry?.value, false);
			const startMin = parseClockToMinutes(entry?.start);
			const endMin = parseClockToMinutes(entry?.end);
			if (col < 0 || col >= COLS || value === null) continue;
			if (startMin === null || endMin === null || endMin <= startMin) continue;
			const startRow = Math.max(0, Math.floor(startMin / slotMinutes));
			const endRow = Math.min(rows, Math.ceil(endMin / slotMinutes));
			for (let r = startRow; r < endRow; r++) {
				cells[r * COLS + col] = value;
			}
		}
		return { cells };
	}

	const weekStart = typeof plan.config?.week_start_local_date === 'string'
		? plan.config.week_start_local_date
		: '';
	if (!weekStart) return { cells };

	const colByDate = new Map<string, number>();
	for (let c = 0; c < COLS; c++) {
		colByDate.set(format(addDays(new Date(`${weekStart}T00:00:00`), c), 'yyyy-MM-dd'), c);
	}

	const intervals = Array.isArray(availability.intervals_utc) ? availability.intervals_utc : [];
	for (const interval of intervals) {
		if (!Array.isArray(interval) || interval.length < 3) continue;
			const value = normalizeCellValue(interval[2], false);
			if (value === null) continue;
			try {
				const startLocal = utcToZoned(String(interval[0]), anchorTz);
				const endLocal = utcToZoned(String(interval[1]), anchorTz);
			const dateKey = format(startLocal, 'yyyy-MM-dd');
			const col = colByDate.get(dateKey);
			if (col === undefined) continue;
			const startMin = startLocal.getHours() * 60 + startLocal.getMinutes();
			const endMin = endLocal.getHours() * 60 + endLocal.getMinutes();
			if (endMin <= startMin) continue;
			const startRow = Math.max(0, Math.floor(startMin / slotMinutes));
			const endRow = Math.min(rows, Math.ceil(endMin / slotMinutes));
			for (let r = startRow; r < endRow; r++) {
				cells[r * COLS + col] = value;
			}
		} catch {
			continue;
		}
	}

	return { cells };
}

export function weeklyGridToAvailability(
	plan: PlanLike,
	state: WeeklyGridEditorState
): Record<string, any> {
	const anchorTz = plan.anchor_timezone || 'UTC';
	const slotMinutes = plan.slot_minutes || 15;
	const scope = scopeFromPlan(plan);
	const cells = state.cells || [];

	if (scope === 'ANY_WEEK') {
		return {
			type: 'WEEKLY_GRID',
			scope: 'ANY_WEEK',
			anchor_timezone: anchorTz,
			weekly: intervalsToWeekly(cells, COLS, slotMinutes)
		};
	}

	const weekStart = typeof plan.config?.week_start_local_date === 'string'
		? plan.config.week_start_local_date
		: '';
	const rows = rowsFromSlotMinutes(slotMinutes);
	const intervals: [string, string, string][] = [];
	if (!weekStart) {
		return {
			type: 'WEEKLY_GRID',
			scope: 'SPECIFIC_WEEK',
			intervals_utc: []
		};
	}

	for (let c = 0; c < COLS; c++) {
		const dateStr = weekStart
			? format(addDays(new Date(`${weekStart}T00:00:00`), c), 'yyyy-MM-dd')
			: '';
		let runStart = -1;
		let runValue: CellValue = 'UNSET';
		for (let r = 0; r <= rows; r++) {
			const val: CellValue = r < rows ? (cells[r * COLS + c] || 'UNSET') : 'UNSET';
			if (val !== 'UNSET' && val === runValue) continue;
			if (runValue !== 'UNSET' && runStart >= 0) {
				const sMin = runStart * slotMinutes;
				const eMin = r * slotMinutes;
				const sH = String(Math.floor(sMin / 60)).padStart(2, '0');
				const sM = String(sMin % 60).padStart(2, '0');
				const eH = String(Math.floor(eMin / 60)).padStart(2, '0');
				const eM = String(eMin % 60).padStart(2, '0');
				intervals.push([
					zonedToUtc(new Date(`${dateStr}T${sH}:${sM}:00`), anchorTz),
					zonedToUtc(new Date(`${dateStr}T${eH}:${eM}:00`), anchorTz),
					runValue
				]);
			}
			runStart = r;
			runValue = val;
		}
	}

	return {
		type: 'WEEKLY_GRID',
		scope: 'SPECIFIC_WEEK',
		intervals_utc: sortByDateTimeAsc(intervals)
	};
}
