import cv2
from deepface import DeepFace

# Load the authorized user's image 
authorized_image = cv2.imread("hitarthi.jpg")

# Initialize webcam
cap = cv2.VideoCapture(0)

# Check if the webcam is opened successfully
if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

while True:
    # Capture frame from the webcam
    ret, frame = cap.read()

    if not ret:
        print("Failed to capture frame.")
        break

    frame = cv2.resize(frame, (640, 480))

    cv2.imshow('Face Recognition', frame)

    # Try face verification with DeepFace
    try:
        # Perform face verification
        result = DeepFace.verify(img1_path=frame, img2_path=authorized_image, enforce_detection=False)

        if result['verified']:
            print("Authorized user detected! Gesture control activated.")
        else:
            print("Unauthorized user detected.")
    except Exception as e:
        print(f"Error: {str(e)}")

    # Press 'q' to exit the webcam feed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()