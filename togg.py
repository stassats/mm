#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os
import re
import readline
import shlex
import shutil
import codecs
from optparse import OptionParser

import cue
import tag
import tempfile

use_musicbrainz = False
cue_encoding = 'utf-8'

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
    readline.set_startup_hook(lambda: readline.insert_text(initial_text))

    try:
        return input(prompt)
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
    cues = [file for file in files if extension(file) == ".cue"]
    non_cues = [file for file in files if extension(file) != ".cue"]

    if len(cues) == len(non_cues) and len(cues) > 1:
        return group_multiple_cues(cues, non_cues)

    return (cues, non_cues)

def is_various_artists(cue_album):
    for track in cue_album.tracks:
        if track and track.performer and track.performer != cue_album.performer:
            return True

    return False

def parse_year(year):
    if isinstance(year, str):
        match = re.search(r"\d{4}", year)
        if match:
            return match.group()

def guess_from_cue(cue_file):
    try:
        album = cue.parse_cue(cue_file, cue_encoding)
    except Exception as e:
        print(e)
        return
        
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

    year = None
    if album.date:
        year = parse_year(album.date)

    if not year:
        year = parse_year(os.path.basename(
                os.path.dirname(os.path.abspath(cue_file))))

    return ("Various Artists" if va else album.performer,
            album.title, year or album.date, tracks)

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

    corrected_year = None
    if year:
        corrected_year = parse_year(year)

    if not corrected_year:
        corrected_year = parse_year(os.path.basename(
                os.path.dirname(os.path.abspath(files[0]))))
            
    return (artist, album, corrected_year or year, tracks)

##

music_dir = os.path.expanduser("~/music/")

def remove_article(string):
    return re.sub('^(the|a)_', '', string)

def make_filename(tags):
    file_name = music_dir

    artist, album, year, _ = tags

    if not artist or not album:
        return music_dir

    artist = remove_article(tag.remove_junk(artist))

    album = tag.remove_junk(album)

    if artist == 'various_artists':
        file_name += '_/'
    else:
        first_letter = artist[0]
        if first_letter.isdigit():
            first_letter = '0'
        file_name += first_letter + '/' + artist + '/'

    file_name += album
    
    if year:
        file_name += '_' + str(year)

    return file_name

def remove_directory(files):
    return (os.path.dirname(files[0]),
            list(map(os.path.basename, files)))

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
        if cue_encoding != 'utf-8':
            temp = tempfile.NamedTemporaryFile()
            with codecs.open(cue, encoding=cue_encoding) as input:
                with codecs.open(temp.name, 'w', encoding='utf-8') as output:
                    output.write(input.read())
            cue = temp.name

        mode = "split -t %n_%t -f " + shlex.quote(os.path.abspath(cue))
    else:
        mode = "conv"

    run_program("shntool " + mode + " -o " + encoder +
                " -O always " + str.join(' ', list(map(shlex.quote, files)))
                ,dir)

def set_tags(directory, tags, remove=None):
    def track_number(file_name, common=""):
        match = re.match(re.escape(common) + r'(\d\d?)',
                         tag.remove_junk(os.path.basename(file_name)))
        if match:
            return int(match.group(1))

    file_list = [os.path.join(directory, file)
                 for file in os.listdir(directory)]

    if not file_list:
        return

    common = os.path.basename(os.path.commonprefix
                              (list(map(tag.unjunk_filename, file_list))))

    for file in file_list:
        new_tag = tag.find_track(tags, track_number(file, common))

        if not new_tag:
            print("WARNING: couldn't find track with number " + \
                str(track_number(file, common)))
        else:
            new_tag.file = file

            if remove:
                tag.remove_tag(file)

    if any(not tag.album or tag.album != tags[0].album for tag in tags):
        for i in tags:
            i.set_album()

    if any(not tags[0].year or tag.year != tags[0].year
           for tag in tags):
        for i in tags:
            i.set_year()

    if use_musicbrainz:
        tag.guess_mb_release(tags)

    tag.rename_files(tags)
    list(map(tag.Tag.write_tag, tags))

def copy_mp3(files, destination):
    if not os.path.exists(destination):
        os.makedirs(destination)

    for file in files:
        new_name = tag.unjunk_filename(os.path.basename(file))
        shutil.copy(file, os.path.join(destination, new_name))

def recode_release(release, dest):
    cues, files = release

    if cues and len(files) == 1:
        guess = guess_from_cue(cues[0])
    elif not cues:
        guess = guess_from_tags(files)
    else:
        guess = guess_from_cue(cues[0])
        if not guess or any(not part for part in guess[:-1]):
            guess = guess_from_tags(files)
        cues = None

    if dest:
        destination = dest
    else:
        destination = read_line("Destination: ", make_filename(guess))

    if not destination:
        return

    if all(extension(file) == ".mp3" for file in files):
        copy_mp3(files, destination)
        set_tags(destination, guess[3], True)
    else:
        shntool(destination, files, cues and cues[0])
        if os.path.exists(destination + "/00_pregap.ogg"):
            os.remove(destination + "/00_pregap.ogg")

        set_tags(destination, guess[3])

    os.system("mpc update " + destination.replace(music_dir, "", 1))

def recode(directory, dest):
    releases = get_dirs(directory)
    for release in releases:
        recode_release(release, dest)

def parse_opt():
    usage = "%prog [options] [files]"
    parser = OptionParser(usage=usage)

    parser.add_option("-n", "--no-musicbrainz", dest="no_mb", action="store_true",
                      default=False,
                      help="Disable musicbrainz access")
    parser.add_option("-c", "--cue-encoding", dest="cue_encoding", action="store",
                      default="utf-8",
                      help="Specify CUE file encoding")

    return parser.parse_args()

def main ():
    global use_musicbrainz
    global cue_encoding

    options, args = parse_opt()
    destination = args[0] if len(args) else False
    if options.no_mb:
        use_musicbrainz = False
    cue_encoding = options.cue_encoding

    recode(".", destination)

main()
