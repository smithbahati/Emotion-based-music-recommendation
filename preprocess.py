import cv2
import numpy as np

def preprocess_frame(frame):
    """
    Preprocess a single frame for the emotion detection model.

    Args:
        frame (numpy.ndarray): Input frame captured from the webcam.

    Returns:
        numpy.ndarray: Preprocessed frame ready for model prediction, or None if preprocessing fails.
    """
    try:
        # Convert the frame to grayscale as the model expects grayscale images
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces in the frame using Haar cascade
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.3, minNeighbors=5, minSize=(48, 48))
        
        if len(faces) == 0:
            # No face detected
            return None
        
        # Extract the first face detected
        x, y, w, h = faces[0]
        face = gray_frame[y:y+h, x:x+w]
        
        # Resize the face to the input size required by the model
        resized_face = cv2.resize(face, (48, 48))
        
        # Normalize pixel values to the range [0, 1]
        normalized_face = resized_face / 255.0
        
        # Expand dimensions to match the model's input shape (1, 48, 48, 1)
        preprocessed_face = np.expand_dims(normalized_face, axis=(0, -1))
        
        return preprocessed_face
    except Exception as e:
        print(f"Error in preprocessing frame: {e}")
        return None
