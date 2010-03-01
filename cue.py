import ply.lex as lex
import os

tokens = ('STRING', 'NUMBER', 'REM', 'DATE', 'FLAG',
          'TAG', 'TRACK', 'FILE_MODE', 'FILE', 'MODE', 'INDEX')

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

t_TAG=r'(TITLE)|(PERFORMER)|(SONGWRITER)|(COMPOSER)| \
(ARRANGER)|(GENRE)|(CATALOG)|(PREGAP)|(FLAGS)'
t_MODE=r'(AUDIO)'
t_FILE_MODE=r'(WAVE)'
t_FLAG=r'(DCP)'

rem_exceptions = ['DATE']

def t_REM(t):
    r'REM\s*(.*)'

    remaining = t.lexer.lexmatch.group(5)
    [first_word, rest] = remaining.split(None,1)

    if first_word in rem_exceptions:
        t.type = first_word
        t.value = first_word
        t.lexer.lexpos -= len(rest)
        return t
    else:
        pass

t_ignore  = ' \t'

def t_newline(t):
    r'((\r\n)|\n)+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    print "Illegal character '%s'" % t.value[0]
    t.lexer.skip(1)

lexer = lex.lex()

# Yacc

import ply.yacc as yacc

def p_expression_cue(p):
    'expression : tag file'
    p[0] = (p[1], p[2])

def p_tag_index(p):
    '''tag : INDEX NUMBER NUMBER ':' NUMBER ':' NUMBER'''
    p[0] = [(p[1], (p[2], p[3], p[5], p[7]))]

def p_tag_date(p):
    'tag : DATE NUMBER'
    p[0] = [('date', p[2])]

def p_tag_1(p):
    '''tag : TAG STRING
           | TAG NUMBER
           | TAG FLAG'''
    p[0] = [(p[1].lower(), p[2])]

def p_tag_2(p):
    '''tag : tag tag'''
    p[0] = p[1] + p[2]

def p_file_1(p):
    '''file : FILE STRING FILE_MODE track'''
    p[0] = p[4]

def p_file_2(p):
    '''file : file file'''
    p[0] = p[1] + p[2]

def p_track_1(p):
    '''track : TRACK NUMBER MODE tag'''

    p[0] = [[('number', p[2])] + p[4]]

def p_track_2(p):
    '''track : track track'''
    p[0] = p[1] + p[2]

def p_error(p):
    print "Syntax error in:", p

parser = yacc.yacc(debug=0, outputdir=os.path.dirname(__file__))

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

def parse_cue(file):
    with open(file) as file:
        return fill_objects(parser.parse(file.read()))
