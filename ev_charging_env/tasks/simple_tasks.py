from typing import Any, Dict, Tuple, List

def _clamp_score(value: float) -> float:
    return max(0.0, min(1.0, float(value)))

def grade_easy(env, obs):
    \"\"\"Easy grader: completion ratio\"\"\"
    vehicles_charged = sum(1 for v in env.vehicles.values() if v.fully_charged)
    total = len(env.vehicles)
    return _clamp_score(vehicles_charged / total) if total > 0 else 0.0

def grade_medium(env, obs):
    \"\"\"Medium grader: completion + cost\"\"\"
    vehicles_charged = sum(1 for v in env.vehicles.values() if v.fully_charged)
    total = len(env.vehicles)
    cost_score = max(0.0, 1.0 - env.total_cost / 50.0)
    return _clamp_score(vehicles_charged / total * 0.6 + cost_score * 0.4) if total > 0 else 0.0

def grade_hard(env, obs):
    \"\"\"Hard grader: completion + deadlines + grid\"\"\"
    vehicles_charged = sum(1 for v in env.vehicles.values() if v.fully_charged)
    total = len(env.vehicles)
    missed = sum(1 for v in env.vehicles.values() if env.time_step > v.deadline and not v.fully_charged)
    deadline_score = max(0.0, 1.0 - missed * 0.1)
    grid_penalty = 0.3 if obs.grid.current_load > obs.grid.max_load else 0.0
    return _clamp_score((vehicles_charged / total * 0.5 + deadline_score * 0.3 + (1.0 - grid_penalty) * 0.2)) if total > 0 else 0.0

TASKS = [
    {"name": "easy_charging", "grader": grade_easy},
    {"name": "medium_charging", "grader": grade_medium},
    {"name": "hard_charging", "grader": grade_hard},
]

def create_easy_task():
    from ..models import EnvironmentConfig
    from ..env import EVChargingEnvironment
    config = EnvironmentConfig(
        num_vehicles=5,
        num_stations=3,
        max_steps=150,
        slots_per_station=2,
        max_power_per_station=100.0,
        max_grid_load=2.0,
        base_electricity_price=0.12,
        price_volatility=0.0,
        seed=42,
    )
    env = EVChargingEnvironment(config)
    env.task_name = "easy_charging"
    env.grader = grade_easy
    return env

def create_medium_task():
    from ..models import EnvironmentConfig
    from ..env import EVChargingEnvironment
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
    env = EVChargingEnvironment(config)
    env.task_name = "medium_charging"
    env.grader = grade_medium
    return env

def create_hard_task():
    from ..models import EnvironmentConfig
    from ..env import EVChargingEnvironment
    config = EnvironmentConfig(
        num_vehicles=15,
        num_stations=5,
        max_steps=200,
        slots_per_station=3,
        max_power_per_station=150.0,
        max_grid_load=1.0,
        base_electricity_price=0.18,
        price_volatility=0.5,
        seed=44,
    )
    env = EVChargingEnvironment(config)
    env.task_name = "hard_charging"
    env.grader = grade_hard
    return env

