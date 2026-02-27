import { toZonedTime, fromZonedTime } from 'date-fns-tz';
import { format } from 'date-fns';

export function utcToZoned(utcIso: string, tz: string): Date {
	return toZonedTime(new Date(utcIso), tz);
}

export function zonedToUtc(date: Date, tz: string): string {
	return fromZonedTime(date, tz).toISOString();
}

export function getSlotLabel(slotIndex: number, slotMinutes: number): string {
	const totalMinutes = slotIndex * slotMinutes;
	const h = Math.floor(totalMinutes / 60);
	const m = totalMinutes % 60;
	return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

export function slotsPerDay(slotMinutes: number): number {
	return Math.floor((24 * 60) / slotMinutes);
}

export function getBrowserTimezone(): string {
	return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

const COMMON_TIMEZONES = [
	'Pacific/Honolulu',
	'America/Anchorage',
	'America/Los_Angeles',
	'America/Denver',
	'America/Chicago',
	'America/New_York',
	'America/Sao_Paulo',
	'Atlantic/Reykjavik',
	'Europe/London',
	'Europe/Paris',
	'Europe/Berlin',
	'Europe/Moscow',
	'Africa/Cairo',
	'Asia/Dubai',
	'Asia/Kolkata',
	'Asia/Bangkok',
	'Asia/Shanghai',
	'Asia/Tokyo',
	'Asia/Seoul',
	'Australia/Sydney',
	'Pacific/Auckland'
];

export function ianaTimezones(): string[] {
	try {
		const all = (Intl as any).supportedValuesOf('timeZone') as string[];
		return all;
	} catch {
		return COMMON_TIMEZONES;
	}
}

export const DOW_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

export function dowTimeToViewerTz(
	dow: number,
	time: string,
	anchorTz: string,
	viewerTz: string
): { dow: number; time: string } {
	const baseDate = new Date(2024, 0, 7 + dow);
	const [h, m] = time.split(':').map(Number);
	baseDate.setHours(h, m, 0, 0);
	const utcDate = fromZonedTime(baseDate, anchorTz);
	const viewerDate = toZonedTime(utcDate, viewerTz);
	return {
		dow: viewerDate.getDay(),
		time: format(viewerDate, 'HH:mm')
	};
}

export function dateToWeekStart(dateStr: string): string {
	const d = new Date(dateStr + 'T00:00:00');
	const day = d.getDay();
	d.setDate(d.getDate() - day);
	return format(d, 'yyyy-MM-dd');
}
