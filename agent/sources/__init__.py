"""Live data source modules.

One file per real HK API. Each module exposes one or more pure `fetch_*`
functions; the `@tool` wrappers in agent/tools.py call into them.

This separation keeps the tool registry thin and the real network/parsing
logic isolated for testing and reuse.
"""
