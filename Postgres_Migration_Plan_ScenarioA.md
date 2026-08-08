# PostgreSQL Migration Plan for Scenario A

## Objective

Migrate the current Scenario A audit log service from SQLite to PostgreSQL while preserving the existing API behavior, hash-chain integrity model, and validation flow.

## Goals

- Keep the current FastAPI-based architecture intact.
- Preserve the write, query, and verify endpoints.
- Replace the SQLite persistence layer with PostgreSQL.
- Make the deployment more production-like without changing the core Scenario A requirements.

## Proposed Migration Approach

### Phase 1: Prepare the application for configuration-driven persistence

1. Introduce environment-based database configuration.
   - DB_HOST
   - DB_PORT
   - DB_NAME
   - DB_USER
   - DB_PASSWORD
   - DB_SSL_MODE (optional)

2. Add a database connection module.
   - Centralize connection creation and connection pooling.
   - Keep the application logic independent from the storage implementation.

3. Create a small abstraction layer for database operations.
   - This helps reduce the risk of scattering SQLite-specific logic across the codebase.

### Phase 2: Replace SQLite-specific implementation with PostgreSQL-compatible SQL

1. Update the schema definition.
   - Use PostgreSQL-compatible table creation statements.
   - Prefer JSONB for payload storage if flexible structured payloads are important.
   - Use TIMESTAMP WITH TIME ZONE for timestamps.

2. Adjust the table and query implementation.
   - Replace SQLite-specific connection and row handling with PostgreSQL-compatible code.
   - Ensure SQL queries remain compatible with PostgreSQL syntax.

3. Add indexes for common query paths.
   - actorId
   - resourceType
   - resourceId
   - eventType
   - timestamp

### Phase 3: Introduce migrations

1. Add migration tooling such as Alembic.
   - This is preferable to relying on ad hoc schema creation at startup.

2. Create initial migration for the audit_events table.
   - Include the hash-chain fields and required indexes.

3. Add a migration path for later schema changes.
   - This becomes important if the service evolves beyond Scenario A.

### Phase 4: Update tests and validation

1. Update the test suite to run against PostgreSQL instead of temporary SQLite files.
   - Use a test database or containerized PostgreSQL instance.

2. Keep the current test scenarios intact.
   - Happy path
   - invalid input validation
   - tamper detection

3. Add database-specific integration tests where needed.
   - For example, verify connection failure handling and transaction behavior.

### Phase 5: Add deployment support

1. Add Docker support for the application and PostgreSQL.
   - A docker-compose file would make local development and demonstration easier.

2. Add environment files or configuration templates.
   - Example: `.env.example`.

3. Update run instructions.
   - Document how to bring up PostgreSQL and connect the service.

## File-Level Changes Anticipated

### Application code
- Update [src/audit_log_service/app.py](src/audit_log_service/app.py)
  - Replace SQLite connection logic.
  - Use PostgreSQL connection parameters.
  - Adjust row access patterns where needed.

### Tests
- Update [tests/test_audit_service.py](tests/test_audit_service.py)
  - Replace the temporary SQLite database fixture with a PostgreSQL-backed test setup.

### Project configuration
- Add PostgreSQL dependency to [requirements.txt](requirements.txt).
- Add Docker or compose files.
- Add environment configuration examples.

### Documentation
- Update [README.md](README.md) to describe PostgreSQL setup and run instructions.
- Update the testing and architecture documentation to reflect the new persistence layer.

## Risks and Considerations

- The current implementation is intentionally simple and SQLite-backed; moving to PostgreSQL introduces operational overhead.
- Schema and connection management need to be more disciplined for production-like use.
- Tests must be run in a controlled environment with available PostgreSQL infrastructure.
- The hash-chain logic itself does not need to change; only the storage mechanism does.

## Recommended Rollout Order

1. Introduce configuration-driven database access.
2. Replace SQLite-specific persistence code.
3. Add PostgreSQL schema and indexes.
4. Introduce migrations.
5. Update tests and documentation.
6. Add containerized deployment support.

## Expected Outcome

After this migration, Scenario A will remain functionally the same but will be more realistic for a production-style deployment: the service will use a real relational database, support more durable storage, and be more aligned with enterprise expectations while preserving the core tamper-evident design.

## Implementation status
The repository now includes explicit migration markers for the initial schema and governance metadata, a migration helper module, and documentation that explains the operational expectations for versioned schema evolution and backup/restore compatibility.
