# File: sender.py
# Author: Jonathan Lee
# Last Modified: 7/6/2022 
# Description: This is a CLI program that will ask for the user's phone number and send them the photos stored on Google Drive.

from __future__ import print_function

import time
import os.path
import json

from twilio.rest import Client

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


def loadTwiloCredentials():
    """Loads the Twilio credentials from the twilo_creds.json file.
    """
    with open('twilo_creds.json', 'r') as f:
        credentials = json.load(f)
    return credentials


def printIntro():
    """Prints the introduction to the program.
    """
    print("Welcome to the Google Drive Sender!")
    print("[*] Authenticating...")


def sendPhotos(client, urls, user_hp):
    """Sends the photos to the user.

    Args:
        client (Twilio Client): Authenticated Twilio API Account 
        urls (list): List of photo
        user_hp (string): Handphone number of user
    """
    for url in urls:
        message = client.messages.create(
            from_='whatsapp:+14155238886',
            media_url=url,
            body='Thank you for coming!',
            to='whatsapp:' + user_hp
        )
    print(f"[*] Message with #{message.sid} is successfully sent to {user_hp}")


def handleInput():
    """Handles the phone number and batch given by the user.

    Returns:
        String: Hand phone number and batch number to be read. 
    """
    print("Please enter your phone number: ")
    hp_number = "+65" + input()
    print("Please enter the batch number you would like to claim: ")
    batch_number = input()
    return hp_number, batch_number


def printSendingMessage(hp_number):
    """Prints the sending photo message.

    Args:
        hp_number (string): Phone number of user.
    """
    print(f"[*] Sending photos to your number {hp_number}")


def getParentFolder(service, batch_number):
    """Gets the parent folder of the batch number.

    Args:
        service (service): Google Drive handler object.
        batch_number (string): Batch number of the photos.

    Returns:
        String: ID of the parent folder.
    """
    page_token = None
    # Get all folders not in thrash bin that is named after our batch number.
    response = service.files().list(q=f"mimeType='application/vnd.google-apps.folder' and trashed=false and name='{batch_number}'",
                                            spaces='drive',
                                            pageToken=page_token).execute()
    # Get ID of the only response which is the parent folder
    parentFolder = response.get('files', [])[0].get('id')
    return parentFolder


def changeToGlobalReadPermissions(service, parent_id):
    """Changes the permissions of the photos to be global read.

    Args:
        service (service): Google Drive handler object.
        parent_id (string): ID of the parent folder.
    """
    service.permissions().create(
            fileId=f'{parent_id}',
            body={
                'role': 'reader',
                'type': 'anyone',
            }).execute()


def getURLFromBatchNumber(service, parent_id):
    """Gets the URL of the photos from the batch number.

    Args:
        service (service): Google Drive handler object.
        parent_id (string): ID of parent folder.

    Returns:
        List: List of URLs of the photos.
    """
    page_token = None
    urls = []
    while True:
        response = service.files().list(q=f"'{parent_id}' in parents",
                                            spaces='drive',
                                            fields='nextPageToken, files(id)',
                                            pageToken=page_token).execute()
        # Traverse through all the files in the root folder.
        for file in response.get('files', []):
            urls.append(f"https://drive.google.com/uc?id={file.get('id')}&export=download")
        page_token = response.get('nextPageToken', None)
        # End of all files, quit loop.
        if page_token is None:
            break 
    return urls


def main():
    """Main logic of the code that will be run.
    """
    printIntro()
    # Get the credentials of the Twilio account.
    twilo_creds = loadTwiloCredentials()
    client = Client(twilo_creds["account_sid"], twilo_creds["auth_token"])
    time.sleep(2)
    try:
        creds = authentication()
        service = createDriveObject(creds)
        while True:
            hp_number, batch_number = handleInput()
            printSendingMessage(hp_number)
            parent_id = getParentFolder(service, batch_number)
            changeToGlobalReadPermissions(service, parent_id)
            urls = getURLFromBatchNumber(service, parent_id)
            sendPhotos(client, urls, hp_number)
    except HttpError as error:
        # Handles error from drive API.
        print(f'An error occurred: {error}')


if __name__ == "__main__":
    main()


