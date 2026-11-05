"""verifier-hub library modules.

Each <family>.py exposes a ``register(subparsers)`` and a per-subcommand
``cmd_<name>(args) -> dict`` function.  ``bin/verifier`` lazily imports
each family only when its first-level subcommand is invoked, so startup
stays fast even as more families get added.
"""
