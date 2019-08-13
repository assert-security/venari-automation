import requests
import os
import os.path
import glob

def ensure_empty_dir(dir: str):
    if (not os.path.exists(dir)):
        os.mkdir(dir)
        if (not os.path.exists(dir)):
            return False

    path = f'{dir}/*'
    files = glob.glob(path)
    for file in files:
        os.remove(file)

    files = glob.glob(path)
    return True if (len(files) == 0) else False

