export type CellValue = 'IDEAL' | 'OK' | 'UNSET';

export interface DragState {
	active: boolean;
	brush: CellValue;
	anchorRow: number;
	anchorCol: number;
	lastRow: number;
	lastCol: number;
}

export function createDragState(): DragState {
	return {
		active: false,
		brush: 'IDEAL',
		anchorRow: -1,
		anchorCol: -1,
		lastRow: -1,
		lastCol: -1
	};
}

export function cellIndex(row: number, col: number, cols: number): number {
	return row * cols + col;
}

export function cellFromIndex(index: number, cols: number): { row: number; col: number } {
	return { row: Math.floor(index / cols), col: index % cols };
}

export function fillRect(
	cells: CellValue[],
	r1: number,
	c1: number,
	r2: number,
	c2: number,
	cols: number,
	value: CellValue
): CellValue[] {
	const minR = Math.min(r1, r2);
	const maxR = Math.max(r1, r2);
	const minC = Math.min(c1, c2);
	const maxC = Math.max(c1, c2);
	const out = [...cells];
	for (let r = minR; r <= maxR; r++) {
		for (let c = minC; c <= maxC; c++) {
			out[cellIndex(r, c, cols)] = value;
		}
	}
	return out;
}

export function cellsToIntervals(
	cells: CellValue[],
	cols: number,
	slotMinutes: number,
	dateStarts: string[],
	anchorTz: string
): Array<[string, string, string]> {
	const intervals: Array<[string, string, string]> = [];

	for (let col = 0; col < cols; col++) {
		const dateStr = dateStarts[col];
		if (!dateStr) continue;

		let runStart = -1;
		let runValue: CellValue = 'UNSET';

		for (let row = 0; row <= cells.length / cols; row++) {
			const idx = cellIndex(row, col, cols);
			const val = row < cells.length / cols ? cells[idx] : 'UNSET';

			if (val !== 'UNSET' && val === runValue) {
				continue;
			}

			if (runValue !== 'UNSET' && runStart >= 0) {
				const startMin = runStart * slotMinutes;
				const endMin = row * slotMinutes;
				const startH = String(Math.floor(startMin / 60)).padStart(2, '0');
				const startM = String(startMin % 60).padStart(2, '0');
				const endH = String(Math.floor(endMin / 60)).padStart(2, '0');
				const endM = String(endMin % 60).padStart(2, '0');
				intervals.push([
					`${dateStr}T${startH}:${startM}:00`,
					`${dateStr}T${endH}:${endM}:00`,
					runValue
				]);
			}

			runStart = row;
			runValue = val;
		}
	}

	return intervals;
}

export function intervalsToWeekly(
	cells: CellValue[],
	cols: number,
	slotMinutes: number
): Array<{ dow: number; start: string; end: string; value: string }> {
	const result: Array<{ dow: number; start: string; end: string; value: string }> = [];

	for (let col = 0; col < cols; col++) {
		let runStart = -1;
		let runValue: CellValue = 'UNSET';
		const rows = Math.floor(cells.length / cols);

		for (let row = 0; row <= rows; row++) {
			const idx = cellIndex(row, col, cols);
			const val = row < rows ? cells[idx] : 'UNSET';

			if (val !== 'UNSET' && val === runValue) continue;

			if (runValue !== 'UNSET' && runStart >= 0) {
				const startMin = runStart * slotMinutes;
				const endMin = row * slotMinutes;
				result.push({
					dow: col,
					start: `${String(Math.floor(startMin / 60)).padStart(2, '0')}:${String(startMin % 60).padStart(2, '0')}`,
					end: `${String(Math.floor(endMin / 60)).padStart(2, '0')}:${String(endMin % 60).padStart(2, '0')}`,
					value: runValue
				});
			}
			runStart = row;
			runValue = val;
		}
	}

	return result;
}
