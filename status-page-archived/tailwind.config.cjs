/** @type {import('tailwindcss').Config} */
module.exports = {
	content: ['./src/**/*.{js,svelte,ts}', './index.html'],
	theme: {
		extend: {
			colors: {
				// Monochrome theme - black and white only
				primary: '#000000', // Pure Black
				secondary: '#000000', // Pure Black
				accent: '#000000', // Pure Black
				destructive: '#000000', // Pure Black
				success: '#000000', // Pure Black
				warning: '#000000', // Pure Black
				info: '#000000', // Pure Black

				// Background colors
				'bg-primary': '#000000', // Pure Black
				'bg-secondary': '#000000', // Pure Black
				'bg-surface': '#000000', // Pure Black

				// Foreground colors
				'fg-primary': '#ffffff', // Pure White
				'fg-secondary': '#ffffff', // Pure White
				'fg-disabled': '#ffffff' // Pure White
			},
			fontFamily: {
				mono: ['JetBrains Mono', 'Consolas', 'Monaco', 'monospace'],
				hacker: ['Hacker', 'JetBrains Mono', 'Consolas', 'Monaco', 'monospace'],
				sans: [
					'Hacker',
					'system-ui',
					'-apple-system',
					'BlinkMacSystemFont',
					'Segoe UI',
					'Roboto',
					'Helvetica Neue',
					'Arial',
					'sans-serif'
				]
			}
		}
	},
	/* eslint @typescript-eslint/no-require-imports: "off" */
	plugins: [require('daisyui')],
	daisyui: {
		logs: false,
		themes: [
			{
				ptolemies: {
					// Monochrome DaisyUI theme
					primary: '#000000', // Pure Black
					secondary: '#000000', // Pure Black
					accent: '#000000', // Pure Black
					neutral: '#000000', // Pure Black
					'base-100': '#000000', // Pure Black
					'base-200': '#000000', // Pure Black
					'base-300': '#000000', // Pure Black
					info: '#000000', // Pure Black
					success: '#000000', // Pure Black
					warning: '#000000', // Pure Black
					error: '#000000', // Pure Black

					// Text colors
					'base-content': '#ffffff', // Pure White
					'primary-content': '#ffffff', // Pure White
					'secondary-content': '#ffffff', // Pure White
					'accent-content': '#ffffff', // Pure White
					'neutral-content': '#ffffff', // Pure White
					'info-content': '#ffffff', // Pure White
					'success-content': '#ffffff', // Pure White
					'warning-content': '#ffffff', // Pure White
					'error-content': '#ffffff' // Pure White
				}
			}
		],
		base: true,
		styled: true,
		utils: true,
		prefix: '',
		darkTheme: 'ptolemies'
	},
	darkMode: 'class'
};
