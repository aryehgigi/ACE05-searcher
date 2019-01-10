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
    d2 = d.print_tree()
    for s in d2:
        print_mod(s)

def find_tree(text, out, g_index):
    d = nlp(text)
    
    for s2 in d.sents:
        out.append((s2.text, nlp(s2.text).print_tree(), g_index + text.find(s2.text), g_index + text.find(s2.text) + len(s2.text) - 1))
        # TODO - for debuging: print_mod(nlp(s2).print_tree())
    

# TODO - nlp line spliting might not be best for our text!
def bla(path):
    f = io.open(path, "r", encoding="utf-8").read()
    complete_text = f.strip().replace("\n", " ")
    pointer = 0
    ace_indices = 0
    the_friqin_list = []
    start_collecting = False
    copy_of_complete_text = complete_text
    while pointer != len(complete_text):
        match = re.search("<.*?>", copy_of_complete_text)
        found = copy_of_complete_text[match.start(): match.end()]
        
        if start_collecting:
            text_to_tree = copy_of_complete_text[:match.start()]
            text_to_tree = text_to_tree.rstrip()
            text_with_trail_spaces_len = len(text_to_tree)
            text_to_tree = text_to_tree.lstrip()
            spaces_len = text_with_trail_spaces_len - len(text_to_tree)
            if found == "</POSTER>" or found == "</SPEAKER>":
                the_friqin_list.append((text_to_tree, [], ace_indices + spaces_len, ace_indices + spaces_len + len(text_to_tree) - 1))
            elif len(text_to_tree) > 0:
                find_tree(text_to_tree, the_friqin_list, ace_indices + spaces_len)
        
        if found == "<TEXT>":
            start_collecting = True
        
        ace_indices += match.start()
        pointer += match.end()
        copy_of_complete_text = copy_of_complete_text[match.end():]
    
    return the_friqin_list
    #
    # c = re.sub('<.*?>', '', aaa)  # has correct inditing, TODO - use it
    # m = re.search("(?<=<TEXT>).", aaa)
    # import pdb;pdb.set_trace()
    # m.group(0)
    # m.start()
    # m.end()
    # only_analyze = re.sub('\s*<QUOTE PREVIOUSPOST.*?>\s*', '. ', re.split("<TEXT>", aaa)[1])
    # text1 = [re.sub('\s*<.*?>\s*', '', s) for s in re.findall("</SPEAKER>.*?</TURN>", only_analyze)]
    # posters = [re.sub('\s*<.*?>\s*', '', s) for s in re.findall("<POSTER>.*?</POSTER>", only_analyze)]
    # postdates = [re.sub('\s*<.*?>\s*', '', s) for s in re.findall("<POSTDATE>.*?</POSTDATE>", only_analyze)]
    # subjects = [re.sub('\s*<.*?>\s*', '', s) for s in re.findall("<SUBJECT>.*?</SUBJECT>", only_analyze)]
    # text2 = [re.sub('\s*<.*?>\s*', '', s) for s in re.findall("</SUBJECT>.*?</POST>", only_analyze)]
    # text3 = []
    # if not text2:
    #     text3 = [re.sub('\s*<.*?>\s*', '', s) for s in re.findall("</POSTDATE>.*?</POST>", only_analyze)]
    #
    # for doc_portion in (posters + postdates + subjects + text1 + text2 + text3):
    #     print_my_tree(doc_portion)

import pdb;pdb.set_trace()
l1 = bla("C:/Users/inbaryeh/PycharmProjects/ace05_parser/data/bc/timex2norm/CNN_CF_20030303.1900.00.sgm")
l2 = bla("C:/Users/inbaryeh/PycharmProjects/ace05_parser/data/un/timex2norm/alt.atheism_20041104.2428.sgm")

# TODO
# 1. rewrite for speed up
# 2. on all docs, and combine the rest of the algo
# 3. nlp sentence breaking bug
