"""
Configuration examples for EV Charging Scheduler.
Shows how to customize the environment for different scenarios.
"""

from ev_charging_env import EVChargingEnvironment, EnvironmentConfig, Task

# ============================================================================
# Example 1: Small Grid (Low Complexity)
# ============================================================================
small_grid_config = EnvironmentConfig(
    num_vehicles=3,
    num_stations=2,
    max_steps=100,
    slots_per_station=2,
    max_power_per_station=50.0,
    max_grid_load=2.0,  # No constraint
    base_electricity_price=0.10,
    price_volatility=0.0,
    seed=42,
)

small_env = EVChargingEnvironment(small_grid_config)
print("Small Grid Config:", small_grid_config.dict())


# ============================================================================
# Example 2: Large Grid (High Complexity)
# ============================================================================
large_grid_config = EnvironmentConfig(
    num_vehicles=50,
    num_stations=15,
    max_steps=500,
    slots_per_station=5,
    max_power_per_station=300.0,
    max_grid_load=0.9,  # Tight constraint
    base_electricity_price=0.25,
    price_volatility=0.8,
    seed=None,  # Non-deterministic
)

large_env = EVChargingEnvironment(large_grid_config)
print("Large Grid Config:", large_grid_config.dict())


# ============================================================================
# Example 3: Peak Hours Scenario (High Load)
# ============================================================================
peak_config = EnvironmentConfig(
    num_vehicles=30,
    num_stations=5,
    max_steps=200,
    slots_per_station=4,
    max_power_per_station=150.0,
    max_grid_load=0.85,  # Very constrained
    base_electricity_price=0.35,  # High peak time price
    price_volatility=0.9,
    seed=100,
)

peak_task = Task("peak_hours", "hard", peak_config)
obs = peak_task.reset()
print(f"Peak Config - {len(obs.vehicles)} vehicles, "
      f"price ${obs.grid.electricity_price:.3f}/kWh")


# ============================================================================
# Example 4: Off-Peak Scenario (Low Load)
# ============================================================================
offpeak_config = EnvironmentConfig(
    num_vehicles=10,
    num_stations=4,
    max_steps=150,
    slots_per_station=3,
    max_power_per_station=120.0,
    max_grid_load=1.5,  # Relaxed
    base_electricity_price=0.08,  # Cheap off-peak
    price_volatility=0.1,
    seed=200,
)

offpeak_task = Task("off_peak", "easy", offpeak_config)
obs = offpeak_task.reset()
print(f"Off-Peak Config - {len(obs.vehicles)} vehicles, "
      f"price ${obs.grid.electricity_price:.3f}/kWh")


# ============================================================================
# Example 5: Critical Infrastructure (Reliability Focus)
# ============================================================================
critical_config = EnvironmentConfig(
    num_vehicles=20,
    num_stations=10,  # Over-provisioned for reliability
    max_steps=240,
    slots_per_station=3,
    max_power_per_station=200.0,
    max_grid_load=0.75,  # Conservative limit
    base_electricity_price=0.18,
    price_volatility=0.2,
    seed=300,
)

critical_env = EVChargingEnvironment(critical_config)
obs = critical_env.reset()
print(f"Critical Config - {len(obs.stations)} stations for {len(obs.vehicles)} vehicles")
print(f"Station capacity: {obs.stations[0].max_slots} slots × "
      f"{len(obs.stations)} stations = {obs.stations[0].max_slots * len(obs.stations)} total")


# ============================================================================
# Example 6: Cost-Optimized Scenario
# ============================================================================
cost_optimized_config = EnvironmentConfig(
    num_vehicles=15,
    num_stations=6,
    max_steps=180,
    slots_per_station=3,
    max_power_per_station=100.0,
    max_grid_load=1.2,
    base_electricity_price=0.20,
    price_volatility=0.6,  # Volatile for optimization opportunity
    seed=400,
)

cost_env = EVChargingEnvironment(cost_optimized_config)
print(f"Cost-Optimized Config - High price volatility ($0.08-$0.32/kWh)")


# ============================================================================
# Comparison Function
# ============================================================================
def compare_scenarios():
    """Compare performance across different scenarios."""
    from ev_charging_env import PriorityAwareAgent
    
    scenarios = {
        "Small": (small_grid_config, "small"),
        "Large": (large_grid_config, "large"),
        "Peak": (peak_config, "peak"),
        "Off-Peak": (offpeak_config, "offpeak"),
        "Critical": (critical_config, "critical"),
    }
    
    agent = PriorityAwareAgent()
    
    print("\n" + "="*60)
    print("SCENARIO COMPARISON")
    print("="*60)
    
    for name, (config, _) in scenarios.items():
        env = EVChargingEnvironment(config)
        obs = env.reset()
        
        # Run 50 steps
        for _ in range(50):
            action = agent.get_action(obs)
            result = env.step(action)
            obs = result.observation
        
        vehicles_charged = sum(1 for v in obs.vehicles if v.fully_charged)
        grid_load = obs.grid.current_load
        
        print(f"{name:12s}: {vehicles_charged:2d}/{len(obs.vehicles)} charged, "
              f"Grid={grid_load:.1%}, Cost=${env.total_cost:.2f}")


if __name__ == "__main__":
    print("\n📋 EV Charging Scheduler - Configuration Examples\n")
    
    print("✅ Small Grid Config: 3 vehicles, 2 stations")
    print("✅ Large Grid Config: 50 vehicles, 15 stations")
    print("✅ Peak Hours Config: 30 vehicles, high price volatility")
    print("✅ Off-Peak Config: 10 vehicles, low price")
    print("✅ Critical Infrastructure: Over-provisioned for reliability")
    print("✅ Cost-Optimized: Volatile pricing for optimization")
    
    compare_scenarios()
    
    print("\n" + "="*60)
    print("Use these configs as templates for your own scenarios!")
    print("="*60)
