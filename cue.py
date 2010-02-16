import ply.lex as lex

tokens = ('STRING', 'NUMBER', 'REM',
          'TAG', 'TRACK', 'FILE_MODE', 'FILE', 'MODE', 'INDEX')

t_STRING=r'(?<=").+(?=")'

def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)
    return t

literals = ':'

t_TRACK=r'TRACK'
t_FILE=r'FILE'

t_INDEX=r'INDEX'

t_TAG=r'(TITLE)|(PERFORMER)|(SONGWRITER)|(COMPOSER)|(ARRANGER)|(GENRE)'
t_MODE=r'(AUDIO)'
t_FILE_MODE=r'(WAVE)'

t_ignore_REM  = r'^REM.*'

t_ignore  = ' \t"'
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
    
def p_tag_1(p):
    '''tag : TAG STRING'''
    p[0] = [(p[1].lower(), p[2])]

def p_tag_2(p):
    '''tag : tag tag'''
    p[0] = p[1] + p[2]

def p_file_1(p):
    '''file : FILE STRING FILE_MODE track'''
    p[0] = (p[2], p[4])

def p_track_1(p):
    '''track : TRACK NUMBER MODE tag'''
    p[0] = [[('number', p[2])] + p[4]]

def p_track_2(p):
    '''track : track track'''
    p[0] = p[1] + p[2]
    
def p_error(p):
    print "Syntax error in:", p

parser = yacc.yacc()

class Album:
    performer = None
    title = None
    tracks = []

class Track:
    number = 0
    title = None
    performer = None

def fill_object(object, slots):
    for (attr, value) in slots:
        if hasattr(object, attr):
            setattr(object, attr, value)

    return object

def fill_objects(parsed_cue):
    album = Album()
    fill_object(album, parsed_cue[0])
    for track in parsed_cue[1][1]:
        album.tracks.append(fill_object(Track(), track))
    # for track in album.tracks:
    #     print track.number
    return album

def parse_cue(file):
    with open(file) as file:
        return fill_objects(parser.parse(file.read()))

#parse_cue("/home/stas/test.cue")    
