# Entity Relationship Diagram

```mermaid
erDiagram
    USERS {
        int id PK
        string username UK
        string password_hash
        string role
        boolean is_active
        datetime last_login_at
        datetime created_at
    }
    SERVERS {
        int id PK
        string name UK
        string hostname
        string ip_address
        string environment
        string os_type
        string status
        string monitoring_target
        string automation_group
        string azure_resource_id
        boolean is_active
        datetime last_seen_at
        datetime created_at
        datetime updated_at
    }
    ALERTS {
        int id PK
        int server_id FK
        int acknowledged_by FK
        string fingerprint
        string alert_name
        string category
        string source
        string severity
        string status
        string summary
        text description
        datetime starts_at
        datetime acknowledged_at
        datetime resolved_at
        datetime created_at
    }
    AUTOMATION_JOBS {
        int id PK
        int server_id FK
        int alert_id FK
        int requested_by FK
        string trigger_source
        string executor
        string action_key
        text parameters_json
        string status
        int exit_code
        text output_excerpt
        datetime started_at
        datetime finished_at
        datetime created_at
    }
    AUDIT_LOGS {
        int id PK
        int user_id FK
        string action
        string resource_type
        string resource_id
        text details_json
        string ip_address
        datetime created_at
    }
    SERVERS o|--o{ ALERTS : has
    USERS o|--o{ ALERTS : acknowledges
    SERVERS o|--o{ AUTOMATION_JOBS : runs_on
    ALERTS o|--o{ AUTOMATION_JOBS : triggers
    USERS o|--o{ AUTOMATION_JOBS : requests
    USERS o|--o{ AUDIT_LOGS : creates
```

## Data Rules

- A server can have many alerts and automation jobs; their foreign keys are set to `NULL` if a server is removed.
- An alert can be acknowledged by one user and associated with multiple remediation jobs.
- An automation job is created for one server and can optionally originate from an alert and user request.
- Audit records keep the actor when available and preserve an immutable action history.
- SQLite foreign-key enforcement is enabled; the migration indexes commonly filtered columns.
