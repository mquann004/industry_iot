import argparse
from pathlib import Path
from time import strftime

import cv2

from basket_detector import MODEL_PATH, load_basket_model, predict_is_basket
from firebase_color import DEFAULT_COLOR_PATH, DEFAULT_FIREBASE_URL, FirebaseColorClient, SUPPORTED_COLORS, ShelfFullError
from predict_color import predict_color


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mo webcam va nhan dien mau ro theo thoi gian thuc."
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="ID camera. Mac dinh la 0, thu 1 neu laptop co nhieu camera.",
    )
    parser.add_argument(
        "--roi-scale",
        type=float,
        default=0.6,
        help="Ti le khung giua dung de nhan mau. Mac dinh: 0.6.",
    )
    parser.add_argument(
        "--min-area-ratio",
        type=float,
        default=0.005,
        help="Ti le dien tich mau toi thieu trong vung nhan dien. Mac dinh: 0.005.",
    )
    parser.add_argument(
        "--save-dir",
        type=Path,
        default=Path("outputs"),
        help="Thu muc luu anh khi bam phim s.",
    )
    parser.add_argument(
        "--basket-model",
        type=Path,
        default=MODEL_PATH,
        help="Model SVM de kiem tra co phai ro khong. Neu file chua ton tai, webcam chi do mau.",
    )
    parser.add_argument(
        "--color-fallback-area-ratio",
        type=float,
        default=0.008,
        help="Neu model chua nhan ra ro nhung mau do/xanh/vang du lon, van chap nhan la co ro. Mac dinh: 0.008.",
    )
    parser.add_argument(
        "--basket-hold-frames",
        type=int,
        default=8,
        help="So frame tiep tuc giu trang thai co ro sau khi vua nhan ra ro. Mac dinh: 8.",
    )
    parser.add_argument(
        "--firebase-enabled",
        action="store_true",
        help="Bat gui ket qua mau len Firebase Realtime Database.",
    )
    parser.add_argument(
        "--firebase-url",
        default=DEFAULT_FIREBASE_URL,
        help="Firebase Realtime Database URL.",
    )
    parser.add_argument(
        "--firebase-color-path",
        default=DEFAULT_COLOR_PATH,
        help="Duong dan node color tren Firebase. Mac dinh: devices/esp32_01/color.",
    )
    parser.add_argument(
        "--stable-frames",
        type=int,
        default=10,
        help="So frame cung mau lien tiep truoc khi dem. Mac dinh: 10.",
    )
    parser.add_argument(
        "--reset-frames",
        type=int,
        default=15,
        help="So frame khong thay ro/mau truoc khi cho dem luot moi. Mac dinh: 15.",
    )
    return parser.parse_args()


def get_center_roi(frame, roi_scale: float):
    height, width = frame.shape[:2]
    roi_scale = max(0.1, min(1.0, roi_scale))

    roi_width = int(width * roi_scale)
    roi_height = int(height * roi_scale)
    x1 = (width - roi_width) // 2
    y1 = (height - roi_height) // 2
    x2 = x1 + roi_width
    y2 = y1 + roi_height

    return frame[y1:y2, x1:x2], (x1, y1, x2, y2)


def draw_result(frame, box, color_vi: str, color_en: str, confidence: float, is_basket: bool) -> None:
    x1, y1, x2, y2 = box
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    label = "Chua phat hien ro"
    if is_basket:
        label = f"Mau ro: {color_vi} ({confidence:.0%})"
        if color_en == "unknown":
            label = "Mau ro: khong xac dinh"

    cv2.rectangle(frame, (10, 10), (620, 80), (0, 0, 0), -1)
    cv2.putText(
        frame,
        label,
        (20, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        "Dat ro vao khung xanh | q: thoat | s: luu anh | n: luu not_basket",
        (20, 70),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (220, 220, 220),
        1,
        cv2.LINE_AA,
    )


def main() -> None:
    args = parse_args()
    capture = cv2.VideoCapture(args.camera)
    basket_model = None
    basket_hold_count = 0
    firebase_client = None
    last_stable_color = None
    stable_count = 0
    reset_count = 0
    ready_to_count = True

    if not capture.isOpened():
        raise RuntimeError(
            f"Khong mo duoc camera ID {args.camera}. Hay thu --camera 1 hoac kiem tra quyen camera."
        )
    if args.basket_model.exists():
        basket_model = load_basket_model(args.basket_model)
        print(f"Da tai model nhan dien ro: {args.basket_model}")
    else:
        print("Chua co model nhan dien ro, webcam se chi do mau trong khung xanh.")
        print("Hay chay collect_basket_data.py va train_basket_detector.py neu muon phat hien ro/khong-ro.")

    if args.firebase_enabled:
        firebase_client = FirebaseColorClient(
            database_url=args.firebase_url,
            color_path=args.firebase_color_path,
        )
        try:
            firebase_client.ensure_color_defaults()
        except Exception as error:
            raise RuntimeError(
                "Khong ket noi/ghi duoc Firebase color path. "
                "Hay kiem tra internet, databaseURL va Firebase Realtime Database rules."
            ) from error
        print(f"Da ket noi Firebase color path: {args.firebase_color_path}")

    print("Dang mo webcam...")
    print("Dat chiec ro vao khung xanh.")
    print("Bam q de thoat, bam s de luu anh hien tai.")

    args.save_dir.mkdir(parents=True, exist_ok=True)

    while True:
        ok, frame = capture.read()
        if not ok:
            print("Khong doc duoc frame tu webcam.")
            break

        roi, box = get_center_roi(frame, args.roi_scale)
        color_en, color_vi, confidence, areas, _ = predict_color(
            image=roi,
            min_area_ratio=args.min_area_ratio,
        )
        is_basket = True
        if basket_model is not None:
            is_basket = predict_is_basket(basket_model, roi)
            roi_area = roi.shape[0] * roi.shape[1]
            color_area = areas.get(color_en, 0) if color_en != "unknown" else 0
            has_clear_color = color_area / roi_area >= args.color_fallback_area_ratio

            if not is_basket and has_clear_color:
                is_basket = True

            if is_basket:
                basket_hold_count = args.basket_hold_frames
            elif basket_hold_count > 0:
                is_basket = True
                basket_hold_count -= 1

        can_count_color = is_basket and color_en in SUPPORTED_COLORS
        if can_count_color:
            reset_count = 0
            if color_en == last_stable_color:
                stable_count += 1
            else:
                last_stable_color = color_en
                stable_count = 1

            if (
                firebase_client is not None
                and ready_to_count
                and stable_count >= args.stable_frames
            ):
                try:
                    next_count = firebase_client.increment_color(color_en, color_vi)
                    print(f"Da gui Firebase: color={color_en}, count={next_count}")
                    ready_to_count = False
                except ShelfFullError as error:
                    print(
                        f"Ke {error.color_en} da day "
                        f"({error.current_count}/{error.capacity}), khong tang so luong."
                    )
                    ready_to_count = False
                except Exception as error:
                    print(f"Loi gui Firebase: {error}")
        else:
            stable_count = 0
            last_stable_color = None
            reset_count += 1
            if reset_count >= args.reset_frames:
                ready_to_count = True

        draw_result(frame, box, color_vi, color_en, confidence, is_basket)
        cv2.imshow("Nhan dien mau ro", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord("s"):
            filename = args.save_dir / f"webcam_{strftime('%Y%m%d_%H%M%S')}.jpg"
            cv2.imwrite(str(filename), frame)
            print(f"Da luu anh: {filename}")
        if key == ord("n"):
            not_basket_dir = Path("data/basket_detector/not_basket")
            not_basket_dir.mkdir(parents=True, exist_ok=True)
            filename = not_basket_dir / f"hard_negative_{strftime('%Y%m%d_%H%M%S')}.jpg"
            cv2.imwrite(str(filename), roi)
            print(f"Da luu anh sai vao not_basket: {filename}")

    capture.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
