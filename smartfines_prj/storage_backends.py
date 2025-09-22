from storages.backends.s3boto3 import S3Boto3Storage

class MediaStorage(S3Boto3Storage):
    location = 'media'
    file_overwrite = False
    querystring_auth = False
    custom_domain = 'media.smartfines.net'
