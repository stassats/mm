#!/usr/bin/python
# -*- coding: utf-8 -*-

# This software is in the public domain and is
# provided with absolutely no warranty.

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
from mutagen.mp4 import MP4

####

q = ws.Query()

class Tag:
    artist = None
    title = None
    album = None
    year = None
    number = None
    file = None

    def __init__(self, file = None):
        if file:
           self.read_tag(file)

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
            self.number = int(audio['tracknumber'][0].partition('/')[0])

        audio.save()
        return self

    def write_tag(self):
        audio = open_file(self.file)

        if self.artist:
            audio['artist'] = self.artist

        if self.title:
            audio['title'] = self.title.replace('`', "'")

        if self.album:
            audio['album'] = self.album

        if self.year:
            audio['date'] = str(self.year)

        if self.number:
            if self.number > 0:
                audio['tracknumber'] = str(self.number)

        audio.save()

    def capitalize(self):
        self.title = capitalize(self.title)
        self.album = capitalize(self.album)

    def lower_articles(self):
        self.title = lower_articles(self.title)
        self.album = lower_articles(self.album)

    def set_title(self):
        title = unicode(os.path.splitext(os.path.basename(self.file))[0],
                        'utf-8', 'ignore')
        title = title.replace('_', ' ')

        self.title = re.search('^(?:\d\d? )?(.+)', title).group(1)

    def set_number(self):
        title = os.path.basename(self.file)
        track = re.search('^\d\d?', title)

        if track:
            self.number = int(track.group())

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
        print "Tracknumber:", str(self.number)

class not_media_file(exceptions.Exception):
    def __init__(self):
        pass

class not_album(exceptions.Exception):
    def __init__(self):
        pass

########

junk = [("[\\]()`´':;,!|?=\/\"~*\\[]", ""),
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

art = 'a an the and but or nor as at by for in of on to'.split()
rom = re.compile('^m{,3}(c[md]|d?c{,3})(x[cl]|l?x{,3})(i[xv]|v?i{,3})$')

def isroman(i):
    return re.search(rom, i)

def cap(i):
    if isroman(i):
        return i.upper()

    if i[0] == '(':
        return '(' + i[1:].capitalize()

    return i.capitalize()

def articlify(string):
    def parenthesed(string):
        return string[0] == '(' or string[-1] == ')'

    if string.lower() in art and not parenthesed(string):
        return string.lower()
    else:
        return string

def lower_articles(str):
    if not str:
        return

    words = str.split()
    if not words:
        return str

    words = [words[0]] + map(articlify, words[1:-1]) + [words[-1]]
    return string.join(words, ' ')

def capitalize(str):
    if not str:
        return

    words = [word.capitalize() for word in str.split()]

    words = map(cap, words)

    return lower_articles(string.join(words, ' '))

def get_file_ext(file):
    return os.path.splitext(file)[1][1:]

def rename_files(tags):
    for tag in tags:
        rename_file(tag, len(tags) > 9)

def rename_file(tag, zero=True):
    if not tag.title:
        return

    if tag.number:
        if zero and tag.number < 10:
            track = '0' + str(tag.number)
        else:
            track = str(tag.number)
        track += '_'
    else:
        track = ''
        print "WARNING: no track number on file " + tag.file

    new_name = unicode(os.path.dirname(tag.file), 'utf-8', 'ignore') + '/'
    new_name += remove_junk(track + tag.title)
    new_name += os.path.splitext(tag.file)[1]

    if new_name == tag.file:
        return

    if os.path.exists(new_name):
        print 'WARNING: path', new_name, 'exists'
        return

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
    elif ftype == 'm4a':
        audio = MP4(file)
    elif ftype == 'mp3':
        try:
            audio = EasyID3(file)
        except mutagen.id3.error:
            # If the tag is absent it needs to be explicitly added
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
            tag_list.append(Tag(file))
        except not_media_file:
            print file, "is not a media file!"
            continue

    return tag_list

def get_tags_album(tags):
    if any(tag.album != tags[0].album for tag in tags):
            raise not_album

    return tags[0].album

def get_tags_artist(tag_list):
    artist = tag_list[0].artist

    for i in tag_list:
        if artist != i.artist:
            return "Various Artists"

    return artist

def get_mb_data(id):
    try:
        inc = ws.ReleaseIncludes(tracks=True, artist=True)
        release = q.getReleaseById(id, inc)
    except ws.WebServiceError, exceptions.e:
        print 'Error:', exceptions.e
        sys.exit(1)

    return parse_mb_release(release)

def set_mb_data(tag, mb_data):
    track_number = tag.number
    if track_number < len(mb_data):
        tag.album = mb_data[0]
        tag.artist, tag.title = mb_data[tag.number]
    else:
        print 'WARNING: there is no track', track_number, 'in this MusicBrainz release'

def parse_mb_release(release):
    result = [release.title]
    release_artist = release.getArtist().name

    for track in release.tracks:
        artist = track.getArtist()

        if artist:
            artist = artist.name
        else:
            artist = release_artist

        result.append([artist, track.title])

    return result

def guess_mb_release(tag_list):
    artist = get_tags_artist(tag_list)
    album = get_tags_album(tag_list)

    filter = ws.ReleaseFilter(query='%s and tracks:%d and artist:"%s"' \
                                  % (album, len(tag_list), artist),
                              limit=5)

    results = q.getReleases(filter=filter)
    res_len = len(results)

    if res_len > 0:
        releases = []

        print "Data from tags:", artist, '-', album, "[" + str(len(tag_list)), "tracks]\n"
        print "Variants from MusicBrainz:"

        inc = ws.ReleaseIncludes(tracks=True, artist=True)

        for i in range(res_len):
            id = results[i].release.id
            releases.append(q.getReleaseById(id, inc))

            print str(i + 1) + ")", results[i].release.artist.name, '-', \
                results[i].release.title, \
                "[" + str(len(releases[i].tracks)), "tracks]" , \
                "(" + str(results[i].score), "%)"

            print " Details:", id + ".html\n"

        while True:
            a = raw_input("Number of the release or a release id (zero for none): ")
            if not a.isdigit():
                mb_data = get_mb_data(a)
                break
            elif int(a) <= res_len and int(a) > -1:
                a = int(a)
                if a == 0: return
                
                mb_data = parse_mb_release(releases[a - 1])
                break
            else:
                print "Must be a positive number less than %d" % res_len

        for tag in tag_list:
            set_mb_data(tag, mb_data)

def find_track(tracks, number):
    for track in tracks:
        if track.number == number:
            return track

def set_from_cue(tag, cue_data):
    track = find_track(cue_data.tracks, tag.number)
    if not track:
        print "error, no track with such number in a cue file", str(tag.number)

    tag.album = cue_data.title
    tag.title = track.title
    tag.artist = track.performer or cue_data.performer

    return track

def get_file_list(args):
    # Walk current directory if no argumnets was specified
    if not args:
        args = [os.getcwd()]

    file_list = []

    for path in args:
        path = os.path.normpath(os.path.join(os.getcwd(), path))

        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for name in files:
                    file_list.append(os.path.join(root, name))
        else:
            file_list.append(path)

    # Remove duplicates
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

    parser.add_option("-N", "--number", dest="Number",
                      action="store", default=None,
                      help="Set track number to NUMBER")

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
                      help="Make articles lowercase")

    parser.add_option("-C", "--capitalize-all", dest="cap_all",
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

    parser.add_option("", "--print-tracklisting", dest="tracklist",
                      action="store_true", default=False,
                      help="Print tracklisting")
    parser.add_option("", "--cue", dest="cue_file",
                      action="store", default=None,
                      help="Set tags according to a CUE file")

    return parser.parse_args()

def main():
    options, args = parse_opt()

    file_list = get_file_list(args)

    if not file_list:
        exit()

    tag_list = read_tags(file_list)

    if options.tracklist:
        for tag in tag_list:
            print str(tag.number) + ".", tag.title
        exit

    if (len(sys.argv) - len(args) == 1):
        map(Tag.display_tag, tag_list)
        exit()

    if options.mb_id:
        mb_data = get_mb_data(options.mb_id)

    if options.cue_file:
        import cue
        cue_data = cue.parse_cue(options.cue_file)

    for tag in tag_list:
        if options.set_year:
            tag.set_year()

        if options.set_num:
            tag.set_number()

        if tag.number:
            tag.number = tag.number - int(options.shift)

        if options.rem_tag:
            remove_tag(tag.file)

        if options.mb_id:
            set_mb_data(tag, mb_data)

        if options.cue_file:
            set_from_cue(tag, cue_data)

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

        if options.Number:
            tag.number = int(options.Number)

        if not options.mb_id and options.cap_tag:
            tag.lower_articles()

        if not options.mb_id and options.cap_all:
            tag.capitalize()

    if options.mb_guess:
        guess_mb_release(tag_list)

    if options.rename:
        rename_files(tag_list)

    for tag in tag_list:
        tag.write_tag()

if __name__ == "__main__":
    main()
