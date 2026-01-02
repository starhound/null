import asyncio
import os
import subprocess
from typing import Callable, Awaitable

class ExecutionEngine:
    @staticmethod
    async def run_command_and_get_rc(command: str, callback: Callable[[str], None]) -> int:
        """
        Runs command, calls callback with stdout lines, returns exit code.
        """
        # Respect SHELL env var, default to /bin/bash on Linux
        shell = os.environ.get("SHELL", "/bin/bash")
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                shell=True,
                executable=shell
            )

            if process.stdout:
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                    decoded_line = line.decode("utf-8", errors="replace")
                    callback(decoded_line)

            # Wait for the process to exit
            try:
                return await process.wait()
            except ChildProcessError:
                # In some event loops, if the process is already reaped, wait() might fail
                # or warn. We can try to get returncode directly.
                return process.returncode if process.returncode is not None else 255

        except Exception as e:
            callback(f"Error executing command: {e}\n")
            return 127
