"""
Benchmark Suite for EV Charging Scheduler Environment.
Provides comprehensive benchmarking and evaluation across agents and tasks.
"""

import json
import time
from typing import Dict, Any, List, Tuple
from datetime import datetime
import numpy as np

from ev_charging_env import (
    create_easy_task,
    create_medium_task,
    create_hard_task,
    RandomAgent,
    GreedyAgent,
    PriorityAwareAgent,
    OptimalSearchAgent,
)


class BenchmarkSuite:
    """Comprehensive benchmarking for EV Charging Scheduler agents."""

    def __init__(self):
        self.agents = {
            "random": RandomAgent(),
            "greedy": GreedyAgent(),
            "priority": PriorityAwareAgent(),
            "optimal": OptimalSearchAgent(),
        }
        
        self.tasks = {
            "easy": create_easy_task(),
            "medium": create_medium_task(),
            "hard": create_hard_task(),
        }
        
        self.results = []

    def evaluate_agent_on_task(
        self, agent_name: str, agent, task_name: str, task, max_steps: int = None
    ) -> Dict[str, Any]:
        """Run a single agent on a single task and return detailed metrics."""
        start_time = time.time()
        
        obs = task.reset()
        total_reward = 0.0
        step_count = 0
        rewards_history = []
        grid_loads = []
        costs = []
        
        max_steps = max_steps or task.config.max_steps

        for step in range(max_steps):
            try:
                action = agent.get_action(obs)
                result = task.step(action)
                step_count += 1
                total_reward += result.reward
                rewards_history.append(result.reward)
                obs = result.observation
                
                grid_loads.append(obs.grid.current_load)
                costs.append(obs.grid.electricity_price)

                if result.done:
                    break

            except Exception as e:
                print(f"Error at step {step}: {e}")
                continue

        elapsed_time = time.time() - start_time

        # Grade the task
        grade_result = task.grade(use_llm=False)

        metrics = {
            "agent": agent_name,
            "task": task_name,
            "score": grade_result.score,
            "episode_reward": grade_result.episode_reward,
            "steps_taken": grade_result.steps_taken,
            "vehicles_charged": grade_result.vehicles_charged,
            "missed_deadlines": grade_result.missed_deadlines,
            "grid_overloads": grade_result.grid_overloads,
            "total_cost": grade_result.total_cost,
            "elapsed_time_seconds": round(elapsed_time, 3),
            "avg_reward_per_step": round(total_reward / max(step_count, 1), 4),
            "reward_std": round(float(np.std(rewards_history)) if rewards_history else 0, 4),
            "avg_grid_load": round(float(np.mean(grid_loads)) if grid_loads else 0, 4),
            "peak_grid_load": round(float(np.max(grid_loads)) if grid_loads else 0, 4),
            "avg_electricity_price": round(float(np.mean(costs)) if costs else 0, 4),
            "timestamp": datetime.now().isoformat(),
        }

        return metrics

    def run_benchmark(
        self, agents_to_run: List[str] = None, tasks_to_run: List[str] = None, 
        max_steps: int = None
    ) -> List[Dict[str, Any]]:
        """Run benchmark suite on specified agents and tasks."""
        if agents_to_run is None:
            agents_to_run = list(self.agents.keys())
        if tasks_to_run is None:
            tasks_to_run = list(self.tasks.keys())

        results = []
        total_runs = len(agents_to_run) * len(tasks_to_run)
        current_run = 0

        for task_name in tasks_to_run:
            task = self.tasks[task_name]
            
            for agent_name in agents_to_run:
                current_run += 1
                print(f"[{current_run}/{total_runs}] Running {agent_name} on {task_name}...")
                
                agent = self.agents[agent_name]
                result = self.evaluate_agent_on_task(
                    agent_name, agent, task_name, task, max_steps
                )
                results.append(result)
                self.results.append(result)

        return results

    def get_summary_by_agent(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get aggregated metrics by agent."""
        by_agent = {}
        
        for result in results:
            agent = result["agent"]
            if agent not in by_agent:
                by_agent[agent] = {
                    "avg_score": [],
                    "avg_reward": [],
                    "avg_vehicles_charged": [],
                    "avg_missed_deadlines": [],
                    "avg_grid_overloads": [],
                    "avg_cost": [],
                    "avg_time": [],
                }
            
            by_agent[agent]["avg_score"].append(result["score"])
            by_agent[agent]["avg_reward"].append(result["episode_reward"])
            by_agent[agent]["avg_vehicles_charged"].append(result["vehicles_charged"])
            by_agent[agent]["avg_missed_deadlines"].append(result["missed_deadlines"])
            by_agent[agent]["avg_grid_overloads"].append(result["grid_overloads"])
            by_agent[agent]["avg_cost"].append(result["total_cost"])
            by_agent[agent]["avg_time"].append(result["elapsed_time_seconds"])

        # Calculate averages
        summary = {}
        for agent, metrics in by_agent.items():
            summary[agent] = {
                "avg_score": round(np.mean(metrics["avg_score"]), 4),
                "avg_reward": round(np.mean(metrics["avg_reward"]), 4),
                "avg_vehicles_charged": round(np.mean(metrics["avg_vehicles_charged"]), 2),
                "avg_missed_deadlines": round(np.mean(metrics["avg_missed_deadlines"]), 2),
                "avg_grid_overloads": round(np.mean(metrics["avg_grid_overloads"]), 2),
                "avg_cost": round(np.mean(metrics["avg_cost"]), 2),
                "total_time": round(np.sum(metrics["avg_time"]), 2),
            }

        return summary

    def get_summary_by_task(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get aggregated metrics by task difficulty."""
        by_task = {}
        
        for result in results:
            task = result["task"]
            if task not in by_task:
                by_task[task] = []
            by_task[task].append(result)

        summary = {}
        for task_name, task_results in by_task.items():
            agents_data = {}
            for result in task_results:
                agent = result["agent"]
                agents_data[agent] = {
                    "score": result["score"],
                    "reward": result["episode_reward"],
                    "vehicles": result["vehicles_charged"],
                    "cost": result["total_cost"],
                }
            summary[task_name] = agents_data

        return summary

    def save_results(self, results: List[Dict[str, Any]], filename: str):
        """Save benchmark results to JSON."""
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        return f"Results saved to {filename}"

    def format_results_for_display(self, results: List[Dict[str, Any]]) -> str:
        """Format results as readable text."""
        by_task = {}
        for result in results:
            task = result["task"]
            if task not in by_task:
                by_task[task] = []
            by_task[task].append(result)

        output = []
        output.append("=" * 100)
        output.append("BENCHMARK RESULTS SUMMARY")
        output.append("=" * 100)

        for task_name in sorted(by_task.keys()):
            task_results = by_task[task_name]
            task_results.sort(key=lambda x: x["score"], reverse=True)
            
            output.append(f"\n{task_name.upper()} TASK")
            output.append("-" * 100)
            output.append(
                f"{'Agent':<12} {'Score':<8} {'Reward':<10} {'Vehicles':<10} "
                f"{'Missed':<8} {'Overloads':<10} {'Cost':<10} {'Time(s)':<8}"
            )
            output.append("-" * 100)

            for result in task_results:
                output.append(
                    f"{result['agent']:<12} {result['score']:<8.3f} "
                    f"{result['episode_reward']:<10.2f} {result['vehicles_charged']:<10d} "
                    f"{result['missed_deadlines']:<8d} {result['grid_overloads']:<10d} "
                    f"${result['total_cost']:<9.2f} {result['elapsed_time_seconds']:<8.2f}"
                )

        return "\n".join(output)
