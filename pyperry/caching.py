
enabled = True
registry = []

def reset():
    for item in registry:
        item()

def register(function):
    registry.append(function)

def enable():
    enabled = True

def disable():
    enabled = False

def clean_registry():
    registry = []
    enabled = True

