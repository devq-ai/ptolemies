<script lang="ts">
	import Incidents from '$lib/components/Incidents.svelte';
	import Status from '$lib/components/Status.svelte';
	import System from '$lib/components/System.svelte';
	import PtolemiesStats from '$lib/components/PtolemiesStats.svelte';
	import Neo4jStats from '$lib/components/Neo4jStats.svelte';
	import DehallucinatorStats from '$lib/components/DehallucinatorStats.svelte';
	import ExecutiveDashboard from '$lib/components/ExecutiveDashboard.svelte';
	import ServiceStatusGrid from '$lib/components/ServiceStatusGrid.svelte';

	import type { PageData } from './$types';

	export let data: PageData;
</script>

<!-- Executive Dashboard - Overall System Health -->
<ExecutiveDashboard />

<main class="text-center mx-4 md:mx-12 py-4">
	<div class="max-w-6xl mx-auto">
		<!-- Service Status Grid - Individual Service Monitoring -->
		<ServiceStatusGrid />

		<!-- Ptolemies Knowledge Base Statistics -->
		<section id="knowledge-base">
			<PtolemiesStats />
		</section>

		<!-- Neo4j Knowledge Graph Statistics -->
		<section id="neo4j-graph">
			<Neo4jStats />
		</section>

		<!-- Dehallucinator AI Detection Service -->
		<section id="ai-detection">
			<DehallucinatorStats />
		</section>

		<!-- Legacy Status Monitoring -->
		<div class="max-w-3xl mx-auto mt-8">
			<div class="card shadow-xl" style="background: #000000 !important;">
				<div class="card-body" style="background: #000000 !important;">
					<h2 class="card-title flex items-center gap-2 mb-4" style="color: #ffffff !important;">
						<span class="text-2xl">📊</span>
						Legacy Status Reports
					</h2>
					<div class="w-full header min-h-[10vh] flex items-end justify-center rounded-lg mb-4" style="background: #000000 !important; background-color: #000000 !important;">
						<div class="h-full w-full mx-2">
							<System systems={data.statusLog} />
						</div>
					</div>
					{#each data.statusLog as [name, siteStatus]}
						<Status {name} statuses={siteStatus} />
					{/each}
					{#if data.incidents?.length > 0}
						<div class="divider" />
						<Incidents incidents={data.incidents} />
					{/if}
				</div>
			</div>
		</div>
	</div>
</main>

<style lang="postcss">
	.header {
		height: 100%;
		background: #000000 !important;
	}
</style>
