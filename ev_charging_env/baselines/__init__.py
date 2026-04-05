"""
Baseline agents for EV Charging Scheduler.
Provides simple heuristic-based agents for benchmarking.
"""

import random
from typing import Dict, List, Any
from abc import ABC, abstractmethod

from ..models import Observation, VehicleStatus, ChargingStationStatus, PriorityLevel


class BaseAgent(ABC):
    """Base agent interface."""

    @abstractmethod
    def get_action(self, observation: Observation) -> Dict[str, Any]:
        """Get next action based on observation."""
        pass


class RandomAgent(BaseAgent):
    """Agent that takes random valid actions."""

    def get_action(self, observation: Observation) -> Dict[str, Any]:
        """Random action: either assign a vehicle or delay."""
        if random.random() < 0.5:
            # Try to assign a vehicle
            available_vehicles = [
                v for v in observation.vehicles
                if not v.fully_charged
            ]
            if not available_vehicles:
                return {"action_type": "delay", "vehicle_id": 0, "duration": 1}
            
            vehicle = random.choice(available_vehicles)
            station = random.choice(observation.stations)
            power = random.uniform(0.3, 1.0)
            
            return {
                "action_type": "assign",
                "vehicle_id": vehicle.id,
                "station_id": station.id,
                "power_level": power,
            }
        else:
            # Delay a random vehicle
            available_vehicles = [
                v for v in observation.vehicles
                if not v.fully_charged
            ]
            vehicle_id = available_vehicles[0].id if available_vehicles else 0
            
            return {
                "action_type": "delay",
                "vehicle_id": vehicle_id,
                "duration": random.randint(1, 5),
            }


class GreedyAgent(BaseAgent):
    """
    Greedy agent: assign vehicles to stations with lowest electricity cost,
    prioritizing vehicles with approaching deadlines.
    """

    def get_action(self, observation: Observation) -> Dict[str, Any]:
        """Greedily assign vehicle with nearest deadline to cheapest station."""
        available_vehicles = [
            v for v in observation.vehicles
            if not v.fully_charged and v.arrival_time <= observation.time_step
        ]
        
        if not available_vehicles:
            return {"action_type": "delay", "vehicle_id": 0, "duration": 1}
        
        # Sort by deadline urgency
        available_vehicles.sort(key=lambda v: v.deadline - observation.time_step)
        vehicle = available_vehicles[0]
        
        # Find best station (with available slots)
        available_stations = [
            s for s in observation.stations
            if s.occupied_slots < s.max_slots and s.available_power > 10.0
        ]
        
        if not available_stations:
            return {
                "action_type": "delay",
                "vehicle_id": vehicle.id,
                "duration": 1,
            }
        
        # Choose station with lowest cost (assume price is same for all at observation time)
        # But choose one with better capacity
        station = max(available_stations, key=lambda s: s.available_power)
        
        # Use full power
        power = min(station.available_power, 100.0) / station.max_power
        power = min(1.0, max(0.5, power))
        
        return {
            "action_type": "assign",
            "vehicle_id": vehicle.id,
            "station_id": station.id,
            "power_level": power,
        }


class PriorityAwareAgent(BaseAgent):
    """
    Priority-aware agent: prioritizes urgent vehicles while managing costs
    and avoiding grid overload.
    """

    def get_action(self, observation: Observation) -> Dict[str, Any]:
        """Assign urgent vehicles first, then others based on deadline."""
        available_vehicles = [
            v for v in observation.vehicles
            if not v.fully_charged and v.arrival_time <= observation.time_step
        ]
        
        if not available_vehicles:
            return {"action_type": "delay", "vehicle_id": 0, "duration": 1}
        
        # Sort: urgent first, then by deadline
        available_vehicles.sort(
            key=lambda v: (
                0 if v.priority == PriorityLevel.URGENT else 1,
                v.deadline - observation.time_step,
            )
        )
        vehicle = available_vehicles[0]
        
        # Choose station: prefer those with lower load to avoid grid issues
        available_stations = [
            s for s in observation.stations
            if s.occupied_slots < s.max_slots
        ]
        
        if not available_stations:
            return {
                "action_type": "delay",
                "vehicle_id": vehicle.id,
                "duration": 1,
            }
        
        # Choose station with best load ratio
        station = min(
            available_stations,
            key=lambda s: s.occupied_slots / s.max_slots
        )
        
        # Adjust power based on grid load (avoid overload)
        base_power = 1.0
        if observation.grid.current_load > 0.7:
            base_power = 0.5  # Reduce power if grid is stressed
        elif observation.grid.current_load > 0.9:
            base_power = 0.3  # Further reduce
        
        # For urgent vehicles, use more power
        if vehicle.priority == PriorityLevel.URGENT:
            base_power = min(1.0, base_power * 1.5)
        
        power = min(station.available_power, 100.0) / station.max_power
        power = min(base_power, max(0.3, power))
        
        return {
            "action_type": "assign",
            "vehicle_id": vehicle.id,
            "station_id": station.id,
            "power_level": power,
        }


class OptimalSearchAgent(BaseAgent):
    """
    Simple heuristic agent that tries to find reasonable assignments
    by considering multiple factors.
    """

    def get_action(self, observation: Observation) -> Dict[str, Any]:
        """Search for best vehicle-station pair."""
        available_vehicles = [
            v for v in observation.vehicles
            if not v.fully_charged and v.arrival_time <= observation.time_step
        ]
        
        if not available_vehicles:
            return {"action_type": "delay", "vehicle_id": 0, "duration": 1}
        
        # Score each vehicle-station pair
        best_score = -float("inf")
        best_action = None
        
        for vehicle in available_vehicles:
            for station in observation.stations:
                if station.occupied_slots >= station.max_slots:
                    continue
                if station.available_power < 10.0:
                    continue
                
                # Score = urgency + deadline pressure - grid penalty
                score = 0.0
                
                if vehicle.priority == PriorityLevel.URGENT:
                    score += 10.0
                
                time_to_deadline = vehicle.deadline - observation.time_step
                if time_to_deadline < 30:
                    score += 5.0
                elif time_to_deadline < 60:
                    score += 2.0
                
                # Penalize if grid is stressed
                if observation.grid.current_load > 0.8:
                    score -= 3.0
                
                # Bonus for efficient use of station
                slot_utilization = station.occupied_slots / station.max_slots
                score += (1.0 - slot_utilization) * 2.0
                
                if score > best_score:
                    best_score = score
                    power = min(station.available_power, 100.0) / station.max_power
                    best_action = {
                        "action_type": "assign",
                        "vehicle_id": vehicle.id,
                        "station_id": station.id,
                        "power_level": min(1.0, max(0.5, power)),
                    }
        
        if best_action is None:
            return {
                "action_type": "delay",
                "vehicle_id": available_vehicles[0].id,
                "duration": 1,
            }
        
        return best_action
