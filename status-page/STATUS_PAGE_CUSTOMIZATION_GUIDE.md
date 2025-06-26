# 🎨 **Status Page Customization Guide**

Here are the specific files to edit for text, colors, and emojis:

## 🎯 **Text & Emojis**

### **Main Status Messages & Emojis**

**1. Executive Dashboard (`src/lib/components/ExecutiveDashboard.svelte`)**

```svelte
<!-- Line 88-96: Main status text & emojis -->
<span class="text-4xl">{getOverallStatusIcon(systemHealth.overall_status)}</span>
<h1 class="text-3xl md:text-5xl font-bold">
    {getOverallStatusText(systemHealth.overall_status)}
</h1>

<!-- Lines 75-85: Status functions to edit -->
function getOverallStatusIcon(status: string) {
    switch (status) {
        case 'operational': return '🟢';  // ← Change emoji here
        case 'degraded': return '🟡';
        case 'outage': return '🔴';
    }
}

function getOverallStatusText(status: string) {
    switch (status) {
        case 'operational': return 'All Systems Operational';  // ← Change text here
        case 'degraded': return 'Degraded Performance';
        case 'outage': return 'Service Outage';
    }
}
```

**2. Service Status Grid (`src/lib/components/ServiceStatusGrid.svelte`)**

```svelte
<!-- Line 15: Main title & emoji -->
<h2 class="card-title text-info flex items-center gap-2">
    <span class="text-2xl">🔧</span>  <!-- ← Change emoji -->
    Service Status Grid               <!-- ← Change title -->
</h2>

<!-- Lines 130-140: Service names & descriptions -->
const services: ServiceStatus[] = [
    {
        name: 'FastAPI Backend',                    // ← Edit service name
        description: 'Main API server with Logfire', // ← Edit description
        // ... other config
    }
];
```

**3. Component Titles (All Components)**

```svelte
<!-- Ptolemies Stats -->
<h2 class="card-title text-primary flex items-center gap-2">
	<span class="text-2xl">📚</span>
	<!-- Change emoji -->
	Ptolemies Knowledge Base <!-- Change title -->
</h2>

<!-- Neo4j Stats -->
<h2 class="card-title text-secondary flex items-center gap-2">
	<span class="text-2xl">🕸️</span>
	<!-- Change emoji -->
	Neo4j Knowledge Graph <!-- Change title -->
</h2>

<!-- Dehallucinator Stats -->
<h2 class="card-title text-warning flex items-center gap-2">
	<span class="text-2xl">🛡️</span>
	<!-- Change emoji -->
	Dehallucinator Service <!-- Change title -->
</h2>
```

## 🌈 **Colors**

### **Primary Color Configuration**

**1. Tailwind Config (`tailwind.config.cjs`)**

```javascript
// Lines 9-27: Main color palette
colors: {
    primary: '#1B03A3',      // ← Change primary color (Neon Blue)
    secondary: '#9D00FF',    // ← Change secondary color (Neon Purple)
    accent: '#FF10F0',       // ← Change accent color (Neon Pink)
    success: '#39FF14',      // ← Change success color (Neon Green)
    warning: '#E9FF32',      // ← Change warning color (Neon Yellow)
    destructive: '#FF3131',  // ← Change error color (Neon Red)
    info: '#00FFFF',         // ← Change info color (Neon Cyan)

    // Background colors
    'bg-primary': '#010B13',   // ← Main background
    'bg-secondary': '#0F1111', // ← Card backgrounds
    'bg-surface': '#1A1A1A',   // ← Surface elements
}
```

**2. CSS Variables (`src/app.css`)**

```css
/* Lines 1-20: Root color variables */
:root {
	--color-primary: #1b03a3; /* ← Edit hex values */
	--color-secondary: #9d00ff;
	--color-accent: #ff10f0;
	--color-success: #39ff14;
	--color-warning: #e9ff32;
	--color-error: #ff3131;
	--color-info: #00ffff;

	--bg-primary: #010b13; /* ← Background colors */
	--bg-secondary: #0f1111;
	--bg-surface: #1a1a1a;
}
```

### **Status-Specific Colors**

**Service Status Colors (`src/lib/components/ServiceStatusGrid.svelte`)**

```javascript
// Lines 200-210: Status color functions
function getStatusColor(status: string) {
    switch (status) {
        case 'operational': return 'text-success';    // Green
        case 'degraded': return 'text-warning';       // Yellow
        case 'partial_outage': return 'text-error';   // Red
        case 'maintenance': return 'text-info';       // Blue
    }
}
```

## 📝 **Quick Edit Examples**

### **Change Main Header**

```svelte
<!-- In ExecutiveDashboard.svelte, line 90 -->
<h1 class="text-3xl md:text-5xl font-bold">
	My Custom Status Page <!-- ← Your text here -->
</h1>
```

### **Change Service Names**

```javascript
// In ServiceStatusGrid.svelte, lines 130+
{
    name: 'My API Service',           // ← Custom name
    description: 'My custom API',    // ← Custom description
    status: 'operational',
    // ...
}
```

### **Change Color Theme**

```javascript
// In tailwind.config.cjs, pick any color scheme:
primary: '#FF6B6B',      // Coral Red
secondary: '#4ECDC4',    // Teal
accent: '#45B7D1',       // Sky Blue
success: '#96CEB4',      // Mint Green
warning: '#FFEAA7',      // Light Yellow
```

### **Change Status Emojis**

```javascript
// In any component's status functions:
case 'operational': return '✅';     // Checkmark
case 'degraded': return '⚠️';       // Warning
case 'outage': return '💥';         // Explosion
case 'maintenance': return '🔧';    // Wrench
```

## 🎨 **Pre-Made Color Themes**

**Dark Cyber Theme:**

```javascript
primary: '#FF0090',      // Neon Magenta
secondary: '#C7EA46',    // Neon Lime
accent: '#FF5F1F',       // Neon Orange
```

**Soft Pastel Theme:**

```javascript
primary: '#AEC6CF',      // Pastel Blue
secondary: '#D8BFD8',    // Pastel Purple
accent: '#FFB347',       // Pastel Orange
```

**High Contrast Theme:**

```javascript
primary: '#FFFFFF',      // Pure White
secondary: '#00FF00',    // Bright Green
accent: '#FF00FF',       // Bright Magenta
```

## 🔤 **Hacker Font Usage**

### **Available Font Classes**

The custom Hacker font is now available with these utility classes:

```html
<!-- Basic Hacker font -->
<div class="font-hacker">Hacker font text</div>
<div class="text-hacker">Hacker with letter spacing</div>

<!-- Title styling with Hacker font -->
<h1 class="title-hacker">UPPERCASE HACKER TITLE</h1>

<!-- Terminal/console styling -->
<div class="terminal-text">$ system status: operational</div>

<!-- Glowing cyber effect -->
<span class="cyber-glow text-accent">CYBER GLOW EFFECT</span>

<!-- Inline code with Hacker font -->
<code class="code-hacker">api.status.check()</code>
```

### **Font Application Examples**

```svelte
<!-- Status titles with cyber glow -->
<h1 class="title-hacker cyber-glow text-accent">SYSTEM STATUS: OPERATIONAL</h1>

<!-- Metrics with Hacker font -->
<div class="text-2xl font-bold font-hacker text-success">99.9%</div>

<!-- Button with Hacker styling -->
<button class="btn btn-primary font-hacker"> > ACCESS_TERMINAL </button>
```

### **Terminal Styling**

```svelte
<!-- Full terminal block -->
<div class="terminal-text">
	$ neo4j-admin status<br />
	Status: ONLINE<br />
	Nodes: 77 | Relationships: 156<br />
	> Connection established
</div>
```

Just edit these files and save - the changes will appear immediately in your browser! 🚀
