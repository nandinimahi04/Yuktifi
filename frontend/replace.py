import os
import glob

files = glob.glob(r'd:\yukti\frontend\app\[locale]\**\*.tsx', recursive=True)

for path in files:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    if 'from "next/navigation"' in content:
        new_content = content.replace('from "next/navigation"', 'from "@/routing"')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {path}")
