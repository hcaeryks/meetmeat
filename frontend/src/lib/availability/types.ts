import type { CellValue } from '$lib/utils/grid';

export interface PlanLike {
	mode?: string;
	anchor_timezone?: string;
	slot_minutes?: number;
	config?: Record<string, any>;
}

export interface ChangeMeta {
	immediate?: boolean;
}

export type ChangeHandler = (meta?: ChangeMeta) => void;

export interface WeeklyGridEditorState {
	cells: CellValue[];
}

export interface DateTimeWindowsEditorState {
	dateCells: Record<string, CellValue[]>;
}

export interface DurationFinderEditorState {
	cells: CellValue[];
}

export interface DatesOnlyEditorState {
	dateValues: Record<string, CellValue>;
}

export interface OptionsPollEditorState {
	votes: Record<string, CellValue>;
}
