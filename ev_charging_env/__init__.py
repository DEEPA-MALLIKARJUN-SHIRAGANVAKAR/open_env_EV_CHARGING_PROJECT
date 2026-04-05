"""
EV Charging Scheduler - Production OpenEnv Environment

A sophisticated multi-objective optimization environment for electric vehicle
charging scheduling with dynamic pricing, grid constraints, and priority management.
"""

__version__ = "1.0.0"
__author__ = "AI Engineering Team"

from .env import EVChargingEnvironment, EVChargingEnvironmentWrapper
from .models import (
    EnvironmentConfig,
    Observation,
    ChargingAction,
    StepResult,
    VehicleStatus,
    ChargingStationStatus,
    GridStatus,
)
from .tasks import (
    Task,
    TaskGrader,
    TaskResult,
    create_easy_task,
    create_medium_task,
    create_hard_task,
)
from .baselines import (
    BaseAgent,
    RandomAgent,
    GreedyAgent,
    PriorityAwareAgent,
    OptimalSearchAgent,
)

__all__ = [
    "EVChargingEnvironment",
    "EVChargingEnvironmentWrapper",
    "EnvironmentConfig",
    "Observation",
    "ChargingAction",
    "StepResult",
    "VehicleStatus",
    "ChargingStationStatus",
    "GridStatus",
    "Task",
    "TaskGrader",
    "TaskResult",
    "create_easy_task",
    "create_medium_task",
    "create_hard_task",
    "BaseAgent",
    "RandomAgent",
    "GreedyAgent",
    "PriorityAwareAgent",
    "OptimalSearchAgent",
]
