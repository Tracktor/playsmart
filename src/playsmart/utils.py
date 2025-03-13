from __future__ import annotations

import re

from bs4 import BeautifulSoup


def extract_code_from_markdown(source: str, language: str = "python") -> str:
    """Retrieve the content of a source code embedded in a Markdown document."""
    match = re.search(rf"```{language.lower()}\n(.*?)\n```", source, re.DOTALL)

    if not match:
        raise ValueError(f"{language.capitalize()} code snippet not found in source")

    return re.sub(r'(["\']#.*?["\'])', lambda e: f"'{re.sub(r'(?<!\\):', r'\\:', e.group(1).strip('\'"'))}'", match.group(1))


def extract_playwright_instruction(source: str) -> list[tuple[str, list[str | float | int]]]:
    """The LLM usually return a plain Python code with one or several instruction. This extracts them.

    Given a source code, find every call to a Playwright 'page' and extract for each the
    method name and given arguments."""
    instructions = []

    for match in re.finditer(r"\.([a-zA-Z_]\w*)\s*\(", source.replace(".mouse.", ".mouse().")):
        method_name: str = match.groups()[0]
        method_end_pos: int = match.end()

        inner_body: str = ""

        count_parenthesis_open = 1

        for c in source[method_end_pos:]:
            if c == "(":
                count_parenthesis_open += 1
            elif c == ")":
                count_parenthesis_open -= 1

            if count_parenthesis_open == 0:
                break

            inner_body += c

        if count_parenthesis_open:
            raise ValueError("expected ')' character for method body delimiter")

        instructions.append((method_name, extract_python_arguments(inner_body)))

    return instructions


def extract_python_arguments(source_arguments: str) -> list[str | float | int]:
    """A smart way to parse a list of arguments from a raw source arguments.

    This function immediately complete the function extract_playwright_instruction.
    In our attempt to parse the LLM response, we need to extract arguments and
    re-inject them later manually.

    This function extracts arguments from a string and converts them to appropriate types.
    It handles strings, integers, and floating point numbers, including those with units or symbols.

    Arguments can be:
    - Quoted strings: "example" or 'example'
    - Numbers: 123, 45.67
    - Numbers with units: "10km", "20$", "30°C", etc.
    - Keyword arguments: key=value

    Support only str args for now.

    Returns:
        A list of parsed arguments with their appropriate types.

    Examples:
    >>> extract_python_arguments('"arg0", "arg1", "arg2"')
    ['arg0', 'arg1', 'arg2']
    >>> extract_python_arguments('"arg0", "arg1", arg2, 9988')
    ['arg0', 'arg1', 'arg2', 9988]
    >>> extract_python_arguments("x=998, y=91982.11")
    [998, 91982.11]
    >>> extract_python_arguments("'-99%', '3.14m'")
    [-99, 3.14]
    >>> extract_python_arguments('"price=499$, distance=10km"')
    [499, 10]
    """
    # Split the arguments by comma, respecting quotes
    # Example: '"arg0", "arg1", arg2' -> ['"arg0"', '"arg1"', 'arg2']
    pattern = r',\s*(?=(?:[^"\']*["|\'][^"\']*["|\'])*[^"\']*$)'
    args = re.split(pattern, source_arguments)

    result = []

    for arg in args:
        arg = arg.strip()

        # Handle quoted strings: "example" or 'example'
        if (arg.startswith('"') and arg.endswith('"')) or (arg.startswith("'") and arg.endswith("'")):
            # Extract content within quotes
            # Example: '"arg0"' -> 'arg0'
            stripped_arg = arg[1:-1]

            # Use the same regex to extract all numbers, whether from key-value pairs or strings with units
            numbers = re.findall(r"[-+]?\d+(?:[.,]\d+)?", stripped_arg)
            if numbers:
                # If multiple numbers or if there's an '=' symbol, extract all numbers
                # Example: "price=499$, distance=10km" -> [499, 10]
                if len(numbers) > 1 or "=" in stripped_arg:
                    for num in numbers:
                        result.append(convert_to_number(num))
                    continue
                # If just one number at the beginning (case of numbers with units)
                # Examples: "10km" -> 10, "20$" -> 20, "30°C" -> 30
                elif re.match(r"^[-+]?\d", stripped_arg):
                    result.append(convert_to_number(numbers[0]))
                    continue

            # If not a number with unit, add as string
            # Example: '"hello"' -> 'hello'
            result.append(stripped_arg)
            continue

        # Handle keyword arguments (x=123 or x='abc')
        # Examples: "x=998" -> 998, "x='abc'" -> 'abc'
        if "=" in arg and not (arg.startswith('"') or arg.startswith("'")):
            _, value = arg.split("=", 1)
            value = value.strip()

            # Check if value is quoted
            # Example: "x='abc'" -> 'abc'
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                result.append(value[1:-1])  # Add string value without quotes
                continue

            # Try to convert to number if not quoted
            # Example: "x=998" -> 998
            try:
                result.append(convert_to_number(value))
                continue
            except ValueError:
                pass

        # Handle direct numbers or identifier strings
        # Examples: "9988" -> 9988, "arg2" -> 'arg2'
        try:
            # Try to convert to a number first
            # Example: "9988" -> 9988
            result.append(convert_to_number(arg))
        except ValueError:
            # If not a number, keep as string
            # Example: "arg2" -> 'arg2'
            result.append(arg)

    return result


def convert_to_number(value: str) -> int | float:
    """Convert a string to its appropriate numeric type (int or float)."""
    value = value.replace(",", ".")
    if "." in value:
        return float(value)
    return int(value)


def strip_needless_tags_for_llm(source: str) -> str:
    """Remove most useless tags that won't be useful for our prompt. Wasting tokens at scale!"""

    soup = BeautifulSoup(source, "html.parser")

    for e in soup.find_all():
        if hasattr(e, "name") and e.name in ["style", "link", "script", "path", "meta"]:
            e.decompose()

    return source
