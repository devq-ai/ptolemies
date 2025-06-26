<script lang="ts">
	import { onMount } from 'svelte';

	interface SystemHealth {
		overall_status: 'operational' | 'degraded' | 'outage';
		last_updated: string;
		system_uptime: number;
		active_incidents: number;
		services_operational: number;
		total_services: number;
		response_time_avg: number;
		error_rate: number;
	}

	interface QuickMetrics {
		knowledge_base_chunks: number;
		neo4j_nodes: number;
		ai_accuracy: number;
		graph_density: number;
	}

	let systemHealth: SystemHealth = {
		overall_status: 'operational',
		last_updated: new Date().toISOString(),
		system_uptime: 99.9,
		active_incidents: 0,
		services_operational: 8,
		total_services: 8,
		response_time_avg: 127,
		error_rate: 0.1
	};

	let quickMetrics: QuickMetrics = {
		knowledge_base_chunks: 292,
		neo4j_nodes: 77,
		ai_accuracy: 97.3,
		graph_density: 2.64
	};

	let isLoading = false;
	let refreshInterval: ReturnType<typeof setInterval>;

	// Auto-refresh every 30 seconds
	onMount(() => {
		loadSystemHealth();
		refreshInterval = setInterval(loadSystemHealth, 30000);

		return () => {
			if (refreshInterval) {
				clearInterval(refreshInterval);
			}
		};
	});

	async function loadSystemHealth() {
		try {
			// Simulate API call - in production, this would fetch from monitoring API
			await new Promise(resolve => setTimeout(resolve, 200));

			// Update timestamps
			systemHealth.last_updated = new Date().toISOString();

			// Simulate some variation in metrics
			systemHealth.response_time_avg = 120 + Math.floor(Math.random() * 20);
			systemHealth.error_rate = 0.1 + (Math.random() * 0.2);
		} catch (error) {
			console.error('Failed to load system health:', error);
		}
	}

	async function refreshStats() {
		isLoading = true;
		await loadSystemHealth();
		isLoading = false;
	}

	function getOverallStatusColor(status: string) {
		switch (status) {
			case 'operational': return 'text-success';
			case 'degraded': return 'text-warning';
			case 'outage': return 'text-error';
			default: return 'text-neutral';
		}
	}

	function getOverallStatusBadge(status: string) {
		switch (status) {
			case 'operational': return 'badge-success';
			case 'degraded': return 'badge-warning';
			case 'outage': return 'badge-error';
			default: return 'badge-neutral';
		}
	}

	function getOverallStatusIcon(status: string) {
		switch (status) {
			case 'operational': return '🟢';
			case 'degraded': return '🟡';
			case 'outage': return '🔴';
			default: return '⚪';
		}
	}

	function getOverallStatusText(status: string) {
		switch (status) {
			case 'operational': return 'All Systems Operational';
			case 'degraded': return 'Degraded Performance';
			case 'outage': return 'Service Outage';
			default: return 'Status Unknown';
		}
	}

	function formatLastUpdated(timestamp: string) {
		const date = new Date(timestamp);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffSec = Math.floor(diffMs / 1000);

		if (diffSec < 60) return `${diffSec}s ago`;
		if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
		return date.toLocaleTimeString();
	}

	// Reactive calculations
	$: serviceHealth = (systemHealth.services_operational / systemHealth.total_services) * 100;
	$: isHealthy = systemHealth.overall_status === 'operational';
	$: hasIncidents = systemHealth.active_incidents > 0;
</script>

<div class="hero text-white mb-8" data-theme="ptolemies" style="background: #000000 !important;">
	<div class="hero-content text-center w-full max-w-6xl py-8">
		<div class="w-full">
			<!-- Main Status Header -->
			<div class="mb-6">
				<div class="flex items-center justify-center gap-3 mb-2">
					<span class="text-4xl">{getOverallStatusIcon(systemHealth.overall_status)}</span>
					<h1 class="text-3xl md:text-5xl font-bold title-hacker text-white">
						{getOverallStatusText(systemHealth.overall_status)}
					</h1>
				</div>

				<div class="flex flex-wrap items-center justify-center gap-4 text-sm opacity-90">
					<div class="flex items-center gap-2">
						<span class="loading loading-ring loading-xs {isLoading ? 'opacity-100' : 'opacity-0'}"></span>
						<span>Last updated: {formatLastUpdated(systemHealth.last_updated)}</span>
					</div>
					<div class="badge badge-lg text-white">
						{systemHealth.overall_status.toUpperCase()}
					</div>
					{#if hasIncidents}
						<div class="badge badge-lg text-white">
							{systemHealth.active_incidents} Active Incident{systemHealth.active_incidents !== 1 ? 's' : ''}
						</div>
					{/if}
				</div>
			</div>

			<!-- Quick System Metrics -->
			<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
				<!-- System Uptime -->
				<div class="card bg-base-100 text-base-content shadow-lg">
					<div class="card-body p-4">
						<div class="flex items-center gap-2 mb-2">
							<span class="text-2xl">⏱️</span>
							<h3 class="font-semibold text-sm font-hacker">Uptime</h3>
						</div>
						<div class="text-2xl font-bold text-white font-hacker">
							{systemHealth.system_uptime}%
						</div>
						<div class="text-xs opacity-70 font-hacker">30-day average</div>
					</div>
				</div>

				<!-- Services Health -->
				<div class="card bg-black text-white shadow-lg">
					<div class="card-body p-4">
						<div class="flex items-center gap-2 mb-2">
							<span class="text-2xl">🔧</span>
							<h3 class="font-semibold text-sm font-hacker">Services</h3>
						</div>
						<div class="text-2xl font-bold font-hacker text-white">
							{systemHealth.services_operational}/{systemHealth.total_services}
						</div>
						<div class="text-xs opacity-70 font-hacker">Operational</div>
					</div>
				</div>

				<!-- Response Time -->
				<div class="card bg-black text-white shadow-lg">
					<div class="card-body p-4">
						<div class="flex items-center gap-2 mb-2">
							<span class="text-2xl">⚡</span>
							<h3 class="font-semibold text-sm font-hacker">Response</h3>
						</div>
						<div class="text-2xl font-bold font-hacker text-white">
							{systemHealth.response_time_avg}ms
						</div>
						<div class="text-xs opacity-70 font-hacker">Average</div>
					</div>
				</div>

				<!-- Error Rate -->
				<div class="card bg-black text-white shadow-lg">
					<div class="card-body p-4">
						<div class="flex items-center gap-2 mb-2">
							<span class="text-2xl">📊</span>
							<h3 class="font-semibold text-sm font-hacker">Error Rate</h3>
						</div>
						<div class="text-2xl font-bold font-hacker text-white">
							{systemHealth.error_rate.toFixed(1)}%
						</div>
						<div class="text-xs opacity-70 font-hacker">Last 24h</div>
					</div>
				</div>
			</div>

			<!-- Quick Access Navigation -->
			<div class="flex flex-wrap justify-center gap-4 mb-6">
				<a href="#knowledge-base" class="btn btn-outline btn-sm font-hacker text-white">
					📚 Knowledge Base ({quickMetrics.knowledge_base_chunks} chunks)
				</a>
				<a href="#neo4j-graph" class="btn btn-outline btn-sm font-hacker text-white">
					🕸️ Neo4j Graph ({quickMetrics.neo4j_nodes} nodes)
				</a>
				<a href="#ai-detection" class="btn btn-outline btn-sm font-hacker text-white">
					🛡️ AI Detection ({quickMetrics.ai_accuracy}% accuracy)
				</a>
				<a href="#services" class="btn btn-outline btn-sm font-hacker text-white">
					🔧 Service Status
				</a>
			</div>

			<!-- System Health Progress Indicators -->
			<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
				<!-- Overall Health Score -->
				<div class="card bg-black text-white shadow-lg">
					<div class="card-body">
						<h3 class="card-title text-sm flex items-center gap-2">
							<span class="text-lg">💚</span>
							System Health Score
						</h3>
						<div class="flex items-center gap-4">
							<div class="radial-progress text-white" style="--value:{serviceHealth};" role="progressbar">
								{serviceHealth.toFixed(0)}%
							</div>
							<div class="text-sm space-y-1">
								<div class="flex justify-between">
									<span>Services Online:</span>
									<span class="font-bold">{systemHealth.services_operational}/{systemHealth.total_services}</span>
								</div>
								<div class="flex justify-between">
									<span>Uptime:</span>
									<span class="font-bold text-white">{systemHealth.system_uptime}%</span>
								</div>
								<div class="flex justify-between">
									<span>Performance:</span>
									<span class="font-bold text-white">
										{systemHealth.response_time_avg < 200 ? 'Excellent' : 'Good'}
									</span>
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- Quick Metrics Summary -->
				<div class="card bg-black text-white shadow-lg">
					<div class="card-body">
						<h3 class="card-title text-sm flex items-center gap-2">
							<span class="text-lg">📈</span>
							Key Metrics
						</h3>
						<div class="space-y-3">
							<div class="flex items-center justify-between">
								<span class="text-sm">Knowledge Base</span>
								<div class="flex items-center gap-2">
									<progress class="progress w-16" value={quickMetrics.knowledge_base_chunks} max="500"></progress>
									<span class="text-xs font-bold">{quickMetrics.knowledge_base_chunks}</span>
								</div>
							</div>
							<div class="flex items-center justify-between">
								<span class="text-sm">Graph Nodes</span>
								<div class="flex items-center gap-2">
									<progress class="progress w-16" value={quickMetrics.neo4j_nodes} max="100"></progress>
									<span class="text-xs font-bold">{quickMetrics.neo4j_nodes}</span>
								</div>
							</div>
							<div class="flex items-center justify-between">
								<span class="text-sm">AI Accuracy</span>
								<div class="flex items-center gap-2">
									<progress class="progress w-16" value={quickMetrics.ai_accuracy} max="100"></progress>
									<span class="text-xs font-bold">{quickMetrics.ai_accuracy}%</span>
								</div>
							</div>
							<div class="flex items-center justify-between">
								<span class="text-sm">Graph Density</span>
								<div class="flex items-center gap-2">
									<progress class="progress w-16" value={quickMetrics.graph_density} max="10"></progress>
									<span class="text-xs font-bold">{quickMetrics.graph_density}%</span>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>

			<!-- Action Buttons -->
			<div class="flex flex-wrap justify-center gap-4 mt-8">
				<button
					class="btn btn-sm text-white"
					on:click={refreshStats}
					disabled={isLoading}
				>
					{#if isLoading}
						<span class="loading loading-spinner loading-xs"></span>
					{:else}
						🔄
					{/if}
					Refresh Status
				</button>
				<button class="btn btn-outline btn-sm text-white">
					📋 View Incidents
				</button>
				<button class="btn btn-outline btn-sm text-white">
					📊 Detailed Metrics
				</button>
				<button class="btn btn-outline btn-sm text-white">
					⚙️ System Settings
				</button>
			</div>
		</div>
	</div>
</div>

<style lang="postcss">
	.hero {
		background: #000000 !important;
		position: relative;
		overflow: hidden;
	}

	.hero::before {
		content: '';
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: radial-gradient(circle at 30% 20%, rgba(57, 255, 20, 0.1) 0%, transparent 50%),
		            radial-gradient(circle at 70% 80%, rgba(0, 255, 255, 0.1) 0%, transparent 50%);
		pointer-events: none;
	}

	.card {
		backdrop-filter: blur(10px);
		border: 1px solid rgba(255, 255, 255, 0.1);
	}

	.radial-progress {
		--size: 4rem;
		--thickness: 0.3rem;
	}

	.progress {
		height: 0.5rem;
	}

	@media (max-width: 768px) {
		.hero-content {
			padding: 1.5rem 1rem;
		}

		.text-3xl {
			font-size: 1.875rem;
		}

		.radial-progress {
			--size: 3rem;
		}
	}
</style>
