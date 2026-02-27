import { addDays, differenceInDays, format, parseISO } from 'date-fns';
import type { CellValue } from '$lib/utils/grid';

export function normalizeCellValue(value: unknown, allowUnset = true): CellValue | null {
	if (value === 'IDEAL' || value === 'OK') return value;
	if (allowUnset && value === 'UNSET') return value;
	return null;
}

export function emptyCells(length: number): CellValue[] {
	return Array.from({ length }, () => 'UNSET');
}

export function parseClockToMinutes(value: unknown): number | null {
	if (typeof value !== 'string') return null;
	const parts = value.split(':');
	if (parts.length !== 2) return null;
	const hh = Number.parseInt(parts[0], 10);
	const mm = Number.parseInt(parts[1], 10);
	if (!Number.isFinite(hh) || !Number.isFinite(mm)) return null;
	if (hh < 0 || hh > 23 || mm < 0 || mm > 59) return null;
	return hh * 60 + mm;
}

export function dateRange(startDate: string, endDate: string, maxDays: number): string[] {
	try {
		const start = parseISO(startDate);
		const end = parseISO(endDate);
		const days = differenceInDays(end, start) + 1;
		return Array.from({ length: Math.min(Math.max(days, 0), maxDays) }, (_, i) =>
			format(addDays(start, i), 'yyyy-MM-dd')
		);
	} catch {
		return [];
	}
}

export function rowsFromSlotMinutes(slotMinutes: number): number {
	return Math.floor((24 * 60) / Math.max(slotMinutes, 1));
}

export function sortByDateTimeAsc<T extends [string, string, string]>(items: T[]): T[] {
	return [...items].sort((a, b) => {
		const byStart = a[0].localeCompare(b[0]);
		if (byStart !== 0) return byStart;
		return a[1].localeCompare(b[1]);
	});
}
