# Implementation Status

Date: 2026-03-31

## Completed

- Replaced old SET/TEMP/PWM runtime path with STM32 telemetry parser.
- Added ACK message handling.
- Added outgoing command support with CMD: <name> (including CHARGE).
- Added auto-trigger logic based on temperature threshold.
- Simplified config to only active runtime sections.
- Simplified logger schema to telemetry/ack/event rows.
- Removed obsolete protocol artifacts and outdated docs.

## Current Runtime Contract

Incoming telemetry example:

T:43440, V:0, I:6 mA, STATE:1, Temp: -1.2 C

Outgoing test command:

CMD: CHARGE

Incoming ACK:

ACK: CMD: CHARGE

## Remaining Hardware Responsibility

Any board-specific behavior and constants should be maintained in firmware files only (for this repository, the firmware source under arduino/...).
