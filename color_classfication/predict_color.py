import argparse
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class ColorRange:
    name_en: str
    name_vi: str
    ranges: tuple[tuple[tuple[int, int, int], tuple[int, int, int]], ...]


COLOR_RANGES = (
    ColorRange(
        name_en="red",
        name_vi="do",
        ranges=(
            ((0, 70, 50), (10, 255, 255)),
            ((170, 70, 50), (180, 255, 255)),
        ),
    ),
    ColorRange(
        name_en="blue",
        name_vi="xanh duong",
        ranges=(
            ((90, 60, 40), (130, 255, 255)),
        ),
    ),
    ColorRange(
        name_en="yellow",
        name_vi="vang",
        ranges=(
            ((18, 70, 60), (38, 255, 255)),
        ),
    ),
)


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def load_image(image_path: Path) -> np.ndarray:
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Khong the doc anh: {image_path}")
    return image


def resize_keep_ratio(image: np.ndarray, max_width: int = 640) -> np.ndarray:
    height, width = image.shape[:2]
    if width <= max_width:
        return image

    scale = max_width / width
    new_size = (max_width, int(height * scale))
    return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)


def build_mask(hsv_image: np.ndarray, color_range: ColorRange) -> np.ndarray:
    mask = np.zeros(hsv_image.shape[:2], dtype=np.uint8)

    for lower, upper in color_range.ranges:
        lower_np = np.array(lower, dtype=np.uint8)
        upper_np = np.array(upper, dtype=np.uint8)
        mask = cv2.bitwise_or(mask, cv2.inRange(hsv_image, lower_np, upper_np))

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask


def largest_region_area(mask: np.ndarray, min_component_area: int = 300) -> int:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return 0

    areas = [int(cv2.contourArea(contour)) for contour in contours]
    largest_area = max(areas)
    return largest_area if largest_area >= min_component_area else 0


def predict_color(
    image: np.ndarray,
    min_area_ratio: float = 0.01,
) -> tuple[str, str, float, dict[str, int], dict[str, np.ndarray]]:
    image = resize_keep_ratio(image)
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    image_area = image.shape[0] * image.shape[1]

    areas: dict[str, int] = {}
    masks: dict[str, np.ndarray] = {}

    for color_range in COLOR_RANGES:
        mask = build_mask(hsv_image, color_range)
        area = largest_region_area(mask)
        areas[color_range.name_en] = area
        masks[color_range.name_en] = mask

    total_detected_area = sum(areas.values())
    if total_detected_area == 0:
        return "unknown", "khong xac dinh", 0.0, areas, masks

    best_color = max(COLOR_RANGES, key=lambda item: areas[item.name_en])
    best_area = areas[best_color.name_en]
    confidence = best_area / total_detected_area

    if best_area / image_area < min_area_ratio:
        return "unknown", "khong xac dinh", confidence, areas, masks

    return best_color.name_en, best_color.name_vi, confidence, areas, masks


def save_debug_image(
    original_image: np.ndarray,
    masks: dict[str, np.ndarray],
    output_path: Path,
) -> None:
    image = resize_keep_ratio(original_image)
    overlay = image.copy()

    colors_bgr = {
        "red": (0, 0, 255),
        "blue": (255, 0, 0),
        "yellow": (0, 255, 255),
    }

    for color_name, mask in masks.items():
        color_layer = np.zeros_like(image)
        color_layer[:, :] = colors_bgr[color_name]
        overlay = np.where(mask[:, :, None] > 0, cv2.addWeighted(overlay, 0.6, color_layer, 0.4, 0), overlay)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), overlay)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Nhan dien mau cua mot chiec ro trong anh tinh bang xu ly anh HSV."
    )
    parser.add_argument("--image", required=True, type=Path, help="Duong dan den anh can du doan.")
    parser.add_argument(
        "--debug-output",
        type=Path,
        default=None,
        help="Neu truyen vao, luu anh overlay mask de kiem tra qua trinh nhan mau.",
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
    image = load_image(args.image)
    color_en, color_vi, confidence, areas, masks = predict_color(
        image=image,
        min_area_ratio=args.min_area_ratio,
    )

    print(f"Mau ro: {color_vi}")
    print(f"Nhan tieng Anh: {color_en}")
    print(f"Do tin cay: {confidence:.0%}")
    print("Dien tich mau phat hien:")
    for color_name, area in areas.items():
        print(f"- {color_name}: {area} pixel")

    if args.debug_output is not None:
        save_debug_image(image, masks, args.debug_output)
        print(f"Da luu anh debug: {args.debug_output}")


if __name__ == "__main__":
    main()
