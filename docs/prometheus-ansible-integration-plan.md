# Kế hoạch tích hợp Prometheus và Ansible

## Hiện trạng

- Số liệu và cảnh báo Prometheus đi qua lớp chuyển tiếp HTTP, cấu hình bằng các biến môi trường `PROMETHEUS_*`.
- Đồng bộ cảnh báo được chạy tay bằng lệnh `flask --app wsgi sync-prometheus-alerts`. Chưa có bộ lập lịch.
- Tự động hóa mặc định dùng `AUTOMATION_EXECUTOR=mock` và ghi kết quả giả lập một cách an toàn.
- Có ba playbook Ansible nằm trong danh sách cho phép: khởi động lại dịch vụ, khởi động lại container và dọn đĩa ở chế độ chạy thử. Bộ thực thi Ansible cố ý không mở tiến trình.

## Tích hợp Prometheus

1. Triển khai Prometheus và các bộ thu thập trên máy, rồi cấu hình mục tiêu thu thập khớp với `monitoring_target`, tên máy hoặc địa chỉ IP của từng máy chủ.
2. Tạo quy tắc cảnh báo với nhãn `severity` và `instance`. Dùng các tên cảnh báo khắc phục được hỗ trợ: `service_down`, `container_down` và `disk_high`.
3. Đặt `PROMETHEUS_BASE_URL`, kiểm tra chứng chỉ TLS và mã thông báo tùy chọn trong kho bí mật triển khai. Không đưa mã thông báo vào git.
4. Chạy `sync-prometheus-alerts` bằng bộ lập lịch, ban đầu mỗi năm phút một lần.
5. Kiểm tra số liệu trên bảng điều khiển, việc tạo, cập nhật và đóng cảnh báo, và việc cổng vẫn chạy khi Prometheus không truy cập được.

## Tích hợp Ansible

1. Cài và ghim phiên bản `ansible-runner`. Tạo thư mục dữ liệu Ansible riêng bên ngoài kho mã, hoặc loại thư mục đó khỏi quản lý mã nguồn.
2. Sinh danh sách máy từ `automation_group`. Giữ khóa SSH, thông tin WinRM và mật khẩu vault trong trình quản lý bí mật hoặc Ansible Vault.
3. Thay bộ thực thi giữ chỗ bằng lời gọi `ansible-runner`, mỗi hành động hiện có trỏ tới đúng một playbook cố định.
4. Chỉ truyền tham số đã kiểm tra dưới dạng biến bổ sung. Tiếp tục từ chối lệnh, script, shell và đường dẫn playbook tùy ý.
5. Bắt buộc đúng máy đích, thời gian chờ, ghi kết quả, che đầu ra và ghi nhật ký trước khi đặt `AUTOMATION_EXECUTOR=ansible`.
6. Giữ `AUTO_REMEDIATION_ENABLED=false` cho đến khi các lần chạy thử thủ công đạt. Chỉ bật cho cảnh báo đã duyệt và một nhóm máy giới hạn trước.

## Tiêu chí nghiệm thu

- Prometheus lỗi thì cổng vẫn vào được bảng điều khiển, chỉ thiếu số liệu.
- Đồng bộ theo lịch nhập, cập nhật và đóng cảnh báo mà không tạo bản ghi trùng.
- Mỗi playbook đã duyệt chạy được trên môi trường thử. Người xem không chạy được hành động. Mọi lần chạy đều có nhật ký.
- Đường dẫn playbook không hợp lệ, lệnh shell, thông tin đăng nhập và tham số chưa duyệt đều bị từ chối.
- Công việc Ansible thất bại lưu trạng thái thất bại và phần đầu ra đã che, không lưu bí mật.

## Triển khai và quay lui

- Triển khai theo thứ tự: chế độ `mock`, rồi Ansible trên môi trường thử, rồi sản xuất giới hạn sau khi xem nhật ký và bản ghi kiểm tra.
- Quay lui bằng cách đặt `AUTOMATION_EXECUTOR=mock` và `AUTO_REMEDIATION_ENABLED=false`. Lịch sử vận hành vẫn được giữ.
