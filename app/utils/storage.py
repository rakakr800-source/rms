import os
from werkzeug.utils import secure_filename
from flask import current_app

def upload_to_persistent_storage(file, prefix="menu"):
    """
    Uploads a file to Cloudinary if CLOUDINARY_URL or CLOUDINARY_CLOUD_NAME is configured.
    Otherwise, falls back to local storage inside the Flask uploads directory.
    """
    # Check if Cloudinary is configured
    cloudinary_url = os.environ.get("CLOUDINARY_URL")
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME")
    
    if cloudinary_url or cloud_name:
        try:
            import cloudinary
            import cloudinary.uploader
            
            # Configure Cloudinary if we have individual config variables
            if not cloudinary_url and cloud_name:
                cloudinary.config(
                    cloud_name=cloud_name,
                    api_key=os.environ.get("CLOUDINARY_API_KEY"),
                    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
                    secure=True
                )
                
            # Perform upload
            upload_result = cloudinary.uploader.upload(
                file,
                folder=f"rms/{prefix}",
                resource_type="image"
            )
            # Return secure URL
            return upload_result.get("secure_url")
        except Exception as e:
            print(f"Cloudinary upload failed: {e}. Falling back to local storage.")
            # Fall back to local filesystem storage if upload failed
            
    # Local fallback
    filename = secure_filename(f"{prefix}_{os.urandom(4).hex()}_{file.filename}")
    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'products')
    os.makedirs(upload_path, exist_ok=True)
    file_path = os.path.join(upload_path, filename)
    
    # Seek to start of file if it was read by third party
    file.seek(0)
    file.save(file_path)
    
    return f"uploads/products/{filename}"