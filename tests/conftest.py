from __future__ import annotations

import json
import typing
from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock

import pytest

from playsmart import version


@pytest.fixture(scope="session")
def playwright_page() -> MagicMock:
    # we create a fake Playwright Page instance
    # ensure basic methods/properties are there
    return MagicMock(
        content=lambda: """<html><head><style type="text/css">
            h1 {
              text-align: center;
              font-size: 120px;
              font-family: Helvetica, Verdana, Arial;
            }
            </style>
            </head><body><h1>You spelled it wrong.</h1>
            <script src="/assets/index.KodKi87.js"/>
            </body></html>""",
        url="https://example.tld/this/that",
        locator=lambda x: MagicMock(fill=lambda y: None, page=MagicMock()),
    )


@pytest.fixture(scope="function")
def cache_file() -> typing.Generator[str]:
    with NamedTemporaryFile("w") as fp:
        fp.write(
            json.dumps(
                {
                    "__version__": version,
                    "example.tld": {
                        "app_fingerprint": "14b9fd56bc1c69fcff6c33bfe0048b9eded09c113f89a8d9d814b2a5ceb359d4",
                        "generic": {
                            "Fill the email input with hello@example.tld": "```python\n"
                            'page.locator("[name=\'email\']").fill("hello@example.tld")\n```'
                        },
                        "contexts": {},
                    },
                }
            )
        )
        fp.seek(0)
        yield fp.name
