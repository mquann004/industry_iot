# Smart Warehouse Color Classification

Đồ án mô phỏng hệ thống kho thông minh gồm 2 phần chính:

- **Computer Vision bằng Python**: mở webcam, nhận diện rổ, phân loại màu rổ `red`, `blue`, `yellow`, gửi số lượng lên Firebase.
- **Dashboard Web**: hiển thị nhiệt độ, độ ẩm, khí gas từ ESP32 và quản lý kệ kho theo màu rổ.

Hệ thống hiện có 3 kệ:

- **Kệ A**: rổ màu đỏ.
- **Kệ B**: rổ màu xanh.
- **Kệ C**: rổ màu vàng.

Khi webcam nhận diện được rổ màu nào, chương trình sẽ tăng số lượng kệ tương ứng trên Firebase. Nếu kệ đã đạt sức chứa được cấu hình trên website, Python sẽ không tăng thêm số lượng nữa.

## 1. Cấu Trúc Project

```text
color_classfication/
  predict_color.py              # Nhận diện màu từ ảnh tĩnh
  webcam_color.py               # Mở webcam, nhận màu, gửi Firebase
  firebase_color.py             # Ghi dữ liệu màu lên Firebase Realtime Database
  basket_detector.py            # Helper nhận diện rổ / không-rổ bằng SVM
  collect_basket_data.py        # Thu dataset rổ / không-rổ bằng webcam
  train_basket_detector.py      # Train model SVM nhận diện rổ
  augment_dataset.py            # Tạo thêm ảnh dataset bằng augmentation
  evaluate_dataset.py           # Đánh giá accuracy màu trên dataset ảnh tĩnh
  requirements.txt              # Thư viện Python cần cài
  web/
    index.html                  # Dashboard web hoàn chỉnh
  data/                         # Dataset local, không commit ảnh lên GitHub
  models/                       # Model local, không commit file train lên GitHub
  outputs/                      # Ảnh debug/output local
```

## 2. Công Nghệ Sử Dụng

- Python 3.10+
- OpenCV
- NumPy
- Requests
- Firebase Realtime Database
- HTML, CSS, JavaScript
- Chart.js
- ESP32, DHT11, MQ2 cho phần cảm biến môi trường

## 3. Cài Đặt Python

Mở CMD tại thư mục project:

```bat
cd /d D:\color_classfication
```

Tạo môi trường ảo nếu chưa có:

```bat
python -m venv .venv
```

Kích hoạt môi trường ảo:

```bat
.venv\Scripts\activate.bat
```

Cài thư viện:

```bat
pip install -r requirements.txt
```

## 4. Chạy Nhận Diện Ảnh Tĩnh

Ví dụ nhận diện một ảnh rổ:

```bat
python predict_color.py --image data/red/red1.png
```

Lưu ảnh debug để xem vùng màu được nhận:

```bat
python predict_color.py --image data/red/red1.png --debug-output outputs/debug.jpg
```

## 5. Chạy Webcam Không Gửi Firebase

```bat
python webcam_color.py
```

Phím dùng trong cửa sổ webcam:

- `q`: thoát.
- `s`: lưu ảnh hiện tại vào `outputs/`.
- `n`: lưu vùng bị nhận nhầm vào `data/basket_detector/not_basket/`.

## 6. Chạy Webcam Có Gửi Firebase

Đây là lệnh chính khi demo:

```bat
python webcam_color.py --firebase-enabled
```

Nếu muốn nhạy hơn:

```bat
python webcam_color.py --firebase-enabled --stable-frames 8 --reset-frames 12
```

Dữ liệu được ghi vào:

```text
devices/esp32_01/color
```

Dạng dữ liệu:

```json
{
  "red": 0,
  "blue": 0,
  "yellow": 0,
  "last_detected": "red",
  "last_detected_label": "do",
  "last_update": 1781059200
}
```

## 7. Cấu Hình Firebase Rules

Vào Firebase Console:

```text
Realtime Database -> Rules
```

Rules demo:

```json
{
  "rules": {
    "devices": {
      "esp32_01": {
        ".read": true,
        "color": {
          ".write": true
        },
        "settings": {
          ".write": true
        },
        "latest": {
          ".write": true
        },
        "history": {
          ".write": true
        }
      }
    }
  }
}
```

Sau khi sửa rules, bấm **Publish**.

## 8. Chạy Website Dashboard

Mở file:

```text
web/index.html
```

Hoặc bản đang dùng ngoài project:

```text
D:\demo_app\index.html
```

Dashboard gồm:

- Trạng thái an toàn / cảnh báo.
- Nhiệt độ.
- Độ ẩm.
- Nồng độ khí gas.
- Biểu đồ lịch sử dữ liệu.
- Kệ kho A/B/C theo màu rổ.
- Cài đặt hệ thống.

Trong **Cài đặt hệ thống**, có thể chỉnh:

- Ngưỡng nhiệt độ.
- Ngưỡng độ ẩm.
- Ngưỡng khí gas.
- Sức chứa kệ A.
- Sức chứa kệ B.
- Sức chứa kệ C.

Nếu một kệ đã đầy, website sẽ cảnh báo và Python sẽ không tăng thêm số lượng cho kệ đó.

## 9. Reset Số Lượng Kệ

Trong mục **Kệ kho**, mỗi kệ có nút:

```text
Reset kệ
```

Khi nhấn, số lượng kệ tương ứng trên Firebase sẽ được đưa về `0`.

## 10. Train Model Nhận Diện Rổ / Không-Rổ

Nếu webcam hay nhận nhầm vật khác là rổ, cần thu thêm dataset.

Thu dữ liệu:

```bat
python collect_basket_data.py
```

Trong cửa sổ webcam:

- Đưa rổ vào khung xanh, bấm `b`.
- Đưa mặt, tay, áo, tường, nền phòng, đồ vật khác vào khung xanh, bấm `n`.
- Bấm `q` để thoát.

Train model:

```bat
python train_basket_detector.py
```

Model được lưu tại:

```text
models/basket_svm.xml
```

Nếu chỉ có ít ảnh gốc, tạo thêm ảnh bằng augmentation:

```bat
python augment_dataset.py
```

Sau đó train bằng dataset augment:

```bat
python train_basket_detector.py --data-dir data/basket_detector_aug
```

## 11. Lưu Ý Khi Up GitHub

File `.gitignore` đã được cấu hình để không commit:

- `.venv/`
- `__pycache__/`
- ảnh dataset trong `data/`
- model train trong `models/`
- ảnh debug trong `outputs/`

Các thư mục `data/`, `models/`, `outputs/` vẫn giữ `.gitkeep` để repo có sẵn cấu trúc thư mục.

Nếu muốn chia sẻ model hoặc dataset cho giáo viên, có thể nén riêng và gửi ngoài GitHub.

## 12. Lệnh Demo Nhanh

Terminal 1:

```bat
cd /d D:\color_classfication
.venv\Scripts\activate.bat
python webcam_color.py --firebase-enabled
```

Trình duyệt:

```text
D:\color_classfication\web\index.html
```

Hoặc:

```text
D:\demo_app\index.html
```

