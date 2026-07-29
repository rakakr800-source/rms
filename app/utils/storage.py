import os

def upload_to_cloudinary(file, folder="menu"):
    """
    Uploads a file directly to Cloudinary and returns (secure_url, public_id).
    """
    try:
        import cloudinary
        import cloudinary.uploader
        
        cloudinary.config(
            cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
            api_key=os.environ.get("CLOUDINARY_API_KEY"),
            api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
            secure=True
        )
        
        upload_result = cloudinary.uploader.upload(
            file,
            folder=f"rms/{folder}"
        )
        return upload_result.get("secure_url"), upload_result.get("public_id")
    except Exception as e:
        print(f"Cloudinary upload failed: {e}")
        return None, None

def delete_from_cloudinary(public_id):
    """
    Deletes an image from Cloudinary using its public_id.
    """
    if not public_id:
        return
    try:
        import cloudinary
        import cloudinary.uploader
        
        cloudinary.config(
            cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
            api_key=os.environ.get("CLOUDINARY_API_KEY"),
            api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
            secure=True
        )
        
        cloudinary.uploader.destroy(public_id)
    except Exception as e:
        print(f"Cloudinary delete failed for public_id {public_id}: {e}")