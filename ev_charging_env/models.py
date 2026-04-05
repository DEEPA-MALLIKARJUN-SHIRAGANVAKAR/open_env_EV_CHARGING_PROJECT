"""
Pydantic models for EV Charging Scheduler Environment.
Defines all typed data structures for observations, actions, and game state.
"""

from typing import List, Dict, Literal, Optional
from pydantic import BaseModel, Field
from enum import Enum
import numpy as np


class PriorityLevel(str, Enum):
    """Vehicle priority levels."""
    NORMAL = "normal"
    URGENT = "urgent"


class VehicleStatus(BaseModel):
    """Status of a single EV vehicle."""
    id: int = Field(..., description="Unique vehicle identifier")
    battery_level: float = Field(..., ge=0.0, le=1.0, description="Current battery charge (0-1)")
    required_charge: float = Field(..., ge=0.0, le=1.0, description="Amount of charge needed (0-1)")
    deadline: int = Field(..., ge=0, description="Time step deadline for charging")
    priority: PriorityLevel = Field(default=PriorityLevel.NORMAL, description="Priority level")
    arrival_time: int = Field(..., ge=0, description="Time when vehicle arrived")
    fully_charged: bool = Field(default=False, description="Whether vehicle is fully charged")


class ChargingStationStatus(BaseModel):
    """Status of a charging station."""
    id: int = Field(..., description="Unique station identifier")
    max_slots: int = Field(..., ge=1, description="Maximum concurrent charging slots")
    max_power: float = Field(..., gt=0.0, description="Maximum power capacity (kW)")
    occupied_slots: int = Field(..., ge=0, description="Current occupied slots")
    queue_size: int = Field(default=0, description="Number of vehicles waiting")
    available_power: float = Field(..., ge=0.0, description="Available power for allocation")


class GridStatus(BaseModel):
    """Status of the power grid."""
    current_load: float = Field(..., ge=0.0, description="Current grid load (normalized 0-1)")
    max_load: float = Field(default=1.0, ge=0.0, description="Maximum allowed load")
    electricity_price: float = Field(..., ge=0.0, description="Current price per kWh")
    price_history: List[float] = Field(default_factory=list, description="Historical prices")
    time_step: int = Field(default=0, ge=0, description="Current time step")


class Observation(BaseModel):
    """Full observation returned by environment at each step."""
    time_step: int = Field(..., ge=0, description="Current simulation time step")
    vehicles: List[VehicleStatus] = Field(..., description="All vehicles in the system")
    stations: List[ChargingStationStatus] = Field(..., description="All charging stations")
    grid: GridStatus = Field(..., description="Current grid status")
    total_reward: float = Field(default=0.0, description="Cumulative reward so far")

    def to_dict(self) -> Dict:
        """Convert observation to dictionary for API serialization."""
        return {
            "time_step": self.time_step,
            "vehicles": [v.dict() for v in self.vehicles],
            "stations": [s.dict() for s in self.stations],
            "grid": self.grid.dict(),
            "total_reward": self.total_reward,
        }


class ChargingAction(BaseModel):
    """Action to assign a vehicle to a charging station."""
    action_type: Literal["assign", "delay"] = Field(
        ..., description="Type of action (assign or delay)"
    )
    vehicle_id: int = Field(..., description="Vehicle to act on")
    station_id: Optional[int] = Field(None, description="Target station (for assign)")
    power_level: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Normalized power level (0-1)"
    )
    duration: int = Field(default=1, ge=1, description="Duration in time steps")


class ActionSpace(BaseModel):
    """Schema for valid actions."""
    action_type: Literal["assign", "delay"]
    vehicle_id: int
    station_id: Optional[int] = None
    power_level: float
    duration: int


class RewardBreakdown(BaseModel):
    """Detailed breakdown of reward components."""
    completion_bonus: float = Field(default=0.0, description="Reward for completing charging")
    deadline_bonus: float = Field(default=0.0, description="Reward for meeting deadline")
    priority_bonus: float = Field(default=0.0, description="Reward for prioritizing urgent")
    grid_penalty: float = Field(default=0.0, description="Penalty for grid overload")
    cost_penalty: float = Field(default=0.0, description="Penalty for high energy cost")
    efficiency_bonus: float = Field(default=0.0, description="Reward for efficiency")
    idle_penalty: float = Field(default=0.0, description="Penalty for idle stations")

    @property
    def total(self) -> float:
        """Calculate total normalized reward [-1, 1]."""
        return (
            self.completion_bonus
            + self.deadline_bonus
            + self.priority_bonus
            - self.grid_penalty
            - self.cost_penalty
            + self.efficiency_bonus
            - self.idle_penalty
        )


class StepResult(BaseModel):
    """Result of a single environment step."""
    observation: Observation = Field(..., description="New observation after step")
    reward: float = Field(..., ge=-1.0, le=1.0, description="Reward for this step [-1, 1]")
    done: bool = Field(..., description="Whether episode is finished")
    info: Dict = Field(default_factory=dict, description="Additional info (truncated, etc)")

    def to_dict(self) -> Dict:
        """Convert to dictionary for API serialization."""
        return {
            "observation": self.observation.to_dict(),
            "reward": self.reward,
            "done": self.done,
            "info": self.info,
        }


class EnvironmentConfig(BaseModel):
    """Configuration for environment initialization."""
    num_vehicles: int = Field(default=10, ge=1, description="Number of vehicles in system")
    num_stations: int = Field(default=5, ge=1, description="Number of charging stations")
    max_steps: int = Field(default=200, ge=10, description="Max steps per episode")
    slots_per_station: int = Field(default=3, ge=1, description="Slots per station")
    max_power_per_station: float = Field(default=150.0, gt=0, description="Max power (kW)")
    max_grid_load: float = Field(default=1.0, gt=0, description="Max grid load threshold")
    base_electricity_price: float = Field(default=0.15, gt=0, description="Base price ($/kWh)")
    price_volatility: float = Field(default=0.3, ge=0, description="Price volatility factor")
    seed: Optional[int] = Field(None, description="Random seed")
