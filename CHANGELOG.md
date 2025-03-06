# Changelog
All notable changes to charset-normalizer will be documented in this file. This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## 0.1.3 (2025-03-06)

### Fixed
- Unstable cache key with no workaround to force it (see README to see how to apply `PLAYSMART_CACHE_PRESET` environment variable)
- No retries if the LLM gave unparsable content

## 0.1.2 (2025-02-25)

### Fixed
- Not auto retrying prompt on LLM bad code/selector generation.
- Weak fingerprint matching for caching. We started using resources content instead of their uris.

## 0.1.1 (2025-02-21)

### Fixed
- Unparsable LLM answer when the output purposely skip the intended (markdown) format.

## 0.1.0 (2025-02-21)

### Added
- initial release
