import json
import re
import sys


def main():
    try:
        # Read the tool input from stdin
        input_data = sys.stdin.read().strip()
        if not input_data:
            sys.exit(0)

        payload = json.loads(input_data)

        # Extract the command line argument from tool invocation arguments
        command_line = payload.get("CommandLine", "")
        if not command_line:
            # Fallback checks for different parameter names
            command_line = payload.get("command", payload.get("command_line", ""))

        # Inspect for destructive patterns
        destructive_patterns = [
            r"rm\s+-rf\s+/",
            r"rm\s+-f\s+/",
            r"rm\s+-r\s+/",
            r"rm\s+--no-preserve-root",
        ]

        for pattern in destructive_patterns:
            if re.search(pattern, command_line):
                sys.stderr.write(
                    f"Security Error: Blocked destructive command: '{command_line}'\n"
                )
                sys.exit(2)  # Exit code 2 blocks tool execution in Antigravity

        sys.exit(0)

    except Exception as e:
        sys.stderr.write(f"Validation hook error: {e}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
