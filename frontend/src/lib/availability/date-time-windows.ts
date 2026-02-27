import { dateRange, emptyCells, normalizeCellValue, rowsFromSlotMinutes, sortByDateTimeAsc } from './common';
import { zonedToUtc, utcToZoned } from '$lib/utils/time';
import type { DateTimeWindowsEditorState, PlanLike } from './types';
import type { CellValue } from '$lib/utils/grid';
import { format } from 'date-fns';

export function dateTimeWindowsDates(plan: PlanLike, maxDays = 31): string[] {
	const start = typeof plan.config?.date_start_local === 'string' ? plan.config.date_start_local : '';
	const end = typeof plan.config?.date_end_local === 'string' ? plan.config.date_end_local : '';
	if (!start || !end) return [];
	return dateRange(start, end, maxDays);
}

function buildInitialDateCells(dates: string[], rows: number): Record<string, CellValue[]> {
	const result: Record<string, CellValue[]> = {};
	for (const dateStr of dates) {
		result[dateStr] = emptyCells(rows);
	}
	return result;
}

export function dateTimeWindowsEmpty(): Record<string, any> {
	return {
		type: 'DATE_TIME_WINDOWS',
		intervals_utc: []
	};
}

export function dateTimeWindowsFromAvailability(
	plan: PlanLike,
	availability: Record<string, any> | null | undefined
): DateTimeWindowsEditorState {
	const anchorTz = plan.anchor_timezone || 'UTC';
	const slotMinutes = plan.slot_minutes || 15;
	const rows = rowsFromSlotMinutes(slotMinutes);
	const dates = dateTimeWindowsDates(plan, 31);
	const dateCells = buildInitialDateCells(dates, rows);
	if (!availability || availability.type !== 'DATE_TIME_WINDOWS') {
		return { dateCells };
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
			const cells = dateCells[dateKey];
			if (!cells) continue;
			const startMin = startLocal.getHours() * 60 + startLocal.getMinutes();
			const endMin = endLocal.getHours() * 60 + endLocal.getMinutes();
			if (endMin <= startMin) continue;
			const startRow = Math.max(0, Math.floor(startMin / slotMinutes));
			const endRow = Math.min(rows, Math.ceil(endMin / slotMinutes));
			for (let r = startRow; r < endRow; r++) cells[r] = value;
		} catch {
			continue;
		}
	}

	return { dateCells };
}

export function dateTimeWindowsToAvailability(
	plan: PlanLike,
	state: DateTimeWindowsEditorState
): Record<string, any> {
	const anchorTz = plan.anchor_timezone || 'UTC';
	const slotMinutes = plan.slot_minutes || 15;
	const rows = rowsFromSlotMinutes(slotMinutes);
	const intervals: [string, string, string][] = [];
	for (const [dateStr, cells] of Object.entries(state.dateCells || {})) {
		let runStart = -1;
		let runValue: CellValue = 'UNSET';
		for (let r = 0; r <= rows; r++) {
			const val: CellValue = r < rows ? (cells[r] || 'UNSET') : 'UNSET';
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
