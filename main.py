import os
import re
import sys

from expression_evaluator import ExpressionError, evaluate_expression, format_result

# Default files are looked for in the same folder as this script, so the
# program works no matter which folder it is started from.
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INPUT = os.path.join(PROJECT_DIR, "input.txt")
DEFAULT_OUTPUT = os.path.join(PROJECT_DIR, "output.txt")

# A separator line is three or more hyphens, optionally surrounded by spaces.
SEPARATOR_PATTERN = re.compile(r"^\s*-{3,}\s*$")


def is_separator(line):
    """Return True if the line is a separator line such as '-----'."""
    return bool(SEPARATOR_PATTERN.match(line))


def process_lines(lines):
    """Convert a list of input lines into a list of output lines.

    Returns a tuple (output_lines, errors) where errors is a list of
    (line_number, message) for every invalid expression.
    """
    output_lines = []
    errors = []

    for line_number, line in enumerate(lines, start=1):
        if is_separator(line):
            output_lines.append(line)          # keep the separator exactly
        elif line.strip() == "":
            output_lines.append("")            # keep blank lines as blank
        else:
            try:
                result = evaluate_expression(line)
                output_lines.append(format_result(result))
            except ExpressionError as error:
                output_lines.append(f"ERROR: {error}")
                errors.append((line_number, str(error)))

    return output_lines, errors


def process_file(input_path, output_path):
    """Read input_path, evaluate it, and write output_path.

    Returns the list of (line_number, message) errors.
    """
    if os.path.abspath(input_path) == os.path.abspath(output_path):
        raise ValueError("the output file must be different from the input file")

    # "utf-8-sig" also accepts files saved by Windows Notepad with a BOM.
    with open(input_path, "r", encoding="utf-8-sig") as file:
        lines = file.read().splitlines()

    output_lines, errors = process_lines(lines)

    with open(output_path, "w", encoding="utf-8", newline="\n") as file:
        for out_line in output_lines:
            file.write(out_line + "\n")

    return errors


def main(argv=None):
    """Run the program. Returns an exit code (0 = success)."""
    if argv is None:
        argv = sys.argv[1:]

    if len(argv) > 2:
        print("Usage: python main.py [input_file] [output_file]", file=sys.stderr)
        return 2

    input_path = argv[0] if len(argv) >= 1 else DEFAULT_INPUT
    output_path = argv[1] if len(argv) == 2 else DEFAULT_OUTPUT

    try:
        errors = process_file(input_path, output_path)
    except FileNotFoundError:
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 1
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    for line_number, message in errors:
        print(f"Line {line_number}: invalid expression - {message}", file=sys.stderr)

    print(f"Results written to {output_path}")
    if errors:
        print(f"{len(errors)} expression(s) could not be evaluated (marked ERROR).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
