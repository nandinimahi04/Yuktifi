import os

paths = [
    r'd:\yukti\frontend\app\[locale]\report\page.tsx',
    r'd:\yukti\frontend\app\[locale]\category\[categoryId]\page.tsx',
    r'd:\yukti\frontend\app\[locale]\capital\page.tsx',
    r'd:\yukti\frontend\app\[locale]\dashboard\page.tsx',
    r'd:\yukti\frontend\app\[locale]\discover\page.tsx',
    r'd:\yukti\frontend\components\Sidebar.tsx'
]

for p in paths:
    if os.path.exists(p):
        with open(p, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'from "next/navigation"' in content:
            new_content = content.replace('from "next/navigation"', 'from "@/routing"')
            with open(p, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated {p}")
