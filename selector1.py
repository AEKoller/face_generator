import requests
import json
import sys
import time
import os
from datetime import datetime
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


def create_timestamped_folder(base_dir="generations"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"{base_dir}_{timestamp}"
    os.makedirs(folder_name, exist_ok=True)
    return folder_name


def get_timestamped_filename(base_name, extension):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_{timestamp}.{extension}"


def save_and_show_image(image_data, filename, folder):
    full_path = os.path.join(folder, filename)
    if not full_path.lower().endswith('.jpg'):
        full_path += '.jpg'
    with open(full_path, "wb") as f:
        f.write(image_data)
    print(f"Image saved as '{full_path}'")
    Image.open(full_path).show()


def save_characteristic_info(attribute, beta, filename, folder, s3_key, photo_filename):
    full_path = os.path.join(folder, filename)
    with open(full_path, 'w') as f:
        f.write(f"Characteristic: {attribute}\n")
        f.write(f"Beta: {beta}\n")
        f.write(f"S3 Key: {s3_key}\n")
        f.write(f"Photo Filename: {photo_filename}")
    print(f"Characteristic info saved to {full_path}")


def generate_and_approve_face(token, output_folder):
    while True:
        random_face = decode_random_face(token)
        if not random_face:
            print("Failed to generate a random face. Please try again.")
            return None

        print(f"Random face generated: {json.dumps(random_face, indent=2)}")
        s3_key = random_face["s3_key"]

        wait_with_message(10, "Waiting for the server to generate the image...")

        path, id = s3_key.split('/', 1)[1].split('/', 1)
        image_data = get_image(token, path, id)
        if not image_data:
            print("Failed to retrieve the image. Trying again...")
            continue

        image_filename = get_timestamped_filename("initial_face", "jpg")
        save_and_show_image(image_data, image_filename, output_folder)

        # Get and save predictions for the initial face
        predictions = get_predictions(token, s3_key)
        if predictions:
            predictions_filename = image_filename.replace(".jpg", "_predictions.json")
            save_predictions(predictions, predictions_filename, output_folder)
        else:
            print("Failed to get predictions for the initial face")

        approval = input("Do you approve this random face? (yes/no): ").lower()
        if approval == 'yes':
            return s3_key
        else:
            print("Generating a new random face...")


def request_transformation(token, s3_key, attribute, beta, control_attributes=None):
    headers = {"Authorization": f"Bearer {token}"}
    
    # Remove only the trailing identifier if present, but keep the image name
    s3_key_parts = s3_key.split('~~')
    if len(s3_key_parts) > 2:
        s3_key = '~~'.join(s3_key_parts[:2])  # Keep everything up to and including the image name
    
    path, id = s3_key.split('/', 1)[1].split('/', 1)
    data = {
        "attribute": attribute,
        "betas": [float(beta)],
        "control_attributes": control_attributes,
        "interpretable_betas": True
    }
    
    # Print the s3_key being used in the JSON payload
    print(f"Using s3_key in transformation request: {s3_key}")
    
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

    output_folder = create_timestamped_folder()
    print(f"Output will be saved in: {output_folder}")

    while True:
        # Generate and approve initial random face
        initial_s3_key = generate_and_approve_face(token, output_folder)
        if not initial_s3_key:
            return

        current_s3_key = initial_s3_key

        while True:
        # Generate and approve initial random face
            initial_s3_key = generate_and_approve_face(token, output_folder)
            if not initial_s3_key:
                return

            current_s3_key = initial_s3_key

            while True:
                attribute = input("Enter the characteristic to transform (or 'quit' to exit): ")
                if attribute.lower() == 'quit':
                    return

                beta = input("Enter the beta value for the transformation: ")
                try:
                    beta = float(beta)
                except ValueError:
                    print("Invalid beta value. Please enter a number.")
                    continue

                transformation = request_transformation(token, current_s3_key, attribute, beta)
                if transformation:
                    print(f"Transformation result: {json.dumps(transformation, indent=2)}")

                    wait_with_message(10, "Waiting for the server to generate transformed image...")

                    # Get transformed image
                    transformed_s3_key = transformation["images"][0]
                    path, id = transformed_s3_key.split('/', 1)[1].split('/', 1)
                    image_data = get_image(token, path, id)
                    if image_data:
                        image_filename = get_timestamped_filename(f"transformed_face_{attribute}", "jpg")
                        save_and_show_image(image_data, image_filename, output_folder)
                        
                        info_filename = image_filename.replace(".jpg", "_info.txt")
                        save_characteristic_info(attribute, beta, info_filename, output_folder, transformed_s3_key, image_filename)

                        # Update the current_s3_key for the next transformation
                        # Keep everything up to and including the image name, remove trailing identifier
                        current_s3_key = '~~'.join(transformed_s3_key.split('~~')[:2])
                    else:
                        print("Failed to retrieve transformed image")

                else:
                    print("Transformation failed. Please try again.")

            while True:
                choice = input("Would you like to: (1) Perform another transformation, (2) Generate a new random face, or (3) Quit? ").strip()
                if choice == '1':
                    break  # Continue with the current face
                elif choice == '2':
                    break  # Generate a new face
                elif choice == '3':
                    print("Thank you for using the Interactive Face Transformer!")
                    return
                else:
                    print("Invalid choice. Please enter 1, 2, or 3.")

            if choice == '2':
                break  # Break the inner loop to generate a new face

    print("Transformation process completed. Thank you for using the Interactive Face Transformer!")

if __name__ == "__main__":
    main()