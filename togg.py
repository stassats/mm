#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, os, re, readline, pipes, shutil
import cue, tag

## Readline and completion

def filename_completer(text, state):
    directory, rest = os.path.split(text)
    if not os.path.exists(directory):
        return

    files = os.listdir(directory)
    possible_files = [file for file in files
                      if file.startswith(rest)]

    if len(possible_files) <= state:
        return

    result = os.path.join(directory, possible_files[state])
    if len(possible_files) == 1:
        if os.path.isdir(result):
            result += "/"
        else:
            result += " "

    return result

readline.set_completer_delims(" ")
readline.parse_and_bind("tab: complete")
readline.set_completer(filename_completer)

def read_line(prompt, initial_text):
    def startup_hook():
        readline.insert_text(initial_text)

    readline.set_startup_hook(startup_hook)
    try:
        return raw_input(prompt)
    finally:
        readline.set_startup_hook(None)

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

    grouped_files = []
    for files in result:
        files = group_files(files)

        if isinstance(files, list):
            grouped_files.extend(files)
        else:
            grouped_files.append(files)

    return grouped_files

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
    if not album:
        return

    va = is_various_artists(album)

    tracks = []
    for cue_track in album.tracks:
        track = tag.Tag()
        tracks.append(track)

        track.artist = cue_track.performer or album.performer
        track.album = album.title
        track.title = cue_track.title
        track.year = album.date
        track.number = cue_track.number

    return ("Various Artists" if va else album.performer,
            album.title, album.date, tracks)

def guess_from_tags(files):
    first = tag.Tag(files[0])

    year = first.year
    artist = first.artist
    album = first.album

    tracks = []
    tracks.append(first)

    for file in files[1:]:
        tags = tag.Tag(file)
        tracks.append(tags)

        if year != tags.year:
            year = None
        if album != tags.album:
            album = None
        if artist and artist != tags.artist:
            artist = "Various Artists"

    for track in tracks:
        if not track.number:
            track.set_number()

    return (artist, album, year, tracks)

##

music_dir = os.path.expanduser("~/music/")

def make_filename(tags):
    file_name = music_dir

    artist, album, year, _ = tags

    if not artist or not album:
        return music_dir

    artist = tag.remove_junk(artist)
    album = tag.remove_junk(album)

    if artist == 'various_artists':
        file_name += '_/'
    else:
        file_name += artist[0] + '/' + artist + '/'

    file_name += album

    if year:
        file_name += '_' + str(year)

    return file_name

def remove_directory(files):
    return (os.path.dirname(files[0]),
            map(os.path.basename, files))

def run_program(command, directory):
    original_cwd = os.getcwd()
    if directory:
        os.chdir(directory)
    try:
        return os.system(command)
    finally:
        os.chdir(original_cwd)

def shntool(destination, files, cue=None):
    dir, files = remove_directory(files)
    encoder = "'cust ext=ogg oggenc -q8 -o %s/%%f -'" % destination

    if cue:
        mode = "split -t %n_%t -f " + pipes.quote(os.path.basename(cue))
    else:
        mode = "conv"

    run_program("shntool " + mode + " -o " + encoder +
                " -O always " + str.join(' ', map(pipes.quote, files))
                ,dir)

def set_tags(directory, tags, remove=None):

    def track_number(file_name, common=""):
        match = re.search('^' + common + '(\d\d?)',
                          tag.remove_junk(os.path.basename(file_name)))
        if match:
            return int(match.group(1))

    file_list = [os.path.join(directory, file)
                 for file in os.listdir(directory)]

    if not file_list:
        return

    common = os.path.basename(os.path.commonprefix(file_list))

    for file in file_list:
        new_tag = tag.find_track(tags, track_number(file, common))

        if not new_tag:
            print "WARNING: couldn't find track with number " + \
                str(track_number(file, common))
        else:
            new_tag.file = file

            if remove:
                tag.remove_tag(file)

    if any(tag.album != tags[0].album for tag in tags):
        for i in tags:
            i.set_album()

    if any(tag.year != tags[0].year for tag in tags):
        for i in tags:
            i.set_year()

    tag.guess_mb_release(tags)
    tag.rename_files(tags)
    map(tag.Tag.write_tag, tags)

def recode_release(release):
    cues, files = release

    if len(cues) == len(files) and len(cues) == 1:
        guess = guess_from_cue(cues[0])
    elif not cues:
        guess = guess_from_tags(files)
    else:
        guess = guess_from_cue(cues[0]) or guess_from_tags(files)
        cues = None

    if len(sys.argv) == 2:
        destination = sys.argv[1]
    else:
        destination = read_line("Destination: ", make_filename(guess))

    if not destination:
        return

    if all(extension(file) == ".mp3" for file in files):
        if not os.path.exists(destination):
            os.makedirs(destination)

        for file in files:
            shutil.copy(file, os.path.join(destination, file))

        set_tags(destination, guess[3], True)
    else:
        shntool(destination, files, cues and cues[0])
        set_tags(destination, guess[3])

    os.system("mpc update " + destination.replace(music_dir, "", 1))

def recode(directory):
    releases = get_dirs(directory)
    map(recode_release, releases)

recode(".")
