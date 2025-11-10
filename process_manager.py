"""
Process Manager - Handles all process-related operations
"""
import psutil
import time
from typing import List, Optional, Tuple, Dict, Set
from models import ProcessInfo, ThreadInfo
from config import (
    SIGNIFICANT_CPU_CHANGE,
    SIGNIFICANT_MEMORY_CHANGE,
    NEW_PROCESS_HIGHLIGHT_DURATION,
    NORMALIZE_CPU_PERCENT,
    FILTER_SYSTEM_IDLE
)


class ProcessManager:
    """Manages system process operations with intelligent caching"""

    def __init__(self):
        self._processes_cache: Dict[int, ProcessInfo] = {}  # Cache by PID
        self._process_birth_times: Dict[int, float] = {}  # Track when processes were first seen
        self._last_full_update = 0
        self._last_partial_update = 0
        self._update_interval = 2.0  # Full update every 2 seconds
        self._partial_interval = 0.3  # Partial update every 0.3 seconds
        self._last_sort_key = 'cpu'
        self._last_sort_reverse = True
        self._cached_sorted_list = []
        self._visible_pids: Set[int] = set()  # Track visible PIDs for targeted updates

        # Get CPU count for normalization
        self._cpu_count = psutil.cpu_count(logical=True)

        # Initialize CPU measurement for all processes on startup
        self._initialize_cpu_measurements()

    def _normalize_cpu(self, cpu_percent: float) -> float:
        """Normalize CPU percentage if configured"""
        if NORMALIZE_CPU_PERCENT and self._cpu_count > 0:
            # Divide by number of cores to get percentage per core
            return cpu_percent / self._cpu_count
        return cpu_percent

    def _initialize_cpu_measurements(self):
        """Initialize CPU measurements for all processes using fast iteration"""
        # Use process_iter for maximum performance
        for proc in psutil.process_iter(['pid']):
            try:
                # First call to cpu_percent() to establish baseline
                proc.cpu_percent(interval=0.0)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

    def _calculate_trends(self, process_info: ProcessInfo, old_info: Optional[ProcessInfo]):
        """Calculate CPU and memory trends for a process"""
        if old_info is None:
            process_info.cpu_trend = ""
            process_info.memory_trend = ""
            return

        # Update previous values
        process_info.previous_cpu = old_info.cpu_percent
        process_info.previous_memory = old_info.memory_mb

        # CPU trend
        cpu_diff = process_info.cpu_percent - old_info.cpu_percent
        if abs(cpu_diff) >= SIGNIFICANT_CPU_CHANGE:
            process_info.cpu_trend = "▲" if cpu_diff > 0 else "▼"
        else:
            process_info.cpu_trend = ""

        # Memory trend
        memory_diff = process_info.memory_mb - old_info.memory_mb
        if abs(memory_diff) >= SIGNIFICANT_MEMORY_CHANGE:
            process_info.memory_trend = "▲" if memory_diff > 0 else "▼"
        else:
            process_info.memory_trend = ""

    def get_processes(self, sort_by: str = 'cpu', reverse: bool = True, visible_range: Optional[Tuple[int, int]] = None, search_query: str = "") -> List[ProcessInfo]:
        """
        Get list of all running processes with intelligent caching and optional filtering

        Args:
            sort_by: Sort key ('cpu', 'memory', 'pid', 'name')
            reverse: Sort in descending order if True
            visible_range: (start_index, end_index) of visible processes for optimization
            search_query: Filter processes by name (case-insensitive partial match)

        Returns:
            List of ProcessInfo objects
        """
        current_time = time.time()
        needs_sort = False

        # Full update: refresh all processes (but optimized with process_iter)
        if current_time - self._last_full_update >= self._update_interval:
            self._full_update_optimized()
            self._last_full_update = current_time
            self._last_partial_update = current_time
            needs_sort = True
        # Partial update: only update visible processes
        elif current_time - self._last_partial_update >= self._partial_interval:
            self._partial_update_optimized()
            self._last_partial_update = current_time
            needs_sort = True

        # Check if sort parameters changed
        if (self._last_sort_key != sort_by or
            self._last_sort_reverse != reverse or
            needs_sort):

            # Convert cache to list
            processes = list(self._processes_cache.values())

            # Apply search filter if provided
            if search_query.strip():
                search_lower = search_query.lower().strip()
                processes = [
                    proc for proc in processes
                    if search_lower in proc.name.lower()
                ]

            # Update "is_new" flag based on birth time
            current_time = time.time()
            for proc in processes:
                if proc.pid in self._process_birth_times:
                    age = current_time - self._process_birth_times[proc.pid]
                    proc.is_new = age < NEW_PROCESS_HIGHLIGHT_DURATION
                else:
                    proc.is_new = False

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

        # If we have a search query, we need to re-filter the cached list
        elif search_query.strip():
            search_lower = search_query.lower().strip()
            processes = [
                proc for proc in self._cached_sorted_list
                if search_lower in proc.name.lower()
            ]
            # Don't cache filtered results, return them directly
            return processes

        # Update visible PIDs if range provided
        if visible_range and self._cached_sorted_list:
            start_idx, end_idx = visible_range
            # Add buffer (10 processes before/after) for smooth scrolling
            buffer_start = max(0, start_idx - 10)
            buffer_end = min(len(self._cached_sorted_list), end_idx + 10)
            self._visible_pids = {self._cached_sorted_list[i].pid for i in range(buffer_start, buffer_end)}

        return self._cached_sorted_list

    def _full_update_optimized(self):
        """Perform a full update using process_iter for maximum speed"""
        new_cache = {}
        current_time = time.time()

        # Use process_iter with attrs for MUCH faster bulk collection
        # This is 5-10x faster than creating Process objects individually
        attrs = ['pid', 'name', 'memory_info', 'status']

        for proc in psutil.process_iter(attrs=attrs, ad_value=''):
            try:
                info = proc.info
                pid = info['pid']

                # Filter System Idle Process if configured
                if FILTER_SYSTEM_IDLE and pid == 0:
                    continue

                # Get basic info from cached data
                name = info.get('name', 'N/A')
                mem_info = info.get('memory_info')
                memory_mb = mem_info.rss / (1024 * 1024) if mem_info else 0.0
                status = info.get('status', 'unknown')

                # Get CPU - needs special handling with actual Process object
                if pid in self._processes_cache:
                    # Process already tracked - use non-blocking call
                    cpu_percent = self._normalize_cpu(proc.cpu_percent(interval=0.0))
                else:
                    # New process - establish baseline
                    proc.cpu_percent(interval=0.0)
                    try:
                        cpu_percent = self._normalize_cpu(proc.cpu_percent(interval=0.01))
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        cpu_percent = 0.0

                    # Mark as new process
                    self._process_birth_times[pid] = current_time

                # Get old process info for trend calculation
                old_info = self._processes_cache.get(pid)

                process_info = ProcessInfo(
                    pid=pid,
                    name=name or 'N/A',
                    cpu_percent=cpu_percent,
                    memory_mb=memory_mb,
                    status=status
                )

                # Calculate trends
                self._calculate_trends(process_info, old_info)

                new_cache[pid] = process_info

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Clean up birth times for dead processes
        current_pids = set(new_cache.keys())
        dead_pids = set(self._process_birth_times.keys()) - current_pids
        for pid in dead_pids:
            del self._process_birth_times[pid]

        self._processes_cache = new_cache

    def _partial_update_optimized(self):
        """Perform a fast partial update - prioritize visible processes"""
        pids_to_remove = []

        # If we have visible PIDs tracked, update those first
        if self._visible_pids:
            # Update visible processes (high priority)
            for pid in self._visible_pids:
                if pid not in self._processes_cache:
                    continue

                # Skip System Idle if filtered
                if FILTER_SYSTEM_IDLE and pid == 0:
                    continue

                process_info = self._processes_cache[pid]
                try:
                    proc = psutil.Process(pid)

                    # Update CPU and memory for visible processes
                    old_cpu = process_info.cpu_percent
                    old_memory = process_info.memory_mb

                    process_info.cpu_percent = self._normalize_cpu(proc.cpu_percent(interval=0.0))
                    process_info.memory_mb = proc.memory_info().rss / (1024 * 1024)

                    # Update trends
                    cpu_diff = process_info.cpu_percent - old_cpu
                    if abs(cpu_diff) >= SIGNIFICANT_CPU_CHANGE:
                        process_info.cpu_trend = "▲" if cpu_diff > 0 else "▼"
                    else:
                        process_info.cpu_trend = ""

                    memory_diff = process_info.memory_mb - old_memory
                    if abs(memory_diff) >= SIGNIFICANT_MEMORY_CHANGE:
                        process_info.memory_trend = "▲" if memory_diff > 0 else "▼"
                    else:
                        process_info.memory_trend = ""

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pids_to_remove.append(pid)

            # Quick CPU-only update for non-visible processes (lower priority)
            non_visible_pids = set(self._processes_cache.keys()) - self._visible_pids
            for pid in non_visible_pids:
                # Skip System Idle if filtered
                if FILTER_SYSTEM_IDLE and pid == 0:
                    continue

                process_info = self._processes_cache[pid]
                try:
                    proc = psutil.Process(pid)
                    old_cpu = process_info.cpu_percent
                    process_info.cpu_percent = self._normalize_cpu(proc.cpu_percent(interval=0.0))

                    # Update CPU trend only
                    cpu_diff = process_info.cpu_percent - old_cpu
                    if abs(cpu_diff) >= SIGNIFICANT_CPU_CHANGE:
                        process_info.cpu_trend = "▲" if cpu_diff > 0 else "▼"
                    else:
                        process_info.cpu_trend = ""

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pids_to_remove.append(pid)
        else:
            # Fallback: update all processes (CPU only)
            for pid, process_info in self._processes_cache.items():
                # Skip System Idle if filtered
                if FILTER_SYSTEM_IDLE and pid == 0:
                    continue

                try:
                    proc = psutil.Process(pid)
                    old_cpu = process_info.cpu_percent
                    process_info.cpu_percent = self._normalize_cpu(proc.cpu_percent(interval=0.0))

                    cpu_diff = process_info.cpu_percent - old_cpu
                    if abs(cpu_diff) >= SIGNIFICANT_CPU_CHANGE:
                        process_info.cpu_trend = "▲" if cpu_diff > 0 else "▼"
                    else:
                        process_info.cpu_trend = ""

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pids_to_remove.append(pid)

        # Remove dead processes
        for pid in pids_to_remove:
            del self._processes_cache[pid]
            if pid in self._process_birth_times:
                del self._process_birth_times[pid]
            if pid in self._visible_pids:
                self._visible_pids.discard(pid)

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
