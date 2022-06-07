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

# This is hardcoded according to the folder ID in my drive.
PHOTOBOOTH_FOLDER_ID = "1Q9AW-f9C_WJGwhdQt3OHpcyMVB964KvY"
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


def uploadFile(service, path, inner_folder_id):
    """Uploads the file to the Google Drive.

    Args:
        service (service): Google Drive handler object.
        path (string): Path to the file.
        inner_folder_id (string): ID of the folder.
    """
    file_metadata = {
        'name': path.split('/')[-1],
        'parents': [inner_folder_id]
    }
    media = MediaFileUpload(path, 
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
    print("Please enter the path to the photo you would like to upload: ")
    path = input()
    return path


def isLegitFile(path):
    """Checks if the path provided is link to a legitimate file.

    Args:
        path (string): Path to the file.

    Returns:
        Boolean: True if the file exists, False otherwise.
    """
    return os.path.isfile(path)


def printUploadingMessage(path):
    """Prints the uploading message.

    Args:
        path (string): Path to the file.
    """
    global batch_number
    print(f"[*] Uploading {path.split('/')[-1]} as batch {batch_number}")


def printFileNotFound(path):
    """Print message that file is not found.

    Args:
        path (string): Path to the file.
    """
    print(f"[!] File not found: {path}")
    print("[!] Try again!!")


def main():
    """Main logic of the code that will be run.
    """
    printIntro()
    time.sleep(2)
    try:
        creds = authentication()
        service = createDriveObject(creds)
        while True:
            path = handleInput()
            # If not a legitimate file, re-run loop
            if not isLegitFile(path):
                printFileNotFound(path)
                continue
            printUploadingMessage(path)
            inner_folder_id = createBatchFolder(service)
            uploadFile(service, path, inner_folder_id)
    except HttpError as error:
        # Handles error from drive API.
        print(f'An error occurred: {error}')


if __name__ == "__main__":
    main()
