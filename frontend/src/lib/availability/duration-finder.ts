import { dateTimeWindowsDates } from './date-time-windows';
import { emptyCells, normalizeCellValue, rowsFromSlotMinutes, sortByDateTimeAsc } from './common';
import { zonedToUtc, utcToZoned } from '$lib/utils/time';
import type { DurationFinderEditorState, PlanLike } from './types';
import type { CellValue } from '$lib/utils/grid';
import { format } from 'date-fns';

export function durationFinderEmpty(): Record<string, any> {
	return {
		type: 'DATE_TIME_WINDOWS',
		intervals_utc: []
	};
}

export function durationFinderFromAvailability(
	plan: PlanLike,
	availability: Record<string, any> | null | undefined
): DurationFinderEditorState {
	const anchorTz = plan.anchor_timezone || 'UTC';
	const slotMinutes = plan.slot_minutes || 15;
	const rows = rowsFromSlotMinutes(slotMinutes);
	const dates = dateTimeWindowsDates(plan, 60);
	const cols = dates.length;
	const cells = emptyCells(rows * Math.max(cols, 1));
	if (!availability || availability.type !== 'DATE_TIME_WINDOWS' || cols === 0) {
		return { cells: cols > 0 ? cells : [] };
	}

	const colByDate = new Map<string, number>();
	for (let c = 0; c < cols; c++) colByDate.set(dates[c], c);

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
				cells[r * cols + col] = value;
			}
		} catch {
			continue;
		}
	}
	return { cells };
}

export function durationFinderToAvailability(
	plan: PlanLike,
	state: DurationFinderEditorState
): Record<string, any> {
	const anchorTz = plan.anchor_timezone || 'UTC';
	const slotMinutes = plan.slot_minutes || 15;
	const rows = rowsFromSlotMinutes(slotMinutes);
	const dates = dateTimeWindowsDates(plan, 60);
	const cols = dates.length;
	const cells = state.cells || [];
	const intervals: [string, string, string][] = [];

	for (let c = 0; c < cols; c++) {
		const dateStr = dates[c];
		let runStart = -1;
		let runValue: CellValue = 'UNSET';
		for (let r = 0; r <= rows; r++) {
			const val: CellValue = r < rows ? (cells[r * cols + c] || 'UNSET') : 'UNSET';
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
		type: 'DATE_TIME_WINDOWS',
		intervals_utc: sortByDateTimeAsc(intervals)
	};
}
