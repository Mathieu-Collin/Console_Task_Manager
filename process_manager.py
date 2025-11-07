"""
Process Manager - Handles all process-related operations
"""
import psutil
from typing import List, Optional, Tuple
from models import ProcessInfo, ThreadInfo


class ProcessManager:
    """Manages system process operations"""

    def __init__(self):
        self._processes_cache: List[ProcessInfo] = []
        self._last_update = 0

    def get_processes(self, sort_by: str = 'cpu', reverse: bool = True) -> List[ProcessInfo]:
        """
        Get list of all running processes with their information

        Args:
            sort_by: Sort key ('cpu', 'memory', 'pid', 'name')
            reverse: Sort in descending order if True

        Returns:
            List of ProcessInfo objects
        """
        processes = []

        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status']):
            try:
                pinfo = proc.info
                memory_mb = pinfo['memory_info'].rss / (1024 * 1024) if pinfo.get('memory_info') else 0

                process_info = ProcessInfo(
                    pid=pinfo['pid'],
                    name=pinfo['name'] or 'N/A',
                    cpu_percent=pinfo.get('cpu_percent', 0.0) or 0.0,
                    memory_mb=memory_mb,
                    status=pinfo.get('status', 'unknown')
                )
                processes.append(process_info)

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Sort processes
        sort_key_map = {
            'cpu': lambda p: p.cpu_percent,
            'memory': lambda p: p.memory_mb,
            'pid': lambda p: p.pid,
            'name': lambda p: p.name.lower()
        }

        if sort_by in sort_key_map:
            processes.sort(key=sort_key_map[sort_by], reverse=reverse)

        self._processes_cache = processes
        return processes

    def get_process_threads(self, pid: int) -> Tuple[List[ThreadInfo], Optional[str]]:
        """
        Get threads for a specific process

        Args:
            pid: Process ID

        Returns:
            Tuple of (list of ThreadInfo, error message if any)
        """
        try:
            proc = psutil.Process(pid)
            threads = []

            for thread in proc.threads():
                thread_info = ThreadInfo(
                    thread_id=thread.id,
                    user_time=thread.user_time,
                    system_time=thread.system_time
                )
                threads.append(thread_info)

            return threads, None

        except psutil.NoSuchProcess:
            return [], "Process no longer exists"
        except psutil.AccessDenied:
            return [], "Access denied"
        except Exception as e:
            return [], f"Error: {str(e)}"

    def get_process_exe(self, pid: int) -> Tuple[Optional[str], Optional[str]]:
        """
        Get executable path for a process

        Args:
            pid: Process ID

        Returns:
            Tuple of (exe path, error message if any)
        """
        try:
            proc = psutil.Process(pid)
            exe_path = proc.exe()
            return exe_path, None

        except psutil.NoSuchProcess:
            return None, "Process no longer exists"
        except psutil.AccessDenied:
            return None, "Access denied"
        except Exception as e:
            return None, f"Error: {str(e)}"

    def kill_process(self, pid: int, include_children: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Kill a process and optionally its children

        Args:
            pid: Process ID
            include_children: Kill child processes too

        Returns:
            Tuple of (success, error message if any)
        """
        try:
            proc = psutil.Process(pid)

            if include_children:
                # Get children before terminating parent
                children = proc.children(recursive=True)

                # Terminate parent
                proc.terminate()

                # Terminate children
                for child in children:
                    try:
                        child.terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                # Wait for termination
                gone, alive = psutil.wait_procs([proc] + children, timeout=3)

                # Force kill if still alive
                for p in alive:
                    try:
                        p.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            else:
                proc.terminate()
                proc.wait(timeout=3)

            return True, None

        except psutil.NoSuchProcess:
            return False, "Process no longer exists"
        except psutil.AccessDenied:
            return False, "Access denied - requires administrator privileges"
        except psutil.TimeoutExpired:
            # Try force kill
            try:
                proc.kill()
                return True, None
            except Exception as e:
                return False, f"Failed to kill process: {str(e)}"
        except Exception as e:
            return False, f"Error: {str(e)}"

