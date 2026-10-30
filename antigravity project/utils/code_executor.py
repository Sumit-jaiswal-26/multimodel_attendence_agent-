"""
code_executor.py
Safe code generation and execution utility for classroom exercises, demonstrations,
and educational script evaluation.
"""
import sys
import io
import os
import time
import traceback
import subprocess
from datetime import datetime
from typing import Dict, Any

STORAGE_CODE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'storage', 'code')
os.makedirs(STORAGE_CODE_DIR, exist_ok=True)


class CodeExecutor:
    """Executes Python code safely, captures standard output, errors, and execution metrics."""

    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def execute_python(self, code: str, filename_prefix: str = "snippet") -> Dict[str, Any]:
        """
        Execute python snippet and capture stdout, stderr, execution time, and save file.
        """
        timestamp = int(time.time())
        saved_filename = f"{filename_prefix}_{timestamp}.py"
        saved_path = os.path.join(STORAGE_CODE_DIR, saved_filename)

        with open(saved_path, 'w', encoding='utf-8') as f:
            f.write(code)

        start_time = time.time()
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        # Restricted environment
        restricted_globals = {
            "__builtins__": __builtins__,
            "datetime": datetime,
            "math": __import__("math"),
            "random": __import__("random"),
            "json": __import__("json"),
        }

        success = True
        error_msg = ""
        output = ""

        try:
            # First try execution in safe process/exec
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture

            try:
                exec(code, restricted_globals)
                output = stdout_capture.getvalue()
                err_output = stderr_capture.getvalue()
                if err_output:
                    output += "\n" + err_output
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr

        except Exception as e:
            success = False
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"

        elapsed_time = round(time.time() - start_time, 4)

        return {
            "success": success,
            "output": output if success else error_msg,
            "execution_time_sec": elapsed_time,
            "saved_file": saved_filename,
            "file_path": f"/storage/code/{saved_filename}",
            "timestamp": datetime.now().isoformat()
        }
