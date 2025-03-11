from __future__ import annotations

import re


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

    Support only str args for now.
    """
    # Match either:
    # - A quoted string (with escaped quotes allowed)
    # - OR a sequence of non-comma characters
    pattern = r'"((?:\\.|[^"\\])*?)"|\'((?:\\.|[^\'\\])*?)\'|([^,]+)'

    args = []

    for match in re.finditer(pattern, source_arguments):
        # The groups will be either quoted string or non-quoted content
        quoted_double, quoted_single, non_quoted = match.groups()
        arg = (quoted_double or quoted_single or non_quoted).strip()
        if arg:  # Skip empty matches
            # remove string quotes if any
            if (arg.startswith('"') and arg.endswith('"')) or (arg.startswith("'") and arg.endswith("'")):
                arg = arg[1:-1]
            else:
                # LLM might give us kwargs[...]
                # awkward! let's assume we can roughly
                # expect the order to match positional ones.
                if "=" in arg:
                    maybe_key, maybe_arg = arg.split("=", maxsplit=1)
                    if maybe_key.isalpha() and not (
                        (maybe_arg.startswith('"') and maybe_arg.endswith('"'))
                        or (maybe_arg.startswith("'") and maybe_arg.endswith("'"))
                    ):
                        arg = maybe_arg

                # anything from -50 to 50 or even +50
                # catch int and float; positives or negatives!
                if re.match(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", arg):
                    if "." in arg:
                        arg = float(arg)
                    else:
                        arg = int(arg)
                # todo: maybe threat other cases like possible constants

            args.append(arg)

    return args
