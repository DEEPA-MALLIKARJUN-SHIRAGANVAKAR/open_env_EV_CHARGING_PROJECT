__version__ = "1.0.0"

from .tasks.simple_tasks import SimpleTask, create_easy_task, create_medium_task, create_hard_task

__all__ = [
    "SimpleTask",
    "create_easy_task",
    "create_medium_task",
    "create_hard_task",
]
