"""Centralized logging system for ncsdl."""

import sys
from datetime import datetime
from pathlib import Path

# ANSI Color Codes
CLR_RESET = "\033[0m"
CLR_BOLD = "\033[1m"
CLR_GREEN = "\033[32m"
CLR_RED = "\033[31m"
CLR_YELLOW = "\033[33m"
CLR_BLUE = "\033[34m"
CLR_CYAN = "\033[36m"
CLR_DIM = "\033[2m"


class Logger:
    def __init__(self, log_file: str | Path | None = None):
        self.log_file = Path(log_file) if log_file else None
        self.use_colors = False  # Disabled: Colors are considered unprofessional by user

    def _format(self, msg: str, color: str = "", bold: bool = False) -> str:
        if not self.use_colors:
            return msg
        prefix = color + (CLR_BOLD if bold else "")
        return f"{prefix}{msg}{CLR_RESET}"

    def _write_to_file(self, level: str, msg: str):
        if not self.log_file:
            return
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.log_file, "a") as f:
                f.write(f"[{timestamp}] {level.upper()}: {msg}\n")
        except Exception:
            pass

    def info(self, msg: str, bold: bool = False):
        print(self._format(msg, bold=bold))
        self._write_to_file("info", msg)

    def success(self, msg: str):
        print(self._format(msg, color=CLR_GREEN))
        self._write_to_file("success", msg)

    def warning(self, msg: str):
        print(self._format(msg, color=CLR_YELLOW))
        self._write_to_file("warning", msg)

    def error(self, msg: str):
        print(self._format(msg, color=CLR_RED), file=sys.stderr)
        self._write_to_file("error", msg)

    def heading(self, msg: str):
        print(f"\n{self._format(msg, color=CLR_CYAN, bold=True)}")
        self._write_to_file("heading", msg)

    def dim(self, msg: str):
        print(self._format(msg, color=CLR_DIM))
        self._write_to_file("debug", msg)

    def progress(self, current: int, total: int, status: str, msg: str):
        """Standardized progress log: [x/y] status: msg"""
        # Determine color for status
        status_lower = status.lower()
        color = CLR_RESET
        if "ok" in status_lower or "success" in status_lower:
            color = CLR_GREEN
        elif "skip" in status_lower:
            color = CLR_YELLOW
        elif "fail" in status_lower or "error" in status_lower:
            color = CLR_RED
        
        count_str = f"[{current}/{total}]"
        formatted_status = self._format(f"{status}:", color=color, bold=True)
        
        full_msg = f"{count_str} {formatted_status} {msg}"
        print(full_msg)
        self._write_to_file("progress", f"{count_str} {status}: {msg}")


# Global logger instance
# Default to ncsdl.log in the current directory if it exists or is specifically enabled
logger = Logger(log_file="ncsdl.log")
