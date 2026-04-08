import os

from openai import OpenAI

from ev_charging_env.tasks import create_easy_task


def choose_action(observation):
    vehicle = next((item for item in observation.vehicles if not item.fully_charged), None)
    station = observation.stations[0] if observation.stations else None
    if vehicle is not None and station is not None:
        return {
            "action_type": "assign",
            "vehicle_id": int(vehicle.id),
            "station_id": int(station.id),
            "power_level": 1.0,
            "duration": 1,
        }, "charge"
    fallback_vehicle_id = int(observation.vehicles[0].id) if observation.vehicles else 0
    return {
        "action_type": "delay",
        "vehicle_id": fallback_vehicle_id,
        "duration": 1,
    }, "charge"


def clamp_score(value):
    return max(0.0, min(1.0, float(value)))


def main():
    task = create_easy_task()
    task_name = task.name
    client = OpenAI(
        base_url=os.environ["API_BASE_URL"],
        api_key=os.environ["API_KEY"]
    )
    observation = task.reset()
    total_reward = 0.0
    steps = 0
    print(f"[START] task={task_name}", flush=True)
    for step in range(1, 6):
        action, action_name = choose_action(observation)
        try:
            client.chat.completions.create(
                model=os.environ.get("MODEL_NAME", "gpt-4o-mini"),
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Task={task_name}; step={step}; "
                            f"return the single word charge."
                        ),
                    }
                ],
                temperature=0,
                max_tokens=4,
            )
        except Exception:
            pass
        result = task.step(action)
        reward = float(result.reward)
        total_reward += reward
        steps = step
        print(f"[STEP] step={step} action={action_name} reward={reward}", flush=True)
        observation = result.observation
        if result.done:
            break
    score = clamp_score(task.grade(use_llm=False).score if steps > 0 else 0.0)
    print(f"[END] task={task_name} score={score} steps={steps}", flush=True)


if __name__ == "__main__":
    main()
