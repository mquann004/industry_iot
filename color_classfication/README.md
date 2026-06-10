# Color Classification - Nhan Dien Mau Ro

Project nay nhan dien mau cua mot chiec ro trong anh tinh bang xu ly anh HSV.
Phien ban dau ho tro 3 mau: `red`, `blue`, `yellow`.

## 1. Cai Dat

Can Python 3.10 tro len.

```bash
pip install -r requirements.txt
```

## 2. Chuan Bi Du Lieu

Tao cau truc thu muc:

```text
data/
  red/
    red_001.jpg
    red_002.jpg
  blue/
    blue_001.jpg
    blue_002.jpg
  yellow/
    yellow_001.jpg
    yellow_002.jpg
```

Moi mau nen co it nhat 30-50 anh de kiem thu. Anh nen co nhieu dieu kien anh sang
va goc chup khac nhau, nhung ban dau nen dam bao moi anh chi co mot chiec ro chinh.

## 3. Du Doan Mot Anh

```bash
python predict_color.py --image data/red/red_001.jpg
```

Vi du output:

```text
Mau ro: do
Nhan tieng Anh: red
Do tin cay: 87%
Dien tich mau phat hien:
- red: 25000 pixel
- blue: 0 pixel
- yellow: 120 pixel
```

Co the luu anh debug de xem vung mau chuong trinh da nhan:

```bash
python predict_color.py --image data/red/red_001.jpg --debug-output outputs/debug_red_001.jpg
```

## 4. Danh Gia Ca Dataset

```bash
python evaluate_dataset.py --data-dir data --output-csv results.csv
```

Script se in accuracy va tao file `results.csv` gom:

- Ten anh.
- Mau that.
- Mau du doan.
- Do tin cay.
- Dung/sai.
- Dien tich tung mau phat hien duoc.

## 5. Chay Bang Webcam Laptop

Mo webcam va nhan dien mau truc tiep:

```bash
python webcam_color.py
```

Khi cua so camera hien len:

- Dat chiec ro vao khung mau xanh o giua man hinh.
- Chuong trinh se hien mau du doan tren goc trai.
- Bam `q` de thoat.
- Bam `s` de luu anh hien tai vao thu muc `outputs/`.
- Neu chuong trinh nham nen/mat/tuong la ro, bam `n` de luu vung sai vao `data/basket_detector/not_basket/`, sau do train lai model.

Neu khong mo duoc camera, thu camera ID khac:

```bash
python webcam_color.py --camera 1
```

Neu nen co mau giong ro, hay dua ro vao sat khung xanh va giam kich thuoc vung nhan:

```bash
python webcam_color.py --roi-scale 0.4
```

## 6. Gui Mau Len Firebase Va Dashboard Ke Hang

Website dashboard doc du lieu tai:

```text
devices/esp32_01/color
```

Du lieu tren Firebase co dang:

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

Chay webcam va gui ket qua len Firebase:

```bash
python webcam_color.py --firebase-enabled
```

Mac dinh chuong trinh dung database URL:

```text
https://smartwarehouse-f36ba-default-rtdb.asia-southeast1.firebasedatabase.app
```

Neu database URL khac, truyen vao:

```bash
python webcam_color.py --firebase-enabled --firebase-url YOUR_DATABASE_URL
```

De tranh mot ro bi dem nhieu lan, chuong trinh chi tang so luong khi cung mot
mau on dinh trong nhieu frame va phai lay ro ra/doi trang thai truoc khi dem luot
moi. Co the tinh chinh:

```bash
python webcam_color.py --firebase-enabled --stable-frames 8 --reset-frames 12
```

Firebase Realtime Database rules cho demo can cho phep doc/ghi node color:

```json
{
  "rules": {
    "devices": {
      "esp32_01": {
        ".read": true,
        "color": {
          ".write": true
        }
      }
    }
  }
}
```

Website `index.html` se hien:

- Ke A: so ro mau do.
- Ke B: so ro mau xanh.
- Ke C: so ro mau vang.
- Mau vua nhan dien va thoi gian cap nhat gan nhat.

## 7. Train Nhan Dien Co Phai Cai Ro Khong

Ban dau webcam chi do mau trong khung xanh. Neu muon no biet "co phai cai ro
khong", can train them model ro/khong-ro.

Buoc 1: thu thap du lieu bang webcam:

```bash
python collect_basket_data.py
```

Trong cua so webcam:

- Dua ro vao khung xanh, bam `b` de luu anh `basket`.
- Dua mat, ao, tuong, nen phong, ban tay, do vat khac vao khung xanh, bam `n` de luu anh `not_basket`.
- Bam `q` de thoat.

Nen chuan bi:

- Toi thieu 20 anh `basket` va 20 anh `not_basket` de chay thu.
- Nen co 100-200 anh moi nhom de ket qua on dinh hon.
- Anh `basket` nen co nhieu mau ro, goc chup, khoang cach, anh sang khac nhau.
- Anh `not_basket` nen gom nhung thu hay xuat hien khi demo: mat nguoi, ao, tay, tuong, nen phong.

Buoc 2: train model:

```bash
python train_basket_detector.py
```

Model se duoc luu tai:

```text
models/basket_svm.xml
```

Buoc 3: chay webcam lai:

```bash
python webcam_color.py
```

Luc nay neu khung xanh khong co ro, man hinh se hien:

```text
Chua phat hien ro
```

Neu co ro, chuong trinh moi hien mau cua ro.

Neu model nhan sai khi khong co ro:

1. Chay `python webcam_color.py`.
2. De dung canh bi nham trong khung xanh.
3. Bam `n` nhieu lan de luu anh sai vao `not_basket`.
4. Train lai:

```bash
python train_basket_detector.py --data-dir data/basket_detector
```

5. Chay lai webcam.

Neu chi co it anh goc, co the tao them anh bang augmentation:

```bash
python augment_dataset.py
```

Lenh nay doc anh tu:

```text
data/basket_detector/basket/
data/basket_detector/not_basket/
```

Va tao dataset moi tai:

```text
data/basket_detector_aug/
```

Sau do train bang dataset da augmentation:

```bash
python train_basket_detector.py --data-dir data/basket_detector_aug
```

Moi anh goc se tao ra khoang 11 bien the: xoay nhe, sang/toi, mo nhe, nhieu nhe,
lat ngang. Nen co it nhat 20-30 anh goc moi nhom truoc khi augmentation.

## 8. Cach Hoat Dong

Quy trinh xu ly:

1. Doc anh bang OpenCV.
2. Resize anh ve chieu rong toi da 640 pixel.
3. Chuyen anh tu BGR sang HSV.
4. Tao mask cho tung mau: do, xanh duong, vang.
5. Loc nhieu bang morphology open/close.
6. Tim vung mau lon nhat cua moi class.
7. Chon mau co dien tich lon nhat.
8. Neu dien tich mau qua nho, tra ve `khong xac dinh`.

HSV duoc dung vi de tach mau on dinh hon RGB khi anh thay doi do sang.

Neu da train model ro/khong-ro, webcam se kiem tra co ro trong khung truoc, sau
do moi nhan dien mau.

## 9. Tinh Chinh Neu Du Doan Sai

Nguong mau nam trong bien `COLOR_RANGES` cua file `predict_color.py`.

Neu anh thuc te bi sai do anh sang, hay chay voi `--debug-output` de xem mask, sau do
dieu chinh cac khoang HSV:

- Hue: sac mau.
- Saturation: do dam cua mau.
- Value: do sang.

Vi du mau vang trong thuc te co the can mo rong:

```python
((15, 50, 50), (42, 255, 255))
```

## 10. Han Che

- De sai neu nen co mau giong mau ro.
- De sai neu anh qua toi, qua chay sang, hoac ro bi bong loang manh.
- Neu chua train model ro/khong-ro, webcam chi do mau trong khung xanh.
- Model ro/khong-ro can du lieu dung voi moi truong demo de dat ket qua tot.
- Chua xu ly truong hop co nhieu ro trong cung mot anh.
- Chua phai deep learning; day la baseline computer vision de lam bai toan nho, de hieu va de bao cao.

## 11. Huong Phat Trien

- Them nhieu mau hon vao `COLOR_RANGES`.
- Cat vung ro truoc khi phan loai neu nen phuc tap.
- Sau khi co nhieu du lieu, co the train CNN hoac YOLO neu giao vien yeu cau mo hinh AI hoc tu du lieu.
