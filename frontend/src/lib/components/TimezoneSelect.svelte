<script lang="ts">
	import { viewerTimezone } from '$lib/stores';
	import { ianaTimezones, getBrowserTimezone } from '$lib/utils/time';
	import { onMount } from 'svelte';

	interface Props {
		value?: string;
		onchange?: (tz: string) => void;
		updateStore?: boolean;
	}

	let { value = $bindable('UTC'), onchange, updateStore = true }: Props = $props();

	const zones = ianaTimezones();

	type Group = { region: string; items: { value: string; label: string }[] };

	const grouped: Group[] = $derived.by(() => {
		const map = new Map<string, { value: string; label: string }[]>();
		for (const tz of zones) {
			const slashIdx = tz.indexOf('/');
			if (slashIdx === -1) {
				const list = map.get('Other') || [];
				list.push({ value: tz, label: tz });
				map.set('Other', list);
			} else {
				const region = tz.substring(0, slashIdx);
				const rest = tz.substring(slashIdx + 1).replace(/_/g, ' ');
				const list = map.get(region) || [];
				list.push({ value: tz, label: rest });
				map.set(region, list);
			}
		}
		return Array.from(map.entries()).map(([region, items]) => ({ region, items }));
	});

	onMount(() => {
		if (updateStore) {
			const tz = getBrowserTimezone();
			viewerTimezone.set(tz);
			value = tz;
		}
	});

	function handleChange(e: Event) {
		const v = (e.target as HTMLSelectElement).value;
		value = v;
		if (updateStore) viewerTimezone.set(v);
		onchange?.(v);
	}
</script>

<select
	{value}
	onchange={handleChange}
	class="text-sm bg-background border border-input rounded-md px-2 py-1 text-foreground focus:outline-none focus:ring-2 focus:ring-ring max-w-[280px]"
>
	{#each grouped as group}
		<optgroup label={group.region}>
			{#each group.items as item}
				<option value={item.value}>{group.region} / {item.label}</option>
			{/each}
		</optgroup>
	{/each}
</select>
