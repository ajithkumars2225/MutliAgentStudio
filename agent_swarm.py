import concurrent.futures
from typing import Dict, List, Any, Callable

class AgentSwarmEngine:
    """
    Enterprise Dynamic Multi-Agent Swarm Engine.
    Decomposes multi-file coding tasks into parallel sub-agent tasks
    and executes them concurrently across worker threads.
    """

    @classmethod
    def decompose_target_tasks(cls, files_list: List[str]) -> List[Dict[str, Any]]:
        """
        Map-Reduce Decomposition: Splits target files into sub-agent work items.
        """
        sub_tasks = []
        for idx, filepath in enumerate(files_list, 1):
            sub_tasks.append({
                "sub_task_id": f"swarm_worker_{idx}",
                "target_file": filepath,
                "role": f"Specialized Coder for {filepath}"
            })
        return sub_tasks

    @classmethod
    def execute_parallel_swarm(cls, sub_tasks: List[Dict[str, Any]], worker_fn: Callable[[Dict[str, Any]], Any], max_workers: int = 4) -> List[Any]:
        """
        Executes sub-agent tasks concurrently across worker threads.
        """
        results = []
        print(f"[Agent Swarm 🐝] Spawning {len(sub_tasks)} sub-agent worker nodes in parallel...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_workers, len(sub_tasks) or 1)) as executor:
            future_to_task = {executor.submit(worker_fn, task): task for task in sub_tasks}
            for future in concurrent.futures.as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    res = future.result()
                    results.append({"task": task, "status": "success", "result": res})
                except Exception as exc:
                    results.append({"task": task, "status": "failed", "error": str(exc)})
        return results
