## Summary

<!-- What does this PR change, and why? -->

## Test plan

- [ ] `pytest` passes locally
- [ ] `ruff check backend engine scripts tests` passes
- [ ] Manually verified in a browser, if this touches `frontend/`
- [ ] `./offline-check.sh` still passes (if this touches engine/model/OCR wiring)

## Checklist

- [ ] No secrets, API keys, or personal data committed
- [ ] No new external network calls introduced at `start` time (only `prepare` may use the network)
- [ ] Updated `README.md` / `docs/` if behavior visible to users changed
