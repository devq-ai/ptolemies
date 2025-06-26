<script lang="ts">
	import { onMount } from 'svelte';
	import {
		fetchNeo4jStats,
		calculateGraphMetrics,
		getNeo4jBrowserUrl,
		type Neo4jStats,
		type GraphMetrics
	} from '$lib/neo4j';

	// Reactive variables for Neo4j stats
	let graphStats: Neo4jStats = {
		totalNodes: 77, // Default fallback values
		totalRelationships: 156,
		frameworks: 17,
		sources: 17,
		topics: 17,
		chunks: 292, // Ready to import from SurrealDB
		nodeTypes: [],
		relationshipTypes: [],
		isOnline: false,
		lastUpdated: new Date().toISOString()
	};

	let graphMetrics: GraphMetrics = {
		density: 0,
		avgConnectionsPerNode: 0,
		maxConnections: 0,
		minConnections: 0
	};

	let isLoading = true;
	let refreshInterval: ReturnType<typeof setInterval>;

	// Load stats on component mount
	onMount(() => {
		loadStats();

		// Refresh stats every 30 seconds
		refreshInterval = setInterval(loadStats, 30000);

		return () => {
			if (refreshInterval) {
				clearInterval(refreshInterval);
			}
		};
	});

	async function loadStats() {
		try {
			graphStats = await fetchNeo4jStats();
			graphMetrics = calculateGraphMetrics(graphStats);
		} catch (error) {
			console.error('Failed to load Neo4j stats:', error);
		} finally {
			isLoading = false;
		}
	}

	async function refreshStats() {
		isLoading = true;
		await loadStats();
	}

	const browserUrl = getNeo4jBrowserUrl();

	// Reactive calculated values
	$: graphDensity = graphMetrics.density.toFixed(2);
	$: avgConnectionsPerNode = graphMetrics.avgConnectionsPerNode.toFixed(1);
	$: lastUpdatedLocal = new Date(graphStats.lastUpdated).toLocaleString();

	// Framework categories for visual breakdown
	const frameworkCategories = [
		{ category: 'AI/ML', count: 4, frameworks: ['Pydantic AI', 'PyMC', 'PyGAD', 'Wildwood'] },
		{ category: 'Web Frontend', count: 4, frameworks: ['Shadcn', 'Tailwind', 'NextJS', 'AnimeJS'] },
		{ category: 'Backend/API', count: 3, frameworks: ['FastAPI', 'FastMCP', 'Logfire'] },
		{ category: 'Data/DB', count: 2, frameworks: ['SurrealDB', 'Panel'] },
		{ category: 'Tools/Utils', count: 4, frameworks: ['Claude Code', 'Crawl4AI', 'bokeh', 'circom'] }
	];

	function openNeo4jBrowser() {
		window.open(browserUrl, '_blank');
	}

	function getStatusBadge(isOnline: boolean) {
		return isOnline ? 'badge-success' : 'badge-error';
	}

	function getStatusText(isOnline: boolean) {
		return isOnline ? '🟢 Online' : '🔴 Offline';
	}
</script>

<div class="card bg-base-300 shadow-xl mb-6" data-theme="ptolemies">
	<div class="card-body">
		<h2 class="card-title text-secondary flex items-center gap-2">
			<span class="text-2xl">🕸️</span>
			Neo4j Knowledge Graph
		</h2>

		<!-- Connection Status & Quick Access -->
		<div class="alert {graphStats.isOnline ? 'alert-info' : 'alert-warning'} mb-4">
			<div class="flex-1">
				<div class="flex items-center gap-3">
					<div class="badge {getStatusBadge(graphStats.isOnline)}">
						{getStatusText(graphStats.isOnline)}
					</div>
					<span class="text-sm">
						{graphStats.isOnline
							? 'Graph database ready for knowledge exploration'
							: 'Graph database offline - showing cached data'}
					</span>
					{#if isLoading}
						<span class="loading loading-spinner loading-sm"></span>
					{/if}
				</div>
			</div>
			<div class="flex-none flex gap-2">
				<button
					class="btn btn-sm btn-outline"
					on:click={refreshStats}
					disabled={isLoading}
				>
					{#if isLoading}
						<span class="loading loading-spinner loading-xs"></span>
					{:else}
						🔄
					{/if}
					Refresh
				</button>
				<button
					class="btn btn-sm btn-primary"
					on:click={openNeo4jBrowser}
				>
					Open Neo4j Browser
				</button>
			</div>
		</div>

		<!-- Core Graph Statistics -->
		<div class="stats stats-vertical lg:stats-horizontal shadow bg-base-200 mb-4">
			<div class="stat">
				<div class="stat-figure text-secondary">
					<svg class="w-8 h-8 fill-current" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
						<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" fill="none"/>
						<circle cx="12" cy="12" r="3" fill="currentColor"/>
						<circle cx="12" cy="6" r="2" fill="currentColor"/>
						<circle cx="18" cy="12" r="2" fill="currentColor"/>
						<circle cx="12" cy="18" r="2" fill="currentColor"/>
						<circle cx="6" cy="12" r="2" fill="currentColor"/>
					</svg>
				</div>
				<div class="stat-title text-base-content">Total Nodes</div>
				<div class="stat-value text-secondary">{graphStats.totalNodes}</div>
				<div class="stat-desc text-secondary">Graph entities</div>
			</div>

			<div class="stat">
				<div class="stat-figure text-accent">
					<svg class="w-8 h-8 fill-current" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
						<path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6-6-6z"/>
					</svg>
				</div>
				<div class="stat-title text-base-content">Relationships</div>
				<div class="stat-value text-accent">{graphStats.totalRelationships}</div>
				<div class="stat-desc text-accent">Connections</div>
			</div>

			<div class="stat">
				<div class="stat-figure text-warning">
					<svg class="w-8 h-8 fill-current" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
						<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
					</svg>
				</div>
				<div class="stat-title text-base-content">Frameworks</div>
				<div class="stat-value text-warning">{graphStats.frameworks}</div>
				<div class="stat-desc text-warning">Tech stacks</div>
			</div>

			<div class="stat">
				<div class="stat-figure text-info">
					<svg class="w-8 h-8 fill-current" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
						<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z"/>
						<polyline points="14,2 14,8 20,8"/>
						<line x1="16" y1="13" x2="8" y2="13"/>
						<line x1="16" y1="17" x2="8" y2="17"/>
						<polyline points="10,9 9,9 8,9"/>
					</svg>
				</div>
				<div class="stat-title text-base-content">Ready Chunks</div>
				<div class="stat-value text-info">{graphStats.chunks}</div>
				<div class="stat-desc text-info">From SurrealDB</div>
			</div>
		</div>

		<!-- Graph Metrics -->
		<div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
			<div class="card bg-base-200 shadow">
				<div class="card-body">
					<h3 class="card-title text-sm text-[#E3E3E3]">Graph Density</h3>
					<div class="flex items-center gap-2">
						<div class="radial-progress text-[#E3E3E3]" style="--value:{graphDensity};" role="progressbar">
							{graphDensity}%
						</div>
						<div class="text-xs opacity-70">
							Connection efficiency
						</div>
					</div>
				</div>
			</div>

			<div class="card bg-base-200 shadow">
				<div class="card-body">
					<h3 class="card-title text-sm text-accent">Avg Connections</h3>
					<div class="flex items-center gap-2">
						<div class="text-2xl font-bold text-accent">{avgConnectionsPerNode}</div>
						<div class="text-xs opacity-70">
							Per node
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Framework Categories Breakdown -->
		<div class="overflow-x-auto">
			<table class="table table-zebra w-full">
				<thead>
					<tr class="text-base-content">
						<th>Category</th>
						<th>Count</th>
						<th>Frameworks</th>
						<th>Coverage</th>
					</tr>
				</thead>
				<tbody>
					{#each frameworkCategories as { category, count, frameworks }}
						<tr class="hover:bg-base-100">
							<td class="font-medium text-[#E3E3E3]">{category}</td>
							<td>
								<div class="badge badge-secondary">{count}</div>
							</td>
							<td class="text-xs">
								<div class="flex flex-wrap gap-1">
									{#each frameworks as framework}
										<span class="badge badge-outline badge-xs">{framework}</span>
									{/each}
								</div>
							</td>
							<td>
								<progress
									class="progress progress-primary w-16"
									value={count}
									max={Math.max(...frameworkCategories.map(c => c.count))}
								></progress>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		<!-- Quick Actions & Info -->
		<div class="card-actions justify-between items-center mt-4">
			<div class="flex flex-col text-sm text-base-content opacity-70">
				<span>Database: bolt://localhost:7687</span>
				<span>Last updated: {lastUpdatedLocal}</span>
			</div>
			<div class="flex gap-2">
				<div class="badge badge-outline badge-info">
					Graph Ready
				</div>
				{#if graphStats.chunks > 0}
					<div class="badge badge-outline badge-warning">
						{graphStats.chunks} Chunks Pending
					</div>
				{/if}
			</div>
		</div>

		<!-- Connection Instructions & Database Info -->
		<div class="alert alert-warning mt-4">
			<div class="flex-1">
				<div class="text-sm">
					<strong>Neo4j Browser Access:</strong><br/>
					URL: <code class="text-xs bg-base-300 px-1 rounded">{browserUrl}</code><br/>
					Credentials: <code class="text-xs bg-base-300 px-1 rounded">neo4j:ptolemies</code>
					{#if graphStats.databaseInfo}
						<br/>
						Version: <code class="text-xs bg-base-300 px-1 rounded">{graphStats.databaseInfo.version}</code>
						({graphStats.databaseInfo.edition})
					{/if}
				</div>
			</div>
		</div>
	</div>
</div>
