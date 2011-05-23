import os

def get_sound_type(input_filename):
    sound_type = os.path.splitext(input_filename.lower())[1].strip(".")

    if sound_type == "fla":
        sound_type = "flac"
    elif sound_type == "aif":
        sound_type = "aiff"

    return sound_type
