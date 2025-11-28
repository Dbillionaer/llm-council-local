## MODIFIED Requirements
### Requirement: Message Re-run
When a user re-runs a message, the system SHALL remove all messages that follow the re-run point before starting the new deliberation, ensuring no stale responses remain.

#### Scenario: Re-run removes subsequent messages
- **WHEN** user clicks re-run on a user message at index N
- **THEN** all messages with index > N are removed from the conversation
- **AND** the new deliberation response is appended after index N
