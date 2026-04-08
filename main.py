from typing import Any, Dict, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from ev_charging_env import EVChargingEnvironmentWrapper, EnvironmentConfig
from ev_charging_env.tasks import TaskGrader, create_easy_task, create_medium_task, create_hard_task


class ResetRequest(BaseModel):
    task_id: Optional[str] = None
    num_vehicles: Optional[int] = Field(default=None, ge=1)
    num_stations: Optional[int] = Field(default=None, ge=1)
    max_steps: Optional[int] = Field(default=None, ge=10)
    slots_per_station: Optional[int] = Field(default=None, ge=1)
    max_power_per_station: Optional[float] = Field(default=None, gt=0)
    max_grid_load: Optional[float] = Field(default=None, gt=0)
    base_electricity_price: Optional[float] = Field(default=None, gt=0)
    price_volatility: Optional[float] = Field(default=None, ge=0)
    seed: Optional[int] = None


class StepRequest(BaseModel):
    action_type: str
    vehicle_id: int
    station_id: Optional[int] = None
    power_level: float = 1.0
    duration: int = 1


def _clean_config(data: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}


app = FastAPI(title="EV Charging Scheduler OpenEnv API", version="1.0.0")
env = EVChargingEnvironmentWrapper()
current_task_id = "task_1"

TASKS_METADATA = [
    {
        "id": "task_1",
        "name": "easy_charging",
        "difficulty": "easy",
        "description": "Basic charging with relaxed constraints.",
        "grader": True,
        "grader_entrypoint": "ev_charging_env.tasks:grade_easy_score",
    },
    {
        "id": "task_2",
        "name": "medium_charging",
        "difficulty": "medium",
        "description": "Charging with dynamic pricing and grid constraints.",
        "grader": True,
        "grader_entrypoint": "ev_charging_env.tasks:grade_medium_score",
    },
    {
        "id": "task_3",
        "name": "hard_charging",
        "difficulty": "hard",
        "description": "Tight multi-objective optimization with urgent vehicles.",
        "grader": True,
        "grader_entrypoint": "ev_charging_env.tasks:grade_hard_score",
    },
]

TASK_CONFIGS = {
    "task_1": create_easy_task().config,
    "task_2": create_medium_task().config,
    "task_3": create_hard_task().config,
}


@app.get("/")
def root() -> Dict[str, Any]:
    return {
        "name": "EV Charging Scheduler",
        "openenv": True,
        "endpoints": {
            "reset": "POST /reset",
            "step": "POST /step",
            "state": "GET /state or POST /state",
            "health": "GET /health",
        },
    }


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/tasks")
def list_tasks() -> Dict[str, Any]:
    return {"tasks": TASKS_METADATA}


@app.get("/validate")
def validate_repo_shape() -> Dict[str, Any]:
    tasks_with_graders = sum(1 for task in TASKS_METADATA if task.get("grader"))
    return {
        "valid": tasks_with_graders >= 3,
        "checks": {
            "min_tasks": len(TASKS_METADATA) >= 3,
            "tasks_with_graders": tasks_with_graders,
            "all_tasks_have_graders": tasks_with_graders == len(TASKS_METADATA),
        },
    }


@app.post("/reset")
def reset_environment(request: Optional[ResetRequest] = None) -> Dict[str, Any]:
    global env, current_task_id

    if request is None:
        return env.reset()

    # Task-specific reset for validator compatibility
    if request.task_id in TASK_CONFIGS:
        current_task_id = request.task_id or "task_1"
        env = EVChargingEnvironmentWrapper(TASK_CONFIGS[current_task_id])
        return env.reset()

    config_data = _clean_config(request.model_dump())
    config_data.pop("task_id", None)
    if config_data:
        env = EVChargingEnvironmentWrapper(EnvironmentConfig(**config_data))

    return env.reset()


@app.get("/state")
def get_state() -> Dict[str, Any]:
    return env.env.state().to_dict()


@app.post("/state")
def post_state() -> Dict[str, Any]:
    return env.env.state().to_dict()


@app.post("/step")
def step_environment(action: StepRequest) -> Dict[str, Any]:
    observation, reward, done, info = env.step(action.model_dump())
    return {
        "observation": observation,
        "reward": reward,
        "done": done,
        "info": info,
    }


@app.get("/grade")
def grade_current_task() -> Dict[str, Any]:
    final_obs = env.env.state()
    if current_task_id == "task_1":
        result = TaskGrader.grade_easy(env.env, final_obs, use_llm=False)
    elif current_task_id == "task_2":
        result = TaskGrader.grade_medium(env.env, final_obs, use_llm=False)
    else:
        result = TaskGrader.grade_hard(env.env, final_obs, use_llm=False)
    return {
        "task_id": current_task_id,
        "score": float(result.score),
        "steps_taken": int(result.steps_taken),
        "vehicles_charged": int(result.vehicles_charged),
    }
