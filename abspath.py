import os

def abs_path(path: str):
    return path if os.path.isabs(path) \
        else os.path.join(os.path.dirname(os.path.abspath(__file__)), path)