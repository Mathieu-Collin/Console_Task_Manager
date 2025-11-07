"""
Console Task Manager for Windows
A htop-like task manager for Windows Command Prompt
"""
import curses
import sys
from process_manager import ProcessManager
from ui_manager import UIManager
from config import REFRESH_INTERVAL


class ConsoleTaskManager:
    """Main application controller"""

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.ui = UIManager(stdscr)
        self.process_manager = ProcessManager()
        self.processes = []
        self.running = True
        self.refresh_timeout_ms = int(REFRESH_INTERVAL * 1000)  # Convert to milliseconds

    def update_processes(self, force: bool = False):
        """Update process list with visible range optimization"""
        # Always get processes - the cache system handles update timing internally
        if force:
            self.process_manager.force_update()

        # Calculate visible range for optimization
        display_height = self.ui.get_display_area_height()
        visible_start = self.ui.scroll_offset
        visible_end = visible_start + display_height

        self.processes = self.process_manager.get_processes(
            sort_by='cpu',
            reverse=True,
            visible_range=(visible_start, visible_end)
        )

    def handle_input(self):
        """Handle user input"""
        key = self.ui.get_input()

        if key == -1:  # No input
            return

        # Navigation
        if key == curses.KEY_UP:
            self.ui.move_selection(-1, len(self.processes))
        elif key == curses.KEY_DOWN:
            self.ui.move_selection(1, len(self.processes))

        # Actions
        elif key in (ord('q'), ord('Q')):
            self.running = False

        elif key in (ord('t'), ord('T')):
            self.show_threads()

        elif key in (ord('k'), ord('K')):
            self.kill_process()

        elif key in (ord('e'), ord('E')):
            self.show_exe_path()

    def show_threads(self):
        """Show threads for selected process"""
        if not self.processes:
            return

        selected_process = self.processes[self.ui.get_selected_index()]
        threads, error = self.process_manager.get_process_threads(selected_process.pid)

        if error:
            lines = [f"Error: {error}"]
        elif not threads:
            lines = ["No threads found"]
        else:
            lines = [f"Process: {selected_process.name} (PID: {selected_process.pid})", ""]
            lines.extend([str(thread) for thread in threads])

        win = self.ui.draw_message_box("Threads", lines)
        if win:
            # Use blocking mode for dialog
            self.stdscr.timeout(-1)  # Block until key press
            self.stdscr.getch()
            self.stdscr.timeout(self.refresh_timeout_ms)  # Restore configured timeout

    def kill_process(self):
        """Kill selected process"""
        if not self.processes:
            return

        selected_process = self.processes[self.ui.get_selected_index()]

        # Show confirmation
        lines = [
            f"Kill process: {selected_process.name}?",
            f"PID: {selected_process.pid}",
            "",
            "Press 'Y' to confirm, any other key to cancel"
        ]

        win = self.ui.draw_message_box("Confirm Kill", lines)
        if win:
            self.stdscr.nodelay(0)
            key = self.stdscr.getch()
            self.stdscr.nodelay(1)

            if key in (ord('y'), ord('Y')):
                success, error = self.process_manager.kill_process(selected_process.pid)

                if success:
                    result_lines = ["Process terminated successfully"]
                else:
                    result_lines = [f"Failed to kill process:", "", f"{error}"]

                win2 = self.ui.draw_message_box("Result", result_lines)
                if win2:
                    self.stdscr.nodelay(0)
                    self.stdscr.getch()
                    self.stdscr.nodelay(1)

                # Force refresh
                self.update_processes(force=True)

            # Redraw UI immediately after dialog closes
            self.ui.clear()
            self.redraw_ui()

    def show_exe_path(self):
        """Show executable path for selected process"""
        if not self.processes:
            return

        selected_process = self.processes[self.ui.get_selected_index()]
        exe_path, error = self.process_manager.get_process_exe(selected_process.pid)

        if error:
            lines = [f"Error: {error}"]
        elif exe_path:
            lines = [
                f"Process: {selected_process.name}",
                f"PID: {selected_process.pid}",
                "",
                "Executable path:",
                exe_path
            ]
        else:
            lines = ["Executable path not available"]

        win = self.ui.draw_message_box("Executable Path", lines)
        if win:
            self.stdscr.timeout(-1)  # Block until key press
            self.stdscr.getch()
            self.stdscr.timeout(self.refresh_timeout_ms)  # Restore configured timeout

        # Redraw UI immediately after dialog closes
        self.ui.clear()
        self.redraw_ui()

    def run(self):
        """Main application loop with event-driven input handling"""
        # Initial update and draw
        self.update_processes()
        self.ui.clear()  # Clear once at start
        self.redraw_ui()

        # Set timeout for getch (in milliseconds) - allows periodic updates
        self.stdscr.timeout(self.refresh_timeout_ms)

        frame_count = 0
        frames_per_update = max(1, int(1.0 / REFRESH_INTERVAL))  # Calculate frames needed for 1s

        while self.running:
            try:
                # Get input with timeout (non-blocking with automatic refresh)
                key = self.stdscr.getch()

                # Handle input if key was pressed - IMMEDIATE RESPONSE
                if key != -1:
                    self.handle_input_key(key)
                    # Redraw immediately for instant feedback (NO data update, just UI)
                    self.ui.draw_process_list(self.processes)
                    self.ui.refresh()
                    # Reset frame counter to avoid immediate update after input
                    frame_count = 0
                else:
                    # Update data periodically (every ~1 second based on REFRESH_INTERVAL)
                    frame_count += 1
                    if frame_count >= frames_per_update:
                        self.update_processes()
                        self.redraw_ui()
                        frame_count = 0

            except KeyboardInterrupt:
                self.running = False
            except Exception as e:
                # Log error and continue
                pass

    def redraw_ui(self):
        """Redraw the user interface (optimized - only draws changed parts)"""
        # Header and controls are drawn once, process list detects changes
        self.ui.draw_header()
        self.ui.draw_process_list(self.processes)
        self.ui.draw_controls()
        self.ui.refresh()

    def handle_input_key(self, key):
        """Handle a single key press event"""
        # Navigation
        if key == curses.KEY_UP:
            self.ui.move_selection(-1, len(self.processes))
        elif key == curses.KEY_DOWN:
            self.ui.move_selection(1, len(self.processes))

        # Actions
        elif key in (ord('q'), ord('Q')):
            self.running = False

        elif key in (ord('t'), ord('T')):
            self.show_threads()

        elif key in (ord('k'), ord('K')):
            self.kill_process()

        elif key in (ord('e'), ord('E')):
            self.show_exe_path()


def main(stdscr):
    """Main entry point"""
    app = ConsoleTaskManager(stdscr)
    app.run()


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
