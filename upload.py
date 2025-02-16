import os
import pickle
import cv2
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

# scope that allows creation and modification of files
SCOPES = ['https://www.googleapis.com/auth/drive.file']
API_SERVER = "http://localhost:3000"  # node.js api server base

# authenticate Google Drive and handle token refresh
def authenticate_google_drive():
    creds = None
    # check if token.pickle file exists and load credentials
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # if credentials don't exist or are expired, re-authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())  # Try refreshing the token
                print("Token refreshed successfully.")
            except RefreshError as e:
                print(f"Token refresh failed: {e}. Re-authenticating.")
                creds = None
        else:
            creds = None

    # if re-authentication fails, start the OAuth flow
    if not creds or not creds.valid:
        creds = authenticate_user()

    # save refreshed credentials for the next session
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)

    # build the service object for Google Drive
    service = build('drive', 'v3', credentials=creds)
    return service


# authenticate user using OAuth2 flow if needed
def authenticate_user():
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', SCOPES)
    creds = flow.run_local_server(port=8080)  # Initiates OAuth flow
    return creds

# opens webcam for preview and captures photos
def cap_photo():
    directory = os.path.join(os.getcwd(), 'static', 'photos')  # directory for photos
    if not os.path.exists(directory):
        os.makedirs(directory)  # create the directory if it doesn't exist

    filename = 'newImage.jpg' # all files have the same file name that will be overwritten
    file_path = os.path.join(directory, filename)

    # open  webcam and capture a photo
    cap = cv2.VideoCapture(1)  # 0 if no other devices are connected to the same network
    if not cap.isOpened():
        print("Error: Could not open video capture device.")
        return None

    print("Starting webcam feed for 1 second.")

    # show the live feed for 1 second
    start_time = cv2.getTickCount()
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        cv2.imshow('Live Feed', frame)

        # check if 1 second has passed
        elapsed_time = (cv2.getTickCount() - start_time) / cv2.getTickFrequency()
        if elapsed_time > 1.0:
            print("1 second elapsed. Capturing photo.")
            cv2.imwrite(file_path, frame)  # save the photo
            break

    cap.release()
    cv2.destroyAllWindows()  # close the OpenCV windows
    return file_path  # return the file path


# upload a photo to google drive
def upload_file(service, file_path, mime_type):
    file_metadata = {'name': os.path.basename(file_path)}
    media = MediaFileUpload(file_path, mimetype=mime_type)
    request = service.files().create(
        media_body=media, body=file_metadata, fields='id')

    file = request.execute()
    photoID = file['id']
    print(f"File uploaded successfully! File ID: {photoID}")

    return photoID


# make file on google drive publicly accessible
def make_file_public(service, photoID):
    permission = {
        'type': 'anyone',
        'role': 'reader'
    }
    service.permissions().create(
        fileId=photoID,
        body=permission,
        fields='id',
    ).execute()
    print(f"File ID {photoID} is now public.")


# save photo ID to the database via node.js api
def save_photo_to_user(photoID, user):
    try:
        url = f"{API_SERVER}/assignPhotoToUser/{photoID}/{user}"
        response = requests.post(url)
        if response.status_code == 200:
            print(f"Photo ID {photoID} assigned to user {user} successfully via Node.js.")
        else:
            print(f"Failed to assign photo ID {photoID} to user {user}. Server responded with: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error assigning photo ID to user: {e}")


def main(user='CURRENT-SESSION'):
    try:
        # authenticate Google Drive service
        service = authenticate_google_drive()
        mime_type = 'image/jpeg'
        count = 0
        
        while count < 4:
            file_path = cap_photo()  # capture photo and get its file path

            if file_path:
                photoID = upload_file(service, file_path, mime_type) # upload each photo to Google Drive
                make_file_public(service, photoID)
                save_photo_to_user(photoID, user) # assign the uploaded photo ID to the user in the database
                print(f"Photo {count+1} captured, uploaded, and saved with photo ID: {photoID}")
                count += 1
            else:
                print(f"Error: Photo {count+1} capture failed.")

        return "Successfully uploaded all photos."

    except Exception as e:
        print(f"Error in main: {e}")
        return "An error occurred during photo capture and upload."


if __name__ == '__main__':
    main()
