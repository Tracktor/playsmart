from __future__ import annotations

import pytest

from playsmart.utils import (
    extract_code_from_markdown,
    extract_playwright_instruction,
    extract_python_arguments,
    strip_needless_tags_for_llm,
)


@pytest.mark.parametrize(
    "source, expected_result",
    [
        (
            '"arg0", "arg1", "arg2"',
            (["arg0", "arg1", "arg2"], {}),
        ),
        (
            '"arg0", "arg1","arg2"',
            (["arg0", "arg1", "arg2"], {}),
        ),
        (
            '"arg0","arg1","arg2"',
            (["arg0", "arg1", "arg2"], {}),
        ),
        (
            "'arg0','arg1',     'arg2'",
            (["arg0", "arg1", "arg2"], {}),
        ),
        (
            '"arg0", "arg1", arg2, 9988',
            (["arg0", "arg1", "arg2", 9988], {}),
        ),
        (
            "x=998, y=91982.11",
            ([], {"x": 998, "y": 91982.11}),
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
        ("page.click(\"text='Commander'\")", [("click", (["text='Commander'"], {}))]),
        (
            "element = page.locator('.MuiDataGrid-virtualScroller .MuiDataGrid-cell[data-field=\"id\"]')\n"
            "pending_orders = element.count()",
            [
                ("locator", (['.MuiDataGrid-virtualScroller .MuiDataGrid-cell[data-field="id"]'], {})),
                ("count", ([], {})),
            ],
        ),
        (
            'page.locator("[name=\'password\']").fill("ksfFkfiFSjA")',
            [("locator", (["[name='password']"], {})), ("fill", (["ksfFkfiFSjA"], {}))],
        ),
        (
            "page.locator(\"button:has-text('Commander')\").click()",
            [("locator", (["button:has-text('Commander')"], {})), ("click", ([], {}))],
        ),
        (
            '```python\npage.locator("[name=\'article\']").fill("RandomEquipment")\npage.locator'
            '("[name=\'dateLocation[]\']").nth(0).fill("01 January 2022")\npage.locator("[name=\'dateLocation[]\']")'
            '.nth(1).fill("31 January 2022")\npage.locator("[name=\'option\']").fill("RandomOption")\npage.locator'
            '("[name=\'worksite\']").fill("RandomWorksite")\npage.locator("[name=\'adress\']").fill("123 Random '
            'Street, City")\npage.locator("[name=\'machineDelivery\']").check()\npage.locator("[name=\'hoursConstraints[]\']").'
            'nth(0).fill("08:00")\npage.locator("[name=\'hoursConstraints[]\']").nth(1).fill("17:00")\n'
            "page.locator(\"[name='machineRetrieval']\").check()\n```",
            [
                ("locator", (["[name='article']"], {})),
                ("fill", (["RandomEquipment"], {})),
                ("locator", (["[name='dateLocation[]']"], {})),
                ("nth", ([0], {})),
                ("fill", (["01 January 2022"], {})),
                (
                    "locator",
                    (
                        ["[name='dateLocation[]']"],
                        {},
                    ),
                ),
                ("nth", ([1], {})),
                ("fill", (["31 January 2022"], {})),
                ("locator", (["[name='option']"], {})),
                ("fill", (["RandomOption"], {})),
                ("locator", (["[name='worksite']"], {})),
                ("fill", (["RandomWorksite"], {})),
                ("locator", (["[name='adress']"], {})),
                ("fill", (["123 Random Street, City"], {})),
                ("locator", (["[name='machineDelivery']"], {})),
                ("check", ([], {})),
                ("locator", (["[name='hoursConstraints[]']"], {})),
                ("nth", ([0], {})),
                ("fill", (["08:00"], {})),
                ("locator", (["[name='hoursConstraints[]']"], {})),
                ("nth", ([1], {})),
                ("fill", (["17:00"], {})),
                ("locator", (["[name='machineRetrieval']"], {})),
                ("check", ([], {})),
            ],
        ),
    ],
)
def test_extract_playwright_instruction(
    source: str, expected_result: list[tuple[str, tuple[list[str], dict[str, str]]]]
) -> None:
    assert extract_playwright_instruction(source) == expected_result


@pytest.mark.parametrize(
    "source, expected_result",
    [
        (
            (
                "<html><head><meta title=abc><title>xyz</title></head><body><h2>hello world</h2>"
                "</body><script type=application/javascript>navigator.language='fr'</script></html>"
            ),
            "<html><head><title>xyz</title></head><body><h2>hello world</h2></body></html>",
        )
    ],
)
def test_purify_html_from_tags(source: str, expected_result: str) -> None:
    assert strip_needless_tags_for_llm(source) == expected_result
