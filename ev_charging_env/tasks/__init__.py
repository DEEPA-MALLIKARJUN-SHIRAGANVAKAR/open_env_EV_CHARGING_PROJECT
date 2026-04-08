"""
Task definitions and graders for EV Charging Scheduler.
Provides easy, medium, and hard difficulty levels with deterministic grading.
"""

from typing import Dict, Any, List
from dataclasses import dataclass
import os
from ..env import EVChargingEnvironment
from ..models import EnvironmentConfig, Observation


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
    
    def evaluate_task(self, task_name: str, env: EVChargingEnvironment, final_obs: Observation) -> tuple[float, str]:
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

Provide a score and brief feedback explaining the rating.
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
            
            # Parse score and feedback
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
    score: float  # 0.0 to 1.0
    details: Dict[str, Any]
    episode_reward: float
    steps_taken: int
    vehicles_charged: int
    missed_deadlines: int
    grid_overloads: int
    total_cost: float
    llm_score: float = 0.0  # LLM-based evaluation score
    llm_feedback: str = ""  # LLM feedback text


class TaskGrader:
    """Deterministic task grader with multi-objective scoring."""

    def __init__(self):
        self.llm_evaluator = LLMEvaluator()

    @staticmethod
    def grade_easy(env: EVChargingEnvironment, final_obs: Observation, use_llm: bool = True) -> TaskResult:
        """
        EASY TASK: Basic charging with no dynamic pricing or grid constraints.
        
        Goal: Charge vehicles efficiently with minimal complexity.
        Grading: 60% completion, 30% efficiency, 10% time
        """
        vehicles_charged = sum(1 for v in env.vehicles.values() if v.fully_charged)
        total_vehicles = len(env.vehicles)
        completion_ratio = vehicles_charged / total_vehicles if total_vehicles > 0 else 0.0
        
        # Efficiency: use less energy and cost
        avg_battery_initial = 0.4  # Typical initial battery
        total_charge_needed = (total_vehicles * 0.3) * 50.0  # energy in kWh
        energy_efficiency = min(1.0, total_charge_needed / max(0.1, env.total_energy_used))
        
        # Time efficiency: complete faster
        time_efficiency = max(0.0, 1.0 - (env.time_step / env.config.max_steps))
        
        score = (
            completion_ratio * 0.6
            + energy_efficiency * 0.3
            + time_efficiency * 0.1
        )
        
        missed_deadlines = sum(
            1 for v in env.vehicles.values()
            if not v.fully_charged and env.time_step > v.deadline
        )
        
        # LLM evaluation
        llm_score = 0.0
        llm_feedback = ""
        if use_llm:
            grader = TaskGrader()
            llm_score, llm_feedback = grader.llm_evaluator.evaluate_task("easy", env, final_obs)
        
        # Combine programmatic and LLM scores (70% programmatic, 30% LLM)
        final_score = score * 0.7 + llm_score * 0.3
        
        return TaskResult(
            task_name="easy",
            score=max(0.0, min(1.0, final_score)),
            details={
                "completion_ratio": completion_ratio,
                "energy_efficiency": energy_efficiency,
                "time_efficiency": time_efficiency,
                "programmatic_score": score,
            },
            episode_reward=env.episode_reward,
            steps_taken=env.time_step,
            vehicles_charged=vehicles_charged,
            missed_deadlines=missed_deadlines,
            grid_overloads=0,  # Easy task has no grid constraints
            total_cost=env.total_cost,
            llm_score=llm_score,
            llm_feedback=llm_feedback,
        )

    @staticmethod
    def grade_medium(env: EVChargingEnvironment, final_obs: Observation, use_llm: bool = True) -> TaskResult:
        """
        MEDIUM TASK: Charging with dynamic pricing and mild grid constraints.
        
        Goal: Minimize cost while charging vehicles, avoid grid overload.
        Grading: 40% completion, 35% cost optimization, 15% grid management, 10% deadlines
        """
        vehicles_charged = sum(1 for v in env.vehicles.values() if v.fully_charged)
        total_vehicles = len(env.vehicles)
        completion_ratio = vehicles_charged / total_vehicles if total_vehicles > 0 else 0.0
        
        # Cost optimization (lower is better)
        # Baseline: ~$50 for full environment
        baseline_cost = 50.0
        cost_ratio = env.total_cost / baseline_cost if baseline_cost > 0 else 1.0
        cost_score = max(0.0, 1.0 - cost_ratio)  # Reward lower cost
        
        # Grid management: track overload events
        # Simulated by checking if grid load exceeded max frequently
        grid_overload_penalty = 0.0
        if final_obs.grid.current_load > final_obs.grid.max_load:
            grid_overload_penalty = 0.2
        
        # Deadline adherence
        missed_deadlines = sum(
            1 for v in env.vehicles.values()
            if not v.fully_charged and env.time_step > v.deadline
        )
        deadline_score = max(0.0, 1.0 - (missed_deadlines * 0.1))
        
        score = (
            completion_ratio * 0.4
            + cost_score * 0.35
            + (1.0 - grid_overload_penalty) * 0.15
            + deadline_score * 0.1
        )
        
        # LLM evaluation
        llm_score = 0.0
        llm_feedback = ""
        if use_llm:
            grader = TaskGrader()
            llm_score, llm_feedback = grader.llm_evaluator.evaluate_task("medium", env, final_obs)
        
        # Combine programmatic and LLM scores (70% programmatic, 30% LLM)
        final_score = score * 0.7 + llm_score * 0.3
        
        return TaskResult(
            task_name="medium",
            score=max(0.0, min(1.0, final_score)),
            details={
                "completion_ratio": completion_ratio,
                "cost_score": cost_score,
                "cost_total": env.total_cost,
                "deadline_score": deadline_score,
                "programmatic_score": score,
            },
            episode_reward=env.episode_reward,
            steps_taken=env.time_step,
            vehicles_charged=vehicles_charged,
            missed_deadlines=missed_deadlines,
            grid_overloads=1 if final_obs.grid.current_load > final_obs.grid.max_load else 0,
            total_cost=env.total_cost,
            llm_score=llm_score,
            llm_feedback=llm_feedback,
        )

    @staticmethod
    def grade_hard(env: EVChargingEnvironment, final_obs: Observation, use_llm: bool = True) -> TaskResult:
        """
        HARD TASK: Complex scenario with grid overload penalties, urgent vehicles,
        tight deadlines, and stochastic arrivals.
        
        Goal: Maximize utility through balanced multi-objective optimization.
        Grading: 30% completion, 20% cost, 20% urgent priority, 15% deadline,
                 10% grid management, 5% efficiency
        """
        vehicles_charged = sum(1 for v in env.vehicles.values() if v.fully_charged)
        total_vehicles = len(env.vehicles)
        completion_ratio = vehicles_charged / total_vehicles if total_vehicles > 0 else 0.0
        
        # Cost score
        baseline_cost = 75.0  # Hard task costs more
        cost_ratio = env.total_cost / baseline_cost if baseline_cost > 0 else 1.0
        cost_score = max(0.0, 1.0 - cost_ratio)
        
        # Urgent vehicle priority
        from ..models import PriorityLevel
        urgent_vehicles = [v for v in env.vehicles.values() if v.priority == PriorityLevel.URGENT]
        urgent_charged = sum(1 for v in urgent_vehicles if v.fully_charged)
        urgent_score = (urgent_charged / len(urgent_vehicles)) if urgent_vehicles else 1.0
        
        # Deadline adherence
        missed_deadlines = sum(
            1 for v in env.vehicles.values()
            if not v.fully_charged and env.time_step > v.deadline
        )
        deadline_score = max(0.0, 1.0 - (missed_deadlines * 0.15))
        
        # Grid management
        grid_overload_count = 1 if final_obs.grid.current_load > final_obs.grid.max_load else 0
        grid_score = max(0.0, 1.0 - grid_overload_count * 0.3)
        
        # Efficiency
        energy_efficiency = min(1.0, (total_vehicles * 40.0) / max(0.1, env.total_energy_used))
        
        score = (
            completion_ratio * 0.30
            + cost_score * 0.20
            + urgent_score * 0.20
            + deadline_score * 0.15
            + grid_score * 0.10
            + energy_efficiency * 0.05
        )
        
        # LLM evaluation
        llm_score = 0.0
        llm_feedback = ""
        if use_llm:
            grader = TaskGrader()
            llm_score, llm_feedback = grader.llm_evaluator.evaluate_task("hard", env, final_obs)
        
        # Combine programmatic and LLM scores (70% programmatic, 30% LLM)
        final_score = score * 0.7 + llm_score * 0.3
        
        return TaskResult(
            task_name="hard",
            score=max(0.0, min(1.0, final_score)),
            details={
                "completion_ratio": completion_ratio,
                "cost_score": cost_score,
                "urgent_score": urgent_score,
                "deadline_score": deadline_score,
                "grid_score": grid_score,
                "energy_efficiency": energy_efficiency,
                "programmatic_score": score,
            },
            episode_reward=env.episode_reward,
            steps_taken=env.time_step,
            vehicles_charged=vehicles_charged,
            missed_deadlines=missed_deadlines,
            grid_overloads=grid_overload_count,
            total_cost=env.total_cost,
            llm_score=llm_score,
            llm_feedback=llm_feedback,
        )


class Task:
    """Base task wrapper."""

    def __init__(self, name: str, difficulty: str, config: EnvironmentConfig):
        self.name = name
        self.difficulty = difficulty
        self.config = config
        self.env = EVChargingEnvironment(config)
        self.episode_steps = 0

    def reset(self) -> Observation:
        """Reset task environment."""
        self.episode_steps = 0
        return self.env.reset()

    def step(self, action: Dict[str, Any]) -> tuple:
        """Execute one step."""
        result = self.env.step(action)
        self.episode_steps += 1
        return result

    def grade(self, use_llm: bool = True) -> TaskResult:
        """Grade completed episode."""
        final_obs = self.env.state()
        
        if self.difficulty == "easy":
            return TaskGrader.grade_easy(self.env, final_obs, use_llm)
        elif self.difficulty == "medium":
            return TaskGrader.grade_medium(self.env, final_obs, use_llm)
        elif self.difficulty == "hard":
            return TaskGrader.grade_hard(self.env, final_obs, use_llm)
        
        raise ValueError(f"Unknown difficulty: {self.difficulty}")


def create_easy_task() -> Task:
    """Create easy difficulty task."""
    config = EnvironmentConfig(
        num_vehicles=5,
        num_stations=3,
        max_steps=150,
        slots_per_station=2,
        max_power_per_station=100.0,
        max_grid_load=2.0,  # No real constraint
        base_electricity_price=0.12,
        price_volatility=0.0,  # No price variation
        seed=42,
    )
    return Task("easy_charging", "easy", config)


def create_medium_task() -> Task:
    """Create medium difficulty task with dynamic pricing."""
    config = EnvironmentConfig(
        num_vehicles=10,
        num_stations=4,
        max_steps=180,
        slots_per_station=3,
        max_power_per_station=120.0,
        max_grid_load=1.2,
        base_electricity_price=0.15,
        price_volatility=0.3,
        seed=43,
    )
    return Task("medium_charging", "medium", config)


def create_hard_task() -> Task:
    """Create hard difficulty task with all constraints."""
    config = EnvironmentConfig(
        num_vehicles=15,
        num_stations=5,
        max_steps=200,
        slots_per_station=3,
        max_power_per_station=150.0,
        max_grid_load=1.0,  # Tight constraint
        base_electricity_price=0.18,
        price_volatility=0.5,
        seed=44,
    )
    return Task("hard_charging", "hard", config)


def _resolve_task_context(*args, **kwargs) -> tuple[EVChargingEnvironment, Observation]:
    """Resolve grader inputs to (env, final_obs) for validator compatibility."""
    if args:
        first = args[0]
        if isinstance(first, Task):
            env = first.env
            final_obs = env.state()
            return env, final_obs
        if isinstance(first, EVChargingEnvironment):
            env = first
            if len(args) > 1 and isinstance(args[1], Observation):
                return env, args[1]
            return env, env.state()

    task = kwargs.get("task")
    if isinstance(task, Task):
        env = task.env
        return env, env.state()

    env = kwargs.get("env")
    if isinstance(env, EVChargingEnvironment):
        final_obs = kwargs.get("final_obs")
        if isinstance(final_obs, Observation):
            return env, final_obs
        return env, env.state()

    raise ValueError("Unsupported grader input; expected Task or EVChargingEnvironment")


def grade_easy_task(*args, **kwargs) -> TaskResult:
    if not args and not kwargs:
        task = create_easy_task()
        task.reset()
        return TaskGrader.grade_easy(task.env, task.env.state(), use_llm=False)
    env, final_obs = _resolve_task_context(*args, **kwargs)
    return TaskGrader.grade_easy(env, final_obs, use_llm=False)


def grade_medium_task(*args, **kwargs) -> TaskResult:
    if not args and not kwargs:
        task = create_medium_task()
        task.reset()
        return TaskGrader.grade_medium(task.env, task.env.state(), use_llm=False)
    env, final_obs = _resolve_task_context(*args, **kwargs)
    return TaskGrader.grade_medium(env, final_obs, use_llm=False)


def grade_hard_task(*args, **kwargs) -> TaskResult:
    if not args and not kwargs:
        task = create_hard_task()
        task.reset()
        return TaskGrader.grade_hard(task.env, task.env.state(), use_llm=False)
    env, final_obs = _resolve_task_context(*args, **kwargs)
    return TaskGrader.grade_hard(env, final_obs, use_llm=False)


def grade_easy_score(*args, **kwargs) -> float:
    return float(grade_easy_task(*args, **kwargs).score)


def grade_medium_score(*args, **kwargs) -> float:
    return float(grade_medium_task(*args, **kwargs).score)


def grade_hard_score(*args, **kwargs) -> float:
    return float(grade_hard_task(*args, **kwargs).score)


__all__ = [
    "Task",
    "TaskGrader",
    "TaskResult",
    "create_easy_task",
    "create_medium_task",
    "create_hard_task",
    "grade_easy_task",
    "grade_medium_task",
    "grade_hard_task",
    "grade_easy_score",
    "grade_medium_score",
    "grade_hard_score",
]
