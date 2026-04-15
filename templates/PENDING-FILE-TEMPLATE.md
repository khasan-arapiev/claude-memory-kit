# Pending updates - {{SESSION_ID}}

<!--
One-file-per-session staging format. Each H2 is one item.
Allowed types:       rule | fact | decision | correction
Allowed confidence:  high | medium | low
Known placeholders in `target:` paths: {{date}}, {{project-slug}}, {{slug}}

The CLI (`brain pending list`) parses this deterministically — don't
invent new fields; add them to the parser first.
-->

## rule
**target:** docs/strategy/WRITING-RULES.md
**confidence:** high

The actual rule text in plain language. Written so it still makes sense in a future session with no context.

## fact
**target:** docs/reference/EXTERNAL-SYSTEMS.md
**confidence:** high

Meta Pixel ID: 0000000000000000

## decision
**target:** docs/decisions/{{date}}-EXAMPLE-DECISION.md
**confidence:** high

Chose X over Y because Z. Alternatives considered: Y (rejected because A), Z (rejected because B).

## correction
**target:** docs/reference/HOSTING.md
**confidence:** high

Previously documented as A, actual behaviour is B. Update the reference in place.
