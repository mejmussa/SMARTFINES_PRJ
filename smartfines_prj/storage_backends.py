
from storages.backends.s3boto3 import S3Boto3Storage

class StaticStorage(S3Boto3Storage):
    location = 'static'  # All static files will be stored in the 'static/' folder

class MediaStorage(S3Boto3Storage):
    location = 'media'  # All media files will be stored in the 'media/' folder
