import type { ReportFile, Status } from './types';
import { StatusCode } from './types';

/**
 * Load status reports from various sources
 * In production, this would fetch from monitoring APIs
 * For now, returns mock data based on the project structure
 */
export function loadStatusReport(): Array<[string, Status[]]> {
	// Generate mock status data for the last 30 days
	const generateStatusHistory = (baseUptime: number): Status[] => {
		const statuses: Status[] = [];
		const now = new Date();

		for (let i = 29; i >= 0; i--) {
			const date = new Date(now);
			date.setDate(date.getDate() - i);

			// Generate status based on base uptime with some randomness
			const random = Math.random();
			let status: StatusCode;

			if (random < baseUptime / 100) {
				status = StatusCode.OK;
			} else if (random < (baseUptime + 5) / 100) {
				status = StatusCode.UNSTABLE;
			} else {
				status = StatusCode.ERROR;
			}

			statuses.push({ status, date });
		}

		return statuses;
	};

	// Mock data for various services
	const services: Array<[string, Status[]]> = [
		['FastAPI Backend', generateStatusHistory(99.9)],
		['SurrealDB Vector Store', generateStatusHistory(99.8)],
		['Neo4j Graph Database', generateStatusHistory(99.7)],
		['Dehallucinator AI Service', generateStatusHistory(98.9)],
		['Documentation Crawler', generateStatusHistory(99.1)],
		['Search API', generateStatusHistory(99.6)],
		['Authentication Service', generateStatusHistory(97.2)],
		['Logfire Monitoring', generateStatusHistory(99.9)]
	];

	return services;
}

/**
 * Load incident reports
 * In production, this would fetch from incident management system
 */
export function loadIncidents(): ReportFile['incidents'] {
	const incidents = [
		{
			date: Math.floor(new Date('2024-01-15').getTime() / 1000),
			title: 'Authentication service degraded performance',
			open: false
		},
		{
			date: Math.floor(new Date('2024-01-10').getTime() / 1000),
			title: 'Scheduled maintenance - Neo4j database upgrade',
			open: false
		},
		{
			date: Math.floor(new Date('2024-01-05').getTime() / 1000),
			title: 'Documentation crawler timeout issues',
			open: false
		}
	];

	// Filter incidents from last 45 days
	const cutoffDate = Math.floor((Date.now() - 45 * 24 * 60 * 60 * 1000) / 1000);
	return incidents.filter((incident) => incident.date > cutoffDate);
}

/**
 * Convert status reports to ReportFile format
 * Used for compatibility with existing log system
 */
export function convertToReportFile(
	statusReports: Array<[string, Status[]]>,
	incidents: ReportFile['incidents']
): ReportFile {
	const site = statusReports.map(([name, statuses]) => ({
		name,
		status: statuses.map((status) => ({
			timestamp: Math.floor(status.date.getTime() / 1000),
			result: status.status === StatusCode.OK
		}))
	}));

	return { site, incidents };
}

/**
 * Calculate overall system health percentage
 */
export function calculateSystemHealth(statusReports: Array<[string, Status[]]>): number {
	if (statusReports.length === 0) return 0;

	const totalServices = statusReports.length;
	const operationalServices = statusReports.filter(([_, statuses]) => {
		if (statuses.length === 0) return false;
		const lastStatus = statuses[statuses.length - 1];
		return lastStatus.status === StatusCode.OK;
	}).length;

	return Math.round((operationalServices / totalServices) * 100);
}

/**
 * Get service uptime percentage for a given period
 */
export function calculateServiceUptime(statuses: Status[], days: number = 30): number {
	if (statuses.length === 0) return 0;

	const cutoffDate = new Date();
	cutoffDate.setDate(cutoffDate.getDate() - days);

	const relevantStatuses = statuses.filter((status) => status.date >= cutoffDate);
	if (relevantStatuses.length === 0) return 0;

	const operationalCount = relevantStatuses.filter(
		(status) => status.status === StatusCode.OK
	).length;
	return Math.round((operationalCount / relevantStatuses.length) * 100);
}

/**
 * Get current service status
 */
export function getCurrentServiceStatus(statuses: Status[]): {
	status: StatusCode;
	message: string;
	badge: string;
} {
	if (statuses.length === 0) {
		return {
			status: StatusCode.ERROR,
			message: 'No data available',
			badge: 'badge-error'
		};
	}

	const lastStatus = statuses[statuses.length - 1];

	switch (lastStatus.status) {
		case StatusCode.OK:
			return {
				status: StatusCode.OK,
				message: 'Operational',
				badge: 'badge-success'
			};
		case StatusCode.UNSTABLE:
			return {
				status: StatusCode.UNSTABLE,
				message: 'Degraded Performance',
				badge: 'badge-warning'
			};
		case StatusCode.ERROR:
			return {
				status: StatusCode.ERROR,
				message: 'Service Outage',
				badge: 'badge-error'
			};
		default:
			return {
				status: StatusCode.ERROR,
				message: 'Unknown Status',
				badge: 'badge-neutral'
			};
	}
}

/**
 * Mock API health check
 * In production, this would make actual HTTP requests to service endpoints
 */
export async function performHealthCheck(
	serviceName: string,
	endpoint?: string
): Promise<{
	status: StatusCode;
	responseTime: number;
	timestamp: Date;
}> {
	// Simulate API call delay
	await new Promise((resolve) => setTimeout(resolve, Math.random() * 200 + 50));

	// Mock different response times and statuses based on service
	const mockResponses: Record<string, { uptime: number; avgResponseTime: number }> = {
		'FastAPI Backend': { uptime: 99.9, avgResponseTime: 127 },
		'SurrealDB Vector Store': { uptime: 99.8, avgResponseTime: 45 },
		'Neo4j Graph Database': { uptime: 99.7, avgResponseTime: 89 },
		'Dehallucinator AI Service': { uptime: 98.9, avgResponseTime: 203 },
		'Documentation Crawler': { uptime: 99.1, avgResponseTime: 345 },
		'Search API': { uptime: 99.6, avgResponseTime: 156 },
		'Authentication Service': { uptime: 97.2, avgResponseTime: 289 },
		'Logfire Monitoring': { uptime: 99.9, avgResponseTime: 67 }
	};

	const serviceConfig = mockResponses[serviceName] || { uptime: 95.0, avgResponseTime: 200 };
	const random = Math.random() * 100;

	let status: StatusCode;
	if (random < serviceConfig.uptime) {
		status = StatusCode.OK;
	} else if (random < serviceConfig.uptime + 3) {
		status = StatusCode.UNSTABLE;
	} else {
		status = StatusCode.ERROR;
	}

	const responseTime = serviceConfig.avgResponseTime + (Math.random() - 0.5) * 50;

	return {
		status,
		responseTime: Math.max(10, Math.round(responseTime)),
		timestamp: new Date()
	};
}

/**
 * Format timestamp for display
 */
export function formatTimestamp(timestamp: number | string | Date): string {
	const date = new Date(timestamp);
	return date.toLocaleString();
}

/**
 * Calculate days between two dates
 */
export function daysBetween(date1: Date, date2: Date): number {
	const oneDay = 24 * 60 * 60 * 1000;
	return Math.round(Math.abs((date1.getTime() - date2.getTime()) / oneDay));
}
