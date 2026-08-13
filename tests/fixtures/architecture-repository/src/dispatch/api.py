"""Synchronous shipment entry point for the representative architecture fixture."""


def accept_shipment() -> str:
    """Persist a validated shipment and publish its identifier for asynchronous work."""

    return "persist shipment, then enqueue shipment id"
