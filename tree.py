import os

def print_tree(startpath, exclude_dirs=['.git', '.venv', 'node_modules', '__pycache__', '.pytest_cache', '.next']):
    print(os.path.basename(os.path.abspath(startpath)) + '/')
    for root, dirs, files in os.walk(startpath):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        if root != startpath:
            print(f'{indent}+-- {os.path.basename(root)}/')
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            print(f'{subindent}+-- {f}')

print_tree('.')
