import os
import json

def search_vscode_history(target_names):
    history_dir = os.path.expanduser("~/Library/Application Support/Code/User/History")
    if not os.path.exists(history_dir):
        return
        
    found_files = {}

    for root, dirs, files in os.walk(history_dir):
        if "entries.json" in files:
            entries_path = os.path.join(root, "entries.json")
            try:
                with open(entries_json, 'r') as f:
                    pass # just check if we can
            except:
                pass
            
            try:
                with open(entries_path, 'r', errors='ignore') as f:
                    content = f.read()
                    
                # The entries.json usually looks like:
                # {"version":1,"resource":"file:///Users/chiragsingh/Desktop/social-ai-reply/app/api/v1/routes/scrapers.py","entries":[{"id":"123","timestamp":123}]}
                for name in target_names:
                    if name in content:
                        print(f"FOUND MATCH in {entries_path}")
                        data = json.loads(content)
                        resource = data.get("resource", "")
                        print(f"Resource: {resource}")
                        
                        entries = data.get("entries", [])
                        if entries:
                            # The latest entry
                            latest = entries[-1]
                            latest_id = latest.get("id")
                            if latest_id:
                                content_file = os.path.join(root, latest_id)
                                if os.path.exists(content_file):
                                    with open(content_file, 'r', errors='ignore') as cf:
                                        file_content = cf.read()
                                        found_files[resource] = file_content
                                        print(f"-> Recovered {len(file_content)} bytes for {resource}")
            except Exception as e:
                pass

    for path, content in found_files.items():
        if "social-ai-reply" in path:
            # Strip file:// prefix
            if path.startswith("file://"):
                path = path[7:]
            
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                f.write(content)
            print(f"Successfully restored {path}")

if __name__ == "__main__":
    targets = [
        "scrapers.py",
        "custom_scrapers.py",
        "gemini_embedding_provider.py",
        "dynamic_adapter.py",
        "20260625_01_create_custom_scrapers.sql",
        "scrapers.ts"
    ]
    
    search_vscode_history(targets)
