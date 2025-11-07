"""
Data models for Console Task Manager
"""
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class ProcessInfo:
    """Represents information about a system process"""
    pid: int
    name: str
    cpu_percent: float
    memory_mb: float
    exe_path: Optional[str] = None
    status: Optional[str] = None

    def __str__(self) -> str:
        return f"{self.pid:>7}  {self.name:<30}  {self.cpu_percent:>6.1f}%  {self.memory_mb:>8.1f} MB"


@dataclass
class ThreadInfo:
    """Represents information about a thread"""
    thread_id: int
    user_time: float
    system_time: float

    def __str__(self) -> str:
        return f"  Thread {self.thread_id:>7}  User: {self.user_time:.2f}s  System: {self.system_time:.2f}s"

