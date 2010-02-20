#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, re
import cue
import tag

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

media_files = [".mp3", ".flac", ".ape", ".wv", ".wav"]

def find_files(directory, types):
    return [os.path.join(directory, name) for name in os.listdir(directory)
            if os.path.splitext(name)[1].lower() in types]

def find_media_files(directory):
    return find_files(directory, media_files)

def find_cue_files(directory):
    return find_files(directory, [".cue"])

def is_various_artists(cue_album):
    for track in cue_album.tracks:
        if track and track.performer != cue_album.performer:
            return True

    return False

def guess_from_cue(cue_file):
    album = cue.parse_cue(cue_file)
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
