import os
from datetime import datetime

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class CandidateResumeStorage(FileSystemStorage):
    """
    Custom storage class for candidate resumes.
    This class handles file storage operations and can be easily extended
    to support different storage backends (e.g., AWS S3) in the future.
    """

    def __init__(self):
        # Define the base directory for resume storage
        self.base_location = settings.MEDIA_ROOT
        super().__init__(location=self.base_location)

    def get_available_name(self, name, max_length=None):
        """
        Generate a unique filename for the uploaded resume.
        Format: YYYY/MM/DD/candidate_id_original_filename
        """
        # Extract the original filename and extension
        filename, ext = os.path.splitext(name)

        # Get the current date for directory structure
        now = datetime.now()
        date_path = now.strftime("%Y/%m/%d")

        # Create the directory if it doesn't exist
        full_dir = os.path.join(self.base_location, date_path)
        os.makedirs(full_dir, exist_ok=True)

        # Generate the new filename with date-based path
        new_name = f"{date_path}/{filename}{ext}"

        # If file exists, append a number to make it unique
        if self.exists(new_name):
            counter = 1
            while self.exists(f"{date_path}/{filename}_{counter}{ext}"):
                counter += 1
            new_name = f"{date_path}/{filename}_{counter}{ext}"

        return new_name

    def url(self, name):
        """
        Return the URL for the file.
        This can be overridden to support different storage backends.
        """
        print("=== Storage URL Debug ===")
        print(f"Input name: {name}")
        print(f"MEDIA_URL from settings: {settings.MEDIA_URL}")

        if not name:
            print("No name provided, returning empty string")
            return ""

        # Remove any leading slashes to avoid double slashes
        name = name.lstrip("/")
        print(f"Name after lstrip: {name}")

        # Return the URL without the MEDIA_URL prefix since it's already included in the path
        final_url = f"/{name}"
        print(f"Final URL: {final_url}")
        print("=====================")
        return final_url

    def delete(self, name):
        """
        Delete the file.
        This can be overridden to handle different storage backends.
        """
        return super().delete(name)


class CandidateProfilePictureStorage(FileSystemStorage):
    """
    Custom storage class for candidate profile pictures.
    This class handles file storage operations and can be easily extended
    to support different storage backends (e.g., AWS S3) in the future.
    """

    def __init__(self):
        # Define the base location for profile picture storage
        self.base_location = os.path.join(settings.MEDIA_ROOT, "profile_pictures")
        super().__init__(location=self.base_location)

    def get_available_name(self, name, max_length=None):
        """
        Generate a unique filename for the uploaded profile picture.
        Format: YYYY/MM/DD/candidate_id_original_filename
        """
        # Extract the original filename and extension
        filename, ext = os.path.splitext(name)

        # Get the current date for directory structure
        now = datetime.now()
        date_path = now.strftime("%Y/%m/%d")

        # Create the directory if it doesn't exist
        full_dir = os.path.join(self.base_location, date_path)
        os.makedirs(full_dir, exist_ok=True)

        # Generate the new filename with date-based path
        new_name = f"{date_path}/{filename}{ext}"

        # If file exists, append a number to make it unique
        if self.exists(new_name):
            counter = 1
            while self.exists(f"{date_path}/{filename}_{counter}{ext}"):
                counter += 1
            new_name = f"{date_path}/{filename}_{counter}{ext}"

        return new_name
