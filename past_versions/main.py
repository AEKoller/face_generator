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

def save_predictions(predictions, filename, folder):
    full_path = os.path.join(folder, filename)
    if not full_path.lower().endswith('.json'):
        full_path += '.json'
    with open(full_path, 'w') as f:
        json.dump(predictions, f, indent=2)
    print(f"Predictions saved to {full_path}")

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

def request_transformation(token, s3_key, attribute, betas, control_attributes=None):
    headers = {"Authorization": f"Bearer {token}"}
    
    # Remove the last part of the s3_key (likely the image ID)
    path = '/'.join(s3_key.split('/')[:-1])
    
    data = {
        "attribute": attribute,
        "betas": betas,
        "control_attributes": control_attributes,
        "interpretable_betas": True
    }
    try:
        response = requests.post(f"{BASE_URL}/request_transformation/{path}", json=data, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to request transformation: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while requesting transformation: {e}")
        return None

def multi_transform(token, initial_s3_key, transformations, original_predictions, generation_folder):
    """
    Perform multiple transformations sequentially, updating predictions and saving results after each transformation.
    
    :param token: Authentication token
    :param initial_s3_key: S3 key of the original image
    :param transformations: List of dictionaries, each containing 'attribute' and 'beta'
    :param original_predictions: Original predictions JSON
    :param generation_folder: Folder to save the results
    :return: None
    """
    current_s3_key = initial_s3_key
    current_predictions = original_predictions.copy()
    
    for transform in transformations:
        attribute = transform['attribute']
        beta = transform['beta']
        
        print(f"Applying transformation: {attribute} with beta {beta}")
        print(f"Using current S3 key: {current_s3_key}")
        
        result = request_transformation(token, current_s3_key, attribute, [beta])
        if result:
            print(f"Transformation request successful for {attribute}")
            
            # Update the predictions for this attribute
            if attribute in current_predictions:
                current_predictions[attribute] = beta
            
            # Get the new image
            new_image_path = result["images"][0]
            path, id = new_image_path.split('/', 1)[1].split('/', 1)
            
            max_retries = 5
            retry_delay = 30  # seconds
            
            for attempt in range(max_retries):
                wait_with_message(retry_delay, f"Waiting for the server to process the image (Attempt {attempt + 1}/{max_retries})...")
                
                image_data = get_image(token, path, id)
                
                if image_data:
                    # Save the new image with attribute and beta in the filename
                    image_filename = f"transformed_face_{attribute}_beta_{beta}"
                    save_and_show_image(image_data, image_filename, generation_folder)

                    
                    # Save updated predictions
                    predictions_filename = f"predictions_{attribute}_beta_{beta}"
                    save_predictions(current_predictions, predictions_filename, generation_folder)


                    
                    # Update the current_s3_key for the next transformation
                    current_s3_key = new_image_path
                    print(f"Successfully retrieved and saved transformed image for {attribute}")
                    print(f"New S3 key: {current_s3_key}")
                    break
                else:
                    print(f"Failed to retrieve transformed image for {attribute} (Attempt {attempt + 1}/{max_retries})")
                    
                    if attempt == max_retries - 1:
                        print(f"Max retries reached. Skipping to next transformation.")
                        break
            
            if not image_data:
                print(f"Failed to retrieve transformed image for {attribute} after all attempts. Skipping to next transformation.")
        else:
            print(f"Failed to request transformation for attribute: {attribute}")
        
        print(f"Completed processing for {attribute}. Moving to next transformation if available.")
        
        # Wait before moving to the next transformation
        wait_with_message(60, "Waiting before moving to the next transformation...")
    
    print("All transformations completed.")

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

    generation_folder = create_timestamped_folder()
    print(f"Created folder for this generation: {generation_folder}")

    while True:
        random_face = decode_random_face(token)
        if random_face:
            print(f"Random face generated: {json.dumps(random_face, indent=2)}")
            s3_key = random_face["s3_key"]

            wait_with_message(30, "Waiting for the server to generate the image...")

            path, id = s3_key.split('/', 1)[1].split('/', 1)
            image_data = get_image(token, path, id)
            if image_data:
                save_and_show_image(image_data, "original_face", generation_folder)
                
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

    # Get predictions for the approved image
    wait_with_message(30, "Waiting before requesting predictions...")
    predictions = get_predictions(token, s3_key)
    if predictions:
        save_predictions(predictions, "original_face_predictions", generation_folder)
    else:
        print("Failed to get predictions for the random face")
        return  # Exit if we couldn't get predictions

    # Define transformations
    transformations = [
        {'attribute': 'black', 'beta': 2},
        {'attribute': 'age', 'beta': 1},
        {'attribute': 'gender', 'beta': 1}
    ]

    # Perform multiple transformations
    multi_transform(token, s3_key, transformations, predictions, generation_folder)

    print(f"All transformations completed. Results saved in: {generation_folder}")

if __name__ == "__main__":
    main()