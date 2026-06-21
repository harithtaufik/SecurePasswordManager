# core/gdrive_utils.py
import os
import io
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import config

# If modifying these scopes, delete the file token.json.
# We use drive.file so the app only accesses files it created itself.
SCOPES = ['https://www.googleapis.com/auth/drive.file']

CREDENTIALS_DIR = os.path.join(config.BASE_DIR, "credentials")
TOKEN_FILE = os.path.join(CREDENTIALS_DIR, "token.json")
CREDENTIALS_FILE = os.path.join(CREDENTIALS_DIR, "credentials.json")


def authenticate_gdrive():
    """Handles Google Drive OAuth2 authentication."""
    creds = None
    # The file token.json stores the user's access and refresh tokens.
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError("credentials.json not found. Please download it from Google Cloud Console.")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)


def get_or_create_folder(service, folder_name="SecurePass Backups"):
    """Checks if the backup folder exists on Drive, creates it if not."""
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])

    if items:
        # Folder exists, return its ID
        return items[0]['id']

    # Folder does not exist, create it
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = service.files().create(body=folder_metadata, fields='id').execute()
    return folder.get('id')


def get_existing_backup_id(service, folder_id):
    """Checks if a backup already exists inside the specific Drive folder."""
    query = f"name='passwords.db' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    if items:
        return items[0]['id']
    return None


def backup_database():
    """Uploads passwords.db to the Google Drive folder."""
    service = authenticate_gdrive()

    # Get or create the 'SecurePass Backups' folder
    folder_id = get_or_create_folder(service, "SecurePass Backups")
    existing_file_id = get_existing_backup_id(service, folder_id)

    media = MediaFileUpload(config.DB_FILE, mimetype='application/octet-stream', resumable=True)

    if existing_file_id:
        # Update existing file
        file = service.files().update(fileId=existing_file_id, media_body=media).execute()
    else:
        # Create new file and place it inside the folder
        file_metadata = {
            'name': "passwords.db",
            'parents': [folder_id]
        }
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    return file.get('id')


def restore_database():
    """Downloads passwords.db from the Google Drive folder and replaces the local file."""
    service = authenticate_gdrive()

    # Get the folder ID to search inside it
    folder_id = get_or_create_folder(service, "SecurePass Backups")
    existing_file_id = get_existing_backup_id(service, folder_id)

    if not existing_file_id:
        raise FileNotFoundError("No backup found inside the 'SecurePass Backups' folder on Google Drive.")

    request = service.files().get_media(fileId=existing_file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()

    # Save to local file
    fh.seek(0)
    with open(config.DB_FILE, 'wb') as f:
        f.write(fh.read())

    return True