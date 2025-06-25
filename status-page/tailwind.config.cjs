/** @type {import('tailwindcss').Config} */
module.exports = {
	content: ['./src/**/*.{js,svelte,ts}', './index.html'],
	theme: {
		extend: {
			colors: {
				// Dark Palette 1: "Midnight UI" (Elegant & Minimal)
				primary: '#1B03A3',           // Neon Blue
				secondary: '#9D00FF',         // Neon Purple
				accent: '#FF10F0',            // Neon Pink (FIXED: Single value, not object)
				destructive: '#FF3131',       // Neon Red
				success: '#39FF14',           // Neon Green
				warning: '#E9FF32',           // Neon Yellow
				info: '#00FFFF',              // Neon Cyan
				
				// Background colors
				'bg-primary': '#010B13',      // Rich Black
				'bg-secondary': '#0F1111',    // Charcoal Black
				'bg-surface': '#1A1A1A',      // Midnight Black
				
				// Foreground colors
				'fg-primary': '#E3E3E3',      // Soft White
				'fg-secondary': '#A3A3A3',    // Stone Grey
				'fg-disabled': '#606770',     // Neutral Grey
			},
			fontFamily: {
				mono: ['JetBrains Mono', 'Consolas', 'Monaco', 'monospace'],
			},
		},
	},
	/* eslint @typescript-eslint/no-require-imports: "off" */
	plugins: [require('daisyui')],
	daisyui: {
		logs: false,
		themes: [
			{
				ptolemies: {
					// Custom DaisyUI theme for Ptolemies
					"primary": "#1B03A3",           // Neon Blue
					"secondary": "#9D00FF",         // Neon Purple  
					"accent": "#FF10F0",            // Neon Pink
					"neutral": "#1A1A1A",           // Midnight Black
					"base-100": "#010B13",          // Rich Black
					"base-200": "#0F1111",          // Charcoal Black
					"base-300": "#1A1A1A",          // Midnight Black
					"info": "#00FFFF",              // Neon Cyan
					"success": "#39FF14",           // Neon Green
					"warning": "#E9FF32",           // Neon Yellow
					"error": "#FF3131",             // Neon Red
					
					// Text colors
					"base-content": "#E3E3E3",      // Soft White
					"primary-content": "#E3E3E3",   // Soft White
					"secondary-content": "#A3A3A3", // Stone Grey
					"accent-content": "#E3E3E3",    // Soft White
					"neutral-content": "#A3A3A3",   // Stone Grey
					"info-content": "#010B13",      // Rich Black
					"success-content": "#010B13",   // Rich Black
					"warning-content": "#010B13",   // Rich Black
					"error-content": "#E3E3E3",     // Soft White
				}
			}
		],
		base: true,
		styled: true,
		utils: true,
		prefix: "",
		darkTheme: "ptolemies",
	},
	darkMode: 'class',
};
