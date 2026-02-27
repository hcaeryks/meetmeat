<script lang="ts">
	import { Calendar, Users, Clock, BarChart3, Vote } from 'lucide-svelte';
</script>

<svelte:head>
	<title>meet me at - Find the best time for everyone</title>
</svelte:head>

<div class="max-w-3xl mx-auto px-4 py-16 text-center">
	<h1 class="text-4xl font-bold mb-4">Find the best time for everyone</h1>
	<p class="text-muted-foreground text-lg mb-10">
		Create a scheduling plan, share a link, and let participants mark their availability.
	</p>

	<a
		href="/create"
		class="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-primary text-primary-foreground text-lg font-medium hover:opacity-90 transition-opacity"
	>
		<Calendar class="h-5 w-5" />
		Create a Plan
	</a>

	<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-16 text-left">
		<div class="p-4 rounded-lg border border-border">
			<Calendar class="h-6 w-6 mb-2 text-ideal" />
			<h3 class="font-semibold mb-1">Weekly Grid</h3>
			<p class="text-sm text-muted-foreground">Drag to paint availability on a 7-day, 24-hour grid with configurable time slots.</p>
		</div>
		<div class="p-4 rounded-lg border border-border">
			<BarChart3 class="h-6 w-6 mb-2 text-ideal" />
			<h3 class="font-semibold mb-1">Dates Only</h3>
			<p class="text-sm text-muted-foreground">Pick dates on a calendar and mark each as ideal or okay.</p>
		</div>
		<div class="p-4 rounded-lg border border-border">
			<Clock class="h-6 w-6 mb-2 text-ideal" />
			<h3 class="font-semibold mb-1">Date + Time Windows</h3>
			<p class="text-sm text-muted-foreground">Select specific dates then paint time slots within each day.</p>
		</div>
		<div class="p-4 rounded-lg border border-border">
			<Vote class="h-6 w-6 mb-2 text-ideal" />
			<h3 class="font-semibold mb-1">Options Poll</h3>
			<p class="text-sm text-muted-foreground">Vote Yes / Maybe / No on a list of specific datetime options.</p>
		</div>
		<div class="p-4 rounded-lg border border-border">
			<Users class="h-6 w-6 mb-2 text-ideal" />
			<h3 class="font-semibold mb-1">Duration Finder</h3>
			<p class="text-sm text-muted-foreground">Paint availability and let the system find the best overlapping time slots.</p>
		</div>
	</div>
</div>
