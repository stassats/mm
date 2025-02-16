#!/usr/bin/python
# -*- coding: utf-8 -*-

# This software is in the public domain and is
# provided with absolutely no warranty.

# Requires PythonMusicBrainz2, python-musicbrainzngs, mutagen

import os
import sys
import time
import re
import string

#import musicbrainz2.webservice as ws
import musicbrainzngs as m
from optparse import OptionParser

from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.easyid3 import EasyID3
from mutagen.easyid3 import EasyID3
import mutagen.id3
from mutagen.musepack import Musepack
from mutagen.easymp4 import EasyMP4 as MP4
from mutagen.wavpack import WavPack
from mutagen.apev2 import APEv2

####

#q = ws.Query()
m.set_useragent("Example music app", "0.1", "http://example.com/music")

class Tag:
    artist = None
    title = None
    album = None
    year = None
    number = None
    file = None

    def __init__(self, file=None):
        if file:
           self.read_tag(file)

    def read_tag(self, file):
        self.file = file
        audio = open_file(file)

        if 'artist' in audio:
            self.artist = audio['artist'][0]

        if 'title' in audio:
            self.title = audio['title'][0]

        if 'album' in audio:
            self.album = audio['album'][0]

        if 'date' in audio:
            self.year = audio['date'][0]

        if 'tracknumber' in audio:
            self.number = int(audio['tracknumber'][0].partition('/')[0])

        audio.save()
        return self

    def write_tag(self):
        audio = open_file(self.file)

        if self.artist:
            audio['artist'] = ensure_unicode(self.artist).replace('‐', '-')

        if self.title:
            audio['title'] = ensure_unicode(self.title).replace('‐', '-').replace('`', "'").replace('’', "'")

        if self.album or self.album == "":
            audio['album'] = ensure_unicode(self.album).replace('‐', '-')

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
        title = os.path.splitext(os.path.basename(self.file))[0]
        title = title.replace('_', ' ')

        self.title = re.search(r'^(?:\d\d? )?(.+)', title).group(1)

    def set_number(self):
        title = os.path.basename(self.file)
        track = re.search(r'^\d\d?', title)

        if track:
            self.number = int(track.group())

    def set_album(self):
        album = os.path.basename(os.path.dirname(self.file))

        album = album.replace('_', ' ')

        album = re.search(r'^(\d\d\w? )?(.+?)( \d{4})?$', album)

        self.album = album.group(2)

    def set_year(self):
        year = os.path.basename(os.path.dirname(self.file))

        year = re.search(r'\d{4}$', year)

        if year:
            self.year = year.group()

    def display_tag(self):
        print("Artist:", self.artist)
        print("Title:", self.title)
        print("Album:", self.album)
        print("Year:", self.year)
        print("Tracknumber:", str(self.number))

class not_media_file(Exception):
    def __init__(self):
        pass

class not_album(Exception):
    def __init__(self):
        pass

########

junk = [(r"[\]\(\)`´':;,!|?=\/\"~*\\[«»]", ""),
        (r"[-_.\\\\ ]+", "_"),
        (r"&+", "_and_"),
        (r"@", "_at_"),
        (r"#", "_n"),
        (r"_+", "_"),
        (r"_$", ""),
        (r"^_", "")]

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

    articled_words = [words[0]] + list(map(articlify, words[1:-1]))
    if len(words) > 1:
        articled_words += [words[-1]]
    return ' '.join(articled_words)

def capitalize(str):
    if not str:
        return

    words = [word.capitalize() for word in str.split()]

    words = list(map(cap, words))

    return lower_articles(' '.join(words))

def get_file_ext(file):
    return os.path.splitext(file)[1][1:]

def rename_files(tags):
    for tag in tags:
        rename_file(tag, len(tags) > 9)

def ensure_unicode(x):
    return x

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
        print("WARNING: no track number in " + tag.file)

    new_name = ensure_unicode(os.path.dirname(tag.file)) + '/'
    new_name += remove_junk(track + ensure_unicode(tag.title))
    new_name += os.path.splitext(tag.file)[1]

    if new_name == tag.file:
        return

    if os.path.exists(new_name):
        print('WARNING: path', new_name, 'exists')
        return

    os.rename (tag.file, new_name)

    tag.file = new_name

def delete_ape_tag(file):
    if get_file_ext(file) == 'mp3':
        mutagen.apev2.delete(file)

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
    elif ftype == 'wv':
        audio = WavPack(file)
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
    delete_ape_tag(file)

def read_tags(file_list):
    tag_list = []

    for file in file_list:
        try:
            tag_list.append(Tag(file))
        except not_media_file:
            print(file, "is not a media file!")
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
    id, disc_id = re.search(r'^(?:https://.+/)?(.+?)(?:#disc(\d+))?$', id).groups()

    try:
        release = m.get_release_by_id(id, ['artists','recordings','artist-credits'])['release']

    except m.MusicBrainzError as xxx_todo_changeme:
        exceptions.e = xxx_todo_changeme
        print('Error:', exceptions.e)
        sys.exit(1)

    return parse_mb_release(release, disc_id)

def set_mb_data(tag, mb_data):
    track_number = tag.number
    print(len(mb_data))
    if track_number < len(mb_data):
        tag.album = mb_data[0]
        tag.artist, tag.title = mb_data[tag.number]
    else:
        print('WARNING: there is no track', track_number, 'in this MusicBrainz release')

def mb_get_artist(release):
    for x in release['artist-credit']:
        if x['artist']:
            return x['artist']['name']

def mb_get_tracks(release, disc_id):
    for disc in release['medium-list']:
        if disc['position'] == disc_id:

            return disc['track-list']

    return release['medium-list'][0]['track-list']

def parse_mb_release(release, disc_id=None):
    result = [release['title']]
    release_artist = mb_get_artist(release)

    for track in mb_get_tracks(release, disc_id):
        recording = track['recording']
        artist = recording['artist-credit-phrase'] or release_artist

        result.append([artist, recording['title']])

    return result

# def mb_request(name, *args, **kwargs):
#     while True:
#         try:
#             # MB doesn't like more than one request per second
#             time.sleep(1)
#             return name(*args, **kwargs)
#         except ws.WebServiceError as exception:
#             if exception.msg and exception.msg.find("503"):
#                 print("WARNING: 503")
#                 time.sleep(1)
#             else:
#                 raise(exception)

# class SearchResult:
#     id = None
#     artist = None
#     title = None
#     score = 0

#     def set_from_mb(self, mb_release):
#         release = mb_release.release
#         self.id = release.id
#         self.score = mb_release.score
#         self.artist = release.artist.name
#         self.title = release.title
#         self.tracks = mb_request(q.getReleaseById,
#                                  release.id,
#                                  ws.ReleaseIncludes(tracks=True, artist=True))
#         return self

# def search_mb(query, tracks_count):
#     results = []
#     includes = ws.ReleaseIncludes(tracks=True, artist=True)

#     for result in mb_request(q.getReleases, query):
#         if result.release.tracksCount == tracks_count:
#             results.append(SearchResult().set_from_mb(result))

#     return results

def old_parse_mb_release(release):
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

def decode_utf8(x):
    return x
    
def guess_mb_release(tag_list):
    artist = get_tags_artist(tag_list)
    album = get_tags_album(tag_list)

    filter = ws.ReleaseFilter(query='%s and tracks:%d and artist:"%s"' \
                                  % (decode_utf8(album), len(tag_list), decode_utf8(artist)),
                              limit=7)

    releases = search_mb(filter, len(tag_list))
    res_len = len(releases)

    if res_len == 0:
        print("No releases found")
        return False
    else:
        print("Data from tags:", artist, '-', album, "[" + str(len(tag_list)), "tracks]\n")
        print("Variants from MusicBrainz:")

        for i in range(res_len):

            print(str(i + 1) + ")", releases[i].artist, '-', \
                releases[i].title, \
                "(" + str(releases[i].score), "%)")

            print(" Details:", releases[i].id + ".html\n")

        while True:
            a = input("Number of the release or a release id (zero for none): ")
            if not a.isdigit():
                mb_data = get_mb_data(a)
                break
            elif int(a) <= res_len and int(a) > -1:
                a = int(a)
                if a == 0: return False

                mb_data = old_parse_mb_release(releases[a - 1].tracks)
                break
            else:
                print("Must be a positive number less than %d" % res_len)

        for tag in tag_list:
            set_mb_data(tag, mb_data)
        return True

def find_track(tracks, number):
    for track in tracks:
        if track.number == number:
            return track

def set_from_cue(tag, cue_data):
    track = find_track(cue_data.tracks, tag.number)
    if not track:
        print("error, no track with such number in a cue file", str(tag.number))

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
            print(str(tag.number) + ".", tag.title)
        exit()

    if (len(sys.argv) - len(args) == 1):
        list(map(Tag.display_tag, tag_list))
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
            tag.album =options.Album

        if options.Title:
            tag.title = options.Title

        if options.Artist:
            tag.artist = options.Artist

        if options.Year:
            tag.year = options.Year

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
