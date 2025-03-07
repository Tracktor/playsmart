from __future__ import annotations

import argparse
from getpass import getpass
from os import environ
from sys import argv

from playwright.sync_api import sync_playwright

from ._version import version
from .core import Playsmart, context_debug
from .exceptions import PlaysmartError


def cli() -> None:
    parser = argparse.ArgumentParser(prog="playsmart", description="Realtime LLM agent for interacting with web pages")

    parser.add_argument(
        "target",
        help="Initial URL to get started",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        dest="verbose",
        help="Enable advanced debugging",
    )

    args = parser.parse_args(argv[1:])

    print(
        rf"""
      _____  _                                      _
     |  __ \| |             {version}                  | |
     | |__) | | __ _ _   _ ___ _ __ ___   __ _ _ __| |_
     |  ___/| |/ _` | | | / __| '_ ` _ \ / _` | '__| __|
     | |    | | (_| | |_| \__ | | | | | | (_| | |  | |_
     |_|    |_|\__,_|\__, |___|_| |_| |_|\__,_|_|   \__|
                      __/ |
                     |___/
    """
    )

    print("!> Welcome to the playground")
    print("!> This will help you to quickly write tests")
    print("!> Prefix your prompt with '/f' to supress the cache")
    print("!> You can manipulate the browser at will in between prompts!", end="\n\n")

    openai_key = None

    if "OPENAI_API_KEY" not in environ:
        openai_key = getpass("(Warning) Provide OpenAI API Key: ")

        if not openai_key:
            exit(1)

    debug_enabled = args.verbose is True

    driver = sync_playwright().start()
    chrome = driver.chromium.launch(headless=False)
    page = chrome.new_page()

    page.goto(args.target)

    smart_hub = Playsmart(
        browser_tab=page,
        openai_key=openai_key,
    )

    while True:
        try:
            prompt = input("(Your prompt) > ")

            if not prompt:
                break

            need_bypass_cache: bool = prompt.startswith("/f")

            if need_bypass_cache:
                prompt = prompt[2:].strip()

            if not prompt:
                print("(Error) Invalid prompt")
                continue

            try:
                if debug_enabled:
                    with context_debug():
                        res = smart_hub.want(prompt, use_cache=not need_bypass_cache)
                else:
                    res = smart_hub.want(prompt, use_cache=not need_bypass_cache)
            except PlaysmartError as e:
                print(f"(Error) > {e}")
            else:
                print(f"(Ok) {res}")
        except KeyboardInterrupt:
            print("(Goodbye!)")
            break


if __name__ == "__main__":
    cli()
