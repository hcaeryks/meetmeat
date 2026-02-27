import type { CellValue } from '$lib/utils/grid';
import { normalizeCellValue } from './common';
import type { OptionsPollEditorState, PlanLike } from './types';

type PollOption = { option_id: string; start_utc: string; duration_minutes: number };

function planOptions(plan: PlanLike): PollOption[] {
	const options = plan.config?.options;
	return Array.isArray(options) ? (options as PollOption[]) : [];
}

export function optionsPollEmpty(plan: PlanLike): Record<string, any> {
	const options = planOptions(plan);
	return {
		type: 'OPTIONS_POLL',
		votes: options.map((option) => ({ option_id: option.option_id, value: 'UNSET' }))
	};
}

export function optionsPollFromAvailability(
	plan: PlanLike,
	availability: Record<string, any> | null | undefined
): OptionsPollEditorState {
	const votes: Record<string, CellValue> = {};
	for (const option of planOptions(plan)) {
		votes[option.option_id] = 'UNSET';
	}
	if (!availability || availability.type !== 'OPTIONS_POLL') return { votes };
	const list = Array.isArray(availability.votes) ? availability.votes : [];
	for (const vote of list) {
		if (!vote || typeof vote !== 'object') continue;
		const optionId = typeof vote.option_id === 'string' ? vote.option_id : '';
		if (!optionId) continue;
		const value = normalizeCellValue(vote.value);
		if (value === null) continue;
		votes[optionId] = value;
	}
	return { votes };
}

export function optionsPollToAvailability(
	plan: PlanLike,
	state: OptionsPollEditorState
): Record<string, any> {
	const votes = planOptions(plan).map((option) => ({
		option_id: option.option_id,
		value: state.votes[option.option_id] || 'UNSET'
	}));
	return {
		type: 'OPTIONS_POLL',
		votes
	};
}
