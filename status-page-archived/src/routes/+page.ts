import { loadIncidents, loadStatusReport } from '$lib/metrics';
import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = () => {
	const reports = loadStatusReport();
	const incidents = loadIncidents();

	if (reports.length === 0) {
		throw error(404, 'No reports found');
	}

	return {
		statusLog: reports,
		incidents
	};
};
