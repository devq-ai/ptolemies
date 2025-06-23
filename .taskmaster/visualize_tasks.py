#!/usr/bin/env python3
"""
Generate text-based visualizations for Ptolemies project tasks.
"""

import json
from datetime import datetime

def load_tasks():
    """Load task structure from JSON file."""
    with open('ptolemies_tasks.json', 'r') as f:
        return json.load(f)

def create_ascii_dependency_graph():
    """Create ASCII art dependency graph."""
    print("\n" + "="*80)
    print("PTOLEMIES PROJECT - TASK DEPENDENCY FLOW")
    print("="*80 + "\n")
    
    graph = """
    ┌─────────────────┐
    │ Phase 1: Found. │ Week 1
    │ Complexity: 5   │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Phase 2: Neo4j  │ Week 2
    │ Complexity: 7   │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Phase 3: Crawl  │ Week 3-4
    │ Complexity: 8   │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Phase 4: Store  │ Week 5-6
    │ Complexity: 9   │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Phase 5: MCP    │ Week 7
    │ Complexity: 7   │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Phase 6: Visual │ Week 8
    │ Complexity: 6   │
    └─────────────────┘
    """
    print(graph)

def create_timeline_view():
    """Create timeline view of tasks."""
    data = load_tasks()
    
    print("\n" + "="*80)
    print("PROJECT TIMELINE")
    print("="*80 + "\n")
    
    timeline = """
    Week 1  ████████ Foundation Setup
    Week 2  ████████ Neo4j MCP Development
    Week 3  ████████ Crawling Infrastructure (Part 1)
    Week 4  ████████ Crawling Infrastructure (Part 2)
    Week 5  ████████ Storage & Retrieval (Part 1)
    Week 6  ████████ Storage & Retrieval (Part 2)
    Week 7  ████████ Ptolemies MCP Service
    Week 8  ████████ Visualization & Analytics
    """
    print(timeline)
    
    print("\nTotal Estimated Hours:", data['metrics']['total_estimated_hours'])
    print("Average Complexity:", f"{data['metrics']['average_complexity']:.1f}/10")

def create_task_breakdown():
    """Create detailed task breakdown."""
    data = load_tasks()
    
    print("\n" + "="*80)
    print("DETAILED TASK BREAKDOWN")
    print("="*80 + "\n")
    
    for task in data['tasks']:
        print(f"\n{'─'*60}")
        print(f"📋 {task['name']}")
        print(f"   Phase: {task['phase']} | Complexity: {task['complexity']}/10")
        print(f"   Duration: {task['duration_days']} days")
        print(f"   Status: {task['status']} | Priority: {task['priority']}")
        
        if task['dependencies']:
            print(f"   Dependencies: {len(task['dependencies'])} task(s)")
        
        print(f"\n   Subtasks ({len(task['subtasks'])}):")
        total_hours = 0
        for st in task['subtasks']:
            print(f"   • {st['name']} ({st['estimated_hours']}h)")
            total_hours += st['estimated_hours']
        print(f"   Total Hours: {total_hours}")

def create_complexity_chart():
    """Create complexity distribution chart."""
    data = load_tasks()
    
    print("\n" + "="*80)
    print("COMPLEXITY DISTRIBUTION")
    print("="*80 + "\n")
    
    complexities = [task['complexity'] for task in data['tasks']]
    
    print("Complexity Scale (1-10):")
    for i in range(10, 0, -1):
        count = complexities.count(i)
        bar = "█" * (count * 10)
        print(f"{i:2d} │ {bar} {count}")
    print("   └" + "─" * 30)
    
    print(f"\nAverage Complexity: {sum(complexities)/len(complexities):.1f}")
    print(f"Most Complex: Phase 4 - Storage & Retrieval (9/10)")
    print(f"Least Complex: Phase 1 - Foundation (5/10)")

def create_resource_summary():
    """Create resource allocation summary."""
    data = load_tasks()
    
    print("\n" + "="*80)
    print("RESOURCE ALLOCATION SUMMARY")
    print("="*80 + "\n")
    
    phase_hours = {}
    for task in data['tasks']:
        phase = task['phase']
        hours = sum(st['estimated_hours'] for st in task['subtasks'])
        phase_hours[phase] = hours
    
    total_hours = sum(phase_hours.values())
    
    print("Hours by Phase:")
    for phase, hours in sorted(phase_hours.items()):
        percentage = (hours / total_hours) * 100
        bar_length = int(percentage / 2)
        bar = "█" * bar_length
        print(f"{phase:7s} │ {bar:<25s} {hours:3d}h ({percentage:4.1f}%)")
    
    print(f"\nTotal Hours: {total_hours}")
    print(f"Daily Hours (8-week timeline): {total_hours / 56:.1f}")
    print(f"Team Size Recommendation: 2-3 developers")

def save_visualization_report():
    """Save all visualizations to a report file."""
    import sys
    from io import StringIO
    
    # Capture all output
    old_stdout = sys.stdout
    sys.stdout = buffer = StringIO()
    
    # Generate all visualizations
    create_ascii_dependency_graph()
    create_timeline_view()
    create_task_breakdown()
    create_complexity_chart()
    create_resource_summary()
    
    # Get the output
    output = buffer.getvalue()
    sys.stdout = old_stdout
    
    # Save to file
    with open('task_visualization_report.txt', 'w') as f:
        f.write("PTOLEMIES PROJECT - TASK VISUALIZATION REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(output)
    
    print("✅ Saved visualization report: task_visualization_report.txt")

def main():
    """Generate all visualizations."""
    print("🎨 Generating task visualizations...")
    
    create_ascii_dependency_graph()
    create_timeline_view()
    create_task_breakdown()
    create_complexity_chart()
    create_resource_summary()
    save_visualization_report()
    
    print("\n✨ All visualizations generated successfully!")

if __name__ == "__main__":
    main()