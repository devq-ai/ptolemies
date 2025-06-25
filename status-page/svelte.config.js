import preprocess from 'svelte-preprocess';
import adapter from '@sveltejs/adapter-static';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	// Consult https://kit.svelte.dev/docs/integrations#preprocessors
	// for more information about preprocessors
	preprocess: [
		preprocess({
			postcss: true
		})
	],

	kit: {
		// adapter-static for GitHub Pages deployment
		adapter: adapter({
			// Generate static files for GitHub Pages
			pages: 'build',
			assets: 'build',
			fallback: null,
			precompress: false,
			strict: true
		}),
		
		// Configure for GitHub Pages subdirectory deployment
		paths: {
			base: process.env.NODE_ENV === 'production' ? '/Status-Page' : '',
		},
		
		// Prerender all pages for static deployment
		prerender: {
			handleHttpError: 'warn'
		}
	}
};

export default config;
