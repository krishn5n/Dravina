import os

path = 'C:\Program Files (x86)'
folders = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
print(folders)