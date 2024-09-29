import requests
import json
import sys
import time
import os
from datetime import datetime
from PIL import Image


BASE_URL = "https://gateway.extempo.rocks"


def create_timestamped_folder(base_dir="generations"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"{base_dir}_{timestamp}"
    os.makedirs(folder_name, exist_ok=True)
    return folder_name


def get_timestamped_filename(base_name, extension):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_{timestamp}.{extension}"


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


def wait_with_message(seconds, message):
    print(message)
    for i in range(seconds, 0, -1):
        print(f"Waiting... {i} seconds remaining", end='\r')
        time.sleep(1)
    print("\nDone waiting.")


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


def save_and_show_image(image_data, filename, folder):
    # Create the full path for the file
    full_path = os.path.join(folder, filename)
    
    # Ensure the filename has a .jpg extension
    if not full_path.lower().endswith('.jpg'):
        full_path += '.jpg'
    
    # Save the image
    with open(full_path, "wb") as f:
        f.write(image_data)
    print(f"Image saved as '{full_path}'")
    
    # Show the image
    Image.open(full_path).show()


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


def save_predictions(predictions, filename, folder):
    full_path = os.path.join(folder, filename)
    if not full_path.lower().endswith('.json'):
        full_path += '.json'
    with open(full_path, 'w') as f:
        json.dump(predictions, f, indent=2)
    print(f"Predictions saved to {full_path}")


def request_transformation(token, s3_key, attribute, betas, control_attributes=None):
    headers = {"Authorization": f"Bearer {token}"}
    path, id = s3_key.split('/', 1)[1].split('/', 1)
    data = {
        "attribute": attribute,
        "betas": betas,
        "control_attributes": control_attributes,
        "interpretable_betas": True
    }
    try:
        response = requests.post(f"{BASE_URL}/request_transformation/{path}/{id}", json=data, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to request transformation: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while requesting transformation: {e}")
        return None

def save_characteristic_info(attribute, beta, filename, folder, s3_key, photo_filename):
    """
    Save the characteristic (attribute), beta value, s3_key, and photo filename to a text file.
    """
    full_path = os.path.join(folder, filename)
    with open(full_path, 'w') as f:
        f.write(f"Characteristic: {attribute}\n")
        f.write(f"Beta: {beta}\n")
        f.write(f"S3 Key: {s3_key}\n")
        f.write(f"Photo Filename: {photo_filename}")
    print(f"Characteristic info saved to {full_path}")


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

    # Create a timestamped folder for this run
    output_folder = create_timestamped_folder()
    print(f"Output will be saved in: {output_folder}")

    while True:
        random_face = decode_random_face(token)
        if random_face:
            print(f"Random face generated: {json.dumps(random_face, indent=2)}")
            s3_key = random_face["s3_key"]

            wait_with_message(10, "Waiting for the server to generate the image...")

            path, id = s3_key.split('/', 1)[1].split('/', 1)
            image_data = get_image(token, path, id)
            if image_data:
                image_filename = get_timestamped_filename("random_face", "jpg")
                save_and_show_image(image_data, image_filename, output_folder)
                
                # Prompt for approval immediately after showing the image
                approval = input("Do you approve this image? (yes/no): ").lower()
                if approval == 'yes':
                    # If approved, proceed with predictions and transformations
                    wait_with_message(10, "Waiting before requesting predictions...")
                    
                    predictions = get_predictions(token, s3_key)
                    if predictions:
                        predictions_filename = image_filename.replace(".jpg", "_predictions.json")
                        save_predictions(predictions, predictions_filename, output_folder)
                    else:
                        print("Failed to get predictions for the random face")
                    
                    break  # Exit the loop if the image is approved
                else:
                    print("Image not approved. Generating a new random face...")
            else:
                print("Failed to retrieve the image. Trying again...")
        else:
            print("Failed to generate a random face. Please try running the script again.")
            return

    # Proceed with transformations only if an image was approved
    attribute = "black"
    betas = [-2, 0, 2]
    transformation = request_transformation(token, s3_key, attribute, betas)
    if transformation:
        print(f"Transformation result: {json.dumps(transformation, indent=2)}")

        wait_with_message(10, "Waiting for the server to generate transformed images...")

        # Get transformed images
        for i, image_path in enumerate(transformation["images"]):
            path, id = image_path.split('/', 1)[1].split('/', 1)
            image_data = get_image(token, path, id)
            if image_data:
                # Generate timestamped filename for the image
                image_filename = get_timestamped_filename(f"transformed_face_{i}", "jpg")
                save_and_show_image(image_data, image_filename, output_folder)
                
                # Save characteristic info with the same timestamp
                info_filename = image_filename.replace(".jpg", "_info.txt")
                save_characteristic_info(attribute, betas[i], info_filename, output_folder, image_path, image_filename)
            else:
                print(f"Failed to retrieve transformed image {i}")

            # Wait between processing each transformed image
            if i < len(transformation["images"]) - 1:  # Don't wait after the last image
                wait_with_message(5, "Waiting before processing the next transformed image...")

if __name__ == "__main__":
    main()