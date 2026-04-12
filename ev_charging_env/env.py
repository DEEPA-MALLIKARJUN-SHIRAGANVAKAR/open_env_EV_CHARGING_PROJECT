"""
EV Charging Scheduler Environment - OpenEnv Compatible
Main environment simulation for electric vehicle charging optimization.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from copy import deepcopy
import random

from .models import (
    VehicleStatus,
    ChargingStationStatus,
    GridStatus,
    Observation,
    ChargingAction,
    StepResult,
    RewardBreakdown,
    EnvironmentConfig,
    PriorityLevel,
)

# FIXED - GradeResult for validator
class GradeResult:
    def __init__(self, score: float):
        self.score = max(0.0, min(1.0, score))



class EVChargingEnvironment:
    """
    OpenEnv-compatible environment for EV charging scheduler optimization.
    
    Agents interact by assigning vehicles to charging stations and choosing
    power levels to minimize cost, avoid grid overload, and meet deadlines.
    """

    def __init__(self, config: EnvironmentConfig = None):
        """Initialize environment with configuration."""
        self.config = config or EnvironmentConfig()
        
        if self.config.seed is not None:
            random.seed(self.config.seed)
            np.random.seed(self.config.seed)

        self.time_step = 0
        self.vehicles: Dict[int, VehicleStatus] = {}
        self.stations: Dict[int, ChargingStationStatus] = {}
        self.vehicle_assignments: Dict[int, int] = {}  # vehicle_id -> station_id
        self.vehicle_power_levels: Dict[int, float] = {}  # vehicle_id -> power (0-1)
        self.total_energy_used = 0.0
        self.total_cost = 0.0
        self.episode_reward = 0.0
        self.queue: Dict[int, List[int]] = {s: [] for s in range(self.config.num_stations)}
        
        self.reset()

    def reset(self) -> Observation:
        """Reset environment and return initial observation."""
        self.time_step = 0
        self.total_energy_used = 0.0
        self.total_cost = 0.0
        self.episode_reward = 0.0
        self.vehicle_assignments = {}
        self.vehicle_power_levels = {}
        self.queue = {s: [] for s in range(self.config.num_stations)}
        
        # Initialize vehicles
        self.vehicles = {}
        for i in range(self.config.num_vehicles):
            arrival_time = random.randint(0, self.config.max_steps // 3)
            deadline = arrival_time + random.randint(20, 80)
            
            # 20% chance of urgent
            priority = (
                PriorityLevel.URGENT
                if random.random() < 0.2
                else PriorityLevel.NORMAL
            )
            
            self.vehicles[i] = VehicleStatus(
                id=i,
                battery_level=random.uniform(0.1, 0.7),
                required_charge=random.uniform(0.2, 0.9),
                deadline=deadline,
                priority=priority,
                arrival_time=arrival_time,
            )
        
        # Initialize stations
        self.stations = {}
        for i in range(self.config.num_stations):
            self.stations[i] = ChargingStationStatus(
                id=i,
                max_slots=self.config.slots_per_station,
                max_power=self.config.max_power_per_station,
                occupied_slots=0,
                available_power=self.config.max_power_per_station,
            )

        return self.state()

    def state(self) -> Observation:
        """Return current observation (OpenEnv required method)."""
        # Calculate current grid load and electricity price
        total_current_power = sum(
            self.stations[s].max_power - self.stations[s].available_power
            for s in self.stations
        )
        grid_load = min(
            total_current_power / (self.config.max_power_per_station * self.config.num_stations),
            1.0,
        )
        
        # Dynamic pricing: higher load = higher price
        price_multiplier = 1.0 + 0.5 * grid_load + 0.3 * np.sin(self.time_step / 10.0)
        electricity_price = self.config.base_electricity_price * price_multiplier
        
        # Build observation
        vehicles_status = list(self.vehicles.values())
        stations_status = list(self.stations.values())
        
        grid = GridStatus(
            current_load=grid_load,
            max_load=self.config.max_grid_load,
            electricity_price=electricity_price,
            time_step=self.time_step,
        )
        
        return Observation(
            time_step=self.time_step,
            vehicles=vehicles_status,
            stations=stations_status,
            grid=grid,
            total_reward=self.episode_reward,
        )

    def step(self, action: Dict[str, Any]) -> StepResult:
        """Execute one step of environment. OpenEnv required method."""
        # Parse and validate action
        try:
            action_obj = ChargingAction(**action)
        except Exception as e:
            # Invalid action, assign penalty
            obs = self.state()
            info = {"error": f"Invalid action: {str(e)}", "action": action}
            result = StepResult(
                observation=obs,
                reward=-0.1,
                done=False,
                info=info,
            )
            self.episode_reward += result.reward
            return result

        reward = self._process_action(action_obj)

        # Advance simulation
        self._advance_simulation()
        
        # Check end condition
        done = self.time_step >= self.config.max_steps

        obs = self.state()
        self.episode_reward += reward

        info = {
            "action_processed": True,
            "time_step": self.time_step,
            "done": done,
        }

        return StepResult(
            observation=obs,
            reward=max(-1.0, min(1.0, reward)),  # Clamp to [-1, 1]
            done=done,
            info=info,
        )

    def _process_action(self, action: ChargingAction) -> float:
        """Process an action and return immediate reward."""
        if action.action_type == "assign":
            return self._assign_vehicle(action)
        elif action.action_type == "delay":
            return self._delay_vehicle(action)
        return -0.05  # Unknown action type

    def _assign_vehicle(self, action: ChargingAction) -> float:
        """Assign a vehicle to a charging station."""
        vehicle_id = action.vehicle_id
        station_id = action.station_id
        power_level = action.power_level
        
        # Validate vehicle exists and not already fully charged
        if vehicle_id not in self.vehicles:
            return -0.05
        
        vehicle = self.vehicles[vehicle_id]
        if vehicle.fully_charged:
            return -0.02
        
        # Validate station exists
        if station_id not in self.stations:
            return -0.05
        
        station = self.stations[station_id]
        
        # Check if station has available slots
        if station.occupied_slots >= station.max_slots:
            return -0.02
        
        # Calculate power to assign
        power_needed = (vehicle.required_charge - vehicle.battery_level) * 50.0  # kW needed
        power_available = station.available_power
        power_assigned = min(power_needed, power_available * power_level)
        
        if power_assigned <= 0.01:
            return -0.01
        
        # Assign vehicle
        self.vehicle_assignments[vehicle_id] = station_id
        self.vehicle_power_levels[vehicle_id] = power_assigned
        station.occupied_slots += 1
        station.available_power -= power_assigned
        
        # Calculate reward for this assignment
        reward = self._calculate_action_reward(vehicle, station, power_assigned)
        
        return reward

    def _delay_vehicle(self, action: ChargingAction) -> float:
        """Delay charging for a vehicle with strategic reward signals."""
        vehicle_id = action.vehicle_id
        if vehicle_id not in self.vehicles:
            return -0.05
        
        vehicle = self.vehicles[vehicle_id]
        if vehicle.fully_charged:
            return -0.02
        
        reward = -0.02  # Base penalty for not charging
        
        # Strategic delay rewards
        time_to_deadline = vehicle.deadline - self.time_step
        current_load = self.state().grid.current_load
        current_price = self.state().grid.electricity_price
        
        # Reward delaying if grid is overloaded
        if current_load > 0.9:
            reward += 0.05
        
        # Reward delaying if price is high
        if current_price > self.config.base_electricity_price * 1.3:
            reward += 0.03
        
        # Penalty for delaying urgent vehicles near deadline
        if vehicle.priority == PriorityLevel.URGENT and time_to_deadline < 20:
            reward -= 0.1
        
        # Small reward for delaying non-urgent vehicles when stations are busy
        busy_stations = sum(1 for s in self.stations.values() if s.occupied_slots >= s.max_slots)
        if vehicle.priority != PriorityLevel.URGENT and busy_stations > len(self.stations) * 0.7:
            reward += 0.02
        
        return reward

    def _calculate_action_reward(self, vehicle: VehicleStatus, station: ChargingStationStatus, power: float) -> float:
        """Calculate reward for an assignment action with meaningful partial progress signals."""
        reward = 0.0
        
        # 1. Completion progress reward (0.1 - 0.3)
        # Reward based on how much this action contributes to vehicle completion
        charge_needed = vehicle.required_charge - vehicle.battery_level
        charge_provided = min(charge_needed, power / 100.0)  # Convert kW to battery units
        completion_progress = charge_provided / max(0.01, charge_needed)
        reward += completion_progress * 0.2  # Up to 0.2 for full completion in one step
        
        # 2. Deadline urgency bonus (0.0 - 0.15)
        time_to_deadline = vehicle.deadline - self.time_step
        if time_to_deadline > 0:
            urgency_factor = max(0.0, 1.0 - (time_to_deadline / 100.0))  # More urgent = higher factor
            reward += urgency_factor * 0.15
        else:
            reward -= 0.1  # Penalty for late charging
        
        # 3. Priority bonus (0.0 - 0.1)
        if vehicle.priority == PriorityLevel.URGENT:
            reward += 0.1
        
        # 4. Load balancing bonus (0.0 - 0.1)
        # Reward efficient use of station capacity
        slot_utilization = station.occupied_slots / station.max_slots
        power_utilization = (station.max_power - station.available_power + power) / station.max_power
        
        # Optimal utilization is around 70-90%
        if 0.7 <= slot_utilization <= 0.9 and 0.7 <= power_utilization <= 0.9:
            reward += 0.1
        elif slot_utilization > 0.95 or power_utilization > 0.95:
            reward -= 0.05  # Penalty for overloading
        
        # 5. Grid management (0.0 - 0.1 or penalty)
        current_load = self.state().grid.current_load
        if current_load > self.config.max_grid_load:
            reward -= 0.1  # Grid overload penalty
        elif current_load < 0.8:
            reward += 0.05  # Reward for keeping grid comfortable
        
        # 6. Cost efficiency (0.0 - 0.05)
        current_price = self.state().grid.electricity_price
        if current_price < self.config.base_electricity_price * 1.2:
            reward += 0.05  # Reward charging during low-price periods
        
        return reward

    def _advance_simulation(self):
        """Advance simulation: apply charging, update states."""
        self.time_step += 1
        
        # Get current electricity price for cost calculation
        current_obs = self.state()
        price = current_obs.grid.electricity_price
        
        # Apply charging to assigned vehicles
        for vehicle_id, station_id in list(self.vehicle_assignments.items()):
            if vehicle_id not in self.vehicles:
                continue
            
            vehicle = self.vehicles[vehicle_id]
            power = self.vehicle_power_levels.get(vehicle_id, 0.0)
            
            # Charge the vehicle (simplified: assume 1 kW charging = 0.01 battery level per step)
            charge_amount = min(power / 100.0, vehicle.required_charge - vehicle.battery_level)
            vehicle.battery_level += charge_amount
            
            # Track energy and cost
            self.total_energy_used += power
            self.total_cost += power * price / 60.0  # Price is per kWh, step is 1 minute
            
            # Check if fully charged
            if vehicle.battery_level >= vehicle.required_charge:
                vehicle.fully_charged = True
                station = self.stations[station_id]
                station.occupied_slots = max(0, station.occupied_slots - 1)
                station.available_power += power
                del self.vehicle_assignments[vehicle_id]
                del self.vehicle_power_levels[vehicle_id]
        
        # Update station statuses for new arrivals
        for vehicle_id, vehicle in self.vehicles.items():
            if vehicle.arrival_time <= self.time_step and vehicle_id not in self.vehicle_assignments:
                if not vehicle.fully_charged:
                    # Vehicle is waiting, don't have a slot yet
                    pass

    def get_reward_breakdown(self) -> RewardBreakdown:
        """Get detailed breakdown of rewards (for analysis)."""
        obs = self.state()
        breakdown = RewardBreakdown()
        
        # Completion bonus
        completed = sum(1 for v in self.vehicles.values() if v.fully_charged)
        breakdown.completion_bonus = min(0.3, completed * 0.05)
        
        # Deadline bonus
        late = sum(
            1
            for v in self.vehicles.values()
            if not v.fully_charged and self.time_step > v.deadline
        )
        breakdown.deadline_bonus = max(-0.2, -late * 0.05)
        
        # Priority bonus
        urgent_charged = sum(
            1
            for v in self.vehicles.values()
            if v.fully_charged and v.priority == PriorityLevel.URGENT
        )
        breakdown.priority_bonus = min(0.2, urgent_charged * 0.05)
        
        # Grid penalty
        if obs.grid.current_load > obs.grid.max_load:
            breakdown.grid_penalty = (obs.grid.current_load - obs.grid.max_load) * 0.5
        
        # Cost penalty (normalized)
        cost_ratio = self.total_cost / 1000.0  # Normalize to ~1000 as baseline
        breakdown.cost_penalty = min(0.3, cost_ratio * 0.05)
        
        # Efficiency bonus
        if self.total_energy_used > 0:
            average_price = self.total_cost / self.total_energy_used
            if average_price < self.config.base_electricity_price * 1.2:
                breakdown.efficiency_bonus = 0.1
        
        # Idle penalty
        idle_stations = sum(1 for s in self.stations.values() if s.occupied_slots == 0)
        breakdown.idle_penalty = idle_stations * 0.02
        
        return breakdown

    def grade(self):
        # FIXED - Mandatory grade method for Phase 2 validator
        total = max(1, len(self.vehicles))
        completed = sum(1 for v in self.vehicles.values() if v.fully_charged)
        score = completed / total
        return GradeResult(score)

    def render(self) -> str:
        """Render current environment state as string."""

        obs = self.state()
        lines = [
            f"=== EV Charging Scheduler (Step {self.time_step}/{self.config.max_steps}) ===",
            f"Grid Load: {obs.grid.current_load:.2%} (max {obs.grid.max_load:.0%})",
            f"Electricity Price: ${obs.grid.electricity_price:.3f}/kWh",
            f"Total Reward: {self.episode_reward:.3f}",
            "",
            "Vehicles:",
        ]
        
        for v in obs.vehicles:
            status = "✓ CHARGED" if v.fully_charged else f"  {v.battery_level:.0%}"
            urgent = " [URGENT]" if v.priority == PriorityLevel.URGENT else ""
            lines.append(
                f"  V{v.id}: Battery {status}, Deadline T{v.deadline}{urgent}"
            )
        
        lines.append("\nCharging Stations:")
        for s in obs.stations:
            lines.append(
                f"  S{s.id}: {s.occupied_slots}/{s.max_slots} slots, "
                f"{s.available_power:.1f}/{s.max_power:.1f} kW available"
            )
        
        return "\n".join(lines)


class EVChargingEnvironmentWrapper:
    """
    Wrapper to ensure full OpenEnv compatibility with typed interfaces.
    """

    def __init__(self, config: EnvironmentConfig = None):
        self.env = EVChargingEnvironment(config)

    def reset(self) -> Dict[str, Any]:
        """Reset and return observation as dict."""
        obs = self.env.reset()
        return obs.to_dict()

    def step(self, action: Dict[str, Any]) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        """Step environment and return (obs_dict, reward, done, info)."""
        result = self.env.step(action)
        return (
            result.observation.to_dict(),
            result.reward,
            result.done,
            result.info,
        )

    def render(self, mode: str = "human") -> Optional[str]:
        """Render the environment."""
        if mode == "human":
            print(self.env.render())
        return self.env.render()
