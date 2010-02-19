import os,re
import cue

junk = [("[\\]()`´':;,!|?=\"~*\\[]", ""),
        ("[-_.\\\\ ]+", "_"),
        ("&+", "_and_"),
        ("@", "_at_"),
        ("#", "_n"),
        ("_+", "_"),
        ("_$", ""),
        ("^_", "")]

junk_re = [(re.compile(rx), sub) for (rx, sub) in junk]

def remove_junk(string):
    string = string.lower()
    for (rx, sub) in junk_re:
        string = rx.sub(sub, string)
    return string

def unjunk_filename(filename):
    (directory, filename) = os.path.split(filename)
    (name, ext) = os.path.splitext(filename)
    name = remove_junk(name)
    return os.path.join(directory, name + ext)

##

media_files = [".mp3", ".flac", ".ape", ".wv", ".wav"]

def find_files(directory, types):
    return [name for name in os.listdir(directory)
            if os.path.splitext(name)[1].lower() in types]

def find_media_files(directory):
    return find_files(directory, media_files)

def find_cue_files(directory):
    return find_files(directory, [".cue"])

def guess_path_from_cue(cue):
    album = cue.parse_cue(cue)
    
    
