from flask import Flask, render_template, Response, jsonify, request
import cv2
import time
import logging
import atexit
from threading import Lock
from flask_caching import Cache
from emotion_model import predict_emotion
from spotify_utils import update_playlist, get_or_create_playlist, play_playlist, EMOTION_GENRE_MAP, sp

app = Flask(__name__)

# Caching to optimize API calls
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Initialize webcam
video_capture = cv2.VideoCapture(0)

# Global variables for emotion detection
detected_emotion = "Waiting..."
last_emotion = None
last_update_time = time.time()
emotion_lock = Lock()

# Setup logging
logging.basicConfig(level=logging.INFO)

# Ensure webcam is open
if not video_capture.isOpened():
    logging.error("❌ Webcam initialization failed.")
    exit(1)  # Exit if the webcam cannot be opened

# Release webcam when the app stops
def release_camera():
    video_capture.release()
    logging.info("🎥 Webcam released successfully.")

atexit.register(release_camera)

@app.route('/')
def index():
    """Render the main webpage."""
    return render_template('index.html')

def get_stable_emotion(new_emotion):
    """Ensure the emotion remains the same for 5 seconds before updating."""
    global last_emotion, last_update_time
    current_time = time.time()

    if new_emotion == last_emotion:
        return new_emotion  # No change, return last emotion

    if current_time - last_update_time >= 5:
        last_emotion = new_emotion
        last_update_time = current_time
        return new_emotion
    
    return last_emotion  # Return previous stable emotion

def gen_frames():
    """Capture frames from webcam, detect emotion, and overlay text."""
    global detected_emotion
    while True:
        if not video_capture.isOpened():
            logging.error("❌ Webcam is not accessible. Stopping frame capture.")
            break

        success, frame = video_capture.read()
        if not success:
            logging.error("❌ Failed to read frame from webcam.")
            continue

        # Predict emotion and stabilize it
        emotion = predict_emotion(frame)
        stable_emotion = get_stable_emotion(emotion)

        # Update emotion only if it's different
        if detected_emotion != stable_emotion:
            with emotion_lock:
                detected_emotion = stable_emotion
                logging.info(f"🔄 Updated Emotion: {detected_emotion}")

        # Overlay emotion text on the frame
        cv2.putText(frame, f"Emotion: {detected_emotion}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Convert frame to JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            logging.error("❌ Failed to encode frame.")
            continue

        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@app.route('/video_feed')
def video_feed():
    """Stream video feed with real-time emotion detection."""
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_emotion', methods=['GET'])
def get_emotion():
    """Return the latest detected emotion."""
    global detected_emotion
    with emotion_lock:
        current_emotion = detected_emotion
    return jsonify({"emotion": current_emotion})

@app.route('/recommend', methods=['GET'])
@cache.cached(timeout=10)  # Cache recommendations for 10 seconds
def recommend():
    """Update Spotify playlist and return recommendations based on detected emotion."""
    global detected_emotion

    with emotion_lock:
        current_emotion = str(detected_emotion).lower()  # Ensure valid string

    logging.info(f"🎭 Current Emotion in /recommend: {current_emotion}")

    if current_emotion in ["waiting...", "error"]:
        return jsonify({"message": "Emotion not detected yet. Please wait."}), 400

    # Ensure emotion exists in Spotify mapping
    if current_emotion not in EMOTION_GENRE_MAP:
        logging.warning(f"⚠ Emotion '{current_emotion}' not in mapping. Using 'pop' as default.")
        current_emotion = "pop"

    playlist_id = get_or_create_playlist()
    if not playlist_id:
        return jsonify({"error": "Failed to retrieve or create playlist"}), 500

    tracks = update_playlist(playlist_id=playlist_id, emotion=current_emotion)

    if not tracks:
        return jsonify({"error": f"No tracks found for emotion '{current_emotion}'."}), 404

    playlist_url = f"https://open.spotify.com/playlist/{playlist_id}"
    
    return jsonify({
        "emotion": current_emotion,
        "message": f"🎵 Playlist updated with {current_emotion.capitalize()} tracks!",
        "spotify_playlist_url": playlist_url,
        "tracks": tracks
    })

@app.route('/play', methods=['POST'])
def play():
    """Trigger playback of the updated Spotify playlist."""
    playlist_id = get_or_create_playlist()
    if not playlist_id:
        return jsonify({"error": "Failed to retrieve playlist"}), 500

    # Ensure a Spotify device is active before playing
    try:
        devices = sp.devices().get("devices", [])
        if not devices:
            return jsonify({"error": "No active Spotify device. Open Spotify and try again."}), 400
    except Exception as e:
        logging.error(f"❌ Error fetching Spotify devices: {e}")
        return jsonify({"error": "Spotify authentication failed."}), 500

    success = play_playlist(playlist_id)
    if success:
        return jsonify({"message": "🎶 Playing playlist on Spotify!"})
    else:
        return jsonify({"error": "Playback failed. Try again."}), 400

if __name__ == '__main__':
    app.run(debug=True)