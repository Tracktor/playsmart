from __future__ import annotations

import pytest

from playsmart.utils import extract_code_from_markdown, extract_playwright_instruction, extract_python_arguments


@pytest.mark.parametrize(
    "source, expected_result",
    [
        (
            '"arg0", "arg1", "arg2"',
            ["arg0", "arg1", "arg2"],
        ),
        (
            '"arg0", "arg1","arg2"',
            ["arg0", "arg1", "arg2"],
        ),
        (
            '"arg0","arg1","arg2"',
            ["arg0", "arg1", "arg2"],
        ),
        (
            "'arg0','arg1',     'arg2'",
            ["arg0", "arg1", "arg2"],
        ),
        (
            '"arg0", "arg1", arg2, 9988',
            ["arg0", "arg1", "arg2", "9988"],
        ),
    ],
)
def test_extract_python_arguments(source: str, expected_result: list[str]) -> None:
    assert extract_python_arguments(source) == expected_result


@pytest.mark.parametrize(
    "source, expected_result",
    [
        ("hello world **markdown**!\n\n```python\nimport xyz\n```", "import xyz"),
        (
            "hello world **markdown**!\n\n```python\nimport xyz\n\npage.hello(a, b, c, d)\npage.quit()\n```",
            "import xyz\n\npage.hello(a, b, c, d)\npage.quit()",
        ),
        (
            "hello world **markdown**!\n\n```python\nimport xyz\n\npage.hello(a, b, c, d)\npage.quit()\n"
            "```\nhello world **markdown**!",
            "import xyz\n\npage.hello(a, b, c, d)\npage.quit()",
        ),
    ],
)
def test_extract_code_from_markdown(source: str, expected_result: str) -> None:
    assert extract_code_from_markdown(source) == expected_result


@pytest.mark.parametrize(
    "source",
    [
        "hello world **markdown**!\n\n```python import xyz```",
        "hello world **markdown**!\n\n```zython\nimport xyz\n\npage.hello(a, b, c, d)\npage.quit()\n```",
        "hello world **markdown**!\n\n```js\nimport xyz\n\npage.hello(a, b, c, d)\npage.quit()\n```\nhello world **markdown**!",
    ],
)
def test_invalid_code_from_markdown(source: str) -> None:
    with pytest.raises(ValueError, match="code snippet not found in source"):
        extract_code_from_markdown(source)


@pytest.mark.parametrize(
    "source, expected_result",
    [
        ("page.click(\"text='Commander'\")", [("click", ["text='Commander'"])]),
        (
            "element = page.locator('.MuiDataGrid-virtualScroller .MuiDataGrid-cell[data-field=\"id\"]')\n"
            "pending_orders = element.count()",
            [
                ("locator", ['.MuiDataGrid-virtualScroller .MuiDataGrid-cell[data-field="id"]']),
                ("count", []),
            ],
        ),
        (
            'page.locator("[name=\'password\']").fill("ksfFkfiFSjA")',
            [("locator", ["[name='password']"]), ("fill", ["ksfFkfiFSjA"])],
        ),
    ],
)
def test_extract_playwright_instruction(source: str, expected_result: list[tuple[str, list[str]]]) -> None:
    assert extract_playwright_instruction(source) == expected_result
