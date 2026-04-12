"""\nAdvanced graders with LLM evaluation for EV Charging Scheduler.\n"""

from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
import os
from ..env import EVChargingEnvironment
from ..models import Observation


class LLMEvaluator:
    """LLM-based evaluation for nuanced task assessment."""
    
    def __init__(self):
        self.api_key = os.getenv("API_KEY")
        self.api_base = os.getenv("API_BASE_URL")
        self.client = None
        if self.api_key and self.api_base:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key, base_url=self.api_base)
            except ImportError:
                pass
    
    def evaluate_task(self, task_name: str, env: EVChargingEnvironment, final_obs: Observation) -> Tuple[float, str]:
        """Use LLM to evaluate task performance and provide feedback."""
        if not self.client:
            return 0.5, "LLM evaluation unavailable - OpenAI API not configured"
        
        # Prepare evaluation prompt
        prompt = f"""
You are an expert evaluator for electric vehicle charging optimization tasks.

TASK: {task_name.upper()} Difficulty
EVALUATION CRITERIA:
- Strategic decision making in resource allocation
- Balance between cost, efficiency, and reliability  
- Adaptability to dynamic conditions (pricing, grid load)
- Priority management for urgent vehicles
- Risk management (avoiding grid overload, deadline misses)

PERFORMANCE SUMMARY:
- Vehicles Charged: {sum(1 for v in env.vehicles.values() if v.fully_charged)}/{len(env.vehicles)}
- Total Cost: ${env.total_cost:.2f}
- Steps Taken: {env.time_step}/{env.config.max_steps}
- Grid Load: {final_obs.grid.current_load:.1%}
- Missed Deadlines: {sum(1 for v in env.vehicles.values() if not v.fully_charged and env.time_step > v.deadline)}

Rate the agent's performance on a scale of 0.0 to 1.0, where:
- 1.0 = Excellent strategic optimization, perfect balance of objectives
- 0.8 = Good performance with minor inefficiencies
- 0.6 = Adequate performance, some objectives compromised
- 0.4 = Poor performance, major issues in multiple areas
- 0.2 = Very poor, fundamental strategy flaws
- 0.0 = Complete failure, no meaningful progress

Format: SCORE: X.X
FEEDBACK: [your analysis]
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300,
            )
            
            response_text = response.choices[0].message.content
            
            lines = response_text.split('\n')
            score = 0.5
            feedback = "LLM evaluation parsing failed"
            
            for line in lines:
                if line.startswith('SCORE:'):
                    try:
                        score = float(line.split(':')[1].strip())
                        score = max(0.0, min(1.0, score))
                    except:
                        pass
                elif line.startswith('FEEDBACK:'):
                    feedback = line.split(':', 1)[1].strip()
            
            return score, feedback
            
        except Exception as e:
            return 0.5, f"LLM evaluation error: {str(e)}"


@dataclass
class TaskResult:
    """Result of a completed task."""
    task_name: str
    score: float
    details: Dict[str, Any]
    episode_reward: float
    steps_taken: int
    vehicles_charged: int
    missed_deadlines: int
    grid_overloads: int
    total_cost: float
    llm_score: float = 0.0
    llm_feedback: str = ""


class TaskGrader:
    """Deterministic task grader with multi-objective scoring."""

    @staticmethod
    def grade_easy(env: EVChargingEnvironment, final_obs: Observation) -> float:
        vehicles_charged = sum(1 for v in env.vehicles.values() if v.fully_charged)
        total_vehicles = len(env.vehicles)
        completion_ratio = vehicles_charged / total_vehicles if total_vehicles > 0 else 0.0
        energy_efficiency = min(1.0, (total_vehicles * 15.0) / max(0.1, env.total_energy_used))
        time_efficiency = max(0.0, 1.0 - (env.time_step / env.config.max_steps))
        return 0.6 * completion_ratio + 0.3 * energy_efficiency + 0.1 * time_efficiency

    @staticmethod
    def grade_medium(env: EVChargingEnvironment, final_obs: Observation) -> float:
        vehicles_charged = sum(1 for v in env.vehicles.values() if v.fully_charged)
        total_vehicles = len(env.vehicles)
        completion_ratio = vehicles_charged / total_vehicles if total_vehicles > 0 else 0.0
        cost_score = max(0.0, 1.0 - env.total_cost / 50.0)
        grid_penalty = 0.2 if final_obs.grid.current_load > final_obs.grid.max_load else 0.0
        deadline_score = max(0.0, 1.0 - sum(1 for v in env.vehicles.values() if env.time_step > v.deadline and not v.fully_charged) * 0.1)
        return 0.4 * completion_ratio + 0.35 * cost_score + 0.15 * (1.0 - grid_penalty) + 0.1 * deadline_score

    @staticmethod
    def grade_hard(env: EVChargingEnvironment, final_obs: Observation) -> float:
        vehicles_charged = sum(1 for v in env.vehicles.values() if v.fully_charged)
        total_vehicles = len(env.vehicles)
        completion_ratio = vehicles_charged / total_vehicles if total_vehicles > 0 else 0.0
        cost_score = max(0.0, 1.0 - env.total_cost / 75.0)
        urgent_charged = sum(1 for v in env.vehicles.values() if v.fully_charged and v.priority == "URGENT")
        urgent_score = urgent_charged / max(1, sum(1 for v in env.vehicles.values() if v.priority == "URGENT"))
        missed_deadlines = sum(1 for v in env.vehicles.values() if env.time_step > v.deadline and not v.fully_charged)
        deadline_score = max(0.0, 1.0 - missed_deadlines * 0.15)
        grid_score = max(0.0, 1.0 - (1 if final_obs.grid.current_load > final_obs.grid.max_load else 0) * 0.3)
        energy_efficiency = min(1.0, (total_vehicles * 40.0) / max(0.1, env.total_energy_used))
        return 0.3 * completion_ratio + 0.2 * cost_score + 0.2 * urgent_score + 0.15 * deadline_score + 0.1 * grid_score + 0.05 * energy_efficiency
