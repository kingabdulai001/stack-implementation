from stack import Stack, StackEmptyError


class ExpressionError(ValueError):
    """Raised when an expression is invalid or cannot be evaluated."""


# Internal names for the unary (sign) operators, so that they are not
# confused with binary subtraction / addition.
UNARY_MINUS = "neg"
UNARY_PLUS = "pos"

BINARY_OPERATORS = ("+", "-", "*", "/")

# Higher number = binds more tightly (evaluated first).
PRECEDENCE = {
    "+": 1,
    "-": 1,
    "*": 2,
    "/": 2,
    UNARY_MINUS: 3,
    UNARY_PLUS: 3,
}

# Binary operators are left-associative: 8 / 4 * 2 means (8 / 4) * 2.
# Unary operators are right-associative: - - 5 means -(-5).
RIGHT_ASSOCIATIVE = {UNARY_MINUS, UNARY_PLUS}

# Number of decimal places kept when a result is not a whole number.
DECIMAL_PLACES = 10


# ---------------------------------------------------------------------------
# Step 1: Tokenizing
# ---------------------------------------------------------------------------

def _parse_number(text):
    """Convert the text of a number token into an int or a float."""
    if text.count(".") > 1 or text == ".":
        raise ExpressionError(f"invalid number '{text}'")
    if "." in text:
        return float(text)
    return int(text)


def tokenize(expression):
    """Split an expression string into a list of tokens and validate the order.

    Tokens are:
      - numbers (int or float)
      - the strings "+", "-", "*", "/", "(", ")"
      - UNARY_MINUS / UNARY_PLUS for a sign in front of an operand

    The function uses a simple state variable, expect_operand:
      True  -> the next token must start an operand (number, "(" or a sign)
      False -> the next token must be a binary operator or ")"
    This is how errors such as "3 + * 2" or "3 4" are detected.
    """
    tokens = []
    expect_operand = True
    i = 0
    length = len(expression)

    while i < length:
        char = expression[i]

        # Spaces and tabs between tokens are ignored.
        if char.isspace():
            i += 1
            continue

        # A number: a run of digits and decimal points, e.g. 12, 3.5, .25
        if char.isdigit() or char == ".":
            start = i
            while i < length and (expression[i].isdigit() or expression[i] == "."):
                i += 1
            number_text = expression[start:i]
            if not expect_operand:
                raise ExpressionError(
                    f"missing operator before '{number_text}' (position {start + 1})"
                )
            tokens.append(_parse_number(number_text))
            expect_operand = False
            continue

        position = i + 1  # 1-based position, easier for people to read

        if char == "(":
            if not expect_operand:
                raise ExpressionError(
                    f"missing operator before '(' (position {position})"
                )
            tokens.append("(")
            # After "(" we still expect an operand.

        elif char == ")":
            if expect_operand:
                raise ExpressionError(
                    f"missing operand before ')' (position {position})"
                )
            tokens.append(")")
            # After ")" we expect an operator, so expect_operand stays False.

        elif char in BINARY_OPERATORS:
            if expect_operand:
                # A "+" or "-" where an operand is expected is a sign.
                if char == "-":
                    tokens.append(UNARY_MINUS)
                elif char == "+":
                    tokens.append(UNARY_PLUS)
                else:
                    raise ExpressionError(
                        f"missing operand before '{char}' (position {position})"
                    )
            else:
                tokens.append(char)
                expect_operand = True

        else:
            raise ExpressionError(
                f"unsupported character '{char}' (position {position})"
            )

        i += 1

    if not tokens:
        raise ExpressionError("empty expression")
    if expect_operand:
        raise ExpressionError("expression ends without a final operand")

    return tokens


# ---------------------------------------------------------------------------
# Step 2: Infix -> Reverse Polish Notation (shunting-yard, uses a Stack)
# ---------------------------------------------------------------------------

def _should_pop(top, current):
    """Decide if the operator on top of the stack must be output before
    the current operator is pushed."""
    if top == "(":
        return False
    if current in RIGHT_ASSOCIATIVE:
        return PRECEDENCE[top] > PRECEDENCE[current]
    return PRECEDENCE[top] >= PRECEDENCE[current]


def infix_to_rpn(tokens):
    """Convert infix tokens to Reverse Polish Notation using an operator stack.

    Example: [3, "+", 5, "*", 2]  ->  [3, 5, 2, "*", "+"]
    """
    output = []
    operators = Stack()

    for token in tokens:
        if isinstance(token, (int, float)):
            # Numbers go straight to the output.
            output.append(token)

        elif token == "(":
            operators.push(token)

        elif token == ")":
            # Pop operators to the output until the matching "(" is found.
            while not operators.is_empty() and operators.peek() != "(":
                output.append(operators.pop())
            if operators.is_empty():
                raise ExpressionError("unmatched ')' - no opening '(' for it")
            operators.pop()  # discard the "("

        else:
            # An operator: first pop any operators that must be done before it.
            while not operators.is_empty() and _should_pop(operators.peek(), token):
                output.append(operators.pop())
            operators.push(token)

    # Move any remaining operators to the output.
    while not operators.is_empty():
        top = operators.pop()
        if top == "(":
            raise ExpressionError("unmatched '(' - missing closing ')'")
        output.append(top)

    return output


# ---------------------------------------------------------------------------
# Step 3: Evaluate Reverse Polish Notation (uses a Stack)
# ---------------------------------------------------------------------------

def _apply_binary(operator, left, right):
    """Apply a binary operator to two numbers."""
    if operator == "+":
        return left + right
    if operator == "-":
        return left - right
    if operator == "*":
        return left * right
    if operator == "/":
        if right == 0:
            raise ExpressionError("division by zero")
        return left / right
    raise ExpressionError(f"unknown operator '{operator}'")


def evaluate_rpn(rpn_tokens):
    """Evaluate a list of RPN tokens using a value stack and return the number.

    Numbers are pushed. When an operator is read, its operand(s) are popped,
    the operator is applied, and the result is pushed back.
    """
    values = Stack()

    try:
        for token in rpn_tokens:
            if isinstance(token, (int, float)):
                values.push(token)
            elif token == UNARY_MINUS:
                values.push(-values.pop())
            elif token == UNARY_PLUS:
                values.push(+values.pop())
            else:
                # The right operand was pushed last, so it is popped first.
                right = values.pop()
                left = values.pop()
                values.push(_apply_binary(token, left, right))

        result = values.pop()
    except StackEmptyError:
        raise ExpressionError("malformed expression - missing operand") from None
    except OverflowError:
        raise ExpressionError("number too large to calculate") from None

    if not values.is_empty():
        raise ExpressionError("malformed expression - too many operands")

    return result


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def evaluate_expression(expression):
    """Evaluate one expression string and return the numeric result.

    Raises ExpressionError if the expression is invalid.
    """
    tokens = tokenize(expression)
    rpn = infix_to_rpn(tokens)
    return evaluate_rpn(rpn)


def format_result(value):
    """Turn a numeric result into clean text for the output file.

    - Whole numbers are written without a decimal point: 2.0 -> "2"
    - Other numbers are rounded to DECIMAL_PLACES and trailing zeros removed:
      3.5 -> "3.5", 10 / 3 -> "3.3333333333"
    """
    if isinstance(value, int):
        return str(value)

    if value != value or value in (float("inf"), float("-inf")):
        raise ExpressionError("result is not a finite number")

    rounded = round(value, DECIMAL_PLACES)
    if rounded == int(rounded):
        return str(int(rounded))  # also turns -0.0 into "0"

    text = f"{rounded:.{DECIMAL_PLACES}f}".rstrip("0").rstrip(".")
    return text
