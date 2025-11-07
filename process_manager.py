"""
Process Manager - Handles all process-related operations
"""
import psutil
import time
from typing import List, Optional, Tuple, Dict
from models import ProcessInfo, ThreadInfo


class ProcessManager:
    """Manages system process operations with intelligent caching"""

    def __init__(self):
        self._processes_cache: Dict[int, ProcessInfo] = {}  # Cache by PID
        self._last_full_update = 0
        self._last_partial_update = 0
        self._update_interval = 2.0  # Full update every 2 seconds
        self._partial_interval = 0.3  # Partial update every 0.3 seconds
        self._last_sort_key = 'cpu'
        self._last_sort_reverse = True
        self._cached_sorted_list = []

        # Initialize CPU measurement for all processes on startup
        self._initialize_cpu_measurements()

    def _initialize_cpu_measurements(self):
        """Initialize CPU measurements for all processes"""
        for proc in psutil.process_iter(['pid']):
            try:
                # First call to cpu_percent() to establish baseline
                proc.cpu_percent(interval=0.0)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

    def get_processes(self, sort_by: str = 'cpu', reverse: bool = True) -> List[ProcessInfo]:
        """
        Get list of all running processes with intelligent caching

        Args:
            sort_by: Sort key ('cpu', 'memory', 'pid', 'name')
            reverse: Sort in descending order if True

        Returns:
            List of ProcessInfo objects
        """
        current_time = time.time()
        needs_sort = False

        # Full update: refresh all processes
        if current_time - self._last_full_update >= self._update_interval:
            self._full_update()
            self._last_full_update = current_time
            self._last_partial_update = current_time
            needs_sort = True
        # Partial update: only update CPU for existing processes
        elif current_time - self._last_partial_update >= self._partial_interval:
            self._partial_update()
            self._last_partial_update = current_time
            needs_sort = True

        # Check if sort parameters changed
        if (self._last_sort_key != sort_by or
            self._last_sort_reverse != reverse or
            needs_sort):

            # Convert cache to list and sort
            processes = list(self._processes_cache.values())

            # Sort processes
            sort_key_map = {
                'cpu': lambda p: p.cpu_percent,
                'memory': lambda p: p.memory_mb,
                'pid': lambda p: p.pid,
                'name': lambda p: p.name.lower()
            }

            if sort_by in sort_key_map:
                processes.sort(key=sort_key_map[sort_by], reverse=reverse)

            # Cache the sorted list
            self._cached_sorted_list = processes
            self._last_sort_key = sort_by
            self._last_sort_reverse = reverse

        return self._cached_sorted_list

    def _full_update(self):
        """Perform a full update of all processes"""
        new_cache = {}

        # Get all PIDs first (fast)
        current_pids = set(psutil.pids())

        # Update or create process info
        for pid in current_pids:
            try:
                proc = psutil.Process(pid)

                # Get basic info
                name = proc.name()
                memory_mb = proc.memory_info().rss / (1024 * 1024)
                status = proc.status()

                # Get CPU - needs special handling
                # cpu_percent() returns 0.0 on first call, so we need to handle it
                if pid in self._processes_cache:
                    # Process already tracked - use non-blocking call
                    cpu_percent = proc.cpu_percent(interval=0.0)
                else:
                    # New process - call twice to get real value
                    proc.cpu_percent(interval=0.0)  # First call establishes baseline
                    try:
                        cpu_percent = proc.cpu_percent(interval=0.01)  # Second call gets actual value (10ms wait)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        cpu_percent = 0.0

                process_info = ProcessInfo(
                    pid=pid,
                    name=name or 'N/A',
                    cpu_percent=cpu_percent,
                    memory_mb=memory_mb,
                    status=status
                )
                new_cache[pid] = process_info

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        self._processes_cache = new_cache

    def _partial_update(self):
        """Perform a fast partial update (only CPU values for cached processes)"""
        pids_to_remove = []

        for pid, process_info in self._processes_cache.items():
            try:
                proc = psutil.Process(pid)
                # Only update CPU (fast)
                process_info.cpu_percent = proc.cpu_percent(interval=0.0)

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Mark for removal
                pids_to_remove.append(pid)

        # Remove dead processes
        for pid in pids_to_remove:
            del self._processes_cache[pid]

    def force_update(self):
        """Force a full update immediately"""
        self._full_update()
        self._last_full_update = time.time()
        self._last_partial_update = time.time()
        # Invalidate cached sorted list to force re-sort
        self._cached_sorted_list = []
        self._last_sort_key = None

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
        proc = None
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
                if proc:
                    proc.kill()
                return True, None
            except Exception as e:
                return False, f"Failed to kill process: {str(e)}"
        except Exception as e:
            return False, f"Error: {str(e)}"
