import argparse
from pathlib import Path
from time import strftime

import cv2

from webcam_color import get_center_roi


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Thu thap anh ro/khong-ro bang webcam de train model nhan dien ro."
    )
    parser.add_argument("--camera", type=int, default=0, help="ID camera. Mac dinh: 0.")
    parser.add_argument("--roi-scale", type=float, default=0.6, help="Ti le khung giua. Mac dinh: 0.6.")
    parser.add_argument("--data-dir", type=Path, default=Path("data/basket_detector"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    basket_dir = args.data_dir / "basket"
    not_basket_dir = args.data_dir / "not_basket"
    basket_dir.mkdir(parents=True, exist_ok=True)
    not_basket_dir.mkdir(parents=True, exist_ok=True)

    capture = cv2.VideoCapture(args.camera)
    if not capture.isOpened():
        raise RuntimeError(f"Khong mo duoc camera ID {args.camera}.")

    print("Bam b de luu anh CO RO.")
    print("Bam n de luu anh KHONG CO RO.")
    print("Bam q de thoat.")

    basket_count = 0
    not_basket_count = 0

    while True:
        ok, frame = capture.read()
        if not ok:
            break

        roi, box = get_center_roi(frame, args.roi_scale)
        x1, y1, x2, y2 = box
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.rectangle(frame, (10, 10), (700, 85), (0, 0, 0), -1)
        cv2.putText(
            frame,
            f"basket: {basket_count} | not_basket: {not_basket_count}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            "b: luu co ro | n: luu khong ro | q: thoat",
            (20, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (220, 220, 220),
            1,
            cv2.LINE_AA,
        )
        cv2.imshow("Thu thap du lieu ro", frame)

        key = cv2.waitKey(1) & 0xFF
        timestamp = strftime("%Y%m%d_%H%M%S")
        if key == ord("q"):
            break
        if key == ord("b"):
            path = basket_dir / f"basket_{timestamp}_{basket_count:04d}.jpg"
            cv2.imwrite(str(path), roi)
            basket_count += 1
            print(f"Da luu: {path}")
        if key == ord("n"):
            path = not_basket_dir / f"not_basket_{timestamp}_{not_basket_count:04d}.jpg"
            cv2.imwrite(str(path), roi)
            not_basket_count += 1
            print(f"Da luu: {path}")

    capture.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
