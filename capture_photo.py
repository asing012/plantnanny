import cv2, os
from datetime import datetime, timedelta

PHOTO_DIR = os.path.join(os.path.dirname(__file__), "photos")
KEEP_DAYS = 30
os.makedirs(PHOTO_DIR, exist_ok=True)

# Capture
cap = cv2.VideoCapture(2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

ret, frame = cap.read()
if ret:
    path = os.path.join(PHOTO_DIR, datetime.now().strftime("%Y-%m-%d.jpg"))
    cv2.imwrite(path, frame)
    print(f"✅ Photo saved: {path}")
else:
    print("❌ Camera not found")
cap.release()

# Cleanup old photos
cutoff = datetime.now() - timedelta(days=KEEP_DAYS)
for f in os.listdir(PHOTO_DIR):
    if f.endswith(".jpg"):
        try:
            date = datetime.strptime(f, "%Y-%m-%d.jpg")
            if date < cutoff:
                os.remove(os.path.join(PHOTO_DIR, f))
                print(f"🗑️ Deleted old photo: {f}")
        except ValueError:
            pass