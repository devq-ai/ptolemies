<script lang="ts">
	import { onMount } from 'svelte';

	interface ServiceStatus {
		id: string;
		name: string;
		description: string;
		status: 'operational' | 'degraded' | 'partial_outage' | 'major_outage' | 'maintenance';
		uptime: number;
		response_time: number;
		last_check: string;
		url?: string;
		repository?: string;
		category: 'core' | 'database' | 'api' | 'ai' | 'monitoring';
		incidents: number;
		dependencies: string[];
	}

	const services: ServiceStatus[] = [
		{
			id: 'fastapi-main',
			name: 'FastAPI Backend',
			description: 'Main API server with Logfire observability',
			status: 'operational',
			uptime: 99.9,
			response_time: 127,
			last_check: new Date().toISOString(),
			url: 'https://api.ptolemies.devq.ai',
			repository: 'devq-ai/ptolemies',
			category: 'core',
			incidents: 0,
			dependencies: ['surrealdb', 'neo4j']
		},
		{
			id: 'surrealdb',
			name: 'SurrealDB Vector Store',
			description: 'Multi-model database for knowledge chunks',
			status: 'operational',
			uptime: 99.8,
			response_time: 45,
			last_check: new Date().toISOString(),
			url: 'ws://localhost:8000/rpc',
			repository: 'surrealdb/surrealdb',
			category: 'database',
			incidents: 0,
			dependencies: []
		},
		{
			id: 'neo4j',
			name: 'Neo4j Graph Database',
			description: 'Knowledge graph with 77 nodes, 156 relationships',
			status: 'operational',
			uptime: 99.7,
			response_time: 89,
			last_check: new Date().toISOString(),
			url: 'bolt://localhost:7687',
			repository: 'neo4j/neo4j',
			category: 'database',
			incidents: 0,
			dependencies: []
		},
		{
			id: 'dehallucinator',
			name: 'Dehallucinator AI',
			description: 'AI hallucination detection service (97.3% accuracy)',
			status: 'operational',
			uptime: 98.9,
			response_time: 203,
			last_check: new Date().toISOString(),
			repository: 'devq-ai/ptolemies',
			category: 'ai',
			incidents: 0,
			dependencies: ['fastapi-main']
		},
		{
			id: 'crawler-service',
			name: 'Documentation Crawler',
			description: 'Framework documentation ingestion pipeline',
			status: 'operational',
			uptime: 99.1,
			response_time: 345,
			last_check: new Date().toISOString(),
			repository: 'devq-ai/ptolemies',
			category: 'api',
			incidents: 0,
			dependencies: ['surrealdb']
		},
		{
			id: 'search-api',
			name: 'Search API',
			description: 'Vector search and semantic query endpoint',
			status: 'operational',
			uptime: 99.6,
			response_time: 156,
			last_check: new Date().toISOString(),
			repository: 'devq-ai/ptolemies',
			category: 'api',
			incidents: 0,
			dependencies: ['surrealdb', 'neo4j']
		},
		{
			id: 'auth-service',
			name: 'Authentication Service',
			description: 'User authentication and authorization',
			status: 'degraded',
			uptime: 97.2,
			response_time: 289,
			last_check: new Date().toISOString(),
			repository: 'devq-ai/ptolemies',
			category: 'core',
			incidents: 1,
			dependencies: []
		},
		{
			id: 'monitoring',
			name: 'Logfire Monitoring',
			description: 'Observability and performance monitoring',
			status: 'operational',
			uptime: 99.9,
			response_time: 67,
			last_check: new Date().toISOString(),
			url: 'https://logfire-us.pydantic.dev',
			repository: 'pydantic/logfire',
			category: 'monitoring',
			incidents: 0,
			dependencies: []
		}
	];

	let filteredServices = services;
	let selectedCategory: string = 'all';
	let selectedStatus: string = 'all';
	let isLoading = false;
	let refreshInterval: ReturnType<typeof setInterval>;

	// Service categories for filtering
	const categories = [
		{ id: 'all', name: 'All Services', icon: '🔧' },
		{ id: 'core', name: 'Core Services', icon: '⚡' },
		{ id: 'database', name: 'Databases', icon: '🗄️' },
		{ id: 'api', name: 'APIs', icon: '🔌' },
		{ id: 'ai', name: 'AI Services', icon: '🤖' },
		{ id: 'monitoring', name: 'Monitoring', icon: '📊' }
	];

	// Status options for filtering
	const statusOptions = [
		{ id: 'all', name: 'All Status', color: 'neutral' },
		{ id: 'operational', name: 'Operational', color: 'success' },
		{ id: 'degraded', name: 'Degraded', color: 'warning' },
		{ id: 'partial_outage', name: 'Partial Outage', color: 'error' },
		{ id: 'major_outage', name: 'Major Outage', color: 'error' },
		{ id: 'maintenance', name: 'Maintenance', color: 'info' }
	];

	onMount(() => {
		loadServiceStatus();
		refreshInterval = setInterval(loadServiceStatus, 60000);

		return () => {
			if (refreshInterval) {
				clearInterval(refreshInterval);
			}
		};
	});

	async function loadServiceStatus() {
		try {
			// Simulate API call to update service statuses
			await new Promise(resolve => setTimeout(resolve, 300));

			// Update timestamps and simulate some variation
			services.forEach(service => {
				service.last_check = new Date().toISOString();
				// Simulate minor response time variations
				service.response_time += Math.floor((Math.random() - 0.5) * 20);
				if (service.response_time < 10) service.response_time = 10;
			});

			filterServices();
		} catch (error) {
			console.error('Failed to load service status:', error);
		}
	}

	async function refreshServices() {
		isLoading = true;
		await loadServiceStatus();
		isLoading = false;
	}

	function filterServices() {
		filteredServices = services.filter(service => {
			const categoryMatch = selectedCategory === 'all' || service.category === selectedCategory;
			const statusMatch = selectedStatus === 'all' || service.status === selectedStatus;
			return categoryMatch && statusMatch;
		});
	}

	function getStatusColor(status: string) {
		switch (status) {
			case 'operational': return 'text-success';
			case 'degraded': return 'text-warning';
			case 'partial_outage': return 'text-error';
			case 'major_outage': return 'text-error';
			case 'maintenance': return 'text-info';
			default: return 'text-neutral';
		}
	}

	function getStatusBadge(status: string) {
		switch (status) {
			case 'operational': return 'badge-success';
			case 'degraded': return 'badge-warning';
			case 'partial_outage': return 'badge-error';
			case 'major_outage': return 'badge-error';
			case 'maintenance': return 'badge-info';
			default: return 'badge-neutral';
		}
	}

	function getStatusIcon(status: string) {
		switch (status) {
			case 'operational': return '🟢';
			case 'degraded': return '🟡';
			case 'partial_outage': return '🟠';
			case 'major_outage': return '🔴';
			case 'maintenance': return '🔵';
			default: return '⚪';
		}
	}

	function getCategoryIcon(category: string) {
		switch (category) {
			case 'core': return '⚡';
			case 'database': return '🗄️';
			case 'api': return '🔌';
			case 'ai': return '🤖';
			case 'monitoring': return '📊';
			default: return '🔧';
		}
	}

	function getResponseTimeColor(responseTime: number) {
		if (responseTime < 100) return 'text-success';
		if (responseTime < 300) return 'text-warning';
		return 'text-error';
	}

	function getUptimeColor(uptime: number) {
		if (uptime >= 99.5) return 'text-success';
		if (uptime >= 98.0) return 'text-warning';
		return 'text-error';
	}

	function formatLastCheck(timestamp: string) {
		const date = new Date(timestamp);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffSec = Math.floor(diffMs / 1000);

		if (diffSec < 60) return `${diffSec}s ago`;
		if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
		return date.toLocaleTimeString();
	}

	function openServiceUrl(url?: string) {
		if (url) {
			window.open(url, '_blank');
		}
	}

	function openRepository(repository?: string) {
		if (repository) {
			const url = repository.startsWith('http') ? repository : `https://github.com/${repository}`;
			window.open(url, '_blank');
		}
	}

	// Reactive filtering
	$: {
		filterServices();
	}

	// Calculate summary stats
	$: operationalServices = filteredServices.filter(s => s.status === 'operational').length;
	$: degradedServices = filteredServices.filter(s => s.status === 'degraded').length;
	$: outageServices = filteredServices.filter(s => s.status === 'partial_outage' || s.status === 'major_outage').length;
	$: maintenanceServices = filteredServices.filter(s => s.status === 'maintenance').length;
	$: avgResponseTime = filteredServices.reduce((sum, s) => sum + s.response_time, 0) / filteredServices.length;
	$: avgUptime = filteredServices.reduce((sum, s) => sum + s.uptime, 0) / filteredServices.length;
</script>

<div class="card bg-base-300 shadow-xl mb-6" data-theme="ptolemies" id="services">
	<div class="card-body">
		<div class="flex flex-col md:flex-row md:items-center md:justify-between mb-6">
			<h2 class="card-title text-info flex items-center gap-2 mb-4 md:mb-0">
				<span class="text-2xl">🔧</span>
				Service Status Grid
			</h2>

			<div class="flex flex-wrap items-center gap-4">
				<!-- Filter Controls -->
				<div class="flex items-center gap-2">
					<span class="text-sm font-medium">Category:</span>
					<select
						class="select select-bordered select-sm"
						bind:value={selectedCategory}
					>
						{#each categories as category}
							<option value={category.id}>
								{category.icon} {category.name}
							</option>
						{/each}
					</select>
				</div>

				<div class="flex items-center gap-2">
					<span class="text-sm font-medium">Status:</span>
					<select
						class="select select-bordered select-sm"
						bind:value={selectedStatus}
					>
						{#each statusOptions as status}
							<option value={status.id}>{status.name}</option>
						{/each}
					</select>
				</div>

				<button
					class="btn btn-outline btn-sm"
					on:click={refreshServices}
					disabled={isLoading}
				>
					{#if isLoading}
						<span class="loading loading-spinner loading-xs"></span>
					{:else}
						🔄
					{/if}
					Refresh
				</button>
			</div>
		</div>

		<!-- Summary Statistics -->
		<div class="stats stats-vertical lg:stats-horizontal shadow bg-base-200 mb-6">
			<div class="stat">
				<div class="stat-figure text-success">
					<span class="text-2xl">✅</span>
				</div>
				<div class="stat-title text-base-content">Operational</div>
				<div class="stat-value text-success">{operationalServices}</div>
				<div class="stat-desc text-success">Services running</div>
			</div>

			<div class="stat">
				<div class="stat-figure text-warning">
					<span class="text-2xl">⚠️</span>
				</div>
				<div class="stat-title text-base-content">Degraded</div>
				<div class="stat-value text-warning">{degradedServices}</div>
				<div class="stat-desc text-warning">Performance issues</div>
			</div>

			<div class="stat">
				<div class="stat-figure text-error">
					<span class="text-2xl">🚨</span>
				</div>
				<div class="stat-title text-base-content">Outages</div>
				<div class="stat-value text-error">{outageServices}</div>
				<div class="stat-desc text-error">Service disruptions</div>
			</div>

			<div class="stat">
				<div class="stat-figure text-info">
					<span class="text-2xl">🔧</span>
				</div>
				<div class="stat-title text-base-content">Maintenance</div>
				<div class="stat-value text-info">{maintenanceServices}</div>
				<div class="stat-desc text-info">Scheduled updates</div>
			</div>
		</div>

		<!-- Performance Summary -->
		<div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
			<div class="card bg-base-200 shadow">
				<div class="card-body">
					<h3 class="card-title text-sm text-primary">Average Response Time</h3>
					<div class="flex items-center gap-2">
						<div class="text-2xl font-bold {getResponseTimeColor(avgResponseTime)}">
							{avgResponseTime.toFixed(0)}ms
						</div>
						<div class="text-xs opacity-70">
							Across {filteredServices.length} services
						</div>
					</div>
				</div>
			</div>

			<div class="card bg-base-200 shadow">
				<div class="card-body">
					<h3 class="card-title text-sm text-secondary">Average Uptime</h3>
					<div class="flex items-center gap-2">
						<div class="text-2xl font-bold {getUptimeColor(avgUptime)}">
							{avgUptime.toFixed(1)}%
						</div>
						<div class="text-xs opacity-70">
							30-day average
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Service Grid -->
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
			{#each filteredServices as service}
				<div class="card bg-base-200 shadow hover:shadow-lg transition-shadow">
					<div class="card-body p-4">
						<!-- Service Header -->
						<div class="flex items-start justify-between mb-3">
							<div class="flex-1">
								<div class="flex items-center gap-2 mb-1">
									<span class="text-lg">{getCategoryIcon(service.category)}</span>
									<h3 class="font-bold text-sm text-primary">{service.name}</h3>
								</div>
								<p class="text-xs opacity-70 mb-2">{service.description}</p>
							</div>
							<div class="flex flex-col items-end gap-1">
								<div class="badge {getStatusBadge(service.status)} badge-sm">
									{getStatusIcon(service.status)} {service.status.replace('_', ' ').toUpperCase()}
								</div>
								{#if service.incidents > 0}
									<div class="badge badge-error badge-xs">
										{service.incidents} incident{service.incidents !== 1 ? 's' : ''}
									</div>
								{/if}
							</div>
						</div>

						<!-- Metrics -->
						<div class="space-y-2 mb-3">
							<div class="flex justify-between text-xs">
								<span>Uptime:</span>
								<span class="font-bold {getUptimeColor(service.uptime)}">{service.uptime}%</span>
							</div>
							<div class="flex justify-between text-xs">
								<span>Response:</span>
								<span class="font-bold {getResponseTimeColor(service.response_time)}">{service.response_time}ms</span>
							</div>
							<div class="flex justify-between text-xs">
								<span>Last Check:</span>
								<span class="font-bold">{formatLastCheck(service.last_check)}</span>
							</div>
						</div>

						<!-- Dependencies -->
						{#if service.dependencies.length > 0}
							<div class="mb-3">
								<div class="text-xs font-medium mb-1">Dependencies:</div>
								<div class="flex flex-wrap gap-1">
									{#each service.dependencies as dep}
										<span class="badge badge-outline badge-xs">{dep}</span>
									{/each}
								</div>
							</div>
						{/if}

						<!-- Actions -->
						<div class="flex gap-2 mt-auto">
							{#if service.url}
								<button
									class="btn btn-outline btn-xs flex-1"
									on:click={() => openServiceUrl(service.url)}
								>
									🔗 Open
								</button>
							{/if}
							{#if service.repository}
								<button
									class="btn btn-outline btn-xs flex-1"
									on:click={() => openRepository(service.repository)}
								>
									📁 Repo
								</button>
							{/if}
							<button class="btn btn-outline btn-xs">
								📊 Metrics
							</button>
						</div>
					</div>
				</div>
			{/each}
		</div>

		<!-- Empty State -->
		{#if filteredServices.length === 0}
			<div class="text-center py-8">
				<div class="text-4xl mb-4">🔍</div>
				<h3 class="text-lg font-bold mb-2">No Services Found</h3>
				<p class="text-sm opacity-70 mb-4">
					No services match the current filters. Try adjusting your selection.
				</p>
				<button
					class="btn btn-primary btn-sm"
					on:click={() => {
						selectedCategory = 'all';
						selectedStatus = 'all';
					}}
				>
					Clear Filters
				</button>
			</div>
		{/if}

		<!-- Footer Info -->
		<div class="card-actions justify-between items-center mt-6 pt-4 border-t border-base-content/10">
			<div class="text-sm text-base-content opacity-70">
				Showing {filteredServices.length} of {services.length} services
			</div>
			<div class="flex gap-2">
				<div class="badge badge-outline badge-info">
					Auto-refresh: 60s
				</div>
				<div class="badge badge-outline badge-success">
					Real-time Monitoring
				</div>
			</div>
		</div>
	</div>
</div>

<style lang="postcss">
	.card:hover {
		transform: translateY(-2px);
		transition: transform 0.2s ease;
	}

	.select {
		min-width: 120px;
	}

	.stats .stat {
		padding: 1rem;
	}

	@media (max-width: 768px) {
		.stats {
			grid-template-columns: repeat(2, 1fr);
		}

		.grid-cols-1 {
			grid-template-columns: 1fr;
		}
	}
</style>
