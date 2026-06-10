import argparse
from pathlib import Path

import cv2
import numpy as np

from predict_color import IMAGE_EXTENSIONS, load_image


def iter_images(folder: Path) -> list[Path]:
    return sorted(
        path
        for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def rotate_image(image: np.ndarray, angle: float) -> np.ndarray:
    height, width = image.shape[:2]
    center = (width // 2, height // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        image,
        matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT,
    )


def adjust_brightness(image: np.ndarray, alpha: float, beta: int) -> np.ndarray:
    return cv2.convertScaleAbs(image, alpha=alpha, beta=beta)


def add_noise(image: np.ndarray, sigma: float) -> np.ndarray:
    noise = np.random.normal(0, sigma, image.shape).astype(np.float32)
    noisy = image.astype(np.float32) + noise
    return np.clip(noisy, 0, 255).astype(np.uint8)


def augment_image(image: np.ndarray) -> list[np.ndarray]:
    variants = [
        image,
        rotate_image(image, -8),
        rotate_image(image, 8),
        rotate_image(image, -15),
        rotate_image(image, 15),
        adjust_brightness(image, 0.75, -10),
        adjust_brightness(image, 1.25, 10),
        adjust_brightness(image, 1.05, 35),
        cv2.GaussianBlur(image, (5, 5), 0),
        add_noise(image, 8),
        cv2.flip(image, 1),
    ]
    return variants


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tao them anh dataset bang data augmentation cho basket/not_basket."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/basket_detector"),
        help="Thu muc chua basket/ va not_basket/ anh goc.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/basket_detector_aug"),
        help="Thu muc luu dataset da augmentation.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    labels = ("basket", "not_basket")
    total_saved = 0

    for label in labels:
        input_label_dir = args.input_dir / label
        output_label_dir = args.output_dir / label
        output_label_dir.mkdir(parents=True, exist_ok=True)

        images = iter_images(input_label_dir)
        if not images:
            print(f"Khong co anh trong: {input_label_dir}")
            continue

        saved_for_label = 0
        for image_index, image_path in enumerate(images):
            image = load_image(image_path)
            variants = augment_image(image)

            for variant_index, variant in enumerate(variants):
                output_path = output_label_dir / f"{image_path.stem}_aug_{image_index:04d}_{variant_index:02d}.jpg"
                cv2.imwrite(str(output_path), variant)
                saved_for_label += 1
                total_saved += 1

        print(f"{label}: tao {saved_for_label} anh tu {len(images)} anh goc.")

    print(f"Tong so anh da tao: {total_saved}")
    print(f"Dataset augmentation nam tai: {args.output_dir}")


if __name__ == "__main__":
    main()
