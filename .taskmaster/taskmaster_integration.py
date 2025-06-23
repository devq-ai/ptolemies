#!/usr/bin/env python3
"""
TaskMaster AI Integration Script for Ptolemies Project.
This script provides the interface between TaskMaster AI and the Ptolemies task structure.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

class TaskMasterIntegration:
    """Integration class for TaskMaster AI with Ptolemies project."""
    
    def __init__(self, task_file: str = "ptolemies_tasks.json"):
        self.task_file = task_file
        self.tasks = self._load_tasks()
        
    def _load_tasks(self) -> Dict[str, Any]:
        """Load tasks from JSON file."""
        file_path = os.path.join(os.path.dirname(__file__), self.task_file)
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def get_current_phase(self) -> Dict[str, Any]:
        """Get the current active phase based on task status."""
        for task in self.tasks['tasks']:
            if task['status'] == 'in_progress':
                return {
                    'phase': task['phase'],
                    'task': task['name'],
                    'complexity': task['complexity'],
                    'progress': self._calculate_task_progress(task)
                }
        
        # If no task is in progress, find the first pending task
        for task in self.tasks['tasks']:
            if task['status'] == 'pending':
                return {
                    'phase': task['phase'],
                    'task': task['name'],
                    'complexity': task['complexity'],
                    'progress': 0
                }
        
        return {'phase': 'completed', 'task': 'All tasks completed', 'progress': 100}
    
    def _calculate_task_progress(self, task: Dict[str, Any]) -> float:
        """Calculate task progress based on subtasks."""
        if not task['subtasks']:
            return 0
        
        # Simplified progress calculation
        # In real implementation, this would track actual subtask completion
        return 0  # Placeholder
    
    def get_next_action(self) -> Dict[str, Any]:
        """Get the next recommended action based on current state."""
        current = self.get_current_phase()
        
        if current['phase'] == 'completed':
            return {
                'action': 'project_complete',
                'message': 'All Ptolemies project tasks have been completed!'
            }
        
        # Find the current task
        current_task = None
        for task in self.tasks['tasks']:
            if task['name'] == current['task']:
                current_task = task
                break
        
        if not current_task:
            return {'action': 'error', 'message': 'Could not find current task'}
        
        # Recommend next subtask
        if current_task['subtasks']:
            next_subtask = current_task['subtasks'][0]  # Simplified: take first subtask
            return {
                'action': 'execute_subtask',
                'phase': current_task['phase'],
                'task': current_task['name'],
                'subtask': next_subtask['name'],
                'estimated_hours': next_subtask['estimated_hours'],
                'complexity': next_subtask['complexity'],
                'description': next_subtask['description']
            }
        
        return {'action': 'complete_task', 'task': current_task['name']}
    
    def update_task_status(self, task_name: str, new_status: str) -> bool:
        """Update the status of a task."""
        for task in self.tasks['tasks']:
            if task['name'] == task_name:
                task['status'] = new_status
                task['updated_at'] = datetime.now().isoformat()
                self._save_tasks()
                return True
        return False
    
    def _save_tasks(self):
        """Save tasks back to JSON file."""
        file_path = os.path.join(os.path.dirname(__file__), self.task_file)
        with open(file_path, 'w') as f:
            json.dump(self.tasks, f, indent=2)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current project metrics."""
        completed_tasks = sum(1 for t in self.tasks['tasks'] if t['status'] == 'completed')
        in_progress_tasks = sum(1 for t in self.tasks['tasks'] if t['status'] == 'in_progress')
        pending_tasks = sum(1 for t in self.tasks['tasks'] if t['status'] == 'pending')
        
        total_hours_completed = 0
        total_hours_remaining = 0
        
        for task in self.tasks['tasks']:
            task_hours = sum(st['estimated_hours'] for st in task['subtasks'])
            if task['status'] == 'completed':
                total_hours_completed += task_hours
            else:
                total_hours_remaining += task_hours
        
        return {
            'tasks': {
                'completed': completed_tasks,
                'in_progress': in_progress_tasks,
                'pending': pending_tasks,
                'total': len(self.tasks['tasks'])
            },
            'hours': {
                'completed': total_hours_completed,
                'remaining': total_hours_remaining,
                'total': total_hours_completed + total_hours_remaining
            },
            'progress_percentage': (completed_tasks / len(self.tasks['tasks'])) * 100,
            'complexity_average': self.tasks['metrics']['average_complexity']
        }
    
    def generate_status_report(self) -> str:
        """Generate a status report for the project."""
        metrics = self.get_metrics()
        current = self.get_current_phase()
        
        report = f"""
PTOLEMIES PROJECT STATUS REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*50}

CURRENT STATUS:
- Active Phase: {current['phase']}
- Current Task: {current['task']}
- Task Complexity: {current['complexity']}/10

PROGRESS METRICS:
- Tasks Completed: {metrics['tasks']['completed']}/{metrics['tasks']['total']}
- Overall Progress: {metrics['progress_percentage']:.1f}%
- Hours Completed: {metrics['hours']['completed']}
- Hours Remaining: {metrics['hours']['remaining']}

PHASE BREAKDOWN:
"""
        
        # Add phase status
        phases = ['phase1', 'phase2', 'phase3', 'phase4', 'phase5', 'phase6']
        for phase in phases:
            phase_task = next((t for t in self.tasks['tasks'] if t['phase'] == phase), None)
            if phase_task:
                status_icon = {
                    'completed': '✓',
                    'in_progress': '→',
                    'pending': '○'
                }.get(phase_task['status'], '?')
                report += f"  {status_icon} {phase}: {phase_task['name']}\n"
        
        return report

def main():
    """Main entry point for TaskMaster integration."""
    integration = TaskMasterIntegration()
    
    # Print current status
    print(integration.generate_status_report())
    
    # Get next action
    next_action = integration.get_next_action()
    print(f"\nNEXT RECOMMENDED ACTION:")
    print(f"- Action Type: {next_action['action']}")
    if 'subtask' in next_action:
        print(f"- Subtask: {next_action['subtask']}")
        print(f"- Estimated Hours: {next_action['estimated_hours']}")
        print(f"- Complexity: {next_action['complexity']}/10")

if __name__ == "__main__":
    main()