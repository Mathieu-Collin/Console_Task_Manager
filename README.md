# Console Task Manager for Windows

A professional htop-like task manager for Windows Command Prompt, built in Python. This project demonstrates system programming skills and process management capabilities for cybersecurity portfolios.

## Features

- **Real-time Process Monitoring**: Display running processes with PID, name, CPU usage, and memory consumption
- **Interactive Navigation**: Use arrow keys to navigate through the process list
- **Thread Inspection**: View all threads and sub-processes for any selected process
- **Process Termination**: Kill processes and their associated threads with proper permission handling
- **Executable Path Display**: Show the source executable path of any process
- **Optimized Performance**: Smart pagination to display only visible processes, ensuring fluid interface
- **Professional UI**: Clean console interface with static control panel

## Requirements

- Python 3.7+
- Windows OS
- Administrator privileges (recommended for full functionality)

## Installation

1. Clone or download this repository

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the application with:
```bash
python main.py
```

**Note**: For full access to all processes and kill operations, run as Administrator.

## Controls

| Key | Action |
|-----|--------|
| ↑ / ↓ | Navigate up/down through process list |
| **T** | Show threads/sub-processes of selected process |
| **K** | Kill selected process and all associated threads |
| **E** | Display executable path of selected process |
| **Q** | Quit the application |

## Architecture

The project follows a clean, modular architecture:

- **main.py**: Application entry point and main controller
- **process_manager.py**: Handles all process operations (listing, inspection, termination)
- **ui_manager.py**: Manages the console user interface with curses
- **models.py**: Data models for processes and threads
- **config.py**: Centralized configuration settings

## Technical Highlights

### System Programming
- Direct interaction with Windows process API via psutil
- Proper handling of process permissions and access rights
- Thread-level process inspection

### Performance Optimization
- Smart pagination: Only processes visible on screen are rendered
- Non-blocking input handling for smooth user experience
- Efficient process list caching with configurable refresh intervals

### Security Considerations
- Graceful handling of access denied errors
- Safe process termination with timeout handling
- Protection against zombie processes

## Cybersecurity Portfolio Value

This project demonstrates:
- **System-level programming** expertise
- **Windows internals** understanding
- **Process management** skills
- **User interface design** for system tools
- **Error handling** and security considerations
- **Professional code quality** with proper documentation

## Error Handling

The application gracefully handles:
- Access denied errors for protected processes
- Non-existent processes (race conditions)
- Terminal resize events
- Permission issues
- Zombie processes

## Future Enhancements

Potential improvements:
- Network connection monitoring per process
- Process search and filtering
- CPU/Memory usage graphs
- Configuration file support
- Export process list to file
- Custom sorting options

## License

This project is part of a personal portfolio for educational and demonstration purposes.

## Author

Created as part of a cybersecurity engineering portfolio project.

---

**Note**: This tool is designed for system monitoring and management. Always use responsibly and only on systems you have permission to manage.

