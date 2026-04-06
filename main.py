from typing import Any, Dict, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from ev_charging_env import EVChargingEnvironmentWrapper, EnvironmentConfig


class ResetRequest(BaseModel):
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


@app.post("/reset")
def reset_environment(request: Optional[ResetRequest] = None) -> Dict[str, Any]:
    global env

    if request is not None:
        config = EnvironmentConfig(**_clean_config(request.model_dump()))
        env = EVChargingEnvironmentWrapper(config)

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
