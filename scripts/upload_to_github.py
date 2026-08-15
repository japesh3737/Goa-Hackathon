"""
Upload all project files and folders directly to GitHub repository via GitHub REST API.
"""
import os
import sys
import base64
import json
import urllib.request
import urllib.error

REPO = "japesh3737/Goa-Hackathon"
BRANCH = "main"

# Directories to upload
INCLUDE_DIRS = ["app", "frontend", "tests", "scripts"]
INCLUDE_FILES = [
    "render.yaml",
    "Dockerfile",
    "requirements.txt",
    "README.md",
    "LICENSE",
    ".dockerignore",
    ".gitignore",
    ".env.example"
]

EXCLUDE_EXTENSIONS = [".pyc", ".faiss", ".pkl", ".parquet", ".bin", ".log"]
EXCLUDE_DIRS = ["__pycache__", "venv", ".venv", ".pytest_cache", ".git"]

def get_file_sha(file_path, token):
    url = f"https://api.github.com/repos/{REPO}/contents/{file_path}?ref={BRANCH}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "UploadScript"
    })
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("sha")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise

def upload_file(local_path, repo_path, token):
    with open(local_path, "rb") as f:
        content_bytes = f.read()
    
    content_b64 = base64.b64encode(content_bytes).decode("utf-8")
    sha = get_file_sha(repo_path, token)
    
    url = f"https://api.github.com/repos/{REPO}/contents/{repo_path}"
    payload = {
        "message": f"Upload {repo_path}",
        "content": content_b64,
        "branch": BRANCH
    }
    if sha:
        payload["sha"] = sha
        
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "UploadScript"
    }, method="PUT")
    
    with urllib.request.urlopen(req) as resp:
        return resp.status in (200, 201)

def collect_files(root_dir):
    files_to_upload = []
    
    # Root files
    for fname in INCLUDE_FILES:
        full_path = os.path.join(root_dir, fname)
        if os.path.isfile(full_path):
            files_to_upload.append((full_path, fname))
            
    # Directories
    for dname in INCLUDE_DIRS:
        dir_path = os.path.join(root_dir, dname)
        if not os.path.isdir(dir_path):
            continue
        for root, dirs, files in os.walk(dir_path):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for file in files:
                if any(file.endswith(ext) for ext in EXCLUDE_EXTENSIONS):
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, root_dir).replace("\\", "/")
                files_to_upload.append((full_path, rel_path))
                
    return files_to_upload

def main():
    token = os.environ.get("GITHUB_TOKEN") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not token:
        print("ERROR: GitHub token is required. Run: python upload_to_github.py <YOUR_GITHUB_TOKEN>")
        sys.exit(1)
        
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    files = collect_files(root_dir)
    print(f"Found {len(files)} files to upload to {REPO}...")
    
    success = 0
    for local_path, repo_path in files:
        try:
            print(f"Uploading {repo_path}...", end=" ", flush=True)
            upload_file(local_path, repo_path, token)
            print("DONE")
            success += 1
        except Exception as e:
            print(f"FAILED: {e}")
            
    print(f"\nCompleted! {success}/{len(files)} files uploaded successfully to https://github.com/{REPO}")

if __name__ == "__main__":
    main()
