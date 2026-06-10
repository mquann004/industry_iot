import argparse
from pathlib import Path

import cv2
import numpy as np

from basket_detector import MODEL_PATH, extract_basket_features
from predict_color import IMAGE_EXTENSIONS, load_image


def iter_images(folder: Path) -> list[Path]:
    return sorted(
        path
        for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train model SVM phan biet ro va khong-ro.")
    parser.add_argument("--data-dir", type=Path, default=Path("data/basket_detector"))
    parser.add_argument("--model-output", type=Path, default=MODEL_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    basket_images = iter_images(args.data_dir / "basket")
    not_basket_images = iter_images(args.data_dir / "not_basket")

    if len(basket_images) < 20 or len(not_basket_images) < 20:
        raise RuntimeError(
            "Can toi thieu 20 anh basket va 20 anh not_basket. "
            "Nen co 100-200 anh moi nhom de on dinh hon."
        )

    features = []
    labels = []

    for image_path in basket_images:
        features.append(extract_basket_features(load_image(image_path))[0])
        labels.append(1)

    for image_path in not_basket_images:
        features.append(extract_basket_features(load_image(image_path))[0])
        labels.append(0)

    train_data = np.array(features, dtype=np.float32)
    responses = np.array(labels, dtype=np.int32)

    svm = cv2.ml.SVM_create()
    svm.setType(cv2.ml.SVM_C_SVC)
    svm.setKernel(cv2.ml.SVM_RBF)
    svm.setC(2.0)
    svm.setGamma(0.5)
    svm.train(train_data, cv2.ml.ROW_SAMPLE, responses)

    _, predictions = svm.predict(train_data)
    accuracy = float(np.mean(predictions.flatten().astype(np.int32) == responses))

    args.model_output.parent.mkdir(parents=True, exist_ok=True)
    svm.save(str(args.model_output))

    print(f"So anh basket: {len(basket_images)}")
    print(f"So anh not_basket: {len(not_basket_images)}")
    print(f"Train accuracy: {accuracy:.2%}")
    print(f"Da luu model: {args.model_output}")


if __name__ == "__main__":
    main()
