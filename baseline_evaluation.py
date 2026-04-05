"""
Baseline Evaluation Script for EV Charging Scheduler Environment.
Runs all baseline agents on all task difficulties and produces reproducible scores.
"""

import json
import argparse
from typing import Dict, Any, List

from ev_charging_env import (
    create_easy_task,
    create_medium_task,
    create_hard_task,
    RandomAgent,
    GreedyAgent,
    PriorityAwareAgent,
    OptimalSearchAgent,
)


class BaselineEvaluator:
    """Evaluate all baseline agents on all tasks."""

    def __init__(self):
        self.agents = {
            "random": RandomAgent(),
            "greedy": GreedyAgent(),
            "priority": PriorityAwareAgent(),
            "optimal": OptimalSearchAgent(),
        }

    def evaluate_agent_on_task(self, agent_name: str, agent, task_name: str, task) -> Dict[str, Any]:
        """Run a single agent on a single task."""
        print(f"Running {agent_name.upper()} agent on {task_name.upper()} task...")

        obs = task.reset()
        total_reward = 0.0
        step_count = 0
        max_steps = task.config.max_steps

        for step in range(max_steps):
            try:
                # Get action from agent
                action = agent.get_action(obs)

                # Execute step
                result = task.step(action)
                step_count += 1
                total_reward += result.reward
                obs = result.observation

                # Print progress every 50 steps
                if (step + 1) % 50 == 0:
                    print(f"  Step {step+1}/{max_steps}: Reward={result.reward:.3f}, "
                          f"Grid Load={obs.grid.current_load:.1%}")

                if result.done:
                    break

            except Exception as e:
                print(f"  Error at step {step}: {e}")
                # Continue with next step
                continue

        # Grade the task
        grade_result = task.grade(use_llm=False)  # Skip LLM for baseline evaluation

        results = {
            "agent": agent_name,
            "task": task_name,
            "score": grade_result.score,
            "episode_reward": grade_result.episode_reward,
            "steps_taken": grade_result.steps_taken,
            "vehicles_charged": grade_result.vehicles_charged,
            "missed_deadlines": grade_result.missed_deadlines,
            "grid_overloads": grade_result.grid_overloads,
            "total_cost": grade_result.total_cost,
            "details": grade_result.details,
        }

        print(f"  Completed! Score: {results['score']:.3f}, "
              f"Vehicles: {results['vehicles_charged']}, Cost: ${results['total_cost']:.2f}")

        return results

    def run_all_evaluations(self) -> List[Dict[str, Any]]:
        """Run all agents on all tasks."""
        tasks = {
            "easy": create_easy_task(),
            "medium": create_medium_task(),
            "hard": create_hard_task(),
        }

        all_results = []

        for task_name, task in tasks.items():
            print(f"\n{'='*60}")
            print(f"EVALUATING {task_name.upper()} TASK")
            print('='*60)

            for agent_name, agent in self.agents.items():
                result = self.evaluate_agent_on_task(agent_name, agent, task_name, task)
                all_results.append(result)

        return all_results

    def print_summary(self, results: List[Dict[str, Any]]):
        """Print evaluation summary."""
        print(f"\n{'='*80}")
        print("BASELINE EVALUATION SUMMARY")
        print('='*80)

        # Group by task
        tasks = {}
        for result in results:
            task = result["task"]
            if task not in tasks:
                tasks[task] = []
            tasks[task].append(result)

        for task_name, task_results in tasks.items():
            print(f"\n{task_name.upper()} TASK RESULTS:")
            print("-" * 40)

            # Sort by score
            task_results.sort(key=lambda x: x["score"], reverse=True)

            for result in task_results:
                agent = result["agent"].upper()
                score = result["score"]
                vehicles = result["vehicles_charged"]
                cost = result["total_cost"]
                print(f"  {agent:8} | Score: {score:.3f} | Vehicles: {vehicles:2d} | Cost: ${cost:6.2f}")

    def save_results(self, results: List[Dict[str, Any]], filename: str):
        """Save results to JSON file."""
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {filename}")


def main():
    parser = argparse.ArgumentParser(description="Run baseline evaluations")
    parser.add_argument("--output", type=str, default="baseline_results.json",
                       help="Output JSON file for results")
    parser.add_argument("--summary-only", action="store_true",
                       help="Only print summary, don't save detailed results")

    args = parser.parse_args()

    evaluator = BaselineEvaluator()
    results = evaluator.run_all_evaluations()

    evaluator.print_summary(results)

    if not args.summary_only:
        evaluator.save_results(results, args.output)


if __name__ == "__main__":
    main()