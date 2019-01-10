import io
import re
import spacy
nlp = spacy.load('en_core_web_sm')


def print_mod(cur, count=0):
    if len(cur['modifiers']) == 0:
        print('\t' * count + '<--- ' + cur['arc'] + ' \"' + cur['word'] + '\"')
    else:
        print('\t' * count + '<--- ' + cur['arc'] + ' \"' + cur['word'] + '\"')
        for mi in cur['modifiers']:
            print_mod(mi, count + 1)


# example:
# print_my_tree(u"She tries to blame the U.S. and other members of the Security Council for not sending enough troops to stop it")
def print_my_tree(text):
    d = nlp(text)
    
    # printing sentence splitting
    for s2 in d.sents:
        print(s2)

    # printing trees for all sentences
    d2 = d.print_tree()
    for s in d2:
        print_mod(s)


# TODO - nlp line spliting might not be best for our text!
def bla(path):
    f = io.open(path, "r", encoding="utf-8").read()
    a = f.strip().replace("\n", " ")
    c = re.sub('<.*?>', '', a)  # has correct inditing, TODO - use it
    only_analyze = re.sub('\s*<QUOTE PREVIOUSPOST.*?>\s*', ' QUOTE. ', re.split("<TEXT>", a)[1])
    text1 = [re.sub('\s*<.*?>\s*', '', s) for s in re.findall("</SPEAKER>.*?</TURN>", only_analyze)]
    posters = [re.sub('\s*<.*?>\s*', '', s) for s in re.findall("<POSTER>.*?</POSTER>", only_analyze)]
    postdates = [re.sub('\s*<.*?>\s*', '', s) for s in re.findall("<POSTDATE>.*?</POSTDATE>", only_analyze)]
    subjects = [re.sub('\s*<.*?>\s*', '', s) for s in re.findall("<SUBJECT>.*?</SUBJECT>", only_analyze)]
    text2 = [re.sub('\s*<.*?>\s*', '', s) for s in re.findall("</SUBJECT>.*?</POST>", only_analyze)]
    text3 = []
    if not text2:
        text3 = [re.sub('\s*<.*?>\s*', '', s) for s in re.findall("</POSTDATE>.*?</POST>", only_analyze)]
    
    for doc_portion in (posters + postdates + subjects + text1 + text2 + text3):
        print_my_tree(doc_portion)


bla("C:/Users/inbaryeh/PycharmProjects/ace05_parser/data/un/timex2norm/alt.atheism_20041104.2428.sgm")
