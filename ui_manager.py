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

        # Initialize colors
        curses.init_pair(COLOR_NORMAL, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(COLOR_SELECTED, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(COLOR_HEADER, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(COLOR_CONTROLS, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(COLOR_ERROR, curses.COLOR_RED, curses.COLOR_BLACK)

        # Configure curses
        curses.curs_set(0)  # Hide cursor
        self.stdscr.nodelay(1)  # Non-blocking input
        self.stdscr.keypad(1)  # Enable keypad

    def get_display_area_height(self) -> int:
        """Calculate available height for process list (excluding header and controls)"""
        # 1 line header + 1 blank + processes + 1 blank + 2 controls
        return max(self.height - 5, 10)

    def draw_header(self):
        """Draw the header with column titles"""
        try:
            header = f"{'PID':>7}  {'Process Name':<30}  {'CPU %':>6}  {'Memory':>10}"
            self.stdscr.attron(curses.color_pair(COLOR_HEADER))
            self.stdscr.addstr(0, 0, header[:self.width-1].ljust(self.width-1))
            self.stdscr.attroff(curses.color_pair(COLOR_HEADER))
        except curses.error:
            pass

    def draw_controls(self):
        """Draw the control panel at the bottom"""
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

        except curses.error:
            pass

    def draw_process_list(self, processes: List[ProcessInfo]):
        """
        Draw the list of processes with pagination

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

        # Draw only visible processes
        for i in range(display_height):
            process_index = self.scroll_offset + i

            if process_index >= len(processes):
                break

            process = processes[process_index]
            line = f"{process.pid:>7}  {process.name:<30}  {process.cpu_percent:>6.1f}%  {process.memory_mb:>8.1f} MB"

            try:
                if process_index == self.selected_index:
                    self.stdscr.attron(curses.color_pair(COLOR_SELECTED))
                    self.stdscr.addstr(start_y + i, 0, line[:self.width-1].ljust(self.width-1))
                    self.stdscr.attroff(curses.color_pair(COLOR_SELECTED))
                else:
                    self.stdscr.addstr(start_y + i, 0, line[:self.width-1])
            except curses.error:
                pass

        # Clear remaining lines in display area
        for i in range(min(len(processes) - self.scroll_offset, display_height), display_height):
            try:
                self.stdscr.addstr(start_y + i, 0, " " * (self.width - 1))
            except curses.error:
                pass

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

    def refresh(self):
        """Refresh the screen"""
        self.stdscr.refresh()

    def get_input(self) -> int:
        """Get user input (non-blocking)"""
        return self.stdscr.getch()
