"""
UI Manager - Handles all user interface operations using curses
"""
import curses
from typing import List
from models import ProcessInfo
from config import *


class UIManager:
    """Manages the console user interface"""

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        self.selected_index = 0
        self.scroll_offset = 0
        self.mode = 'normal'  # 'normal', 'threads', 'message'
        self.message = None
        self.message_lines = []

        # Cache for detecting changes
        self._last_drawn_processes = []
        self._last_selected_index = -1
        self._last_scroll_offset = -1
        self._header_drawn = False
        self._controls_drawn = False

        # Initialize colors
        curses.init_pair(COLOR_NORMAL, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(COLOR_SELECTED, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(COLOR_HEADER, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(COLOR_CONTROLS, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(COLOR_ERROR, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(COLOR_NEW_PROCESS, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(COLOR_HIGH_CPU, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(COLOR_VERY_HIGH_CPU, curses.COLOR_RED, curses.COLOR_BLACK)

        # Configure curses
        curses.curs_set(0)  # Hide cursor
        self.stdscr.nodelay(1)  # Non-blocking input
        self.stdscr.keypad(1)  # Enable keypad

    def _get_process_color(self, process: ProcessInfo, is_selected: bool) -> int:
        """Determine the color pair for a process based on its state"""
        if is_selected:
            return COLOR_SELECTED

        # Priority: new process > very high CPU > high CPU > normal
        if process.is_new:
            return COLOR_NEW_PROCESS
        elif process.cpu_percent >= VERY_HIGH_CPU_THRESHOLD:
            return COLOR_VERY_HIGH_CPU
        elif process.cpu_percent >= HIGH_CPU_THRESHOLD:
            return COLOR_HIGH_CPU
        else:
            return COLOR_NORMAL

    def get_display_area_height(self) -> int:
        """Calculate available height for process list (excluding header and controls)"""
        # 1 line header + 1 blank + processes + 1 blank + 2 controls
        return max(self.height - 5, 10)

    def draw_header(self):
        """Draw the header with column titles"""
        try:
            header = f"{'PID':>7}  {'Process Name':<30}  {'CPU %':>7}  {'Memory':>11}"
            self.stdscr.attron(curses.color_pair(COLOR_HEADER))
            self.stdscr.addstr(0, 0, header[:self.width-1].ljust(self.width-1))
            self.stdscr.attroff(curses.color_pair(COLOR_HEADER))
        except curses.error:
            pass

    def draw_controls(self, force: bool = False):
        """Draw the control panel at the bottom"""
        if self._controls_drawn and not force:
            return  # Skip if already drawn

        try:
            # Draw separator line
            separator_y = self.height - 3
            self.stdscr.addstr(separator_y, 0, "─" * (self.width - 1))

            # Draw controls
            controls_y = self.height - 2
            control_text = "  ".join([f"[{key}] {desc}" for key, desc in CONTROLS])

            self.stdscr.attron(curses.color_pair(COLOR_CONTROLS))
            self.stdscr.addstr(controls_y, 0, control_text[:self.width-1].ljust(self.width-1))
            self.stdscr.attroff(curses.color_pair(COLOR_CONTROLS))
            self._controls_drawn = True

        except curses.error:
            pass

    def draw_process_list(self, processes: List[ProcessInfo]):
        """
        Draw the list of processes with pagination and smart coloring (optimized with cache)

        Args:
            processes: List of ProcessInfo to display
        """
        display_height = self.get_display_area_height()
        start_y = 2  # After header and blank line

        # Adjust scroll offset if needed
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + display_height:
            self.scroll_offset = self.selected_index - display_height + 1

        # Detect what changed
        scroll_changed = self._last_scroll_offset != self.scroll_offset
        selection_changed = self._last_selected_index != self.selected_index

        # Draw only visible processes
        for i in range(display_height):
            process_index = self.scroll_offset + i

            if process_index >= len(processes):
                # Clear remaining lines only if scroll changed
                if scroll_changed or process_index < len(self._last_drawn_processes) + self._last_scroll_offset:
                    try:
                        self.stdscr.addstr(start_y + i, 0, " " * (self.width - 1))
                    except curses.error:
                        pass
                continue

            process = processes[process_index]

            # Check if this line needs redrawing
            needs_redraw = False

            if scroll_changed:
                needs_redraw = True  # Redraw all on scroll
            elif process_index == self.selected_index or process_index == self._last_selected_index:
                needs_redraw = True  # Redraw current and previous selection
            elif process_index - self.scroll_offset < len(self._last_drawn_processes):
                # Check if process data changed
                cached_index = process_index - self._last_scroll_offset
                if 0 <= cached_index < len(self._last_drawn_processes):
                    old_proc = self._last_drawn_processes[cached_index]
                    if (old_proc.pid != process.pid or
                        old_proc.cpu_percent != process.cpu_percent or
                        old_proc.memory_mb != process.memory_mb or
                        old_proc.is_new != process.is_new or
                        old_proc.cpu_trend != process.cpu_trend or
                        old_proc.memory_trend != process.memory_trend):
                        needs_redraw = True
            else:
                needs_redraw = True  # New line

            if not needs_redraw:
                continue  # Skip this line - no changes detected

            # Build the line with indicators
            cpu_indicator = process.cpu_trend if process.cpu_trend else " "
            mem_indicator = process.memory_trend if process.memory_trend else " "
            line = f"{process.pid:>7}  {process.name:<30}  {process.cpu_percent:>6.1f}%{cpu_indicator}  {process.memory_mb:>8.1f}{mem_indicator} MB"

            try:
                is_selected = (process_index == self.selected_index)
                color_pair = self._get_process_color(process, is_selected)

                # Apply color and draw
                self.stdscr.attron(curses.color_pair(color_pair))
                self.stdscr.addstr(start_y + i, 0, line[:self.width-1].ljust(self.width-1))
                self.stdscr.attroff(curses.color_pair(color_pair))

            except curses.error:
                pass

        # Update cache - store visible processes
        visible_end = min(self.scroll_offset + display_height, len(processes))
        self._last_drawn_processes = processes[self.scroll_offset:visible_end].copy()
        self._last_selected_index = self.selected_index
        self._last_scroll_offset = self.scroll_offset

    def draw_message_box(self, title: str, lines: List[str]):
        """
        Draw a message box in the center of the screen

        Args:
            title: Title of the message box
            lines: Content lines to display
        """
        box_height = min(len(lines) + 4, self.height - 4)
        box_width = min(max(len(max(lines, key=len, default="")) + 4, 40), self.width - 4)

        start_y = (self.height - box_height) // 2
        start_x = (self.width - box_width) // 2

        # Create window
        try:
            win = curses.newwin(box_height, box_width, start_y, start_x)
            win.box()

            # Draw title
            win.attron(curses.A_BOLD)
            win.addstr(0, 2, f" {title} ")
            win.attroff(curses.A_BOLD)

            # Draw content
            for i, line in enumerate(lines[:box_height-4]):
                win.addstr(i + 2, 2, line[:box_width-4])

            # Draw close instruction
            win.addstr(box_height - 2, 2, "Press any key to close...")

            win.refresh()
            return win

        except curses.error:
            return None

    def move_selection(self, direction: int, total_items: int):
        """
        Move the selection up or down

        Args:
            direction: -1 for up, 1 for down
            total_items: Total number of items in the list
        """
        if total_items == 0:
            self.selected_index = 0
            return

        self.selected_index += direction
        self.selected_index = max(0, min(self.selected_index, total_items - 1))

    def get_selected_index(self) -> int:
        """Get the currently selected index"""
        return self.selected_index

    def reset_selection(self):
        """Reset selection to top"""
        self.selected_index = 0
        self.scroll_offset = 0

    def clear(self):
        """Clear the screen"""
        self.stdscr.clear()
        # Reset cache when clearing
        self._header_drawn = False
        self._controls_drawn = False
        self._last_drawn_processes = []
        self._last_selected_index = -1
        self._last_scroll_offset = -1

    def refresh(self):
        """Refresh the screen"""
        self.stdscr.refresh()

    def get_input(self) -> int:
        """Get user input (non-blocking)"""
        return self.stdscr.getch()
