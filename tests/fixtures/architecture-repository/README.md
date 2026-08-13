# Dispatch sample

Dispatch sample accepts shipment requests through a public HTTP API. The API validates requests,
stores shipment state in PostgreSQL, and publishes accepted work to a durable queue. A separate
worker consumes the queue, calls an external carrier API, and writes status changes back to the
database. Operations staff view shipment state through an internal console backed by the same API.

Runtime boundaries:

- `dispatch-api`: owned synchronous entry point and shipment orchestration
- `dispatch-worker`: owned asynchronous carrier integration
- PostgreSQL: owned durable shipment state
- Work queue: owned durable handoff between API and worker
- Carrier API: third-party fulfilment dependency
- Customer and operations clients: external and internal actors

The primary deployment consists of the API and worker containers, a managed PostgreSQL database,
and a managed queue. Authentication middleware and database migrations are implementation details,
not independently operated components.
