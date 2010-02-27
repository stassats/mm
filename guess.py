#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, re, readline, pipes
import cue, tag

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
    for rx, sub in junk_re:
        string = rx.sub(sub, string)
    return string

def unjunk_filename(filename):
    directory, filename = os.path.split(filename)
    name, ext = os.path.splitext(filename)
    name = remove_junk(name)
    return os.path.join(directory, name + ext)

##

media_files = [".mp3", ".flac", ".ape", ".wv", ".wav", ".cue"]

def extension(filename):
    return os.path.splitext(filename)[1].lower()

def sans_extension(filename):
    return os.path.splitext(filename)[0]

def get_dirs(path):
    result = []
    for root, dirs, files in os.walk(path):
        media = [os.path.join(root, file) for file in files
                 if extension(file) in media_files]
        if media:
            result.append(media)

    return map(group_files, result)

def group_multiple_cues(cues, non_cues):
    groups = []
    for cue in cues:
        counterpart = [file for file in non_cues
                       if sans_extension(cue) == sans_extension(file)]
        assert len(counterpart) == 1
        groups.append(([cue], counterpart))

    return groups

def group_files(files):
    cues = filter(lambda file: extension(file) == ".cue", files)
    non_cues = filter(lambda file: extension(file) != ".cue", files)

    if len(cues) == len(non_cues) and len(cues) > 1:
        return group_multiple_cues(cues, non_cues)

    return (cues, non_cues)

def is_various_artists(cue_album):
    for track in cue_album.tracks:
        if track and track.performer and track.performer != cue_album.performer:
            return True

    return False

def guess_from_cue(cue_file):
    album = cue.parse_cue(cue_file)
    if album == None:
        return None

    va = is_various_artists(album)

    return ("Various Artists" if va else album.performer,
            album.title, album.date)

def guess_from_tags(files):
    first = tag.Tag(files[0])

    year = first.year
    artist = first.artist
    album = first.album

    for file in files[1:]:
        tags = tag.Tag(file)
        if year != tags.year:
            year = None
        if album != tags.album:
            album = None
        if artist and artist != tags.artist:
            artist = "Various Artists"

    return (artist, album, year)

##

base_dir = os.path.expanduser("~/music/")

def make_filename(tags):
    file_name = base_dir

    artist, album, year = tags
    artist = remove_junk(artist)
    album = remove_junk(album)

    if artist == 'various_artists':
        file_name += '_/'
    else:
        file_name += artist[0] + '/' + artist + '/'

    file_name += album

    if year:
        file_name += '_' + str(year)

    return file_name

def decode_files(directory, files):
    os.system("shntool conv -o \"cust ext=ogg oggenc -q8 -o %s/%%f -\" -O always %s" % \
                  (directory, str.join(' ', files)))

def decode_files_using_cue(directory, cue, files):
    
    command = "shntool split -t %%n_%%t -f %s -o \
'cust ext=ogg oggenc -q8 -o %s/%%f -' -O always %s" % \
                  (pipes.quote(cue),
                   directory, str.join(' ',
                                       map(pipes.quote, files)))
    print command
    os.system(command)

def read_line(prompt, initial_text):
    def startup_hook():
        readline.insert_text(initial_text)

    readline.set_startup_hook(startup_hook)
    return raw_input(prompt)

def recode_release(release):
    cues, files = release

    if len(cues) == len(files) and len(cues) == 1:
        destination = make_filename(guess_from_cue(cues[0]))
        destination = read_line("Destination: ", destination)
        decode_files_using_cue(destination, cues[0], files)
    elif len(cues) == 0:
        destination = make_filename(guess_from_tags(files))
        destination = read_line("Destination: ", destination)
        decode_files(destination, files)
    else:
        destination = make_filename(guess_from_cue(cues[0]))
        destination = read_line("Destination: ", destination)
        decode_files(destination, files)
    os.system("tag -ganyr " + destination)

def recode(directory):
    releases = get_dirs(directory)
    map(recode_release, releases)

recode(".")
