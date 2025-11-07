"""
Configuration file for Console Task Manager
"""

# Display settings
REFRESH_INTERVAL = 1.0  # seconds
MIN_LINES_REQUIRED = 20
MIN_COLS_REQUIRED = 80

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

# Controls
CONTROLS = [
    ('↑/↓', 'Navigate'),
    ('T', 'Threads'),
    ('K', 'Kill'),
    ('E', 'Exe Path'),
    ('Q', 'Quit'),
]

