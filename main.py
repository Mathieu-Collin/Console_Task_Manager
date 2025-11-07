"""
Console Task Manager for Windows
A htop-like task manager for Windows Command Prompt
"""
import curses
import time
import sys
import os
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
        self.last_refresh = 0

    def update_processes(self, force: bool = False):
        """Update process list"""
        current_time = time.time()

        if force or (current_time - self.last_refresh) >= REFRESH_INTERVAL:
            self.processes = self.process_manager.get_processes(sort_by='cpu', reverse=True)
            self.last_refresh = current_time

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
            self.stdscr.nodelay(0)  # Blocking mode
            self.stdscr.getch()  # Wait for key press
            self.stdscr.nodelay(1)  # Back to non-blocking

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
            self.stdscr.nodelay(0)
            self.stdscr.getch()
            self.stdscr.nodelay(1)

    def run(self):
        """Main application loop"""
        while self.running:
            try:
                # Update process list
                self.update_processes()

                # Draw UI
                self.ui.clear()
                self.ui.draw_header()
                self.ui.draw_process_list(self.processes)
                self.ui.draw_controls()
                self.ui.refresh()

                # Handle input
                self.handle_input()

                # Small sleep to prevent high CPU usage
                time.sleep(0.05)

            except KeyboardInterrupt:
                self.running = False
            except Exception as e:
                # Log error and continue
                pass


def main(stdscr):
    """Entry point for curses application"""
    app = ConsoleTaskManager(stdscr)
    app.run()


def check_terminal():
    """Check if running in a proper terminal"""
    # Check if stdout is redirected
    if not sys.stdout.isatty():
        print("Error: This application must be run in a real terminal window.", file=sys.stderr)
        print("Please run directly from Command Prompt or PowerShell.", file=sys.stderr)
        return False
    return True


if __name__ == '__main__':
    # Check terminal before starting
    if not check_terminal():
        sys.exit(1)

    try:
        # Initialize curses with error handling
        curses.wrapper(main)
    except curses.error as e:
        print(f"\nCurses Error: {e}", file=sys.stderr)
        print("\nPlease ensure you are running this in a standard terminal.", file=sys.stderr)
        print("Try running: python main.py", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nApplication terminated by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected Error: {e}", file=sys.stderr)
        sys.exit(1)
