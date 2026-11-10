# Hoàn thành nhãn blob_05 — gán thủ công và rà soát

Đầu vào: [blob_05.png](../../data/raw/blob_05.png), 512×512, ảnh tế bào/nhân
sáng trên nền tối. Chưa có file nhãn đối chiếu được cung cấp cho đúng ảnh này.
Công cụ mở ảnh gốc, có chế độ vẽ tay và chế độ gợi ý khung để người dùng rà soát.
Gợi ý dùng ngưỡng cường độ + thành phần liên thông, độc lập với lõi Gaussian/
LoG của bài tập; chúng chưa phải nhãn chuẩn đã xác nhận.

## Làm nhanh bằng gợi ý

1. Bấm **Tao goi y**, giữ `Nguong goi y` mặc định 32 cho ảnh hiện tại. Các khung
   đã vẽ và vùng bỏ qua được giữ; chỉ thêm khung mới chưa trùng. Vòng/dòng màu
   **tím có dấu ?** là gợi ý chưa duyệt; xanh là nhãn đã vẽ hoặc đã duyệt.
2. Xem từng vùng ảnh, xóa khung sai: nhấp vào đối tượng để chọn, nhấn **Delete**
   hoặc **Xoa muc chon**. Để sửa kích thước, chọn **Ve lai muc chon** rồi kéo
   khung mới bao sát đối tượng. Với cụm dính, xóa khung gộp để vẽ từng nhân hoặc
   khoanh vùng cam nếu không tách chắc chắn.
3. Sau khi đã kiểm tra và sửa các đối tượng trong phần ảnh đang hiển thị, bấm
   **Duyet vung dang xem**. Nút chỉ duyệt khung nằm trọn trong phần ảnh đang
   nhìn thấy; không duyệt phần bị khuất hay ngoài màn hình.
4. Hoặc duyệt từng gợi ý: bấm **Goi y tiep [N]**, kiểm tra đối tượng được chọn,
   nhấn **Enter** để chấp nhận rồi tự chuyển tới gợi ý kế tiếp. Phím N chuyển
   tiếp, Delete xóa; phím tắt hoạt động khi đang chọn vùng ảnh/danh sách.
5. Rà cả các vị trí **không có gợi ý**, bổ sung đốm mờ bị bỏ sót, kiểm tra khung
   vẽ từ trước và các đối tượng ở mép ảnh. Bấm **Luu nhap** thường xuyên.
6. Chỉ bấm **Da ra soat toan anh** khi đã rà toàn bộ ảnh và số gợi ý CHUA DUYET
   là 0. Công cụ từ chối hoàn thành nếu còn gợi ý chưa kiểm tra.

Nếu nhiều đối tượng mờ bị bỏ sót, có thể hạ ngưỡng (ví dụ 25–28) và bấm tạo
gợi ý thêm; ngưỡng thấp cũng dễ đưa thêm nhiễu hoặc khung gộp. Không sửa ngưỡng
để đạt một số lượng tế bào mong muốn. Đây là tham số hỗ trợ gán nhãn, không
thay đổi `config.yaml` hay tham số đánh giá.

Gợi ý thêm vào bản đang làm, chỉ lưu khi bấm lưu. Các gợi ý giữ thông tin nguồn,
ngưỡng, khung ban đầu và cờ đã duyệt trong JSON; nhãn sau hỗ trợ mang origin
`manual_with_component_suggestions`. Bước này vẫn cần người xem sửa/kiểm tra
độc lập; không lấy nguyên dự đoán tự động làm nhãn chuẩn.

Khi cập nhật công cụ, cần lưu nháp và đóng cửa sổ cũ rồi mở lại. Bản mới kiểm
tra thay đổi file để chặn một cửa sổ ghi đè nhãn được lưu từ cửa sổ khác.

## Mở công cụ

Trong File Explorer tại gốc dự án, nhấp đúp
[`MO_GAN_NHAN_TE_BAO_05_11.cmd`](../../MO_GAN_NHAN_TE_BAO_05_11.cmd).
Giữ cửa sổ console để xem thông báo. Khi đóng cửa sổ gán nhãn, file CMD tự chạy
lại bước chuẩn bị GT để cập nhật bảng kiểm kê.

Hoặc mở PowerShell tại gốc dự án:

```powershell
.\.venv\Scripts\python.exe -m src.eval.annotate_cells
```

Nếu chưa tạo GT lần đầu, chạy `python -m src.eval.prepare_ground_truth` bằng
Python trong `.venv` trước. Máy mới cần thư viện ở `requirements-ground-truth.txt`
và Python có Tkinter (Python Windows thông thường có tùy chọn Tcl/Tk khi cài).

## Thao tác

1. Chọn **Khoanh doi tuong (xanh)**. Kéo chuột trái tạo khung bao sát **một nhân
   hoặc một đối tượng tế bào phân biệt được**. Công cụ tính tâm tại giữa khung
   và bán kính tương đương diện tích ellipse: `sqrt(width*height)/2`.
2. Chọn **Vung bo qua (cam)** để khoanh các cụm chồng lấp không thể tách chắc
   chắn, đối tượng bị cắt ở mép hoặc vùng không thể gán nhãn tin cậy.
3. Chọn mục ở danh sách bên phải để xem khung đỏ; **Xoa muc chon** để xóa,
   **Hoan tac** để quay lại thao tác trước. Dùng thanh cuộn để xem mọi phần
   của ảnh; có thể chọn phóng to 1×, 2×, 3×.
4. Bấm **Luu nhap** thường xuyên. Đóng rồi mở lại sẽ đọc đúng bản nháp đã lưu.
5. Điền tên ở **Nguoi gan nhan**. Sau khi rà soát toàn ảnh, bấm
   **Da ra soat toan anh**. Trạng thái `READY` cần ít nhất một đối tượng hợp lệ
   và tên người rà soát; công cụ vẫn cần người dùng kiểm tra độ đầy đủ.

Mỗi đối tượng lưu `bbox_xyxy`, tâm x/y, bán kính r. Mọi giá trị được quy về
pixel ảnh gốc, không phải pixel sau khi phóng to. Một khung xanh tương ứng một
đối tượng. Nếu hai nhân tách được thì khoanh riêng; không đặt một khung quanh
cụm rồi vừa tính là một vừa tính là hai. Cụm không rõ cần vùng bỏ qua.

## Quy tắc rà soát

- Chọn một đơn vị nhất quán: nhân/cấu trúc sáng phân biệt được trong ảnh.
- Rà lần lượt từ trên xuống dưới, trái sang phải, tránh bỏ sót và trùng khung.
- Khung bao sát hình dạng quan sát được; bán kính ellipse tương đương là quy
  ước gần đúng cho sinh học, khác bán kính giải tích của blob tổng hợp.
- Vùng bỏ qua cần bao trọn đối tượng/cluster không chắc chắn. Không đặt tâm
  đối tượng xanh trong vùng cam; trình kiểm tra sẽ từ chối lưu nếu trùng.
- Nhờ một thành viên khác xem overlay nếu có thể. Giấy phép/nguồn ảnh không
  đồng nghĩa ảnh có sẵn nhãn tâm/bán kính chính xác.
- Không bấm đã rà soát khi mới khoanh một phần ảnh. Không dùng nhãn nháp để
  báo Precision/Recall/F1. Khi đánh giá sau này phải áp dụng các vùng bỏ qua
  giống nhau cho cả Python và Fiji.

## File được lưu

- `data/gt/blob/blob_05.json`: nhãn hiện tại, người rà soát và trạng thái.
- `data/gt/blob/history/`: lịch sử JSON trước mỗi lần lưu thay đổi.
- `data/gt/previews/blob_05_overlay.png`: vòng đối tượng và vùng bỏ qua trên ảnh.

Sau khi chỉnh nhãn, việc gán thêm/xóa/hoàn tác sẽ đưa bản đang sửa về nháp,
cần rà soát lại. Lưu nháp không tự động nâng thành nhãn đã duyệt.

Nếu mở trực tiếp bằng lệnh Python, sau khi lưu và đóng công cụ, chạy:

```powershell
.\.venv\Scripts\python.exe -m src.eval.prepare_ground_truth
```

Mở `data/metadata/ground_truth_inventory.csv`, kiểm tra hàng `blob_05` và số
đối tượng. Khi mọi hàng đều `READY`, script trả mã 0 và báo 25/25. Việc này
xác nhận đủ file/quy cách và khai báo rà soát; chất lượng gán nhãn do người
gán nhãn chịu trách nhiệm xác nhận.

Quay lại [README ngày 05/11](../../README_DUC_05_11.md).
