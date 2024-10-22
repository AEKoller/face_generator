
import requests
import json
import sys
import time
from PIL import Image

BASE_URL = "https://gateway.extempo.rocks"

def login(username, password):
    try:
        print(f"Attempting to connect to {BASE_URL}/auth/login")
        response = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password}, timeout=10)
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text}")
        if response.status_code == 200:
            return response.json()["token"]
        else:
            print(f"Login failed: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during login: {e}")
        print(f"Error type: {type(e).__name__}")
        return None

def get_user_info(token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{BASE_URL}/users/me", headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get user info: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while getting user info: {e}")
        return None

def decode_random_face(token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{BASE_URL}/decode", headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to decode random face: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while decoding random face: {e}")
        return None

def get_image(token, path, id):
    headers = {"Authorization": f"Bearer {token}"}
    params = {"path": path, "id": id}
    try:
        response = requests.get(f"{BASE_URL}/image/{path}/{id}", headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            return response.content
        else:
            print(f"Failed to get image: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while getting image: {e}")
        return None

def get_predictions(token, s3_key):
    headers = {"Authorization": f"Bearer {token}"}
    parts = s3_key.split('/')
    if len(parts) < 3:
        print(f"Invalid s3_key format: {s3_key}")
        return None
    
    prefix = parts[1]
    image_name = parts[-1]
    
    try:
        url = f"{BASE_URL}/predictions/{prefix}/{image_name}"
        print(f"Requesting predictions from: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get predictions: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while getting predictions: {e}")
        return None

def save_and_show_image(image_data, filename):
    with open(filename, "wb") as f:
        f.write(image_data)
    print(f"Image saved as '{filename}'")
    Image.open(filename).show()

def save_predictions(predictions, filename):
    with open(filename, 'w') as f:
        json.dump(predictions, f, indent=2)
    print(f"Predictions saved to {filename}")

def wait_with_message(seconds, message):
    print(message)
    for i in range(seconds, 0, -1):
        print(f"Waiting: {i} seconds remaining...")
        time.sleep(1)

def main():
    print(f"Python version: {sys.version}")
    print(f"Requests version: {requests.__version__}")

    username = input("Enter your email: ")
    password = input("Enter your password: ")

    token = login(username, password)
    if not token:
        return

    user_info = get_user_info(token)
    if user_info:
        print(f"User info: {json.dumps(user_info, indent=2)}")

    while True:
        random_face = decode_random_face(token)
        if random_face:
            print(f"Random face generated: {json.dumps(random_face, indent=2)}")
            s3_key = random_face["s3_key"]

            wait_with_message(10, "Waiting for the server to generate the image...")

            path, id = s3_key.split('/', 1)[1].split('/', 1)
            image_data = get_image(token, path, id)
            if image_data:
                save_and_show_image(image_data, "random_face.jpg")
                
                wait_with_message(10, "Waiting before requesting predictions...")
                
                predictions = get_predictions(token, s3_key)
                if predictions:
                    save_predictions(predictions, "random_face_predictions.json")
                else:
                    print("Failed to get predictions for the random face")
                
                approval = input("Do you approve this image? (yes/no): ").lower()
                if approval == 'yes':
                    break
                else:
                    print("Generating a new random face...")
            else:
                print("Failed to retrieve the image. Trying again...")
        else:
            print("Failed to generate a random face. Please try running the script again.")
            return

    # Request transformation
    transformation = request_transformation(token, s3_key, "black", [-2, 0, 2])
    if transformation:
        print(f"Transformation result: {json.dumps(transformation, indent=2)}")

        wait_with_message(10, "Waiting for the server to generate transformed images...")

        # Get transformed images
        for i, image_path in enumerate(transformation["images"]):
            path, id = image_path.split('/', 1)[1].split('/', 1)
            image_data = get_image(token, path, id)
            if image_data:
                save_and_show_image(image_data, f"transformed_face_{i}.jpg")
            else:
                print(f"Failed to retrieve transformed image {i}")

            # Wait between processing each transformed image
            if i < len(transformation["images"]) - 1:  # Don't wait after the last image
                wait_with_message(5, "Waiting before processing the next transformed image...")

if __name__ == "__main__":
    main()