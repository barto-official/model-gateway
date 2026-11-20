"""Composition root: wire adapters to ports."""


def create_app() -> None:
    """Build the HTTP application once inbound adapter exists (Phase 0f).

    Raises:
        NotImplementedError: HTTP wiring is not implemented until Phase 0f.
    """
    raise NotImplementedError("HTTP app wiring lands in Phase 0f")
