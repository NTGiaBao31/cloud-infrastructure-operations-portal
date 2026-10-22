# Sơ đồ thực thể

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
    SERVERS o|--o{ ALERTS : co
    USERS o|--o{ ALERTS : xac_nhan
    SERVERS o|--o{ AUTOMATION_JOBS : chay_tren
    ALERTS o|--o{ AUTOMATION_JOBS : kich_hoat
    USERS o|--o{ AUTOMATION_JOBS : yeu_cau
    USERS o|--o{ AUDIT_LOGS : tao
```

## Quy tắc dữ liệu

- Một máy chủ có nhiều cảnh báo và nhiều công việc tự động hóa. Khóa ngoại của chúng được đặt thành `NULL` nếu máy chủ bị xóa.
- Một cảnh báo do một người dùng xác nhận và có thể gắn với nhiều công việc khắc phục.
- Một công việc tự động hóa được tạo cho một máy chủ, và có thể xuất phát từ một cảnh báo cùng một yêu cầu của người dùng.
- Bản ghi nhật ký giữ người thực hiện khi có thông tin đó, và giữ lịch sử hành động không bị sửa.
- SQLite bật kiểm tra khóa ngoại. Bản nâng cấp cơ sở dữ liệu đánh chỉ mục các cột thường được lọc.

Tên cột trong sơ đồ giữ đúng tên trong cơ sở dữ liệu. Năm bảng là `users`, `servers`, `alerts`, `automation_jobs` và `audit_logs`.
