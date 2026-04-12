"""Gradio UI for EV Charging Scheduler - Minimal for OpenEnv compatibility"""
import gradio as gr
from ev_charging_env.tasks import create_easy_task

def run_demo(task_name="easy"):
    task = create_easy_task()
    obs = task.reset()
    return f"Demo {task_name}: Ready"

gr.Interface(fn=run_demo, inputs="text", outputs="text", title="EV Charging Demo").launch()

