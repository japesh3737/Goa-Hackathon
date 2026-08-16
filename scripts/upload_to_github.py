import os
import sys
import base64
import json
import urllib.request
import urllib.error
import hashlib

REPO = "japesh3737/Goa-Hackathon"
BRANCH = "main"

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

def get_file_info(file_path, token):
    url = f"https://api.github.com/repos/{REPO}/contents/{file_path}?ref={BRANCH}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "UploadScript"
    })
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("sha"), data.get("content", "").replace("\n", "")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, None
        return None, None

def upload_file(local_path, repo_path, token):
    with open(local_path, "rb") as f:
        content_bytes = f.read()
    
    content_b64 = base64.b64encode(content_bytes).decode("utf-8")
    sha, remote_b64 = get_file_info(repo_path, token)
    
    # Skip if identical
    if sha and remote_b64 == content_b64:
        return "UP-TO-DATE"
    
    url = f"https://api.github.com/repos/{REPO}/contents/{repo_path}"
    payload = {
        "message": f"Update {repo_path}",
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
    
    try:
        with urllib.request.urlopen(req) as resp:
            return "UPLOADED" if resp.status in (200, 201) else "FAILED"
    except urllib.error.HTTPError as e:
        # If sha conflict, re-fetch sha and retry once
        if e.code in (409, 422, 400):
            new_sha, _ = get_file_info(repo_path, token)
            if new_sha:
                payload["sha"] = new_sha
                retry_req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json",
                    "Content-Type": "application/json",
                    "User-Agent": "UploadScript"
                }, method="PUT")
                with urllib.request.urlopen(retry_req) as resp2:
                    return "UPLOADED" if resp2.status in (200, 201) else "FAILED"
        raise

def collect_files(root_dir):
    files_to_upload = []
    for fname in INCLUDE_FILES:
        full_path = os.path.join(root_dir, fname)
        if os.path.isfile(full_path):
            files_to_upload.append((full_path, fname))
            
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
    print(f"Checking and uploading {len(files)} files to {REPO}...")
    
    success = 0
    for local_path, repo_path in files:
        try:
            print(f"Processing {repo_path}...", end=" ", flush=True)
            res = upload_file(local_path, repo_path, token)
            print(res)
            success += 1
        except Exception as e:
            print(f"FAILED: {e}")
            
    print(f"\nCompleted! {success}/{len(files)} files processed successfully for https://github.com/{REPO}")

if __name__ == "__main__":
    main()
