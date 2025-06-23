#!/usr/bin/env python3
"""
Generate visual dependency graph for Ptolemies project tasks.
"""

import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

def load_tasks():
    """Load task structure from JSON file."""
    with open('ptolemies_tasks.json', 'r') as f:
        return json.load(f)

def create_dependency_graph():
    """Create visual dependency graph using matplotlib."""
    data = load_tasks()
    tasks = data['tasks']
    
    # Create figure
    fig, ax = plt.subplots(figsize=(16, 10))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis('off')
    
    # Define phase colors
    phase_colors = {
        'phase1': '#FF6B6B',  # Red
        'phase2': '#4ECDC4',  # Teal
        'phase3': '#45B7D1',  # Blue
        'phase4': '#96CEB4',  # Green
        'phase5': '#FECA57',  # Yellow
        'phase6': '#DDA0DD'   # Plum
    }
    
    # Position tasks
    positions = {
        'Foundation Setup': (1.5, 3.5),
        'Neo4j MCP Server Development': (3, 3.5),
        'Crawling Infrastructure Implementation': (4.5, 3.5),
        'Storage and Retrieval System': (6, 3.5),
        'Ptolemies MCP Service': (7.5, 3.5),
        'Visualization and Analytics Platform': (9, 3.5)
    }
    
    # Draw tasks as boxes
    task_boxes = {}
    for task in tasks:
        if task['name'] in positions:
            x, y = positions[task['name']]
            color = phase_colors.get(task['phase'], '#CCCCCC')
            
            # Create fancy box
            box = FancyBboxPatch(
                (x-0.6, y-0.3), 1.2, 0.6,
                boxstyle="round,pad=0.1",
                facecolor=color,
                edgecolor='black',
                linewidth=2,
                alpha=0.8
            )
            ax.add_patch(box)
            task_boxes[task['id']] = (x, y)
            
            # Add task name
            ax.text(x, y, task['name'].replace(' ', '\n'), 
                   ha='center', va='center', fontsize=8, fontweight='bold')
            
            # Add complexity indicator
            ax.text(x, y-0.5, f"Complexity: {task['complexity']}/10", 
                   ha='center', va='center', fontsize=6)
    
    # Draw dependencies as arrows
    for task in tasks:
        if task['id'] in task_boxes:
            x2, y2 = task_boxes[task['id']]
            for dep_id in task['dependencies']:
                if dep_id in task_boxes:
                    x1, y1 = task_boxes[dep_id]
                    arrow = FancyArrowPatch(
                        (x1+0.6, y1), (x2-0.6, y2),
                        arrowstyle='->,head_width=0.4,head_length=0.4',
                        color='black',
                        linewidth=1.5,
                        alpha=0.6
                    )
                    ax.add_patch(arrow)
    
    # Add title and legend
    ax.text(5, 6.5, 'Ptolemies Project - Task Dependency Graph', 
           ha='center', va='center', fontsize=16, fontweight='bold')
    
    ax.text(5, 6, 'DevQ.AI Knowledge Base System Implementation Phases', 
           ha='center', va='center', fontsize=12, style='italic')
    
    # Create legend
    legend_elements = [
        mpatches.Patch(facecolor=color, edgecolor='black', label=f"Phase {i+1}")
        for i, color in enumerate(phase_colors.values())
    ]
    ax.legend(handles=legend_elements, loc='lower center', ncol=6, 
             bbox_to_anchor=(0.5, -0.1), frameon=False)
    
    # Add timeline
    ax.text(0.5, 2, 'Week 1', ha='center', fontsize=9, fontweight='bold')
    ax.text(2.5, 2, 'Week 2', ha='center', fontsize=9, fontweight='bold')
    ax.text(4.5, 2, 'Week 3-4', ha='center', fontsize=9, fontweight='bold')
    ax.text(6.5, 2, 'Week 5-6', ha='center', fontsize=9, fontweight='bold')
    ax.text(8, 2, 'Week 7', ha='center', fontsize=9, fontweight='bold')
    ax.text(9.5, 2, 'Week 8', ha='center', fontsize=9, fontweight='bold')
    
    # Add metrics summary
    total_hours = data['metrics']['total_estimated_hours']
    ax.text(5, 0.5, f'Total Estimated Hours: {total_hours} | Average Complexity: {data["metrics"]["average_complexity"]:.1f}/10', 
           ha='center', va='center', fontsize=10)
    
    # Save the graph
    plt.tight_layout()
    plt.savefig('dependency_graph.png', dpi=300, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    plt.savefig('dependency_graph.pdf', bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    
    print("✅ Generated dependency graph: dependency_graph.png and dependency_graph.pdf")

def create_gantt_chart():
    """Create Gantt chart for project timeline."""
    data = load_tasks()
    tasks = data['tasks']
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Define phase colors (same as dependency graph)
    phase_colors = {
        'phase1': '#FF6B6B',
        'phase2': '#4ECDC4',
        'phase3': '#45B7D1',
        'phase4': '#96CEB4',
        'phase5': '#FECA57',
        'phase6': '#DDA0DD'
    }
    
    # Create Gantt bars
    y_positions = list(range(len(tasks)))
    task_names = [t['name'] for t in tasks]
    
    # Week positions
    week_starts = [0, 7, 14, 28, 42, 49, 56]  # Cumulative days
    week_durations = [7, 7, 14, 14, 7, 7]
    
    for i, task in enumerate(tasks):
        phase_idx = int(task['phase'][-1]) - 1
        start = week_starts[phase_idx]
        duration = week_durations[phase_idx]
        color = phase_colors[task['phase']]
        
        ax.barh(i, duration, left=start, height=0.6, 
                color=color, alpha=0.8, edgecolor='black', linewidth=1)
        
        # Add complexity text
        ax.text(start + duration/2, i, f"C:{task['complexity']}", 
                ha='center', va='center', fontsize=8, fontweight='bold')
    
    # Customize chart
    ax.set_yticks(y_positions)
    ax.set_yticklabels(task_names)
    ax.set_xlabel('Days', fontsize=12)
    ax.set_title('Ptolemies Project - Gantt Chart Timeline', fontsize=16, fontweight='bold')
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    
    # Add week markers
    for i, (start, week_label) in enumerate(zip(week_starts, 
                                                ['Week 1', 'Week 2', 'Week 3-4', 'Week 5-6', 'Week 7', 'Week 8'])):
        ax.axvline(x=start, color='gray', linestyle='--', alpha=0.5)
        ax.text(start + 3.5, -1, week_label, ha='center', fontsize=9)
    
    # Add today marker
    ax.axvline(x=0, color='red', linestyle='-', linewidth=2, alpha=0.7)
    ax.text(0, -1.5, 'Start', ha='center', fontsize=9, color='red', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('gantt_chart.png', dpi=300, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    
    print("✅ Generated Gantt chart: gantt_chart.png")

def main():
    """Generate all visualization outputs."""
    print("🎨 Generating project visualizations...")
    create_dependency_graph()
    create_gantt_chart()
    print("✨ All visualizations generated successfully!")

if __name__ == "__main__":
    main()