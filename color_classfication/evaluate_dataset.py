import argparse
import csv
from pathlib import Path

from predict_color import IMAGE_EXTENSIONS, load_image, predict_color


def iter_images(folder: Path) -> list[Path]:
    return sorted(
        path
        for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Danh gia do chinh xac tren dataset co cau truc data/red, data/blue, data/yellow."
    )
    parser.add_argument("--data-dir", type=Path, default=Path("data"), help="Thu muc dataset.")
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("results.csv"),
        help="File CSV de luu ket qua danh gia.",
    )
    parser.add_argument(
        "--min-area-ratio",
        type=float,
        default=0.01,
        help="Ti le dien tich mau toi thieu so voi ca anh. Mac dinh: 0.01.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    expected_classes = ("red", "blue", "yellow")
    rows: list[dict[str, str]] = []
    total = 0
    correct = 0

    for label in expected_classes:
        class_dir = args.data_dir / label
        if not class_dir.exists():
            print(f"Bo qua vi chua co thu muc: {class_dir}")
            continue

        for image_path in iter_images(class_dir):
            image = load_image(image_path)
            predicted_en, predicted_vi, confidence, areas, _ = predict_color(
                image=image,
                min_area_ratio=args.min_area_ratio,
            )
            is_correct = predicted_en == label
            total += 1
            correct += int(is_correct)

            rows.append(
                {
                    "image": str(image_path),
                    "true_label": label,
                    "predicted_label": predicted_en,
                    "predicted_vi": predicted_vi,
                    "confidence": f"{confidence:.4f}",
                    "is_correct": str(is_correct),
                    "red_area": str(areas["red"]),
                    "blue_area": str(areas["blue"]),
                    "yellow_area": str(areas["yellow"]),
                }
            )

    if not rows:
        print("Chua tim thay anh nao de danh gia.")
        return

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    accuracy = correct / total if total else 0.0
    print(f"Tong so anh: {total}")
    print(f"So anh dung: {correct}")
    print(f"Accuracy: {accuracy:.2%}")
    print(f"Da luu bang ket qua: {args.output_csv}")


if __name__ == "__main__":
    main()
