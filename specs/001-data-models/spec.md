# Feature Specification: Data Models & Mock Database

**Feature Branch**: `001-data-models`  
**Created**: 2026-03-07  
**Status**: Draft  
**Input**: Define Pydantic data models and mock in-memory database for DEUS Bank AI Support System

## Overview

This specification defines all Pydantic data models and the mock in-memory database for the DEUS Bank AI Support System. These models are the single source of truth for the data structures used across all agents and the API layer.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - API Data Exchange (Priority: P1)

As a **developer integrating with the chat API**, I need standardized request/response models so that I can send messages and receive agent responses in a predictable format.

**Why this priority**: Foundation for all API interactions - nothing works without this.

**Independent Test**: Can be fully tested by sending a ChatRequest with session_id and message, verifying ChatResponse contains session_id, response, and agent fields.

### User Story 2 - Customer Identity Verification (Priority: P1)

As a **bouncer agent**, I need access to customer records (name, phone, IBAN, secret question/answer) so that I can verify customer identity before granting access to account information.

**Why this priority**: Core security requirement - must verify identity before any sensitive operations.

**Independent Test**: Can be fully tested by querying the User data store with various combinations of name/phone/IBAN and verifying returned secret questions and answers.

### User Story 3 - Account Tier Determination (Priority: P1)

As a **specialist agent**, I need to check if a customer has a premium account so that I can route them to the appropriate support tier.

**Why this priority**: Business requirement for routing customers to correct support channels.

**Independent Test**: Can be fully tested by looking up Account records by IBAN and verifying premium status is correctly returned.

## Functional Requirements *(mandatory)*

### R1: User Data Model

The system MUST define a User model with the following fields:
- `name` (str): Customer's full name
- `phone` (str): Phone number in international format (e.g., `+1122334455`)
- `iban` (str): IBAN in standard format (e.g., `DE89370400440532013000`)
- `secret` (str): Security question shown to customer
- `answer` (str): Correct answer to security question

### R2: Account Data Model

The system MUST define an Account model with the following fields:
- `iban` (str): Account IBAN (primary key)
- `premium` (bool): Premium tier status

### R3: ChatRequest Data Model

The system MUST define a ChatRequest model for API input with these fields:
- `session_id` (str): Unique conversation identifier
- `message` (str): Customer's input message

### R4: ChatResponse Data Model

The system MUST define a ChatResponse model for API output with these fields:
- `session_id` (str): Matching conversation identifier
- `response` (str): Agent's response message
- `agent` (str): Name of responding agent (e.g., "greeter", "bouncer", "specialist")

### R5: Mock User Database

The system MUST provide at least 3 mock users in the in-memory database:
- One premium client (has matching Account with premium=True)
- One regular client (has matching Account with premium=False)
- One user without bank account (no matching Account record)

### R6: Mock Account Database

The system MUST provide matching Account records for at least 2 of the 3 mock users, with at least one premium and one non-premium account.

### R7: Data Location

All models MUST be defined in `app/models/schemas.py`.
All mock data MUST be defined in `app/models/database.py`.

### R8: Pydantic Validation

All data models MUST use Pydantic v2 for validation and serialization.

## Success Criteria *(mandatory)*

1. **Model Completeness**: All four models (User, Account, ChatRequest, ChatResponse) are defined with correct field types
2. **Mock Data Availability**: At least 3 users and 2 accounts exist in mock database with appropriate test coverage (premium, regular, no-account scenarios)
3. **Validation Works**: Pydantic validation correctly rejects invalid data (e.g., missing required fields)
4. **Import Success**: Models can be imported and used by other modules without errors
5. **No Business Logic**: Models contain only data definitions - no agent logic, no business rules, no computation

## Non-Functional Requirements *(optional)*

### Performance
- Model instantiation and validation MUST complete in <1ms per instance
- Mock database lookup MUST complete in O(n) time (acceptable for in-memory lists)

### Maintainability
- Each model MUST include a docstring describing its purpose
- Field definitions MUST use clear, descriptive names

## Data Models Reference

### User Model Structure
```python
class User(BaseModel):
    name: str
    phone: str  # Format: +1122334455
    iban: str   # Format: DE89370400440532013000
    secret: str # Security question
    answer: str # Security answer
```

### Account Model Structure
```python
class Account(BaseModel):
    iban: str
    premium: bool
```

### ChatRequest Model Structure
```python
class ChatRequest(BaseModel):
    session_id: str
    message: str
```

### ChatResponse Model Structure
```python
class ChatResponse(BaseModel):
    session_id: str
    response: str
    agent: str  # "greeter" | "bouncer" | "specialist"
```

### Mock Data Examples

**Mock Users**:
```python
MOCK_USERS = [
    User(
        name="Lisa",
        phone="+1122334455",
        iban="DE89370400440532013000",
        secret="Which is the name of my dog?",
        answer="Yoda"
    ),
    User(
        name="John",
        phone="+1987654321",
        iban="GB29NWBK60161331926819",
        secret="What is your mother's maiden name?",
        answer="Smith"
    ),
    User(
        name="Maria",
        phone="+1555000111",
        iban="FR7630006000011234567890189",
        secret="What was the name of your first pet?",
        answer="Fluffy"
    ),
]
```

**Mock Accounts**:
```python
MOCK_ACCOUNTS = [
    Account(iban="DE89370400440532013000", premium=True),  # Lisa - Premium
    Account(iban="GB29NWBK60161331926819", premium=False), # John - Regular
    # Maria has no account (tests non-client flow)
]
```

## Assumptions *(optional)*

- Phone numbers are pre-validated and stored in international format
- IBANs are pre-validated and stored in correct format
- Secret questions/answers are case-sensitive
- Session IDs are provided by the client (API doesn't generate them)
- Mock database is sufficient for development and testing (no persistence needed)
- All field values are required (no optional fields in base models)

## Out of Scope *(optional)*

- Database persistence (in-memory only)
- User CRUD operations (read-only access)
- Account balance or transaction data
- Password hashing or authentication tokens
- Phone/IBAN format validation (assumes clean data)
- Multi-language support for secret questions
- Session ID generation or validation
- Rate limiting or API quotas

## Dependencies *(optional)*

- **Pydantic v2**: For data model definitions and validation
- **Python 3.11+**: For modern Python features

## Risks & Mitigations *(optional)*

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Pydantic v1/v2 compatibility issues | High | Low | Pin Pydantic v2 in requirements.txt |
| Mock data doesn't cover edge cases | Medium | Medium | Ensure 3+ test scenarios (premium/regular/no-account) |
| Model changes break agent code | Medium | Low | Keep models stable after initial definition |

## Open Questions *(optional)*

None - specification is complete for implementation.
