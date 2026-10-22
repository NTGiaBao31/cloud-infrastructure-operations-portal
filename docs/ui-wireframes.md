# Wireframe giao diện

Cổng dùng chung một bố cục Bootstrap và thanh điều hướng theo vai trò. Các khung dưới đây mô tả các màn hình của bản dùng thử đã làm.

## Đăng nhập

```text
+------------------------------------------------------------+
|                      Cổng vận hành                         |
|                                                            |
|  Tên đăng nhập  [_____________________________]            |
|  Mật khẩu       [_____________________________]            |
|                                                            |
|                      [ Đăng nhập ]                         |
+------------------------------------------------------------+
```

## Bảng điều khiển

```text
+------------------------------------------------------------+
| Tên | Bảng điều khiển | Máy chủ | Cảnh báo | Tự động | Nhật ký |
+------------------------------------------------------------+
| Bảng điều khiển                         Prometheus: trạng thái |
| [Máy chủ] [Cảnh báo đang mở] [Nghiêm trọng] [Cảnh báo]     |
| [Trực tuyến] [Cảnh báo] [Ngừng] [Bảo trì] [Không rõ]       |
| Số liệu trực tiếp: [Sẵn sàng] [CPU] [Bộ nhớ] [Đĩa]         |
| Grafana: [ Mở Grafana ] hoặc thông báo chưa cấu hình       |
| Công việc gần đây: Hành động | Trạng thái | Bộ thực thi | Lúc |
+------------------------------------------------------------+
```

## Danh sách máy chủ

```text
+------------------------------------------------------------+
| Máy chủ                                      [Thêm máy chủ] |
| [Trạng thái v] [Hệ điều hành v] [Môi trường________] [Lọc]  |
| Tên       Địa chỉ      Môi trường   HĐH    Trạng thái Hoạt động |
| may-01    10.0.0.10    sản xuất     Linux  trực tuyến  có    |
+------------------------------------------------------------+
```

Chọn một máy chủ sẽ mở trang chi tiết. Với quản trị viên, trang này có nút sửa và bật hoặc tắt máy chủ.

## Các màn hình vận hành

```text
+------------------------------------------------------------+
| Cảnh báo: Mức độ | Tên | Máy chủ | Trạng thái | [Xác nhận] |
+------------------------------------------------------------+
| Tự động hóa: Máy chủ [v] Hành động [v] Tham số [...] [Chạy] |
| Lịch sử: hành động | máy đích | bộ thực thi | trạng thái | thời điểm |
+------------------------------------------------------------+
| Nhật ký: Thời điểm | Người dùng | Hành động | Tài nguyên | Chi tiết |
+------------------------------------------------------------+
```

## Quyền theo vai trò

| Vai trò | Quyền |
| --- | --- |
| Người xem | Xem bảng điều khiển, danh sách máy chủ, cảnh báo, công việc và lịch sử nhật ký. |
| Người vận hành | Quyền của người xem, thêm xác nhận cảnh báo và chạy hành động tự động hóa. |
| Quản trị | Quyền của người vận hành, thêm tạo, sửa, bật và tắt máy chủ. |
