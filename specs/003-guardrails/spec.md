# Feature Specification: Guardrails System

**Feature Branch**: `003-guardrails`  
**Created**: 2026-03-07  
**Status**: Draft  
**Input**: User description: "Guardrails layer for DEUS Bank AI Support System"

## Overview

This specification defines the guardrails system for the DEUS Bank AI Support System. Guardrails ensure all customer interactions remain safe, professional, on-topic, and compliant with banking regulations and customer data protection requirements. The system must protect both customers and the bank from harmful, inappropriate, or non-compliant interactions.

## Clarifications

### Session 2026-03-07

- Q: If the guardrail evaluation system fails (timeout, error, system unavailable), should the conversation: A) Fail-closed (block conversation), B) Fail-open (allow conversation to proceed), or C) Degrade gracefully (apply basic checks only)? → A: Fail-closed (block conversation) - prioritizes security and compliance over availability
- Q: When PII (phone numbers, IBANs) is redacted from responses to unauthenticated users, what format should be displayed: A) Type-specific placeholders, B) Generic placeholder `[REDACTED]`, C) Empty string, or D) Masked format? → A: Generic placeholder `[REDACTED]` - simpler, more secure, doesn't reveal PII type
- Q: When a conversation is terminated due to toxic language, should the customer be able to start a new conversation: A) Immediately, B) After cooldown period, C) New session ID required, or D) Manual review required? → A: Immediately - allows customers to restart and engage professionally after cooling down
- Q: What accuracy threshold is acceptable for false positives (legitimate messages incorrectly blocked as toxic or off-topic): A) <1%, B) <5%, C) <10%, or D) No specific threshold? → A: <5% false positive rate - balances safety with acceptable user experience
- Q: Should the guardrail system emit metrics and events for monitoring and analysis: A) No observability, B) Basic metrics only (counts, rates), C) Detailed logging (decisions, scores), or D) Full audit trail (all content)? → A: Basic metrics only - provides operational visibility (block counts, rates, latency, errors) without logging sensitive content

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Toxic Language Protection (Priority: P1)

As a **DEUS Bank compliance officer**, I need the system to immediately detect and block toxic, abusive, or threatening language so that customer service representatives are protected from harassment and the bank maintains professional communication standards.

**Why this priority**: Legal and safety requirement - employee protection and maintaining professional banking standards are non-negotiable.

**Independent Test**: Can be fully tested by submitting messages with toxic language (profanity, threats, harassment) and verifying they are blocked with appropriate warning messages and the conversation is terminated.

**Acceptance Scenarios**:

1. **Given** a customer sends a message with profanity, **When** the system processes the message, **Then** the system immediately blocks the message and returns a professional warning stating the conversation cannot continue
2. **Given** a customer sends threatening language, **When** the system processes the message, **Then** the system terminates the conversation and provides contact information for formal support channels
3. **Given** a customer sends a normal banking inquiry, **When** the system checks for toxicity, **Then** the message is allowed to proceed without interruption

---

### User Story 2 - Topic Boundary Enforcement (Priority: P1)

As a **DEUS Bank operations manager**, I need the system to recognize and politely decline off-topic requests so that support resources focus on banking services and customers receive appropriate guidance for non-banking questions.

**Why this priority**: Business efficiency - prevents misuse of banking support resources and ensures customers get proper help for their actual needs.

**Independent Test**: Can be fully tested by submitting various off-topic requests (coding help, general knowledge, unrelated services) and verifying they are politely redirected back to banking topics.

**Acceptance Scenarios**:

1. **Given** a customer asks for programming help, **When** the system evaluates the topic, **Then** the system politely declines and redirects to banking services
2. **Given** a customer asks about political opinions, **When** the system evaluates the topic, **Then** the system politely declines and offers to help with banking matters
3. **Given** a customer asks about account balance, **When** the system evaluates the topic, **Then** the request is recognized as on-topic and proceeds normally
4. **Given** a customer asks about loan applications, **When** the system evaluates the topic, **Then** the request is recognized as on-topic and proceeds normally

---

### User Story 3 - PII Leakage Prevention (Priority: P1)

As a **DEUS Bank data protection officer**, I need the system to prevent sensitive customer information (phone numbers, account numbers) from being exposed to unverified users so that the bank complies with data protection regulations and prevents identity theft.

**Why this priority**: Regulatory compliance and customer protection - data breaches result in legal penalties and customer harm.

**Independent Test**: Can be fully tested by simulating conversations where unauthenticated users might receive responses containing PII, and verifying that sensitive data is redacted while authenticated users receive complete information.

**Acceptance Scenarios**:

1. **Given** an unauthenticated customer receives a response containing a phone number, **When** the system prepares the response, **Then** the phone number is replaced with `[REDACTED]` before delivery
2. **Given** an unauthenticated customer receives a response containing an IBAN, **When** the system prepares the response, **Then** the IBAN is replaced with `[REDACTED]` before delivery
3. **Given** an authenticated customer receives a response containing their phone number, **When** the system prepares the response, **Then** the phone number is delivered without redaction
4. **Given** an authenticated customer receives a response containing their IBAN, **When** the system prepares the response, **Then** the IBAN is delivered without redaction

---

### Edge Cases

- What happens when a message contains toxic language but is also off-topic? (Toxicity takes precedence - conversation ends immediately)
- What happens when a message is borderline toxic but not clearly abusive? (System should err on the side of caution - block if uncertain, while maintaining <5% false positive rate)
- What happens when a response contains multiple pieces of PII? (All PII instances must be redacted for unauthenticated users)
- What happens when a customer becomes authenticated mid-conversation? (PII redaction stops for all subsequent responses)
- What happens when PII appears in the customer's message vs. the agent's response? (Customer messages are not censored; only outgoing agent responses are redacted)
- What happens when a legitimate banking term triggers topic filter? (Banking terminology must always be recognized as on-topic)
- What happens when guardrail evaluation fails due to timeout or system error? (Fail-closed: block conversation with error message, prioritizing security over availability)
- What happens after a conversation is terminated for toxic language? (Customer can immediately start a new conversation - no cooldown period or manual review required)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST evaluate every customer message for toxic content before processing
- **FR-002**: System MUST evaluate every customer message to determine if it relates to banking services
- **FR-003**: System MUST evaluate every agent response for sensitive customer information (PII) before delivery
- **FR-004**: System MUST immediately terminate conversations when toxic language is detected
- **FR-005**: System MUST provide professional, standardized responses when blocking toxic messages
- **FR-006**: System MUST provide polite, standardized responses when declining off-topic requests
- **FR-007**: System MUST redact phone numbers in agent responses to unauthenticated users by replacing them with `[REDACTED]`
- **FR-008**: System MUST redact IBANs in agent responses to unauthenticated users by replacing them with `[REDACTED]`
- **FR-009**: System MUST allow PII to appear in responses to authenticated users
- **FR-010**: System MUST process guardrail checks in priority order: toxicity first, then topic relevance, then PII protection
- **FR-011**: System MUST return both blocking information (if applicable) and sanitized responses to enable proper conversation flow control
- **FR-012**: System MUST recognize banking-related terminology as on-topic (accounts, loans, cards, transfers, balance, IBAN, etc.)
- **FR-013**: System MUST fail-closed when guardrail evaluation fails (timeout, error, unavailable) - block conversation and provide error message rather than allowing unchecked content
- **FR-014**: System MUST emit basic operational metrics including block counts by type (toxic, off-topic), PII redaction counts, processing latency, and error rates

### Key Entities *(include if feature involves data)*

- **Guardrail Check Result**: Represents the outcome of safety evaluations, including whether the interaction is safe to proceed, the reason for any blocking, and the sanitized response ready for delivery
- **Customer Message**: Input text from customer that requires evaluation for safety and relevance
- **Agent Response**: Output text from agent that requires evaluation for data protection compliance

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Toxic messages (profanity, threats, harassment) are correctly identified and blocked within 500ms; baseline accuracy established via integration tests with production monitoring ongoing
- **SC-002**: Off-topic requests (non-banking subjects) are correctly identified and politely declined; baseline accuracy established via integration tests with production monitoring ongoing
- **SC-003**: 100% of phone numbers and IBANs are redacted from agent responses to unauthenticated users
- **SC-004**: 0% false positive rate for authenticated users (no PII redaction when user is verified)
- **SC-005**: System handles at least 1000 concurrent guardrail evaluations without degradation
- **SC-006**: Average guardrail processing time is under 200ms per message
- **SC-007**: 100% of banking-related terms are correctly identified as on-topic
- **SC-008**: All blocked messages receive appropriate, professional response messages
- **SC-009**: False positive rate remains below 5% (legitimate messages incorrectly blocked as toxic or off-topic)

## Non-Functional Requirements *(optional)*

### Performance
- Guardrail evaluation MUST complete within 500ms for 95% of requests
- System MUST handle concurrent evaluation of multiple messages without blocking
- PII detection MUST be deterministic and instantaneous (no network calls)

### Security
- PII patterns MUST match international formats for phone numbers and IBANs
- Redaction MUST be irreversible - original PII cannot be recovered from redacted responses
- Evaluation logic MUST not log or store customer message content
- Metrics MUST not include message content, only aggregate counts and rates

### Maintainability
- Guardrail responses MUST be configurable without code changes
- Toxic language patterns MUST be updatable to handle new threats
- Banking terminology list MUST be maintainable as bank services evolve

## Assumptions *(optional)*

- Customer authentication status is provided by the session management system
- Banking-related terminology can be defined with reasonable completeness
- Toxic language can be detected with acceptable accuracy using content evaluation
- Phone numbers follow international format patterns (E.164 compatible)
- IBANs follow standard international format (ISO 13616)
- All conversations go through guardrails - no bypass mechanism exists
- Guardrail evaluation occurs synchronously within request/response cycle
- Customers terminated for toxic language can immediately retry without cooldown or manual review
- Each conversation termination is isolated - prior toxic behavior does not affect future conversations

## Out of Scope *(optional)*

- Language translation or multi-language support for guardrail messages
- Real-time human moderation or escalation workflows
- Detailed content logging with classification decisions and confidence scores
- Customer appeals process for blocked messages
- Configuration UI for guardrail settings
- Rate limiting or conversation timeout management (handled by separate systems)
- Detection of social engineering or phishing attempts (covered by separate fraud detection)
- Sentiment analysis beyond toxicity detection
- Audit trails containing actual message content or PII

## Dependencies *(optional)*

- **Session Management**: Requires authentication status (`is_authenticated` flag) for PII protection decisions
- **Agent System**: All agent responses must pass through guardrails before delivery
- **Message Processing**: Customer messages must be evaluated before routing to agents

## Risks & Mitigations *(optional)*

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| False positives block legitimate banking conversations | High | Medium | Maintain comprehensive banking terminology list; monitor and tune detection |
| Toxic language detection misses new threats | Medium | Medium | Regular review and update of detection patterns |
| PII detection regex has gaps | High | Low | Use well-tested patterns; validate against international standards |
| Guardrails add excessive latency | Medium | Low | Use efficient detection methods; optimize for <200ms average processing |
| Customer frustration from being blocked unnecessarily | Medium | Low | Ensure polite, clear messaging; provide alternative contact methods |

## Open Questions *(optional)*

None - specification is complete for implementation.
