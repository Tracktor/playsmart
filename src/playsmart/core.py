from __future__ import annotations

import hashlib
import json
import logging
import os.path
import typing
from contextlib import contextmanager
from os import environ
from urllib.parse import urljoin, urlparse

from httpx import HTTPError, RequestError
from openai import DefaultHttpxClient, OpenAI, OpenAIError
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator, Page

from ._version import version
from .constants import DEFAULT_CACHE_PATH, WORLD_PROMPT
from .exceptions import PlaysmartError
from .structures import CacheObject, FieldDict
from .utils import extract_code_from_markdown, extract_playwright_instruction

logger = logging.getLogger(__name__)


@contextmanager
def context_debug() -> typing.Generator[None]:  # Defensive: debugging purpose only
    old_level = logger.level
    logger.setLevel(logging.DEBUG)
    explain_handler = logging.StreamHandler()
    explain_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(explain_handler)
    yield
    logger.setLevel(old_level)
    logger.removeHandler(explain_handler)


class Playsmart:
    """Awesome class that hugely simplify interacting with ever-changing DOM!

    No more xpath, weird css selectors or having to maintain a consistent unique IDs.

    This standalone add-on need a Playwright "browser tab" also known as a "Page".
    Use OpenAI LLM under the hood. Has a smart caching algorithm integrated.
    A valid OpenAI key is required to make use of this tool.

    We know that LLM browser automation can often fail due to some complex frontend, that
    is why this tool accept a list of hooks to better help this add-on interact with some
    elements such as autocompletes.

    This automatically infers the following arguments from their corresponding environment variables if they are not provided:
        - `openai_key` from `OPENAI_API_KEY`
        - `openai_organization` from `OPENAI_ORG_ID`
        - `openai_project` from `OPENAI_PROJECT_ID`
    """

    def __init__(
        self,
        browser_tab: Page,
        cache_path: str | None = DEFAULT_CACHE_PATH,
        *,
        openai_key: str | None = None,
        openai_organization: str | None = None,
        openai_project: str | None = None,
        openai_model: str = "gpt-4o",
    ) -> None:
        self._openai = OpenAI(
            api_key=openai_key,
            organization=openai_organization,
            project=openai_project,
        )
        self._openai_model = openai_model
        self._page = browser_tab
        self._cache_path: str | None = cache_path
        #: each hostname has a CacheObject tied to him.
        self._cache: dict[str, CacheObject] | None = None
        # used to store latest computed fingerprints (live run)
        self._fingerprints: dict[str, str] = {}

        if self._cache_path is not None and os.path.exists(self._cache_path):
            try:
                with open(self._cache_path) as fp:
                    self._cache = json.load(fp)
            except OSError as e:
                logger.warning(f"unable to access the cache. reason: {e}")
                logger.warning("cache is now disabled")
                self._cache_path = None
            except json.JSONDecodeError as e:
                logger.warning(f"unable to decode the cache. reason: {e}")
                logger.warning("cache will be reset at next prompt query")
            else:
                if "__version__" not in self._cache or version != self._cache["__version__"]:
                    logger.warning("cache will be reset at next prompt query due to a version change")
                    self._cache = {
                        "__version__": version  # type: ignore[dict-item]
                    }

        self._cursor: str | None = None

    @contextmanager
    def context(self, name: str) -> typing.Generator[None]:
        """Temporally set a context name that will be used for the cache key context."""
        self._cursor = name
        logger.debug(f"setting '{name}' as the current context")
        try:
            self._page.wait_for_load_state()
            yield
        finally:
            self._cursor = None

    @property
    def url(self) -> str:
        return self._page.url

    @property
    def host(self) -> str:
        return urlparse(self.url).netloc

    @property
    def _sources(self) -> list[str]:
        """Retrieve a list of sources used by the current page.

        It includes scripts, styles and link modulepreload.
        Prefer local hosted. Fallback on everything.
        """
        current_url = self.url
        current_host = self.host

        local_sources = set()
        sources = set()

        for locator in (
            self._page.locator("script").all()
            + self._page.locator("style").all()
            + self._page.locator("link[rel=modulepreload]").all()
        ):
            resource_src = locator.get_attribute("src") or locator.get_attribute("href")

            if resource_src is None:
                continue

            if not resource_src.lower().startswith("http"):
                resource_src = urljoin(current_url, resource_src)

            sources.add(resource_src)

            if current_host in resource_src:
                local_sources.add(resource_src)

        return sorted(list(local_sources or sources))

    @property
    def _fingerprint(self) -> str:
        """(Incomplete/Not generic) Generate a unique application fingerprint.

        Modern frontend library (React) or framework (Vue) use tool like Vite or
        Webpack to generate assets. They automatically add a suffix to the generated
        JS chunks like (/assets/index.kdDJ76d.js).

        The main idea is to know whenever a frontend deployments occurred. So
        we extract every script src in the app DOM.

        This method is likely to be useless in case of A) no JS used B) JS but no versioning
        C) Using WebAssembly / and so on! We'll need to be smarter!
        """
        if self.host in self._fingerprints:
            return self._fingerprints[self.host]

        resources = []

        forced_input = environ.get("PLAYSMART_CACHE_PRESET", default=None)

        if forced_input is not None:
            for entry in forced_input.split(";"):
                entry = entry.strip()

                try:
                    hostname, forced_tag = tuple(entry.split("="))
                except ValueError:
                    continue

                if self.host != hostname:
                    continue

                resources.append(forced_tag.encode())

        if not resources:
            with DefaultHttpxClient() as client:
                for source in self._sources:
                    try:
                        resources.append(client.get(source).raise_for_status().content)
                    except (RequestError, HTTPError):
                        continue

        self._fingerprints[self.host] = hashlib.sha256(
            b"".join(resources),
            usedforsecurity=False,
        ).hexdigest()

        return self._fingerprints[self.host]

    def _prompt(self, objective: str, use_cache: bool = True, invalid_cache: bool = False) -> str:
        """Host the logic for asking OpenAI LLM to resolve a single objective.

        This method SHOULD NEVER be called directly. It has also the caching
        logic inside. It returns the LLM raw response. Unparsed.
        """
        app_host = self.host
        app_fingerprint = self._fingerprint

        if self._cache is not None:
            if app_host not in self._cache:
                self._cache[app_host] = CacheObject(app_fingerprint=app_fingerprint, generic={}, contexts={})
            else:
                # verify we're still using the same (frontend) version as before!
                if app_fingerprint == self._cache[app_host]["app_fingerprint"]:
                    if use_cache and not invalid_cache:
                        if self._cursor is None:
                            if objective in self._cache[app_host]["generic"]:
                                return self._cache[app_host]["generic"][objective]
                        else:
                            if (
                                self._cursor in self._cache[app_host]["contexts"]
                                and objective in self._cache[app_host]["contexts"][self._cursor]
                            ):
                                return self._cache[app_host]["contexts"][self._cursor][objective]

                        logger.debug(f"cache miss for context({self._cursor or 'Generic'}) with objective: {objective}")
                    else:
                        logger.debug(f"cache ignored for context({self._cursor or 'Generic'}) with objective: {objective}")
                else:
                    logger.debug(
                        f"Cache object invalidated (fingerprint did not match) "
                        f"current({app_fingerprint}) != cached({self._cache[app_host]['app_fingerprint']})"
                    )
                    self._cache[app_host] = CacheObject(app_fingerprint=app_fingerprint, generic={}, contexts={})
        elif self._cache_path is not None:
            logger.debug(f"Application ({app_host}) fingerprint (versioning): {app_fingerprint}")
            logger.debug("Cache object initialization")
            self._cache = {
                "__version__": version  # type: ignore[dict-item]
            }

            self._cache[app_host] = CacheObject(app_fingerprint=app_fingerprint, generic={}, contexts={})

        logger.debug(
            f"requesting OpenAI LLM ({self._openai_model}) for context({self._cursor or 'generic'}) with objective: {objective}"
        )

        prompt = f"""Analyzing end-to-end test scenario (sync playwright in python):

DOM Content:
```html
{self._page.content()}
```

Test Objective: {objective}
"""

        try:
            openai_response = self._openai.chat.completions.create(
                model=self._openai_model,
                messages=[
                    {"role": "system", "content": WORLD_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
        except OpenAIError as e:
            raise PlaysmartError("OpenAI LLM API call failed") from e

        prompt_response = openai_response.choices[0].message.content

        if prompt_response is None:
            raise PlaysmartError("LLM failed to provide an answer to given prompt")

        if self._cache is not None and use_cache is True:
            assert self._cache_path is not None

            if self._cursor is None:
                self._cache[app_host]["generic"][objective] = prompt_response
            else:
                if self._cursor not in self._cache[app_host]["contexts"]:
                    self._cache[app_host]["contexts"][self._cursor] = {}

                self._cache[app_host]["contexts"][self._cursor][objective] = prompt_response

            try:
                with open(self._cache_path, "w") as fp:
                    fp.write(json.dumps(self._cache, indent=2))
            except OSError as e:
                logger.warning(f"unable to save cache using path({self._cache_path}). reason: {e}")

        return prompt_response

    def want(
        self, objective: str, use_cache: bool = True, *, retries: int | None = 3, _retrying: bool = False
    ) -> list[Locator]:
        """The most useful entrypoint. The Playwright prompt! You may order to take action or query elements.

        There's two category of actions you may want to take:

        First,
        If you, for example, order a click on something, everything should happen discretely.
        In that case, the method will return an empty list.

        Second,
        If you, for example, want to list every field in the present page
        In that case, the method will return a list of "Locator".
        """
        response = self._prompt(objective, use_cache=use_cache, invalid_cache=_retrying)

        try:
            # wierd LLM edge case where it can permit itself to avoid markdown
            # heuristic, hello!
            if "```" not in response and "page." in response:
                code = response
            else:
                code = extract_code_from_markdown(response)
        except ValueError:
            logger.debug("the prompt may have returned a list of fields! attempt to extract a JSON payload[...]")

            try:
                if "```" not in response and response.startswith("{"):
                    fields: list[FieldDict] = json.loads(response)
                else:
                    fields = json.loads(
                        extract_code_from_markdown(response, language="json"),
                    )
            except ValueError as e:
                if retries is not None and retries > 0:
                    logger.warning(
                        "LLM seems to have responded with an unparsable content. "
                        f"Retrying! {retries - 1} retry left. Reason: {e}"
                    )
                    return self.want(objective, use_cache=use_cache, retries=retries - 1, _retrying=True)  # type: ignore[call-arg]
                raise PlaysmartError(
                    "LLM seems to have responded with an unparsable content. Did it fail to follow instructions?"
                ) from e

            logger.debug(f"detected fields: {fields}")

            return [self._page.locator(field["xpath"]) for field in fields]
        else:
            instructions = extract_playwright_instruction(code)

            returns = []

            res = None

            for method, args in instructions:
                if not hasattr(self._page, method) and not hasattr(res, method):
                    raise PlaysmartError(
                        f"LLM probably hallucinated. Thought method '{method}' exist in Playwright 'page' methods !"
                    )

                try:
                    root_callable: Page | Locator = self._page if res is None or not hasattr(res, method) else res

                    if root_callable == self._page:
                        logger.debug(f"attempt to execute '{method}' with args: {args}")
                    else:
                        logger.debug(f"nested calls w/ '{method}' with args: {args}")

                    res = getattr(root_callable, method)(*args)

                    #: on ambiguous selectors, take first.
                    if hasattr(res, "count"):
                        # the isinstance is weird but needed
                        # case: MagicMock always return something!
                        if isinstance(res.count(), int) and res.count() > 1:
                            logger.debug("the selector ended selecting multiple element! fallback on first item.")
                            res = res.first

                    if res is not None:
                        if hasattr(res, "page"):
                            logger.debug("method returned a Locator, appending to results!")
                            returns.append(res)
                        else:
                            logger.debug(f"method returned something, but discarded: {res}")
                except TypeError:
                    raise PlaysmartError(f"LLM probably hallucinated. Method '{method}' cannot accept given arguments: {args}")
                except PlaywrightError as e:
                    if "Unexpected token" in str(e) and retries is not None and retries > 0:
                        logger.warning(
                            "LLM failed to produce a valid Playwright selector. "
                            f"Retrying! {retries - 1} retry left. Reason: {e}"
                        )
                        return self.want(objective, use_cache=use_cache, retries=retries - 1, _retrying=True)  # type: ignore[call-arg]
                    raise PlaysmartError(f"LLM failed to produce a valid Playwright selector. reason: {e}") from e

            return returns
