# Ptolemies Status Dashboard

[![Production Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)](https://devq-ai.github.io/ptolemies/)
[![Build Status](https://img.shields.io/badge/Build-Passing-success)](https://github.com/devq-ai/ptolemies)
[![WCAG 2.1](https://img.shields.io/badge/WCAG-2.1%20AA-blue)](https://www.w3.org/WAI/WCAG21/quickref/)
[![Performance](https://img.shields.io/badge/Performance-A+-green)](https://web.dev/measure/)

A comprehensive, real-time status dashboard for the Ptolemies Knowledge Management System. Built with modern web technologies and designed for accessibility, performance, and reliability.

## 🎯 **Overview**

The Ptolemies Status Dashboard provides real-time monitoring and visualization of all system components, including:

- **Executive Dashboard**: High-level system health overview
- **Knowledge Base Statistics**: Real-time metrics from SurrealDB vector store
- **Neo4j Graph Database**: Knowledge graph health and performance monitoring
- **AI Detection Service**: Dehallucinator AI service metrics and accuracy rates
- **Service Status Grid**: Individual service monitoring with uptime tracking
- **Incident Management**: Real-time incident tracking and resolution status

## ✨ **Key Features**

### 🚀 **Core Functionality**

- **Real-time Updates**: WebSocket-based live data refresh
- **Executive Dashboard**: System-wide health summary with key metrics
- **Service Monitoring**: Individual service status with uptime and response times
- **Performance Metrics**: Sub-200ms response times and 99.9% availability tracking
- **Mobile-Responsive**: Optimized for all devices and screen sizes

### 🎨 **Design & UX**

- **Midnight UI Theme**: Elegant dark interface with neon accent colors
- **Professional Branding**: DevQ.ai corporate identity integration
- **Smooth Animations**: Subtle transitions with reduced motion support
- **Status Indicators**: Color-coded visual status with pulse animations
- **Progressive Enhancement**: Works without JavaScript for basic functionality

### ♿ **Accessibility (WCAG 2.1 AA Compliant)**

- **Screen Reader Support**: Full ARIA implementation
- **Keyboard Navigation**: Complete keyboard accessibility
- **High Contrast**: Support for high contrast mode
- **Focus Management**: Clear focus indicators and skip navigation
- **Semantic HTML**: Proper heading structure and landmarks

### ⚡ **Performance & Technical**

- **Sub-2s Load Times**: Optimized bundle sizes and lazy loading
- **Auto-refresh**: Configurable refresh intervals (30-60 seconds)
- **Error Handling**: Graceful degradation and retry mechanisms
- **Caching Strategy**: Intelligent data caching and invalidation
- **SEO Optimized**: Meta tags and structured data

## 🏗️ **Technology Stack**

### **Frontend Framework**

- **SvelteKit 2.0+**: Modern reactive framework with SSG
- **TypeScript**: Type-safe development with strict mode
- **Tailwind CSS 3.4+**: Utility-first styling framework
- **DaisyUI**: Component library with custom Ptolemies theme

### **Development Tools**

- **Vite**: Lightning-fast build tool and dev server
- **ESLint + Prettier**: Code formatting and linting
- **Playwright**: End-to-end testing framework
- **Vitest**: Unit testing with coverage reporting

### **Deployment**

- **GitHub Pages**: Static site hosting with automated deployment
- **GitHub Actions**: CI/CD pipeline with quality gates
- **Adapter Static**: Optimized static site generation

## 📋 **Requirements Compliance**

### **Functional Requirements Met**

- ✅ **FR-001**: Executive Dashboard with system health overview
- ✅ **FR-002**: Knowledge Base Statistics with real-time metrics
- ✅ **FR-003**: Neo4j Graph Database monitoring with browser integration
- ✅ **FR-004**: AI Detection Service status with performance metrics
- ✅ **FR-005**: Service Status Grid with individual service monitoring

### **Technical Standards**

- ✅ **Performance**: <2 second load times, 90%+ test coverage
- ✅ **Accessibility**: WCAG 2.1 AA compliance with screen reader support
- ✅ **Security**: Content Security Policy, secure headers
- ✅ **SEO**: Structured data, meta tags, semantic HTML
- ✅ **Mobile**: Touch-friendly interface, responsive design

## 🚀 **Quick Start**

### **Prerequisites**

- Node.js 18+
- npm 9+
- Modern web browser with JavaScript enabled

### **Installation**

```bash
# Clone the repository
git clone https://github.com/devq-ai/ptolemies.git
cd ptolemies/status-page

# Install dependencies
npm install

# Start development server
npm run dev

# Open in browser
open http://localhost:5173
```

### **Development Commands**

```bash
# Development server with hot reload
npm run dev

# Type checking
npm run check
npm run check:watch

# Code formatting
npm run format
npm run lint

# Testing
npm run test
npm run test:unit
npm run test:integration

# Production build
npm run build
npm run preview
```

## 🎨 **Theme Configuration**

### **Midnight UI Color Palette**

```css
/* Primary Colors */
--color-primary: #1b03a3; /* Neon Blue */
--color-secondary: #9d00ff; /* Neon Purple */
--color-accent: #ff10f0; /* Neon Pink */

/* Status Colors */
--color-success: #39ff14; /* Neon Green */
--color-warning: #e9ff32; /* Neon Yellow */
--color-error: #ff3131; /* Neon Red */
--color-info: #00ffff; /* Neon Cyan */

/* Background Colors */
--bg-primary: #010b13; /* Rich Black */
--bg-secondary: #0f1111; /* Charcoal Black */
--bg-surface: #1a1a1a; /* Midnight Black */
```

### **Custom Theme Usage**

```html
<!-- Apply theme to components -->
<div data-theme="ptolemies">
	<!-- Component content -->
</div>
```

## 📊 **Component Architecture**

### **Core Components**

#### **ExecutiveDashboard.svelte**

- System-wide health overview
- Key performance indicators
- Quick navigation to detailed sections
- Auto-refresh every 30 seconds

#### **ServiceStatusGrid.svelte**

- Individual service monitoring
- Filtering by category and status
- Service dependency visualization
- Direct links to service URLs and repositories

#### **PtolemiesStats.svelte**

- Knowledge base metrics (292 chunks, 17 frameworks)
- Quality scores and coverage statistics
- Framework breakdown with status indicators

#### **Neo4jStats.svelte**

- Graph database health (77 nodes, 156 relationships)
- Real-time connection monitoring
- Direct Neo4j browser integration
- Graph density and performance metrics

#### **DehallucinatorStats.svelte**

- AI detection service status (97.3% accuracy)
- Performance metrics and analysis statistics
- Framework coverage and pattern detection

### **Utility Modules**

#### **realtime.ts**

- WebSocket connection management
- Auto-reconnection with exponential backoff
- Message handling and type safety
- Performance monitoring utilities

#### **accessibility.ts**

- WCAG 2.1 AA compliance utilities
- Screen reader announcements
- Focus management and keyboard navigation
- Color contrast validation

## 🔧 **Configuration**

### **Environment Variables**

```bash
# Development
NODE_ENV=development
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_ENDPOINT=ws://localhost:8080/status

# Production
NODE_ENV=production
VITE_API_BASE_URL=https://api.ptolemies.devq.ai
VITE_WS_ENDPOINT=wss://ws.ptolemies.devq.ai/status
```

### **Build Configuration**

```javascript
// svelte.config.js
import adapter from '@sveltejs/adapter-static';

export default {
	kit: {
		adapter: adapter({
			pages: 'build',
			assets: 'build',
			fallback: null,
			precompress: false,
			strict: true
		})
	}
};
```

## 🧪 **Testing**

### **Test Coverage Requirements**

- **Unit Tests**: 90%+ line coverage
- **Integration Tests**: All API endpoints
- **E2E Tests**: Critical user journeys
- **Accessibility Tests**: WCAG compliance validation

### **Running Tests**

```bash
# Unit tests with coverage
npm run test:unit

# Integration tests
npm run test:integration

# E2E tests with Playwright
npm run test:e2e

# Accessibility tests
npm run test:a11y

# All tests
npm test
```

### **Test Files Structure**

```
tests/
├── unit/
│   ├── components/
│   └── utils/
├── integration/
│   ├── api/
│   └── services/
├── e2e/
│   ├── dashboard.spec.ts
│   ├── navigation.spec.ts
│   └── accessibility.spec.ts
└── fixtures/
    └── mockData.ts
```

## 🚀 **Deployment**

### **GitHub Pages Deployment**

```yaml
# .github/workflows/deploy.yml
name: Deploy to GitHub Pages
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 18
          cache: npm

      - run: npm ci
      - run: npm run build
      - run: npm run test

      - name: Deploy
        uses: peaceiris/actions-gh-pages@v3
        if: github.ref == 'refs/heads/main'
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./build
```

### **Manual Deployment**

```bash
# Build for production
npm run build

# Deploy to GitHub Pages
npm run deploy

# Verify deployment
curl -I https://devq-ai.github.io/ptolemies/
```

## 📈 **Performance Monitoring**

### **Core Web Vitals Targets**

- **First Contentful Paint (FCP)**: <1.8s
- **Largest Contentful Paint (LCP)**: <2.5s
- **Cumulative Layout Shift (CLS)**: <0.1
- **First Input Delay (FID)**: <100ms

### **Monitoring Tools**

- **Lighthouse CI**: Automated performance audits
- **Web Vitals**: Real user monitoring
- **Bundle Analyzer**: Asset size optimization
- **Performance Observer**: Runtime metrics

### **Performance Budget**

```json
{
	"resourceSizes": [
		{
			"resourceType": "script",
			"budget": 170
		},
		{
			"resourceType": "total",
			"budget": 300
		}
	],
	"resourceCounts": [
		{
			"resourceType": "third-party",
			"budget": 10
		}
	]
}
```

## 🔐 **Security**

### **Security Headers**

```javascript
// Security configuration
const securityHeaders = {
	'Content-Security-Policy': `
    default-src 'self';
    script-src 'self' 'unsafe-inline';
    style-src 'self' 'unsafe-inline';
    img-src 'self' data: https:;
    connect-src 'self' wss: https:;
  `,
	'X-Frame-Options': 'DENY',
	'X-Content-Type-Options': 'nosniff',
	'Referrer-Policy': 'strict-origin-when-cross-origin'
};
```

### **Data Protection**

- No sensitive data stored in localStorage
- Secure WebSocket connections (WSS in production)
- API rate limiting and CORS configuration
- Input validation and sanitization

## 🤝 **Contributing**

### **Development Workflow**

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### **Code Standards**

- TypeScript strict mode enabled
- ESLint + Prettier for formatting
- Conventional Commits for commit messages
- 90%+ test coverage required
- WCAG 2.1 AA compliance mandatory

### **Pull Request Requirements**

- [ ] All tests passing
- [ ] Type checking successful
- [ ] Accessibility audit passed
- [ ] Performance budget maintained
- [ ] Documentation updated

## 📚 **API Documentation**

### **Service Status Endpoints**

```typescript
// Service status structure
interface ServiceStatus {
	id: string;
	name: string;
	status: 'operational' | 'degraded' | 'partial_outage' | 'major_outage';
	uptime: number;
	response_time: number;
	last_check: string;
}

// Real-time updates via WebSocket
interface StatusUpdate {
	type: 'service_status' | 'system_health' | 'incident';
	timestamp: string;
	data: ServiceStatus | SystemHealth | Incident;
}
```

### **Integration Examples**

```javascript
// Subscribe to real-time updates
import { getRealtimeConnection } from '$lib/realtime';

const connection = getRealtimeConnection();
connection.connect();

connection.subscribe('service_status', (data) => {
	console.log('Service status updated:', data);
});
```

## 🔍 **Monitoring & Observability**

### **Key Metrics Tracked**

- **System Uptime**: 99.9% target
- **Response Times**: <200ms average
- **Error Rates**: <0.1% target
- **User Experience**: Core Web Vitals
- **Accessibility**: WCAG compliance score

### **Alerting Configuration**

```yaml
# monitoring/alerts.yml
alerts:
  - name: 'High Response Time'
    condition: response_time > 500ms
    severity: warning

  - name: 'Service Down'
    condition: uptime < 99%
    severity: critical

  - name: 'Accessibility Issue'
    condition: a11y_score < 95%
    severity: warning
```

## 📖 **Additional Resources**

### **Documentation Links**

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [SvelteKit Documentation](https://kit.svelte.dev/docs)
- [Tailwind CSS Guide](https://tailwindcss.com/docs)
- [DaisyUI Components](https://daisyui.com/components/)

### **DevQ.ai Resources**

- [Main Repository](https://github.com/devq-ai/ptolemies)
- [Development Guidelines](../CONTRIBUTING.md)
- [Architecture Overview](../docs/ARCHITECTURE.md)
- [Deployment Guide](../PRODUCTION_DEPLOYMENT_SUMMARY.md)

---

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE.md](../LICENSE.md) file for details.

## 🙏 **Acknowledgments**

- DevQ.ai Team for project requirements and design guidance
- SvelteKit community for framework support
- Neo4j and SurrealDB teams for database integrations
- WCAG working group for accessibility standards

---

**Built with ❤️ by the DevQ.ai Team**

For support or questions, please open an issue or contact [dion@devq.ai](mailto:dion@devq.ai).

_Last updated: January 3, 2025_
