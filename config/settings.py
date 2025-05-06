# Media files (Uploads)
MEDIA_URL = "/resumes/"
MEDIA_ROOT = os.path.join(BASE_DIR, "resumes")

# Storage settings
DEFAULT_FILE_STORAGE = "interviews.storage.CandidateResumeStorage"
