"""
Utility functions for EV Charging Scheduler.
"""

from typing import Dict, List, Any
from .models import Observation


def print_observation(obs: Observation) -> None:
    """Pretty print an observation."""
    print(f"\n=== Observation at T={obs.time_step} ===")
    print(f"Grid: Load={obs.grid.current_load:.1%}, Price=${obs.grid.electricity_price:.3f}/kWh")
    print(f"\nVehicles ({len(obs.vehicles)}):")
    for v in obs.vehicles:
        status = "✓" if v.fully_charged else f"{v.battery_level:.0%}"
        priority = f"[{v.priority.value.upper()}]" if v.priority.value == "urgent" else ""
        print(f"  V{v.id}: Battery {status}, Deadline T{v.deadline} {priority}")
    
    print(f"\nStations ({len(obs.stations)}):")
    for s in obs.stations:
        print(f"  S{s.id}: {s.occupied_slots}/{s.max_slots} slots, "
              f"{s.available_power:.1f}/{s.max_power:.1f} kW")


def summarize_observation(obs: Observation) -> Dict[str, Any]:
    """Create a summary dict of observation for logging."""
    return {
        "time_step": obs.time_step,
        "grid_load": float(obs.grid.current_load),
        "electricity_price": float(obs.grid.electricity_price),
        "vehicles_total": len(obs.vehicles),
        "vehicles_charged": sum(1 for v in obs.vehicles if v.fully_charged),
        "stations": [{
            "id": s.id,
            "occupied_slots": s.occupied_slots,
            "total_slots": s.max_slots,
            "available_power": float(s.available_power),
        } for s in obs.stations],
    }


def calculate_action_cost(action: Dict[str, Any], price: float) -> float:
    """Calculate approximate cost of an action."""
    if action.get("action_type") != "assign":
        return 0.0
    
    power_level = action.get("power_level", 1.0)
    # Assume ~1 hour simulation, power in kW
    energy = power_level * 100.0  # Approximate kW based on power level
    cost = energy * price
    
    return cost


def is_valid_action(action: Dict[str, Any]) -> bool:
    """Check if action has required fields."""
    required_fields = ["action_type"]
    if not all(field in action for field in required_fields):
        return False
    
    if action["action_type"] == "assign":
        return all(field in action for field in ["vehicle_id", "station_id"])
    elif action["action_type"] == "delay":
        return "vehicle_id" in action
    
    return False
