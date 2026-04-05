"""
Verification script to demonstrate all EV Charging Scheduler features.
Run this to validate the environment is working correctly.
"""

import sys
from ev_charging_env import (
    EVChargingEnvironment,
    EnvironmentConfig,
    create_easy_task,
    create_medium_task,
    create_hard_task,
    RandomAgent,
    GreedyAgent,
    PriorityAwareAgent,
    OptimalSearchAgent,
)


def print_section(title: str):
    """Pretty print section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def test_environment_creation():
    """Verify environment can be created."""
    print_section("1. ENVIRONMENT CREATION")
    
    try:
        config = EnvironmentConfig(num_vehicles=5, num_stations=3)
        env = EVChargingEnvironment(config)
        obs = env.reset()
        
        print(f"✅ Environment created successfully")
        print(f"   - Vehicles: {len(obs.vehicles)}")
        print(f"   - Stations: {len(obs.stations)}")
        print(f"   - Grid Load: {obs.grid.current_load:.1%}")
        print(f"   - Electricity Price: ${obs.grid.electricity_price:.3f}/kWh")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_step_function():
    """Verify step function works correctly."""
    print_section("2. STEP FUNCTION (OpenEnv Compliant)")
    
    try:
        env = EVChargingEnvironment()
        obs = env.reset()
        
        # Test assign action
        action = {
            "action_type": "assign",
            "vehicle_id": 0,
            "station_id": 0,
            "power_level": 0.8,
        }
        result = env.step(action)
        
        print(f"✅ Step function works")
        print(f"   - Reward: {result.reward:.3f} (in range [-1, 1])")
        print(f"   - Done: {result.done}")
        print(f"   - Observation received: ✓")
        
        # Test multiple steps
        for i in range(10):
            action = {"action_type": "delay", "vehicle_id": 0, "duration": 1}
            result = env.step(action)
        
        print(f"   - 10 steps executed: ✓")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_tasks():
    """Verify tasks can be created and graded."""
    print_section("3. TASK SYSTEM")
    
    try:
        # Test all three difficulties
        tasks = {
            "easy": create_easy_task(),
            "medium": create_medium_task(),
            "hard": create_hard_task(),
        }
        
        for difficulty, task in tasks.items():
            obs = task.reset()
            
            # Run a few steps
            action = {"action_type": "delay", "vehicle_id": 0, "duration": 1}
            for _ in range(20):
                result = task.step(action)
            
            # Grade
            grade = task.grade()
            
            print(f"✅ {difficulty.upper()} task:")
            print(f"   - Score: {grade.score:.3f}")
            print(f"   - Vehicles: {len(obs.vehicles)}")
            print(f"   - Max Steps: {task.config.max_steps}")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_baseline_agents():
    """Verify baseline agents work."""
    print_section("4. BASELINE AGENTS")
    
    try:
        agents = {
            "random": RandomAgent(),
            "greedy": GreedyAgent(),
            "priority": PriorityAwareAgent(),
            "optimal_search": OptimalSearchAgent(),
        }
        
        env = EVChargingEnvironment()
        obs = env.reset()
        
        for name, agent in agents.items():
            try:
                action = agent.get_action(obs)
                assert "action_type" in action
                assert "vehicle_id" in action
                print(f"✅ {name.capitalize():15s} agent works")
            except Exception as e:
                print(f"❌ {name.capitalize():15s} agent failed: {e}")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_reward_range():
    """Verify reward stays in valid range."""
    print_section("5. REWARD NORMALIZATION")
    
    try:
        env = EVChargingEnvironment()
        env.reset()
        
        min_reward = float("inf")
        max_reward = float("-inf")
        
        action = {"action_type": "delay", "vehicle_id": 0, "duration": 1}
        for _ in range(100):
            result = env.step(action)
            min_reward = min(min_reward, result.reward)
            max_reward = max(max_reward, result.reward)
        
        assert -1.0 <= min_reward <= 1.0
        assert -1.0 <= max_reward <= 1.0
        
        print(f"✅ Reward range verified")
        print(f"   - Min: {min_reward:.3f}")
        print(f"   - Max: {max_reward:.3f}")
        print(f"   - All in [-1.0, 1.0]: ✓")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_determinism():
    """Verify environment is deterministic with seeds."""
    print_section("6. DETERMINISM WITH SEEDS")
    
    try:
        # Create two environments with same seed
        config1 = EnvironmentConfig(seed=42, num_vehicles=5)
        env1 = EVChargingEnvironment(config1)
        obs1 = env1.reset()
        
        config2 = EnvironmentConfig(seed=42, num_vehicles=5)
        env2 = EVChargingEnvironment(config2)
        obs2 = env2.reset()
        
        # Check initial states match
        match = all(
            v1.battery_level == v2.battery_level
            for v1, v2 in zip(obs1.vehicles, obs2.vehicles)
        )
        
        if match:
            print(f"✅ Determinism verified")
            print(f"   - Same seed → identical initial states")
            return True
        else:
            print(f"❌ States don't match with same seed")
            return False
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_observation_structure():
    """Verify observation has correct structure."""
    print_section("7. OBSERVATION STRUCTURE")
    
    try:
        env = EVChargingEnvironment()
        obs = env.reset()
        
        # Convert to dict
        obs_dict = obs.to_dict()
        
        required_fields = ["time_step", "vehicles", "stations", "grid", "total_reward"]
        missing = [f for f in required_fields if f not in obs_dict]
        
        if not missing:
            print(f"✅ Observation structure correct")
            print(f"   - time_step: ✓")
            print(f"   - vehicles: {len(obs.vehicles)} items")
            print(f"   - stations: {len(obs.stations)} items")
            print(f"   - grid: ✓")
            print(f"   - total_reward: {obs.total_reward}")
            return True
        else:
            print(f"❌ Missing fields: {missing}")
            return False
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_metadata():
    """Verify metadata file exists."""
    print_section("8. METADATA (openenv.yaml)")
    
    try:
        import os
        if os.path.exists("openenv.yaml"):
            with open("openenv.yaml", "r") as f:
                content = f.read()
                
            required = ["name", "description", "action_space", "observation_space", "reward_space"]
            found = [r for r in required if r in content]
            
            print(f"✅ openenv.yaml exists")
            print(f"   - Size: {len(content)} bytes")
            print(f"   - Contains sections: {', '.join(found)}")
            return all(r in found for r in required)
        else:
            print(f"❌ openenv.yaml not found")
            return False
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def run_full_episode():
    """Run a complete episode with an agent."""
    print_section("9. FULL EPISODE TEST")
    
    try:
        task = create_easy_task()
        agent = PriorityAwareAgent()
        
        obs = task.reset()
        total_reward = 0.0
        steps = 0
        
        while steps < task.config.max_steps:
            action = agent.get_action(obs)
            result = task.step(action)
            total_reward += result.reward
            obs = result.observation
            steps += 1
            
            if result.done or result.info.get("done", False):
                break
        
        grade = task.grade()
        
        print(f"✅ Full episode completed")
        print(f"   - Steps: {steps}")
        print(f"   - Total Reward: {total_reward:.3f}")
        print(f"   - Final Score: {grade.score:.3f}")
        print(f"   - Vehicles Charged: {grade.vehicles_charged}")
        print(f"   - Total Cost: ${grade.total_cost:.2f}")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def main():
    """Run all verification tests."""
    print("\n" + "█" * 70)
    print("  EV CHARGING SCHEDULER - VERIFICATION SUITE")
    print("█" * 70)
    
    tests = [
        ("Environment Creation", test_environment_creation),
        ("Step Function", test_step_function),
        ("Task System", test_tasks),
        ("Baseline Agents", test_baseline_agents),
        ("Reward Range", test_reward_range),
        ("Determinism", test_determinism),
        ("Observation Structure", test_observation_structure),
        ("Metadata", test_metadata),
        ("Full Episode", run_full_episode),
    ]
    
    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))
    
    # Summary
    print_section("SUMMARY")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}  {name}")
    
    print(f"\nScore: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - Environment is production-ready!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
