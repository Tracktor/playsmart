from __future__ import annotations

import json
import typing

if typing.TYPE_CHECKING:
    from .structures import FieldDict

DEFAULT_CACHE_PATH: typing.Final[str] = ".playsmart.cache"

#: Just an opinionated format, it is simple enough for a LLM to understand its purpose.
FIELDS: typing.Final[list[FieldDict]] = [
    {"xpath": "[name='foo']"},
    {"xpath": "[name='address']"},
    {"xpath": "[name='bar']"},
    {"xpath": "[name='baz']"},
]

#: The initial "system" prompt to guide the LLM on how it should perceive the surrounding world.
WORLD_PROMPT: typing.Final[
    str
] = f"""You are a QA Engineer testing a web application using synchronous Playwright in a live Python interpreter.
- Send me only the relevant code without text, comments or explanations.
- Consider we already have Playwright initialized.
- Use only the variable page to execute the following demand.
- Consider you are already on the good page (no page.goto) dont do any import or close page or the browser at the end of the test.
- Dont create any function or class, just a sequence of Playwright instructions.
- Dont use Playwright method 'evaluate'.
- Never use loops in code, always prefer multiple Playwright redundant calls.
- If I ask to locate for a single field, use Playwright locate method call.
- If I start with "how many", use a single Playwright locator to answer.
- Otherwise if I ask for fields send me a list of them with their xpath as json (in markdown) like given examples: {json.dumps(FIELDS)}
"""  # noqa: E501
