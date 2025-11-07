"""
Configuration file for Console Task Manager
"""

# Display settings
REFRESH_INTERVAL = 0.05  # seconds - UI refresh rate (50ms for ultra-responsive)
MIN_LINES_REQUIRED = 20
MIN_COLS_REQUIRED = 80

# Process update intervals (managed by ProcessManager)
FULL_UPDATE_INTERVAL = 3.0  # Full process list update (less frequent)
PARTIAL_UPDATE_INTERVAL = 1.0  # Fast CPU update only (less frequent)

# Process display columns
COLUMN_WIDTHS = {
    'pid': 8,
    'name': 30,
    'cpu': 8,
    'memory': 10,
}

# Color pairs
COLOR_NORMAL = 1
COLOR_SELECTED = 2
COLOR_HEADER = 3
COLOR_CONTROLS = 4
COLOR_ERROR = 5
COLOR_NEW_PROCESS = 6  # Green for new processes
COLOR_HIGH_CPU = 7  # Yellow for high CPU usage
COLOR_VERY_HIGH_CPU = 8  # Red for very high CPU usage

# Thresholds for highlighting
HIGH_CPU_THRESHOLD = 50.0  # Yellow above 50%
VERY_HIGH_CPU_THRESHOLD = 80.0  # Red above 80%
SIGNIFICANT_CPU_CHANGE = 10.0  # Show trend indicator if change > 10%
SIGNIFICANT_MEMORY_CHANGE = 50.0  # Show trend indicator if change > 50 MB
NEW_PROCESS_HIGHLIGHT_DURATION = 5  # seconds to highlight new processes

# Controls
CONTROLS = [
    ('↑/↓', 'Navigate'),
    ('T', 'Threads'),
    ('K', 'Kill'),
    ('E', 'Exe Path'),
    ('Q', 'Quit'),
]
