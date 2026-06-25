import json
import os

def recover_files():
    transcripts = [
        "/Users/chiragsingh/.gemini/antigravity/brain/5935a6fa-9e43-4b4d-8ee2-d6967fd73269/.system_generated/logs/transcript_full.jsonl",
        "/Users/chiragsingh/.gemini/antigravity/brain/e7b9ea84-b991-4d23-9523-4d52af5e549f/.system_generated/logs/transcript_full.jsonl"
    ]
    
    file_contents = {}
    
    for t in transcripts:
        if not os.path.exists(t):
            continue
        with open(t, 'r') as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    if obj.get("type") == "PLANNER_RESPONSE":
                        for tc in obj.get("tool_calls", []):
                            name = tc.get("name", "") or tc.get("function", {}).get("name", "")
                            
                            # Extract args
                            args = tc.get("args") or tc.get("arguments") or {}
                            if isinstance(args, str):
                                try:
                                    args_obj = json.loads(args)
                                except:
                                    args_obj = {}
                            else:
                                args_obj = args
                                
                            # write_to_file
                            if name == "write_to_file" or name == "default_api:write_to_file":
                                target = args_obj.get("TargetFile")
                                content = args_obj.get("CodeContent")
                                if target and content:
                                    file_contents[target] = content
                                    
                            # multi_replace_file_content and replace_file_content
                            elif "replace_file_content" in name:
                                # We only capture write_to_file for complete reconstruction
                                # For modified files, we just flag them.
                                pass

                except Exception as e:
                    pass
                    
    targets = [
        "scrapers.py",
        "custom_scrapers.py",
        "gemini_embedding_provider.py",
        "dynamic_adapter.py",
        "20260625_01_create_custom_scrapers.sql",
        "scrapers.ts",
        "page.tsx"
    ]
    
    restored_count = 0
    for path, content in file_contents.items():
        if "scrapers" in path or "dynamic_adapter" in path or "gemini_embedding" in path:
            if path.startswith("file://"):
                path = path[7:]
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                f.write(content)
            print(f"Restored: {path}")
            restored_count += 1
            
    print(f"Total files restored: {restored_count}")

if __name__ == "__main__":
    recover_files()
