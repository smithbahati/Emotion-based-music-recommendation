import numpy as np
import cv2
import logging
import mediapipe as mp
from tensorflow.keras.models import load_model
import gdown


# Using --fuzzy to handle Drive URLs more flexibly
url = 'https://drive.google.com/file/d/1q-C6W573bSLkSt-uq5yiFYf1hlzSllPu/view?usp=drive_link'
output = 'model_file_30epochs.h5'
gdown.download(url, output, quiet=False, fuzzy=True)

# Setup logging
logging.basicConfig(level=logging.INFO)

# Load the trained model
try:
    model = load_model("model_file_30epochs.h5")
    logging.info("Emotion model loaded successfully.")
except Exception as e:
    logging.error(f" Failed to load model: {e}")
    model = None  # Avoid crashing if the model fails to load

# Emotion labels (standardized to lowercase to match Spotify)
EMOTION_LABELS = ["angry", "disgusted", "fear", "happy", "sad", "surprise", "neutral"]

# Initialize Mediapipe Face Detection
mp_face_detection = mp.solutions.face_detection
face_detection = mp_face_detection.FaceDetection(min_detection_confidence=0.3)  # Lowered threshold

def preprocess_frame(frame):
    try:
        if frame is None or frame.shape[0] == 0 or frame.shape[1] == 0:
            logging.warning(" Invalid frame received for preprocessing.")
            return None

        # Convert to grayscale
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Convert frame to RGB for Mediapipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_detection.process(rgb_frame)

        if not results.detections:
            logging.info(" No face detected in the frame.")
            return None  # No face detected

        # Get bounding box of the first detected face
        h, w, _ = frame.shape
        bboxC = results.detections[0].location_data.relative_bounding_box

        x, y, w, h = (int(bboxC.xmin * w), int(bboxC.ymin * h),
                      int(bboxC.width * w), int(bboxC.height * h))

        # 🔹 Dynamic margin (10% of face size)
        margin = int(min(w, h) * 0.1)
        x = max(0, x - margin)
        y = max(0, y - margin)
        w = min(w + 2 * margin, frame.shape[1] - x)
        h = min(h + 2 * margin, frame.shape[0] - y)

        face = gray_frame[y:y + h, x:x + w]  # Extract face region

        if face.shape[0] == 0 or face.shape[1] == 0:
            logging.warning(" Extracted face region is empty. Skipping frame.")
            return None

        face_resized = cv2.resize(face, (48, 48))  # Resize to model input size
        normalized_face = face_resized / 255.0  # Normalize

        return np.expand_dims(normalized_face, axis=(0, -1))  # Shape: (1, 48, 48, 1)
    except Exception as e:
        logging.error(f" Preprocessing failed: {e}")
        return None

def predict_emotion(frame):
    if model is None:
        logging.error("Model is not loaded. Cannot make predictions.")
        return "neutral"  #  Always return lowercase to match Spotify genres

    try:
        preprocessed_frame = preprocess_frame(frame)
        if preprocessed_frame is None:
            return "neutral"

        logging.info(f" Preprocessed Frame Shape: {preprocessed_frame.shape}")

        predictions = model.predict(preprocessed_frame)[0]  # Extract first array
        logging.info(f" Model Predictions: {predictions}")

        max_prob = np.max(predictions)
        emotion_index = np.argmax(predictions)
        detected_emotion = EMOTION_LABELS[emotion_index]

        #  Improved confidence filtering
        if max_prob < 0.50:  # Increase confidence threshold
            logging.info(f" Low confidence ({max_prob:.2f}), using best guess: {detected_emotion}")
            return "neutral"  # Default to neutral if confidence is too low

        return detected_emotion
    except Exception as e:
        logging.error(f" Prediction failed: {e}")
        return "neutral"
