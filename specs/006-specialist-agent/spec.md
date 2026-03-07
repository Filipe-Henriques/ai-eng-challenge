# Feature Specification: Specialist Agent — DEUS Bank AI Support System

**Feature Branch**: `006-specialist-agent`  
**Created**: March 7, 2026  
**Status**: Draft  
**Input**: User description: "This spec defines the behaviour of the **Specialist Agent**, the third and final node in the LangGraph pipeline. It is activated after the Bouncer Agent has routed the authenticated customer. It is the only agent in the system equipped with **tools** to perform real banking operations."

## Clarifications

### Session 2026-03-07

- Q: What level of IBAN validation should be applied to fund transfer requests? → A: Basic format check only (length 15-34 chars, alphanumeric, starts with 2 letters)
- Q: How should the agent handle tool execution failures due to system errors? → A: Apologize and offer retry once, then escalate if still failing
- Q: How should the agent handle missing or invalid customer tier information in the state? → A: Default to Standard tier and proceed with service
- Q: Can customers request a specific number of transactions in their history? → A: Allow customer to request 1-20 transactions, default 5
- Q: How should the agent handle customers who refuse to end the conversation or keep asking unrelated questions? → A: At turn 10, politely explain limit reached and automatically end conversation with offer to call back if needed

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Account Balance Inquiry (Priority: P1)

An authenticated customer needs to check their current account balance. After being greeted by the Specialist Agent, they request their balance. The agent retrieves and presents the balance in a natural, conversational manner appropriate to the customer's tier.

**Why this priority**: Balance inquiry is the most common banking request and serves as the baseline for verifying the agent's ability to use tools and communicate results effectively.

**Independent Test**: Can be fully tested by authenticating as any customer tier, requesting balance, and verifying the response is accurate and appropriately formatted for that tier.

**Acceptance Scenarios**:

1. **Given** a Standard tier customer is authenticated and routed to the Specialist Agent, **When** they ask "What's my balance?", **Then** the agent retrieves the balance using the appropriate tool and responds concisely with the amount and currency
2. **Given** a VIP tier customer is authenticated and routed to the Specialist Agent, **When** they ask about their account balance, **Then** the agent responds in a highly personalized, white-glove manner with the balance information
3. **Given** an authenticated customer, **When** they request their balance, **Then** the agent never exposes raw tool output, user IDs, or database references

---

### User Story 2 - Transaction History Review (Priority: P2)

An authenticated customer wants to review recent transactions on their account. The agent retrieves the transaction history and presents it in an easy-to-understand format, adapting the level of detail and tone to the customer's tier.

**Why this priority**: Transaction history is a critical banking function that validates the agent's ability to present structured data conversationally and handle follow-up questions.

**Independent Test**: Can be fully tested by authenticating as any customer, requesting transaction history, and verifying the response includes correct transaction details formatted appropriately.

**Acceptance Scenarios**:

1. **Given** an authenticated customer, **When** they request their recent transactions, **Then** the agent retrieves and presents the last 5 transactions in natural language
2. **Given** a Premium tier customer, **When** they ask for transaction history, **Then** the agent responds in a warm, personalized manner with transaction details
3. **Given** an authenticated customer reviewing transactions, **When** they ask follow-up questions about specific transactions, **Then** the agent maintains context and provides relevant information

---

### User Story 3 - Fund Transfer Execution (Priority: P3)

An authenticated customer needs to transfer money to another account. The agent collects necessary details (recipient IBAN, amount, description), validates the transfer is possible given the account balance, executes the transfer, and confirms completion with a transaction reference.

**Why this priority**: Fund transfers represent a critical transactional capability that tests the agent's ability to collect structured information, validate constraints, and execute actions with financial consequences.

**Independent Test**: Can be fully tested by authenticating as a customer with sufficient balance, requesting a transfer, providing valid details, and verifying the transfer is executed and confirmed correctly.

**Acceptance Scenarios**:

1. **Given** an authenticated customer with sufficient balance, **When** they request a fund transfer with valid recipient IBAN, amount, and description, **Then** the agent validates the balance, executes the transfer, and confirms with a transaction ID
2. **Given** an authenticated customer with insufficient balance, **When** they request a transfer exceeding their balance, **Then** the agent politely informs them of insufficient funds without exposing technical details
3. **Given** a VIP tier customer making a transfer, **When** the transfer is completed, **Then** the agent provides a white-glove confirmation with proactive next steps

---

### User Story 4 - Lost Card Reporting (Priority: P3)

An authenticated customer reports a lost or stolen card. The agent immediately flags the card as blocked, initiates a replacement process, and provides the customer with a case reference for tracking.

**Why this priority**: Card security is time-sensitive and validates the agent's ability to handle urgent requests efficiently across all tiers.

**Independent Test**: Can be fully tested by authenticating as any customer, reporting a lost card, and verifying the card is blocked and a case reference is provided.

**Acceptance Scenarios**:

1. **Given** an authenticated customer, **When** they report a lost or stolen card, **Then** the agent immediately flags the card as blocked and provides a case reference
2. **Given** a Standard tier customer reporting a lost card, **When** the block is confirmed, **Then** the agent provides concise next steps for card replacement
3. **Given** a Premium or VIP tier customer reporting a lost card, **When** the block is confirmed, **Then** the agent provides personalized reassurance and proactive support information

---

### User Story 5 - Multi-Turn Conversation Resolution (Priority: P2)

An authenticated customer has multiple related requests in a single conversation session. The agent maintains context across turns, handles each request appropriately, and gracefully concludes when all issues are resolved.

**Why this priority**: Multi-turn capability is essential for natural conversation flow and validates the agent's ability to manage complex customer interactions.

**Independent Test**: Can be fully tested by authenticating and making multiple requests (e.g., check balance, then review transactions, then transfer funds) in sequence and verifying the agent maintains context and completes the conversation appropriately.

**Acceptance Scenarios**:

1. **Given** an authenticated customer with one issue resolved, **When** they indicate they have another question, **Then** the agent continues the conversation without re-authentication
2. **Given** an authenticated customer with all issues resolved, **When** they indicate they're satisfied, **Then** the agent provides an appropriate closing message and sets the conversation as ended
3. **Given** an authenticated customer in a multi-turn conversation, **When** each message is processed, **Then** appropriate guardrails are applied to both user input and agent response

---

### User Story 6 - Tier-Specific Persona Adaptation (Priority: P2)

Customers of different tiers (Standard, Premium, VIP) receive service with appropriately adapted tone, personalization level, and communication style, while maintaining equal access to all banking tools and capabilities.

**Why this priority**: Tier-based personalization is a key differentiator for premium banking services and validates the agent's ability to adapt persona dynamically.

**Independent Test**: Can be fully tested by authenticating as customers from each tier, making identical requests, and verifying the responses have different tones but provide equivalent functionality.

**Acceptance Scenarios**:

1. **Given** a Standard tier customer is authenticated, **When** they interact with the Specialist Agent, **Then** the agent communicates in a concise, efficient manner
2. **Given** a Premium tier customer is authenticated, **When** they interact with the Specialist Agent, **Then** the agent communicates in a warm, personalized manner
3. **Given** a VIP tier customer is authenticated, **When** they interact with the Specialist Agent, **Then** the agent communicates with highly personalized, proactive, white-glove service
4. **Given** customers from any tier, **When** they request banking services, **Then** all tiers have access to the same set of banking tools (balance, transactions, transfers, card reporting)

---

### Edge Cases

- What happens when a customer requests a transfer with an invalid IBAN format? (Agent validates basic format: 15-34 characters, alphanumeric, starts with 2 letters, and rejects with helpful error message)
- How does the agent handle requests for services outside the scope of available tools? (Agent politely explains the request requires human advisor assistance and provides handoff message. **Out-of-scope services include**: mortgage applications, investment advice, opening new accounts, loan applications, credit card applications, account closure, dispute resolution, financial planning)
- What happens when the customer provides ambiguous input that could match multiple intents?
- How does the agent respond when tool execution fails due to system errors? (Agent apologizes, offers one retry attempt, then escalates to human advisor if retry fails)
- What happens when a customer's tier information is missing or invalid in the state? (Agent defaults to Standard tier and proceeds with full service)
- How does the agent handle customers who refuse to end the conversation or keep asking unrelated questions? (At turn 10, agent politely explains limit reached, offers callback option, and automatically ends conversation. **Note**: One turn = one full exchange consisting of one customer message and one agent response)
- What happens when a transfer request is made but the database indicates insufficient funds?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST greet authenticated customers by their first name on the first turn of the Specialist Agent conversation (first turn = first time specialist is invoked in this session, not on re-entry)
- **FR-002**: System MUST acknowledge the customer's classified intent from the Bouncer Agent on the first turn
- **FR-003**: System MUST adapt conversation tone and persona based on customer tier (Standard: concise/efficient, Premium: warm/personalized, VIP: highly personalized/white-glove), and MUST default to Standard tier if tier information is missing or invalid
- **FR-004**: System MUST provide all authenticated customers with access to account balance retrieval, transaction history review, fund transfer execution, and lost card reporting capabilities
- **FR-005**: System MUST retrieve account balance and currency for authenticated customers from the mock in-memory database
- **FR-006**: System MUST retrieve transaction history for authenticated customers from the mock in-memory database, with a default limit of 5 transactions and MUST support customer requests for 1-20 transactions
- **FR-007**: System MUST validate recipient IBAN format for fund transfers using basic format check (15-34 characters, alphanumeric, starts with 2 country code letters) and reject invalid IBANs with helpful error message
- **FR-008**: System MUST validate account balance before executing fund transfers and reject transfers that exceed available balance
- **FR-009**: System MUST execute valid fund transfers by deducting the amount, recording the transaction, and providing a transaction reference
- **FR-010**: System MUST immediately flag cards as blocked when customers report them lost or stolen, and provide a case reference
- **FR-011**: System MUST maintain conversation context across multiple turns within a single session
- **FR-012**: System MUST never expose raw tool output, internal system details, user IDs, database references, or technical implementation to customers
- **FR-013**: System MUST translate all tool results into natural language responses appropriate to the customer's tier
- **FR-014**: System MUST apply guardrails to both customer input and its own proposed responses on every conversation turn
- **FR-015**: System MUST set conversation_ended flag to True when customer issues are resolved and the conversation is complete
- **FR-016**: System MUST identify customer user_id from the verified_user state rather than asking the customer for their ID
- **FR-017**: System MUST detect out-of-scope services (mortgage applications, investment advice, opening new accounts, loan applications, credit card applications, account closure, dispute resolution, financial planning) and politely inform customers that their request requires human advisor assistance, then end the conversation appropriately with handoff message
- **FR-018**: System MUST handle up to 10 conversation turns per session for multi-turn conversations (where 1 turn = 1 customer message + 1 agent response), and MUST politely explain the limit at turn 10, offer callback option, and automatically end the conversation
- **FR-019**: System MUST handle tool execution failures by apologizing to the customer, offering one retry attempt, and escalating to human advisor if the retry fails
- **FR-020**: System MUST NOT make external API calls and MUST use only the in-memory mock database for all operations

### Key Entities *(include if feature involves data)*

- **Customer**: Represents an authenticated bank customer with attributes including user_id, name, tier (Standard/Premium/VIP), and intent classification
- **Account**: Represents a customer's bank account with attributes including balance, currency, transaction history, and card status
- **Transaction**: Represents a financial transaction with attributes including date, description, amount, and type (debit/credit)
- **Transfer Request**: Represents a fund transfer operation with attributes including recipient IBAN, amount, description, and validation status
- **Card Block Request**: Represents a lost/stolen card report with attributes including user_id and case reference
- **Conversation State**: Stores authentication status, current agent, customer tier, verified user details, intent classification, message history, and conversation completion flag

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Authenticated customers can retrieve their account balance in a single conversational turn with 100% accuracy
- **SC-002**: Fund transfers are successfully executed within 3 seconds from request submission for valid transfers with sufficient balance
- **SC-003**: Lost card reports are processed and confirmed within 2 seconds with a valid case reference provided
- **SC-004**: Specialist agent integration tests demonstrate that typical customer requests (balance inquiry, transaction history, single transfer, card blocking) are resolved within 5 conversational turns
- **SC-005**: Tier-specific persona templates (Standard, Premium, VIP) are correctly applied to system prompts for all authenticated customers based on customer_tier state value
- **SC-006**: Zero instances of raw tool output, user IDs, or database references exposed in customer-facing responses
- **SC-007**: Multi-turn conversations maintain context with 100% accuracy across up to 10 related requests
- **SC-008**: Out-of-scope requests are identified and handled gracefully with appropriate handoff messaging in 100% of cases
- **SC-009**: All tool operations complete without external API calls, validated through system monitoring
- **SC-010**: Guardrails are successfully applied to 100% of conversation turns, both for user input and agent responses
