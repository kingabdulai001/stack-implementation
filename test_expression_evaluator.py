import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from stack import Stack, StackEmptyError
from expression_evaluator import (
    ExpressionError,
    evaluate_expression,
    format_result,
    infix_to_rpn,
    tokenize,
)
from main import is_separator, process_file, process_lines

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


def calc(expression):
    """Evaluate an expression and return the formatted text result."""
    return format_result(evaluate_expression(expression))


class TestStack(unittest.TestCase):
    """Test case 13 and general stack behaviour."""

    def test_new_stack_is_empty(self):
        stack = Stack()
        self.assertTrue(stack.is_empty())
        self.assertEqual(len(stack), 0)

    def test_push_then_peek_returns_top_without_removing(self):
        stack = Stack()
        stack.push(1)
        stack.push(2)
        self.assertEqual(stack.peek(), 2)
        self.assertEqual(len(stack), 2)

    def test_pop_follows_lifo_order(self):
        stack = Stack()
        for item in ("a", "b", "c"):
            stack.push(item)
        self.assertEqual([stack.pop(), stack.pop(), stack.pop()], ["c", "b", "a"])
        self.assertTrue(stack.is_empty())

    def test_pop_on_empty_stack_raises(self):
        with self.assertRaises(StackEmptyError):
            Stack().pop()

    def test_peek_on_empty_stack_raises(self):
        with self.assertRaises(StackEmptyError):
            Stack().peek()

    def test_empty_stack_error_is_an_index_error(self):
        with self.assertRaises(IndexError):
            Stack().pop()


class TestAssignmentExamples(unittest.TestCase):
    """Test cases 1-3: the examples shown in the assignment brief."""

    def test_example_1(self):
        self.assertEqual(calc("3 + 5 * 2"), "13")

    def test_example_2(self):
        # The scanned brief appears to show 17, but correct precedence gives 16.
        self.assertEqual(calc("(8 / 4) + 7 * 2"), "16")

    def test_example_3(self):
        self.assertEqual(calc("10 - (2 + 3) * 4"), "-10")


class TestArithmetic(unittest.TestCase):
    """Test cases 4-8: precedence, associativity, division, negatives, spaces."""

    def test_parentheses_change_precedence(self):
        self.assertEqual(calc("2 + 3 * 4"), "14")
        self.assertEqual(calc("(2 + 3) * 4"), "20")
        self.assertEqual(calc("((1 + 2) * (3 + 4)) / 3"), "7")

    def test_equal_precedence_is_left_to_right(self):
        self.assertEqual(calc("8 / 4 * 2"), "4")
        self.assertEqual(calc("10 - 3 - 2"), "5")
        self.assertEqual(calc("100 / 10 / 5"), "2")

    def test_decimal_division(self):
        self.assertEqual(calc("7 / 2"), "3.5")
        self.assertEqual(calc("10 / 3"), "3.3333333333")
        self.assertEqual(calc("1 / 8"), "0.125")

    def test_decimal_numbers(self):
        self.assertEqual(calc("12.5 * 2 - 5"), "20")
        self.assertEqual(calc("0.1 + 0.2"), "0.3")

    def test_negative_results(self):
        self.assertEqual(calc("2 - 5"), "-3")
        self.assertEqual(calc("1 - 2.5"), "-1.5")

    def test_unary_signs(self):
        self.assertEqual(calc("-5"), "-5")
        self.assertEqual(calc("3 * -2"), "-6")
        self.assertEqual(calc("-3 * (2 - 6)"), "12")
        self.assertEqual(calc("-(2 + 3)"), "-5")
        self.assertEqual(calc("+4 - -1"), "5")

    def test_whitespace_variations(self):
        self.assertEqual(calc("3+5*2"), "13")
        self.assertEqual(calc("   3   +   5 *2   "), "13")
        self.assertEqual(calc("\t( 8/4 )+7*2"), "16")

    def test_shunting_yard_produces_rpn(self):
        self.assertEqual(infix_to_rpn(tokenize("3 + 5 * 2")), [3, 5, 2, "*", "+"])
        self.assertEqual(infix_to_rpn(tokenize("(3 + 5) * 2")), [3, 5, "+", 2, "*"])


class TestInvalidExpressions(unittest.TestCase):
    """Test cases 9-12: invalid input raises a clear ExpressionError."""

    def assert_error(self, expression, expected_text):
        with self.assertRaises(ExpressionError) as context:
            evaluate_expression(expression)
        self.assertIn(expected_text, str(context.exception))

    def test_missing_closing_parenthesis(self):
        self.assert_error("(2 + 3", "unmatched '('")

    def test_missing_opening_parenthesis(self):
        self.assert_error("2 + 3)", "unmatched ')'")

    def test_missing_operand_between_operators(self):
        self.assert_error("3 + * 2", "missing operand")

    def test_missing_final_operand(self):
        self.assert_error("3 +", "ends without a final operand")

    def test_empty_parentheses(self):
        self.assert_error("()", "missing operand")

    def test_missing_operator(self):
        self.assert_error("3 4", "missing operator")
        self.assert_error("2(3)", "missing operator")

    def test_unsupported_characters(self):
        self.assert_error("4 $ 2", "unsupported character '$'")
        self.assert_error("2 ^ 3", "unsupported character '^'")
        self.assert_error("x + 1", "unsupported character 'x'")

    def test_invalid_number(self):
        self.assert_error("1.2.3 + 1", "invalid number")

    def test_division_by_zero(self):
        self.assert_error("5 / 0", "division by zero")
        self.assert_error("5 / (2 - 2)", "division by zero")

    def test_empty_expression(self):
        self.assert_error("   ", "empty expression")


class TestFormatting(unittest.TestCase):

    def test_whole_float_has_no_decimal_point(self):
        self.assertEqual(format_result(2.0), "2")

    def test_negative_zero_is_written_as_zero(self):
        self.assertEqual(format_result(-0.0), "0")

    def test_non_integer_keeps_its_decimals(self):
        self.assertEqual(format_result(2.25), "2.25")


class TestLineProcessing(unittest.TestCase):
    """Test case 14: multiple expressions with separators."""

    def test_separator_detection(self):
        self.assertTrue(is_separator("-----"))
        self.assertTrue(is_separator("  ---  "))
        self.assertFalse(is_separator("--"))
        self.assertFalse(is_separator("--5"))
        self.assertFalse(is_separator("3 - 2"))

    def test_multiple_expressions_with_separators(self):
        lines = ["3 + 5 * 2", "-----", "(8 / 4) + 7 * 2", "-----", "10 - (2 + 3) * 4"]
        output, errors = process_lines(lines)
        self.assertEqual(output, ["13", "-----", "16", "-----", "-10"])
        self.assertEqual(errors, [])

    def test_separator_text_is_preserved_exactly(self):
        output, _ = process_lines(["1 + 1", "----------", "2 * 2"])
        self.assertEqual(output, ["2", "----------", "4"])

    def test_blank_lines_are_kept_blank_not_zero(self):
        output, errors = process_lines(["1 + 1", "", "   ", "2 + 2"])
        self.assertEqual(output, ["2", "", "", "4"])
        self.assertEqual(errors, [])

    def test_invalid_line_gets_error_marker_and_processing_continues(self):
        output, errors = process_lines(["3 + * 2", "-----", "6 * 7"])
        self.assertTrue(output[0].startswith("ERROR: "))
        self.assertEqual(output[1:], ["-----", "42"])
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0][0], 1)  # line number of the bad expression


class TestEndToEnd(unittest.TestCase):
    """Test case 15: run the real program on files."""

    EXPECTED_SAMPLE_OUTPUT = (
        "13\n-----\n16\n-----\n-10\n-----\n4\n-----\n3.5\n-----\n-3\n"
        "-----\n7\n-----\n12\n-----\n20\n-----\n3.3333333333\n"
    )

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_main_script_reads_input_and_writes_expected_output(self):
        input_path = os.path.join(PROJECT_DIR, "input.txt")
        output_path = os.path.join(self.temp_dir, "output.txt")
        with open(input_path, encoding="utf-8") as file:
            input_before = file.read()

        completed = subprocess.run(
            [sys.executable, os.path.join(PROJECT_DIR, "main.py"), input_path, output_path],
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        with open(output_path, encoding="utf-8") as file:
            self.assertEqual(file.read(), self.EXPECTED_SAMPLE_OUTPUT)
        # input.txt must not be modified.
        with open(input_path, encoding="utf-8") as file:
            self.assertEqual(file.read(), input_before)

    def test_submitted_output_file_is_up_to_date(self):
        with open(os.path.join(PROJECT_DIR, "output.txt"), encoding="utf-8") as file:
            self.assertEqual(file.read(), self.EXPECTED_SAMPLE_OUTPUT)

    def test_assignment_sample_file(self):
        input_path = os.path.join(self.temp_dir, "in.txt")
        output_path = os.path.join(self.temp_dir, "out.txt")
        with open(input_path, "w", encoding="utf-8") as file:
            file.write("3 + 5 * 2\n-----\n(8 / 4) + 7 * 2\n-----\n10 - (2 + 3) * 4\n")
        errors = process_file(input_path, output_path)
        self.assertEqual(errors, [])
        with open(output_path, encoding="utf-8") as file:
            self.assertEqual(file.read(), "13\n-----\n16\n-----\n-10\n")

    def test_input_and_output_must_be_different_files(self):
        input_path = os.path.join(self.temp_dir, "in.txt")
        with open(input_path, "w", encoding="utf-8") as file:
            file.write("1 + 1\n")
        with self.assertRaises(ValueError):
            process_file(input_path, input_path)
        with open(input_path, encoding="utf-8") as file:
            self.assertEqual(file.read(), "1 + 1\n")

    def test_missing_input_file_gives_error_exit_code(self):
        completed = subprocess.run(
            [sys.executable, os.path.join(PROJECT_DIR, "main.py"),
             os.path.join(self.temp_dir, "does_not_exist.txt"),
             os.path.join(self.temp_dir, "out.txt")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 1)
        self.assertIn("input file not found", completed.stderr)


if __name__ == "__main__":
    unittest.main()
