from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


MODEL_PATH = Path("models/basket_svm.xml")
FEATURE_SIZE = (128, 128)


def extract_basket_features(image: np.ndarray) -> np.ndarray:
    image = cv2.resize(image, FEATURE_SIZE, interpolation=cv2.INTER_AREA)

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1, 2], None, [12, 6, 6], [0, 180, 0, 256, 0, 256])
    hist = cv2.normalize(hist, hist).flatten()

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 80, 160)
    edge_density = np.array([np.count_nonzero(edges) / edges.size], dtype=np.float32)

    features = np.concatenate([hist.astype(np.float32), edge_density])
    return features.reshape(1, -1)


def load_basket_model(model_path: Path = MODEL_PATH) -> cv2.ml_SVM:
    if not model_path.exists():
        raise FileNotFoundError(f"Chua co model nhan dien ro: {model_path}")
    return cv2.ml.SVM_load(str(model_path))


def predict_is_basket(model: cv2.ml_SVM, image: np.ndarray) -> bool:
    features = extract_basket_features(image)
    _, result = model.predict(features)
    return int(result[0][0]) == 1
