"""Session persistence for task resumption across agent restarts."""

import json
import os
import time
import uuid


class SessionStorage:
    def __init__(self, session_dir: str = "~/.vercept/sessions"):
        self.session_dir = os.path.expanduser(session_dir)
        os.makedirs(self.session_dir, exist_ok=True)

    def save_task(self, task_data: dict) -> str:
        """Save a task to disk. Returns the task ID."""
        task_id = task_data.get("task_id") or str(uuid.uuid4())[:8]
        task_data["task_id"] = task_id
        task_data["saved_at"] = time.time()

        path = os.path.join(self.session_dir, f"{task_id}.json")
        with open(path, "w") as f:
            json.dump(task_data, f, indent=2, default=str)
        return task_id

    def load_task(self, task_id: str) -> dict | None:
        """Load a task by ID. Returns None if not found."""
        path = os.path.join(self.session_dir, f"{task_id}.json")
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return json.load(f)

    def list_tasks(self, limit: int = 10) -> list[dict]:
        """List recent tasks, sorted by most recent first."""
        tasks = []
        if not os.path.isdir(self.session_dir):
            return tasks

        for filename in os.listdir(self.session_dir):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(self.session_dir, filename)
            try:
                with open(path) as f:
                    data = json.load(f)
                tasks.append({
                    "task_id": data.get("task_id", filename[:-5]),
                    "instruction": data.get("instruction", ""),
                    "action_count": data.get("action_count", 0),
                    "saved_at": data.get("saved_at", 0),
                    "completed": data.get("completed", False),
                })
            except (json.JSONDecodeError, OSError):
                continue

        tasks.sort(key=lambda t: t["saved_at"], reverse=True)
        return tasks[:limit]

    def delete_task(self, task_id: str) -> bool:
        """Delete a saved task."""
        path = os.path.join(self.session_dir, f"{task_id}.json")
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
