import os
import ply.lex as lex
import ply.yacc as yacc

tokens = ('STRING', 'NUMBER', 'REM', 'DATE', 'ID',
          'TAG', 'TRACK', 'FILE', 'INDEX', 'PREGAP')

def t_STRING(t):
    r'"(.+)"'
    t.value = t.lexer.lexmatch.group(2)
    return t

def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)
    return t

literals = ':'

t_TRACK=r'TRACK'
t_FILE=r'FILE'

t_INDEX=r'INDEX'
t_PREGAP=r'PREGAP'

t_TAG=r'(TITLE)|(PERFORMER)|(SONGWRITER)|(COMPOSER)| \
(ARRANGER)|(CATALOG)|(FLAGS)|(ISRC)'

t_ID = '\w+'

rem_exceptions = ['DATE']

def t_REM(t):
    r'REM\s*(.*)'

    remaining = t.lexer.lexmatch.group(5)

    split = remaining.split(None, 1)
    if len(split) < 2:
        return
    first_word, rest = split

    if first_word in rem_exceptions:
        t.type = first_word
        t.value = first_word
        t.lexer.lexpos -= len(rest)
        return t

t_ignore  = ' \t'

def t_newline(t):
    r'((\r\n)|([^\r]?\n))+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    print "Illegal character '%s'" % t.value[0]
    t.lexer.skip(1)

# Yacc


def p_cue(p):
    'cue : tags tracks'
    p[0] = (p[1], p[2])

def p_tags(p):
    '''tags : tag
            | tags tag'''

    if len(p) == 3:
        if p[2]:
            p[0] = p[1] + [p[2]]
        else:
            p[0] = p[1]
    else:
        if p[1]:
            p[0] = [p[1]]

def p_tag(p):
    '''tag : TAG STRING
           | TAG NUMBER
           | TAG ID'''
    p[0] = (p[1].lower(), p[2])

def p_tag_file(p):
    '''tag : FILE STRING ID'''
    pass

def p_tag_pregap(p):
    '''tag : PREGAP NUMBER ':' NUMBER ':' NUMBER'''
    pass

def p_tag_index(p):
    '''tag : INDEX NUMBER NUMBER ':' NUMBER ':' NUMBER'''
    pass

def p_tag_date(p):
    'tag : DATE NUMBER'
    p[0] = ('date', p[2])

def p_tracks(p):
    '''tracks : track
              | tracks track'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = [p[1]]

def p_track(p):
    '''track : TRACK NUMBER ID tags'''
    p[0] = [('number', p[2])]

    if p[4]:
        p[0] += p[4]


def p_error(p):
    print "Syntax error in:", p

class Album:
    performer = None
    title = None
    tracks = None
    date = None

    def __init__(self):
        self.tracks = []

class Track:
    number = 0
    title = None
    performer = None

def fill_object(object, slots):
    for attr, value in slots:
        if hasattr(object, attr):
            setattr(object, attr, value)

    return object

def fill_objects(parsed_cue):
    if not parsed_cue:
        return

    album = Album()
    fill_object(album, parsed_cue[0])
    for track in parsed_cue[1]:
        album.tracks.append(fill_object(Track(), track))
    # for track in album.tracks:
    #     print track.title
    return album

lexer = lex.lex(debug=0)
parser = yacc.yacc(debug=0, outputdir=os.path.dirname(__file__))

def parse_cue(file):
    with open(file) as file:
        return fill_objects (parser.parse(file.read(), debug=0))
