from __future__ import annotations

import hashlib
from os import unlink
from os.path import exists
from unittest.mock import MagicMock

import pytest
from openai_responses import OpenAIMock
from openai_responses import mock as openai_mocker

from playsmart import Playsmart, PlaysmartError


@openai_mocker()
def test_basic_prompt(openai_mock: OpenAIMock, playwright_page: MagicMock) -> None:
    """This scenario ensure that the basic code path works as intended provided Playwright and OpenAI did not break."""
    openai_mock.chat.completions.create.response = {
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {
                    "content": '```python\npage.locator("[name=\'email\']").fill("hello@example.tld")\n```',
                    "role": "assistant",
                },
            }
        ]
    }

    smart_playwright = Playsmart(browser_tab=playwright_page, openai_key="sk-fake123", cache_path=".shouldnotexist")

    res = smart_playwright.want("Fill the email input with hello@example.tld", use_cache=False)

    assert len(res) == 1
    assert not exists(".shouldnotexist")

    openai_mock.chat.completions.create.response = None

    with pytest.raises(PlaysmartError, match="OpenAI LLM API call failed"):
        smart_playwright.want("Fill the email input with hello@example.tld", use_cache=False)


@openai_mocker()
def test_caching_basic(openai_mock: OpenAIMock, playwright_page: MagicMock) -> None:
    """In that scenario we want the minimum insurance that our caching layer works."""

    # we insert a valid mock response for OpenAI
    openai_mock.chat.completions.create.response = {
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {
                    "content": '```python\npage.locator("[name=\'email\']").fill("hello@example.tld")\n```',
                    "role": "assistant",
                },
            }
        ]
    }

    # construct a basic Playsmart instance
    smart_playwright = Playsmart(browser_tab=playwright_page, openai_key="sk-fake123", cache_path=".shouldexistafter")

    # the fingerprint is computed using relative scripts src
    assert smart_playwright._fingerprint == hashlib.sha256(b"", usedforsecurity=False).hexdigest()

    # the cache object is lazily created, after first prompt
    assert smart_playwright._cache is None

    smart_playwright.want("Fill the email input with hello@example.tld")

    assert smart_playwright._cache is not None

    # the I/O is invoked synchronously, saving each time a new cache entry is there
    assert exists(".shouldexistafter")

    # purposely kill the OpenAI mock to ensure we leverage the cache!
    openai_mock.chat.completions.create.response = None

    res = smart_playwright.want("Fill the email input with hello@example.tld")

    assert len(res) == 1

    with smart_playwright.context("my page"):
        # this will fail, as we have no cache available in that particular context
        with pytest.raises(PlaysmartError, match="OpenAI LLM API call failed"):
            smart_playwright.want("Fill the email input with hello@example.tld")

    unlink(".shouldexistafter")


def test_existing_cache_preload(playwright_page: MagicMock, cache_file: str) -> None:
    smart_playwright = Playsmart(
        browser_tab=playwright_page,
        openai_key="sk-fake123",
        cache_path=cache_file,
    )

    res = smart_playwright.want("Fill the email input with hello@example.tld")

    assert len(res) == 1


def test_cache_via_preset(playwright_page: MagicMock) -> None:
    """We may need to enforce a cache key per hostname if our logic does not apply."""
    from os import environ

    environ["PLAYSMART_CACHE_PRESET"] = "example.tld=v1.22"

    smart_playwright = Playsmart(
        browser_tab=playwright_page,
        openai_key="sk-fake123",
        cache_path=".shouldnotexistafter",
    )

    #: should virtually be sha256(v1.22)
    assert smart_playwright._fingerprint == "999db56e818ea6623b3459a9fca4b77114056a743e1ac250c204ff04973d5014"

    del environ["PLAYSMART_CACHE_PRESET"]

    #: still internally cached!
    assert smart_playwright._fingerprint == "999db56e818ea6623b3459a9fca4b77114056a743e1ac250c204ff04973d5014"

    #: no longer cache preset set!
    smart_playwright = Playsmart(
        browser_tab=playwright_page,
        openai_key="sk-fake123",
        cache_path=".shouldnotexistafter",
    )

    assert smart_playwright._fingerprint == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    assert not exists(".shouldnotexistafter")


@openai_mocker()
def test_llm_went_south(openai_mock: OpenAIMock, playwright_page: MagicMock) -> None:
    """We should not expect the LLM to perfectly follow orders. Sometimes it just return garbage."""

    # we insert an unexpected mock response for OpenAI
    openai_mock.chat.completions.create.response = {
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"content": "```js\ndocument.nonsense\n```", "role": "assistant"},
            }
        ]
    }

    smart_playwright = Playsmart(browser_tab=playwright_page, openai_key="sk-fake123", cache_path=".shouldnotexist")

    with pytest.raises(
        PlaysmartError, match="LLM seems to have responded with an unparsable content. Did it fail to follow instructions?"
    ):
        smart_playwright.want("Fill the email input with hello@example.tld", use_cache=False)


@openai_mocker()
def test_llm_bypass_markdown(openai_mock: OpenAIMock, playwright_page: MagicMock) -> None:
    """We should not expect the LLM to perfectly follow orders. This case handle the LLM decide NOT TO USE markdown!"""

    # we insert an unexpected mock response for OpenAI
    openai_mock.chat.completions.create.response = {
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"content": 'page.locator("[name=\'email\']").fill("hello@example.tld")', "role": "assistant"},
            }
        ]
    }

    smart_playwright = Playsmart(browser_tab=playwright_page, openai_key="sk-fake123", cache_path=".shouldnotexist")

    res = smart_playwright.want("Fill the email input with hello@example.tld", use_cache=False)

    assert len(res) == 1
