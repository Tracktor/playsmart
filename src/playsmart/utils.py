from __future__ import annotations

import re


def extract_code_from_markdown(source: str, language: str = "python") -> str:
    """Retrieve the content of a source code embedded in a Markdown document."""
    match = re.search(rf"```{language.lower()}\n(.*?)\n```", source, re.DOTALL)

    if not match:
        raise ValueError(f"{language.capitalize()} code snippet not found in source")

    return re.sub(r'(["\']#.*?["\'])', lambda e: f"'{re.sub(r'(?<!\\):', r'\\:', e.group(1).strip('\'"'))}'", match.group(1))


def extract_playwright_instruction(source: str) -> list[tuple[str, list[str]]]:
    """The LLM usually return a plain Python code with one or several instruction. This extracts them.

    Given a source code, find every call to a Playwright 'page' and extract for each the
    method name and given arguments."""
    instructions = []

    # the regex works as follows: extract two groups
    #   first) method name
    #   second) arguments of the method
    # regardless of the originating variable
    for raw_instruction in re.findall(r'\.([a-zA-Z_]\w*)\s*\(((?:[^()"]|"(?:\\.|[^"\\])*")*)\)', source):
        page_method, method_arguments = raw_instruction

        # the args are in plain text
        # we want to "smart" split them
        method_arguments = extract_python_arguments(method_arguments)

        instructions.append((page_method, method_arguments))

    return instructions


def extract_python_arguments(source_arguments: str) -> list[str]:
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
                pass  # todo: some args may be constants/int/float etc... find a way!

            args.append(arg)

    return args
