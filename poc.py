# File: backend.py
# Author: Jonathan Lee
# Last Modified: 7/6/2022 
# Description: This is a CLI program that will pick up the photo path provided by the user's input and upload it to Google Drive.

from __future__ import print_function

import time
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive']

# This is hardcoded according to the folder ID in my drives.
PHOTOBOOTH_FOLDER_ID = "19sn_fDILV1TsCwqARZJEdPANpseMWuyV"
batch_number = 1

def authentication():
    """Handles the Authentication of the user.

    Returns:
        creds: Oauth2 credentials.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds


def createDriveObject(creds):
    """Creates drive object to be used for uploading.

    Args:
        creds (credentials): Oauth2 credentials.

    Returns:
        service: Google Drive handler object.
    """
    service = build('drive', 'v3', credentials=creds)
    return service


def createBatchFolder(service):
    """Creates the batch folder in the root photobooth folder.

    Args:
        service (service): Google Drive handler object.

    Returns:
        String: ID of the folder.
    """
    global batch_number
    folder_metadata = {
        'name': batch_number,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [PHOTOBOOTH_FOLDER_ID]
    }
    folder = service.files().create(body=folder_metadata, fields='id').execute()
    batch_number += 1
    return folder['id']


def getPhotosFromDir(path):
    """Gets all the photos in the directory.

    Args:
        path (string): Path to the directory.

    Returns:
        List: List of photos in the directory.
    """
    photos = []
    for photo in os.listdir(path):
        photos.append(os.path.join(path, photo))
    return photos


def uploadFiles(service, path, inner_folder_id):
    """Uploads the file to the Google Drive.

    Args:
        service (service): Google Drive handler object.
        path (string): Path to the file.
        inner_folder_id (string): ID of the folder.
    """
    for photo in getPhotosFromDir(path):
        file_metadata = {
            'name': photo.split('/')[-1],
            'parents': [inner_folder_id]
        }
        media = MediaFileUpload(photo, 
                                mimetype='image/jpeg',
                                resumable=True)
        file = service.files().create(body=file_metadata,
                                    media_body=media, 
                                    fields='id').execute()
        print(f"[*] File #{file['id']} uploaded successfully!")


def printIntro():
    """Prints the introduction to the program.
    """
    print("Welcome to the Google Drive Uploader!")
    print("[*] Authenticating...")


def handleInput():
    """Handles the path given by the user.

    Returns:
        String: Path to the photo. 
    """
    print("Please enter the path to the folder of photos you would like to upload: ")
    path = input()
    return path


def isLegitDir(path):
    """Checks if the path provided is link to a legitimate directory.

    Args:
        path (string): Path to the directory.

    Returns:
        Boolean: True if the directory exists, False otherwise.
    """
    return os.path.isdir(path)


def printUploadingMessage(path):
    """Prints the uploading message.

    Args:
        path (string): Path to the file.
    """
    global batch_number
    print(f"[*] Uploading {path.split('/')[-1]} as batch {batch_number}")


def printDirNotFound(path):
    """Print message that directory is not found.

    Args:
        path (string): Path to the directory.
    """
    print(f"[!] Directory not found: {path}")
    print("[!] Try again!!")


def main():
    """Main logic of the code that will be run.
    """
    printIntro()
    time.sleep(2)
    try:
        creds = authentication()
        service = createDriveObject(creds)
        page_token = None
        response = service.files().list(q=f"mimeType='application/vnd.google-apps.folder' and trashed=false and name='{1}'",
                                            spaces='drive',
                                            pageToken=page_token).execute()
        parentFolder = response.get('files', [])[0].get('id')
        print(f"[*] Found parent folder: {parentFolder}")
        service.permissions().create(
            fileId=f'{parentFolder}',
            body={
                'role': 'reader',
                'type': 'anyone',
            }).execute()
        while True:
            response = service.files().list(q=f"'{parentFolder}' in parents",
                                                spaces='drive',
                                                fields='nextPageToken, files(id, name, webViewLink)',
                                                pageToken=page_token).execute()
            for file in response.get('files', []):
                # Process change
                print('Found file: %s (%s) (link: %s)' % (file.get('name'), file.get('id'), file.get('webViewLink')))

            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break 
            # https://drive.google.com/uc?id=<ID>

    except HttpError as error:
        # Handles error from drive API.
        print(f'An error occurred: {error}')


if __name__ == "__main__":
    main()
