# Sequence diagrams

Use sequence diagrams for chronological interactions between stable participants. Use architecture for structural relationships and flowchart for decision logic that is not primarily message exchange.

## Semantic and visual grammar

Participants are shared `nodes` (`actor`, `service`, `component`, `external-service`) in stable left-to-right order. Put chronological messages in `sequence.messages`, never in generic edges. Every message has a unique contiguous `order`, label, direction and `kind`: `sync`, `async`, `return`, or `event`. Self-messages are allowed only when they describe meaningful internal work. Use guarded `fragments` for alternatives, exceptions, loops and optional paths; activations are optional and should explain responsibility, not decorate every call. Notes attach to a participant and order. Use `sequence.focalMessages` or `focal: true` for at most two messages.

The diagram reads top-to-bottom. Sync messages use a solid line and filled arrowhead; async/event messages use a solid line and open arrowhead; returns use a dashed line and open arrowhead. Always add text or stroke/arrow differences so colour is never the only distinction. Lifelines remain fixed. Labels sit clear of lines and activations. Exception fragments are visibly bounded and titled.

Budget: 5 lifelines, 12 messages, 1 major alternative/exception fragment, 2 focal messages. Preserve primary interaction and material failures, collapse truthful repeated calls, split overview/detail sequences, never reorder, and record every simplification.

## Compositions

### `standard`

- When to use: general chronological interaction with several peer participants.
- When not to use: a tightly paired request/return or dominant exception is the message.
- Message patterns: mixed synchronous calls, events and occasional returns.
- Lifeline ordering: initiator left, owned services centre, external systems right.
- Message placement: one chronological row per semantic message.
- Request/response: pair where meaningful without inventing acknowledgements.
- Sync/async: solid filled versus open arrowheads plus explicit labels.
- Activations: only around meaningful responsibility spans.
- Exceptions/alternatives: one bounded fragment around affected messages.
- Audiences: mixed or technical.
- Complexity: shared 5/12/1/2 budget.
- Failure modes: unstable participant order, diagonal chronology and labels on lifelines.

### `request-response`

- When to use: a dominant request crosses services and returns a result.
- When not to use: event fan-out or repeated background processing dominates.
- Message patterns: nested sync requests followed by dashed returns.
- Lifeline ordering: caller left, processing chain centre, system of record right.
- Message placement: requests descend; returns align immediately after completed work.
- Request/response: returns are dashed, labelled outcomes, never inferred by colour.
- Sync/async: default sync; async only where source contracts establish it.
- Activations: nested bars may expose call ownership, used sparingly.
- Exceptions/alternatives: bound the failed call and resulting return.
- Audiences: technical and mixed.
- Complexity: normally 3–5 lifelines and 4–10 messages.
- Failure modes: response arrows out of order, excessive activations, implementation trivia.

### `authentication-refresh`

- When to use: login, token validation, refresh or authentication failure handling.
- When not to use: generic authorization policy without chronological exchanges.
- Message patterns: credentials/token request, guarded expiry path, refresh and retry.
- Lifeline ordering: user/client left, application centre, identity provider right.
- Message placement: normal authentication first; refresh/exception fragment below.
- Request/response: distinguish token responses and rejected returns with dashed labelled lines.
- Sync/async: authentication calls are normally sync; background revocation may be async.
- Activations: application and identity spans only where helpful.
- Exceptions/alternatives: labelled fragment with guards such as `[token expired]`.
- Audiences: technical, security, mixed.
- Complexity: one major auth alternative; split protocol details if over budget.
- Failure modes: exposing secrets, unlabeled token failures, looping without termination.

### `async-event`

- When to use: publishers, brokers and consumers interacting asynchronously.
- When not to use: the caller blocks for a direct response.
- Message patterns: publish, delivery, acknowledgement and independent side effects.
- Lifeline ordering: producer left, broker centre, consumers right.
- Message placement: event order is top-to-bottom even when execution is decoupled.
- Request/response: acknowledgements are explicit returns only when source supplies them.
- Sync/async: open arrowheads and `Async`/event labels make semantics non-colour dependent.
- Activations: short consumer work spans, never continuous broker decoration.
- Exceptions/alternatives: retry or dead-letter fragment with a guard and exit.
- Audiences: technical and operational.
- Complexity: collapse repeated deliveries; no more than 12 visible messages.
- Failure modes: implying simultaneity as exact timing, missing broker, fake responses.

### `exception-path`

- When to use: one material failure changes the interaction outcome.
- When not to use: several peer alternatives deserve separate diagrams.
- Message patterns: primary exchange followed by rejected, timeout or recovery messages.
- Lifeline ordering: preserve normal participant order inside and outside the fragment.
- Message placement: keep success above or in the first fragment region; failure below.
- Request/response: failed returns are dashed and explicitly labelled.
- Sync/async: retain original call semantics; failure styling adds boundary and text.
- Activations: end or transfer at the actual failure boundary.
- Exceptions/alternatives: visibly bounded `exception` or `alternative` with a guard.
- Audiences: technical, clinical, operational.
- Complexity: one major fragment and two focal messages maximum.
- Failure modes: red-only failure meaning, fragment covering unrelated messages, no outcome.

## Accessibility, safety, and anti-patterns

The accessible description names participants in visual order and summarises primary messages and material outcomes chronologically. Message labels are SVG text. Line style and arrowhead distinguish sync, async and return. Fragment labels and guards are visible text. Avoid too many lifelines, reordered messages, ambiguous arrows, excessive activation bars, empty labels, colour-only semantics, hidden failures, and unreadably dense protocol detail. Use Editorial Blueprint semantic roles, either shared light/dark template, safe inline SVG, prefixed IDs, no JavaScript, and the shared extraction/self-check pipeline.

## Natural-language workflow

For “Show the login and token-refresh flow as a sequence diagram”: inspect relevant non-secret source; determine audience, purpose and message; identify participants and ordered messages; choose composition; preserve chronology; write `diagram.yaml`; validate; compose HTML from the light/dark template; extract SVG; run self-check to create `validation.json`; render and visually inspect; report fidelity. Default output is the shared four-file directory and PNG is never generated by default.
