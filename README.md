Playwright! Playsmart!
----------------------

[![Downloads](https://img.shields.io/pypi/dm/playsmart.svg)](https://pypistats.org/packages/playsmart)
[![Supported Versions](https://img.shields.io/pypi/pyversions/playsmart.svg)](https://pypi.org/project/playsmart)

End the never ending game of having to manually record, inspect, and update your E2E tests with Playwright.

This chunk of code[...]

```python
page.locator("#dkDj87djDA-reo").fill("hello@world.tld")
page.locator("#dflfkZkfAA-reo").fill("$ecr!t")
page.get_by_role("button", name="Log In").click()
```

will become

```python
from playsmart import Playsmart

smart_hub = Playsmart(
    browser_tab=page,
)

with smart_hub.context("login page"):
    smart_hub.want("fill email input with hello@world.tld")
    smart_hub.want("fill password input with $ecr!t")
    smart_hub.want("click on login")
```

nicer, isn't it?

### Get started!

Install **Playsmart** via PyPI

```shell
pip install playsmart
```

_requires Python 3.10+_

Before you get started, either:

- export `OPENAI_API_KEY`
- or set `openai_key=...` parameter within `Playsmart` class constructor.

Here's the minimum runnable example:

```python
from playwright.sync_api import sync_playwright
from playsmart import Playsmart

driver = sync_playwright().start()
chrome = driver.chromium.launch(headless=False)
page = chrome.new_page()

page.goto("https://huggingface.co/docs")

smart_hub = Playsmart(
    browser_tab=page
)

with smart_hub.context("docs page"):
    smart_hub.want("click on PEFT doc section")
```

### OpenAI TPM Errors

Did you get an error immediately?

```
Request too large for gpt-4o in organization org-XlSkSlxsksdS on tokens per min (TPM): Limit 30000, Requested 67653.
```

Ensure your OpenAI project can accept higher limits! See https://platform.openai.com/docs/guides/rate-limits?context=tier-five to learn more.

Your DOM might be too large to be processed by our library. Usually it is because you embed large scripts in your DOM
like when you use a development (webpack/vite live/dev render) server.

### Caching

We know how painful consuming needlessly tokens can be. That's why **Playsmart** have a tiny
caching layer that helps with keeping LLM hints.

You may at any moment disable the cache for a specific instruction as:

```python
smart_hub.want("click on PEFT doc section", use_cache=False)
```

A discrete file, named `.playsmart.cache` will be created. You are encouraged to share this file
across your teams! Commit it!

You may choose a filename at your own convenience via the `cache_path=...` parameter within the `Playsmart` class constructor.

If your application does not have a stable content, you could be embarrassed by the ever invalidating cache.
To remediate to this, set the following environment variable:

```shell
export PLAYSMART_CACHE_PRESET="example.com=v1.22"
# or...
export PLAYSMART_CACHE_PRESET="example.com=v1.22;example.org=v4.33"
```

This will actively prevent the cache to be invalidated.

### The 'want' method in a nutshell

Basically, everything revolve around `Playsmart.want(...)` as you would have already guessed.

There's two types of action you can execute:

A) Immediate action: e.g. I want to click on something
B) Deferred action: e.g. How many orders are marked as 'pending'?

For the case A) you should never expect the method to return anything (aside from empty list).

Finally, for the case B) Playsmart will always translate your query to a (or many) usable `playwright.Locator`.

Here is a solid example for B):

```python
with smart_hub.context("dashboard"):
    locators = smart_hub.want("how many orders are labelled as 'pending'?")

    print(f"we have {locators[0].count()} order(s) pending")
```

Yet, another one:

```python
with smart_hub.context("dashboard"):
    locators = smart_hub.want("list every fields in the form")

    for locator in locators:
        ... # your logic for each 'input<text/select/...>'
```

### Limitation

The "big" caveat here, is that we purposely don't use anything else than DOM analysis.
No computer vision will be used in this project. We saw that introducing it is nice but unfortunately
introduce a lot of "flaky tests".

This immediately prevent you from writing `smart_hub.want("ensure we are on the dashboard page")`.
Most of the time you should write proper assertion yourself.

The project does tremendously reduce the burden of maintaining E2E pipelines.

### Debug runtime

If you are asking yourself "How did we arrive at that result?", use the handy function `context_debug`.

```python
from playsmart import context_debug, Playsmart

smart_hub = Playsmart(
    browser_tab=...
)

with context_debug():
    smart_hub.want("click on PEFT doc section")
```

It will stream a list of detailed events to help you debug your test.

### Disclaimer

This (heuristic) software is still at an early stage and has not been battle tested (yet).
Although we envision a great future for it, it would be unwise to replace your entire E2E suite
with it.

We encourage its incremental adoption and positive feedbacks to help us improve this.

Finally, note that the library is not thread safe.
