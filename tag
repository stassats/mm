#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This software is in the public domain and is
# provided with absolutely no warranty.
#
# Requires PythonMusicBrainz2, mutagen

import os, sys
import re, string
import exceptions

import musicbrainz2.webservice as ws
from optparse import OptionParser

from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.easyid3 import EasyID3
import mutagen.id3
from mutagen.musepack import Musepack

####

class Tag:
    artist = None
    title = None
    album = None
    year = None
    track = None
    file = None

    def __init__(self):
        self.data = []

    def read_tag(self, file):
        self.file = file
        audio = open_file(file)

        if audio.has_key('artist'):
            self.artist = audio['artist'][0]

        if audio.has_key('title'):
            self.title = audio['title'][0]

        if audio.has_key('album'):
            self.album = audio['album'][0]

        if audio.has_key('date'):
            self.year = audio['date'][0]

        if audio.has_key('tracknumber'):
            self.track = tr.sub('', audio['tracknumber'][0])

        audio.save()
        return self

    def write_tag(self):
        audio = open_file(self.file)

        if self.artist and len(self.artist) > 0:
            audio['artist'] = self.artist

        if self.title and len(self.title) > 0:
            audio['title'] = self.title.replace('`', "'")

        if self.album and len(self.album) > 0:
            audio['album'] = self.album

        if self.year and len(self.year) > 0:
           audio['date'] = self.year

        if self.track and self.track > 0:
            audio['tracknumber'] = self.track

        audio.save()

    def capitalize(self):
        self.title = capitalize(self.title)
        self.album = capitalize(self.album)

    def set_title(self):
        title = unicode(os.path.splitext(os.path.basename(self.file))[0])
        title = title.replace('_', ' ')

        self.title = re.search('^(?:\d\d? )?(.+)', title).group(1)

    def set_track(self):
        title = os.path.splitext(os.path.basename(self.file))[0]
        track = re.search('^\d\d?', title)

        if track:
            self.track = track.group()

    def set_album(self):
        album = os.path.basename(os.path.dirname(self.file))
        album = album.replace('_', ' ')

        album = re.search('^(\d\d\w? )?(.+?)( \d{4})?$', album)
        self.album = album.group(2)

    def set_year(self):
        year = os.path.basename(os.path.dirname(self.file))

        year = re.search('\d{4}$', year)

        if year:
            self.year = year.group()

    def display_tag(self):
        print "Artist:", self.artist
        print "Title:", self.title
        print "Album:", self.album
        print "Year:", self.year
        print "Tracknumber:", self.track
        print

class not_media_file(exceptions.Exception):
    def __init__(self):
        pass

class not_album(exceptions.Exception):
    def __init__(self):
        pass

########

art = 'a an the and but or nor as at by for in of on to'.split()
rom = re.compile('^m{,3}(c[md]|d?c{,3})(x[cl]|l?x{,3})(i[xv]|v?i{,3})$')
tr = re.compile('/.+')

def isroman(i):
    return re.search(rom, i)

def cap(i):
    if isroman(i):
        return i.upper()

    if i[0] == '(':
        return '(' + i[1:].capitalize()

    if i in art:
        return i

    return i.capitalize()

def capitalize(str):
    if str == None or len(str) <= 0:
        return

    str = str.capitalize().split()
    str[-1] = str[-1].capitalize()

    str = map(cap, str)

    return string.join(str, ' ')

def get_file_ext(file):
     return os.path.splitext(file)[1][1:]

def rename_file(tag):
    if tag.track != '' and int(tag.track) < 10:
        tag.track = '0' + str(int(tag.track))

    if tag.title == None or len(tag.title) < 1:
        return

    tit = string.lower(tag.title).replace(' ', '_')

    new_name = os.path.dirname(tag.file) + '/'
    new_name += (tag.track + '_' + tit).replace("/", "_")
    new_name += os.path.splitext(tag.file)[1]

    os.rename (tag.file, new_name)

    tag.file = new_name

def open_file(file):
    ftype = get_file_ext(file)

    if ftype == 'flac':
        audio = FLAC(file)
    elif ftype == 'ogg':
        audio = OggVorbis(file)
    elif ftype == 'mpc':
        audio = Musepack(file)
    elif ftype == 'mp3':
        try:
            audio = EasyID3(file)
        except mutagen.id3.error:
# Dirty and ugly hack
            tag = mutagen.id3.ID3()
            tag.add(mutagen.id3.TRCK(encoding=3, text="0"))
            tag.save(file)

            audio = EasyID3(file)
    else:
        raise not_media_file

    return audio

def remove_tag(file):
    audio = open_file(file)
    audio.delete()
    audio.save()

def read_tags(file_list):
    tag_list = []

    for file in file_list:
        try:
            tag_list.append(Tag().read_tag(file))
        except not_media_file:
            print file, "is not a media file!"
            continue

    return tag_list

def get_tags_album(tag_list):
    album = tag_list[0].album

    for i in tag_list:
        if album != i.album:
            raise not_album

    return album

def get_tags_artist(tag_list):
    artist = tag_list[0].artist

    for i in tag_list:
        if artist != i.artist:
            return "Various Artists"

    return artist

def get_mb_data(id):
    q = ws.Query()

    try:
        inc = ws.ReleaseIncludes(tracks=True)
        release = q.getReleaseById(id, inc)
    except ws.WebServiceError, exceptions.e:
        print 'Error:', exceptions.e
        sys.exit(1)

    return parse_mb_release(release)

def set_mb_data(tag, mb_data):
    tag.album = mb_data[0]
    (tag.artist, tag.title) = mb_data[int(tag.track)]

def parse_mb_release(release):
    q = ws.Query()
    result = [release.title]

    for i in range(len(release.tracks)):
        id = release.tracks[i].id
        inc = ws.TrackIncludes(artist=True)
        track = q.getTrackById(id, inc)
        result.append([track.artist.name, track.title])

    return result

def guess_mb_release(tag_list):
    q = ws.Query()
    artist = get_tags_artist(tag_list)
    album = get_tags_album(tag_list)

    filter = ws.ReleaseFilter(title=album, limit=5)

    results = q.getReleases(filter=filter)
    res_len = len(results)

    if res_len > 0:
        releases = []

        print "Data from tags:", artist, '-', album, "[" + str(len(tag_list)), "tracks]\n"
        print "Variants from MusicBrainz:"
        for i in range(res_len):
            id = results[i].release.id
            inc = ws.ReleaseIncludes(tracks=True)
            releases.append(q.getReleaseById(id, inc))

            print str(i + 1) + ")", results[i].release.artist.name, '-', \
            results[i].release.title, \
            "[" + str(len(releases[i].tracks)), "tracks]" , \
            "(" + str(results[i].score), "%)"

            print " Details:", id + ".html\n"

        while True:
            if res_len == 1:
                rng = "[1]"
            else:
                rng = "[1.." + str(res_len) +"]"

            a = raw_input("Enter number of release to use " + rng + ": ")
            if a.isdigit() and int(a) in range(res_len + 1):
                a = int(a)
                break
            else:
                print "Number must be", rng

        if a > 0:
            mb_data = parse_mb_release(releases[a - 1])

            for tag in tag_list:
                set_mb_data(tag, mb_data)

def get_file_list(args):
    #Walk current directory if no argumners was specified
    if len(args) <= 0:
        args = [os.getcwd()]

    file_list = []

    for path in args:
        path = os.path.normpath(os.path.join(os.getcwd(), path))

        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for name in files:
                    file_list.append(unicode(os.path.join(root, name),
                                             "utf-8"))
        else:
            file_list.append(unicode(path, "utf-8"))

    #Remove duplicates
    return [ x for i, x in enumerate(file_list) if i == file_list.index(x) ]

def parse_opt():
    usage = "%prog [options] [files]"
    parser = OptionParser(usage=usage)

    parser.add_option("-t", "--set-title", dest="set_tit", action="store_true",
                      default=False,
                      help="Set title according to file name")

    parser.add_option("-n", "--set-number", dest="set_num", action="store_true",
                      default=False,
                      help="Set track number according to file name")

    parser.add_option("-a", "--set-album", dest="set_album",
                      action="store_true", default=False,
                      help="Set album according to directory name")

    parser.add_option("-A", "--album", dest="Album",
                      action="store", default=None,
                      help="Set album to ALBUM")

    parser.add_option("-T", "--title", dest="Title",
                      action="store", default=None,
                      help="Set title to TITLE")

    parser.add_option("-p", "--artist", dest="Artist",
                      action="store", default=None,
                      help="Set album to ARTIST")

    parser.add_option("-y", "--date", dest="set_year",
                      action="store_true", default=False,
                      help="Set year according to directory name")

    parser.add_option("-Y", "--year", dest="Year",
                      action="store", default=None,
                      help="Set year to YEAR")

    parser.add_option("-r", "--rename-file", dest="rename",
                      action="store_true", default=False,
                      help="Rename file according to tag")

    parser.add_option("-c", "--capitalize", dest="cap_tag",
                      action="store_true", default=False,
                      help="Capitalize tag")

    parser.add_option("-d", "--delete", dest="rem_tag",
                      action="store_true", default=False,
                      help="Remove tag")

    parser.add_option("-i", "--musicbrainz-id", dest="mb_id",
                      action="store", default=None,
                      help="Set tag according to musicbrainz")

    parser.add_option("-g", "--guess-release", dest="mb_guess",
                      action="store_true", default=False,
                      help="Guess musicbrainz release")

    parser.add_option("-S", "--shift-tracknumber", dest="shift",
                      action="store", default=0,
                      help="Shift of tracknumber")

    return parser.parse_args()

def main():
    (options, args) = parse_opt()

    file_list = get_file_list(args)

    if len(file_list) < 1:
        exit()

    tag_list = read_tags(file_list)

    if (len(sys.argv) - len(args) == 1):
        map(Tag.display_tag, tag_list)
        exit()

    if options.mb_id:
        mb_data = get_mb_data(options.mb_id)

    for tag in tag_list:
        if options.set_year:
            tag.set_year()

        if options.set_num:
            tag.set_track()

        if tag.track and tag.track.isdigit():
            tag.track = str(int(tag.track) - int(options.shift))

        if options.rem_tag:
            remove_tag(tag.file)

        if options.mb_id:
            set_mb_data(tag, mb_data)

        if options.set_tit:
            tag.set_title()

        if options.set_album:
            tag.set_album()
        elif options.Album:
            tag.album = unicode(options.Album, 'utf-8')

        if options.Title:
            tag.title = unicode(options.Title, 'utf-8')

        if options.Artist:
            tag.artist = unicode(options.Artist, 'utf-8')

        if options.Year:
            tag.year = unicode(options.Year, 'utf-8')

        if not options.mb_id and options.cap_tag:
            tag.capitalize()

    if options.mb_guess:
        guess_mb_release(tag_list)

    for tag in tag_list:
        if options.rename:
            rename_file(tag)
        tag.write_tag()

main()
