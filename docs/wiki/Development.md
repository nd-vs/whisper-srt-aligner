# Development

For an editable checkout install with `python -m pip install -e .`. Unit tests do
not download models:

```text
python -m unittest discover -s tests -v
python -m compileall -q src
```

CI covers Windows/Linux and Python 3.10/3.12. GPU/runtime and real-media accuracy
are separate integration checks, not implied by passing unit tests.

See [the demo](../demo/README.md) for a reproducible media workflow and measured
results. [Launch materials](../launch/Review.md) include the proposed release,
metadata, announcements and first-user study; they are drafts until approved.

Wiki pages live here so changes can be reviewed with code. `scripts/export_wiki.py`
exports them with links rewritten for the separate GitHub wiki repository.
The exporter does not publish anything. Keep this folder as the source of truth.
