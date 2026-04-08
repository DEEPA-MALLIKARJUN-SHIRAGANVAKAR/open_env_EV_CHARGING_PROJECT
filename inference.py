"""
Inference script for EV Charging Scheduler Environment.
Runs all three task difficulties and evaluates agent performance using OpenAI API.
"""

import json
import os
import sys
from typing import Dict, Any, List

try:
    from openai import OpenAI
except ImportError:
    print("OpenAI library not installed. Install with: pip install openai")
    sys.exit(1)

from ev_charging_env import (
    create_easy_task,
    create_medium_task,
    create_hard_task,
    RandomAgent,
    GreedyAgent,
    PriorityAwareAgent,
    OptimalSearchAgent,
)


def emit_block(tag: str, **fields: Any) -> None:
    """Print validator-friendly structured output to stdout."""
    ordered = " ".join(f"{key}={fields[key]}" for key in fields)
    print(f"[{tag}] {ordered}".rstrip(), flush=True)


def get_api_credentials() -> tuple[str | None, str | None]:
    """Return proxy-compatible API credentials from environment."""
    api_key = os.getenv("API_KEY")
    api_base = os.getenv("API_BASE_URL")
    return api_key, api_base


class InferenceRunner:
    """Run EV Charging environment with OpenAI API-based agent."""

    def __init__(self, model: str = None, seed: int = None):
        """Initialize with OpenAI client and environment variables support."""
        self.api_key, api_base = get_api_credentials()
        if not self.api_key or not api_base:
            raise ValueError("API_KEY and API_BASE_URL environment variables must be set")

        # Model configuration with environment variable support
        self.model = model or os.getenv("MODEL_NAME", "gpt-4")

        self.client = OpenAI(api_key=self.api_key, base_url=api_base)

        # HF_TOKEN support (for HuggingFace models if needed)
        self.hf_token = os.getenv("HF_TOKEN")

        # Reproducibility settings
        self.seed = seed
        self.temperature = 0.0  # Deterministic for reproducibility

        # Conversation history (limited for performance)
        self.conversation_history = []
        self.max_history_length = 6  # Reduced from 10 for performance

    def run_task(self, task_name: str, task, max_runtime_minutes: int = 15) -> Dict[str, Any]:
        """Run a single task with OpenAI agent and return results.

        Args:
            task_name: Name of the task (easy/medium/hard)
            task: Task instance to run
            max_runtime_minutes: Maximum runtime to prevent hanging

        Returns:
            Dictionary with task results and metrics
        """
        import time
        start_time = time.time()
        max_runtime_seconds = max_runtime_minutes * 60

        print(f"\n{'='*60}")
        print(f"Running {task_name.upper()} Task")
        print(f"Model: {self.model} | Temperature: {self.temperature}")
        print('='*60)

        self.conversation_history = []
        obs = task.reset()
        total_reward = 0.0
        step_count = 0
        api_call_count = 0

        emit_block("START", task=task_name, max_steps=task.config.max_steps)
        
        # Initial prompt to set up the task context
        initial_prompt = f"""You are an expert AI agent optimizing electric vehicle charging schedules.

MISSION: {task_name.upper()} difficulty task
- Minimize electricity costs
- Avoid grid overload (>80% capacity)
- Meet vehicle charging deadlines
- Prioritize urgent vehicles (marked as "urgent")

CURRENT ENVIRONMENT:
- Max Steps: {task.config.max_steps}
- Vehicles: {len(obs['vehicles'])}
- Charging Stations: {len(obs['stations'])}
- Grid Capacity: ~80% safe limit

STATE INFORMATION:
- Time Step: {obs['time_step']}/{task.config.max_steps}
- Grid Load: {obs['grid']['current_load']:.1%}
- Electricity Price: ${obs['grid']['electricity_price']:.3f}/kWh

VEHICLES:
{chr(10).join(f"- V{v['id']}: {v['battery_level']:.0%} charge, deadline T{v['deadline']}, priority {v['priority']}" for v in obs['vehicles'][:8])}

STATIONS:
{chr(10).join(f"- S{s['id']}: {s['occupied_slots']}/{s['max_slots']} slots, {s['available_power']:.1f}kW available" for s in obs['stations'][:6])}

REQUIRED ACTION FORMAT (respond with valid JSON only):
{{
    "action_type": "assign" | "delay" | "release" | "power_level",
    "vehicle_id": <integer>,
    "station_id": <integer, required for assign/release/power_level>,
    "power_level": <float 0.0-1.0, default 1.0>,
    "reasoning": "<brief strategy explanation>"
}}

Choose your first action now:"""
        
        self.conversation_history.append({
            "role": "user",
            "content": initial_prompt
        })
        
        # Execute steps with runtime and error safeguards
        max_steps = task.config.max_steps
        consecutive_errors = 0
        max_consecutive_errors = 5

        for step in range(max_steps):
            # Runtime check
            elapsed = time.time() - start_time
            if elapsed > max_runtime_seconds:
                print(f"  Runtime limit ({max_runtime_minutes}min) exceeded. Stopping early.")
                break

            try:
                # Get action from OpenAI
                action_dict = self._get_openai_action()
                api_call_count += 1

                # Execute step
                result = task.step(action_dict)
                step_count += 1
                total_reward = result.reward if step == 0 else total_reward + result.reward
                consecutive_errors = 0  # Reset error counter

                # Update conversation context (limit history for performance)
                next_obs = result.observation
                update_prompt = f"""ACTION RESULT:
- Executed: {action_dict['action_type']} (vehicle {action_dict['vehicle_id']})
- Reward: {result.reward:+.3f}
- New Grid Load: {next_obs['grid']['current_load']:.1%}
- Price: ${next_obs['grid']['electricity_price']:.3f}/kWh
- Progress: {sum(1 for v in next_obs['vehicles'] if v['fully_charged'])}/{len(next_obs['vehicles'])} charged

Choose next action (respond with JSON only):"""

                self.conversation_history.append({
                    "role": "assistant",
                    "content": json.dumps(action_dict, indent=2)
                })
                self.conversation_history.append({
                    "role": "user",
                    "content": update_prompt
                })

                # Limit conversation history for performance
                if len(self.conversation_history) > self.max_history_length:
                    # Keep initial prompt + recent messages
                    self.conversation_history = (
                        self.conversation_history[:2] +  # Initial prompt
                        self.conversation_history[-self.max_history_length:]
                    )

                # Print progress every 10 steps or at key milestones
                if (step + 1) % 10 == 0 or step == 0:
                    charged = sum(1 for v in next_obs['vehicles'] if v['fully_charged'])
                    print(f"  Step {step+1:3d}/{max_steps}: Reward={result.reward:+6.3f}, "
                          f"Grid={next_obs['grid']['current_load']:.1%}, "
                          f"Charged={charged}/{len(next_obs['vehicles'])}, "
                          f"API calls={api_call_count}")
                emit_block(
                    "STEP",
                    task=task_name,
                    step=step_count,
                    reward=round(result.reward, 4),
                    done=result.done,
                )

                if result.done or result.info.get("done", False):
                    print(f"  Task completed at step {step+1}")
                    break

            except Exception as e:
                consecutive_errors += 1
                print(f"  Error at step {step+1}: {e} (error {consecutive_errors}/{max_consecutive_errors})")

                if consecutive_errors >= max_consecutive_errors:
                    print(f"  Too many consecutive errors. Stopping task.")
                    break

                # Fallback to safe action
                try:
                    fallback_action = {
                        "action_type": "delay",
                        "vehicle_id": 0,
                        "duration": 1
                    }
                    result = task.step(fallback_action)
                    step_count += 1
                    print(f"  Using fallback action: {fallback_action}")
                    emit_block(
                        "STEP",
                        task=task_name,
                        step=step_count,
                        reward=round(result.reward, 4),
                        done=result.done,
                    )
                except Exception as fallback_error:
                    print(f"  Fallback action also failed: {fallback_error}")
                    break

                continue
        
        # Grade the task
        grade_result = task.grade(use_llm=False)  # Skip LLM grading for speed

        elapsed_time = time.time() - start_time

        results = {
            "task_name": task_name,
            "score": grade_result.score,
            "episode_reward": grade_result.episode_reward,
            "steps_taken": grade_result.steps_taken,
            "vehicles_charged": grade_result.vehicles_charged,
            "missed_deadlines": grade_result.missed_deadlines,
            "grid_overloads": grade_result.grid_overloads,
            "total_cost": grade_result.total_cost,
            "api_calls": api_call_count,
            "elapsed_time_seconds": round(elapsed_time, 2),
            "details": grade_result.details,
        }

        print(f"\nTask Complete!")
        print(f"  Score: {results['score']:.3f}")
        print(f"  Vehicles Charged: {results['vehicles_charged']}")
        print(f"  Total Cost: ${results['total_cost']:.2f}")
        print(f"  API Calls: {api_call_count}")
        print(f"  Runtime: {elapsed_time:.1f}s")
        emit_block(
            "END",
            task=task_name,
            score=round(results["score"], 4),
            steps=results["steps_taken"],
        )

        return results

    def _get_openai_action(self) -> Dict[str, Any]:
        """Get validated action from OpenAI API with robust error handling.

        Returns:
            Validated action dictionary with fallback safety
        """
        max_retries = 3
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                # Use limited conversation history for performance
                messages = self.conversation_history[-self.max_history_length:]

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,  # Deterministic
                    max_tokens=300,  # Increased for better responses
                    seed=self.seed,  # Reproducibility if supported
                )

                response_text = response.choices[0].message.content
                action = self._parse_and_validate_action(response_text)

                if action:
                    return action
                else:
                    print(f"    Attempt {attempt+1}: Invalid action format, retrying...")

            except Exception as e:
                print(f"    Attempt {attempt+1}: API error: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(base_delay * (2 ** attempt))  # Exponential backoff

        # All retries failed, use safe fallback
        print("    All API attempts failed, using safe fallback action")
        return self._get_safe_fallback_action()

    def _parse_and_validate_action(self, response_text: str) -> Dict[str, Any]:
        """Parse and validate JSON action from LLM response.

        Args:
            response_text: Raw text response from LLM

        Returns:
            Validated action dictionary or None if invalid
        """
        try:
            # Extract JSON if embedded in text
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                return None

            action = json.loads(json_match.group())

            # Validate required fields
            if not isinstance(action.get("action_type"), str):
                return None
            if not isinstance(action.get("vehicle_id"), int):
                return None

            # Validate action types
            valid_action_types = ["assign", "delay", "release", "power_level"]
            if action["action_type"] not in valid_action_types:
                return None

            # Set defaults and validate based on action type
            if action["action_type"] == "assign":
                if not isinstance(action.get("station_id"), int):
                    action["station_id"] = 0
                action["power_level"] = max(0.0, min(1.0, action.get("power_level", 1.0)))
            elif action["action_type"] == "power_level":
                if not isinstance(action.get("station_id"), int):
                    action["station_id"] = 0
                action["power_level"] = max(0.0, min(1.0, action.get("power_level", 1.0)))
            elif action["action_type"] == "delay":
                action["duration"] = max(1, action.get("duration", 1))
            elif action["action_type"] == "release":
                if not isinstance(action.get("station_id"), int):
                    action["station_id"] = 0

            return action

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"    JSON parsing/validation error: {e}")
            return None

    def _get_safe_fallback_action(self) -> Dict[str, Any]:
        """Get a safe fallback action when all else fails."""
        return {
            "action_type": "delay",
            "vehicle_id": 0,
            "duration": 1
        }


def output_results(task_results: List[Dict[str, Any]], output_file: str = None):
    """Output results in both console and JSON formats.

    Args:
        task_results: List of task result dictionaries or dict of baseline results
        output_file: Optional JSON file path to save results
    """
    print("\n" + "="*70)
    print("FINAL RESULTS SUMMARY")
    print("="*70)

    scores = {}
    total_score = 0.0
    valid_tasks = 0

    # Handle both list format (API results) and dict format (baseline results)
    if isinstance(task_results, dict):
        # Baseline results: {task_name: {agent_name: {score, ...}}}
        for task_name, agents in task_results.items():
            print(f"\n{task_name.upper()}:")
            for agent_name, metrics in agents.items():
                score = metrics.get('score', 0.0)
                print(f"  {agent_name}: {score:.3f}")
                scores[f"{task_name}_{agent_name}"] = round(score, 4)
                total_score += score
                valid_tasks += 1
    else:
        # API results: list of {task_name, score, error?, ...}
        for result in task_results:
            if isinstance(result, dict):
                task_name = result.get('task_name', 'unknown')
                if "error" not in result:
                    score = result.get('score', 0.0)
                    status = "[OK]"
                    total_score += score
                    valid_tasks += 1
                else:
                    score = 0.0
                    status = "[ERR]"

                print(f"{status} {task_name.upper():8s}: {score:.4f}")
                scores[task_name] = round(score, 4)

                # Show additional metrics if available
                if "api_calls" in result:
                    print(f"    API Calls: {result['api_calls']}, "
                          f"Runtime: {result.get('elapsed_time_seconds', 0):.1f}s")

    # Calculate average
    if valid_tasks > 0:
        avg_score = round(total_score / valid_tasks, 4)
        scores["average"] = avg_score
        print(f"\nAVG {'AVERAGE':8s}: {avg_score:.4f}")
    else:
        scores["average"] = 0.0
        print(f"\nERR {'AVERAGE':8s}: 0.0000 (no valid tasks)")

    print("\n" + "="*70)
    print("SCORING INFORMATION")
    print("="*70)
    print("- Scores are normalized to [0.0, 1.0]")
    print("- 1.0 = Perfect performance on task")
    print("- 0.0 = No progress made")
    print("- Average = Mean across all valid tasks")

    # JSON output
    if output_file:
        try:
            with open(output_file, 'w') as f:
                json.dump(scores, f, indent=2)
            print(f"\nResults saved to: {output_file}")
        except Exception as e:
            print(f"\nError saving to {output_file}: {e}")

    # Always print JSON to stdout for easy parsing
    print(f"\nJSON Output: {json.dumps(scores, indent=None)}")


def run_baseline_agents() -> Dict[str, Dict[str, float]]:
    """Run all baseline agents on all tasks for comparison."""
    print("\n" + "="*60)
    print("BASELINE AGENT PERFORMANCE")
    print("="*60)

    agents = {
        "random": RandomAgent(),
        "greedy": GreedyAgent(),
        "priority": PriorityAwareAgent(),
        "optimal_search": OptimalSearchAgent(),
    }

    tasks = {
        "easy": create_easy_task(),
        "medium": create_medium_task(),
        "hard": create_hard_task(),
    }

    results = {}

    for task_name, task in tasks.items():
        print(f"\n{task_name.upper()} TASK:")
        results[task_name] = {}

        for agent_name, agent in agents.items():
            obs = task.reset()
            step_count = 0
            max_steps = task.config.max_steps
            emit_block("START", task=f"{task_name}_{agent_name}", max_steps=max_steps)

            while step_count < max_steps and obs is not None:
                action = agent.get_action(obs)
                step_result = task.step(action)
                obs = step_result.observation
                step_count += 1
                emit_block(
                    "STEP",
                    task=f"{task_name}_{agent_name}",
                    step=step_count,
                    reward=round(step_result.reward, 4),
                    done=step_result.done,
                )

                if step_result.done or step_result.info.get("done", False):
                    break

            grade = task.grade()
            results[task_name][agent_name] = {
                "score": grade.score,
                "vehicles_charged": grade.vehicles_charged,
                "total_cost": grade.total_cost,
            }

            print(f"  {agent_name:15s}: {grade.score:.3f} "
                  f"(charged {grade.vehicles_charged}, cost ${grade.total_cost:.2f})")
            emit_block(
                "END",
                task=f"{task_name}_{agent_name}",
                score=round(grade.score, 4),
                steps=step_count,
            )

    return results


def main():
    """Main inference runner with improved argument parsing and output."""
    import argparse

    parser = argparse.ArgumentParser(description="EV Charging Scheduler - OpenAI Inference")
    parser.add_argument("--model", type=str, default=None,
                       help="Model name (default: from MODEL_NAME env var or gpt-4)")
    parser.add_argument("--seed", type=int, default=None,
                       help="Random seed for reproducibility")
    parser.add_argument("--max-runtime", type=int, default=15,
                       help="Maximum runtime per task in minutes (default: 15)")
    parser.add_argument("--output-json", type=str, default=None,
                       help="Output results to JSON file")
    args = parser.parse_args()

    print("\n" + "="*70)
    print("EV CHARGING SCHEDULER - OPENAI INFERENCE EVALUATION")
    print("="*70)

    # Check for proxy credentials
    api_key, api_base = get_api_credentials()
    if not api_key or not api_base:
        print("\nERROR: API_KEY and API_BASE_URL environment variables are required.")
        print("This runner must use the injected LiteLLM proxy and will not fall back.")
        sys.exit(1)

    # Run with OpenAI API
    print(f"\nUsing OpenAI API with model: {args.model or os.getenv('MODEL_NAME', 'gpt-4')}")
    print(f"Using API_BASE_URL: {api_base}")
    print(f"Reproducibility seed: {args.seed}")
    print(f"Max runtime per task: {args.max_runtime} minutes")
    print(f"Estimated total runtime: {args.max_runtime * 3} minutes\n")

    try:
        runner = InferenceRunner(model=args.model, seed=args.seed)
        task_results = []

        # Run all three tasks with error handling
        tasks = [
            ("easy", create_easy_task),
            ("medium", create_medium_task),
            ("hard", create_hard_task)
        ]

        for task_name, task_func in tasks:
            try:
                print(f"\nStarting {task_name.upper()} task...")
                task = task_func()
                result = runner.run_task(task_name, task, args.max_runtime)
                task_results.append(result)
            except Exception as e:
                print(f"Error running {task_name} task: {e}")
                task_results.append({
                    "task_name": task_name,
                    "score": 0.0,
                    "error": str(e),
                    "api_calls": 0,
                    "elapsed_time_seconds": 0
                })

        # Output results
        output_results(task_results, args.output_json)

    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
