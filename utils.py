import io
import re
import spacy

nlp = spacy.load('en_core_web_sm')

relation_options = {
    'Near': ['PER-FAC', 'PER-GPE', 'PER-LOC', 'FAC-FAC', 'FAC-GPE', 'FAC-LOC', 'GPE-FAC', 'GPE-GPE', 'GPE-LOC', 'LOC-FAC', 'LOC-GPE', 'LOC-LOC'],
    'Located': ['PER-FAC', 'PER-GPE', 'PER-LOC'],
    'Business': ['PER-PER'],
    'Family': ['PER-PER'],
    'Lasting-Personal': ['PER-PER'],
    'Geographical': ['FAC-FAC', 'FAC-GPE', 'FAC-LOC', 'GPE-FAC', 'GPE-GPE', 'GPE-LOC', 'LOC-FAC', 'LOC-GPE', 'LOC-LOC'],
    'Subsidiary': ['ORG-ORG', 'ORG-GPE'],
    'Artifact': ['VEH-VEH', 'WEA-WEA'],
    'Employment': ['PER-ORG', 'PER-GPE'],
    'Ownership': ['PER-ORG'],
    'Founder': ['PER-ORG', 'PER-GPE', 'ORG-ORG', 'ORG-GPE'],
    'Student-Alum': ['PER-ORG'],
    'Sports-Affiliation': ['PER-ORG'],
    'Investor-Shareholder': ['PER-ORG', 'PER-GPE', 'ORG-ORG', 'ORG-GPE', 'GPE-ORG', 'GPE-GPE'],
    'Membership': ['PER-ORG', 'ORG-ORG', 'GPE-ORG'],
    'User-Owner-Inventor-Manufacturer': ['PER-WEA', 'PER-VEH', 'PER-FAC', 'ORG-WEA', 'ORG-VEH', 'ORG-FAC', 'GPE-WEA', 'GPE-VEH', 'GPE-FAC'],
    'Citizen-Resident-Religion-Ethnicity': ['PER-PER', 'PER-LOC', 'PER-GPE', 'PER-ORG'],
    'Org-Location-Origin': ['ORG-LOC', 'ORG-GPE']}

# relation_options = {
# "Near": (["PER", "FAC", "GPE", "LOC"], ["FAC", "GPE", "LOC"]),
# "Located": (["PER"], ["FAC", "GPE", "LOC"]),
# "Business": (["PER"], ["PER"]),
# "Family": (["PER"], ["PER"]),
# "Lasting-Personal": (["PER"], ["PER"]),
# "Geographical": (["FAC", "GPE", "LOC"], ["FAC", "GPE", "LOC"]),
# "Subsidiary": (["ORG"], ["ORG", "GPE"]),
# "Artifact_a": (["VEH"], ["VEH"]),
# "Artifact_b": (["WEA"], ["WEA"]),
# "Employment": (["PER"], ["ORG", "GPE"]),
# "Ownership": (["PER"], ["ORG"]),
# "Founder": (["PER", "ORG"], ["ORG", "GPE"]),
# "Student-Alum": (["PER"], ["ORG"]),
# "Sports-Affiliation": (["PER"], ["ORG"]),
# "Investor-Shareholder": (["PER", "ORG", "GPE"], ["ORG", "GPE"]),
# "Membership": (["PER", "ORG", "GPE"], ["ORG"]),
# "User-Owner-Inventor-Manufacturer": (["PER", "ORG", "GPE"], ["WEA", "VEH", "FAC"]),
# "Citizen-Resident-Religion-Ethnicity": (["PER"], ["PER", "LOC", "GPE", "ORG"]),
# "Org-Location-Origin": (["ORG"], ["LOC", "GPE"])}


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
                the_friqin_list.append(
                    (text_to_tree, [], ace_indices + spaces_len, ace_indices + spaces_len + len(text_to_tree) - 1))
            elif len(text_to_tree) > 0:
                find_tree(text_to_tree, the_friqin_list, ace_indices + spaces_len)
        
        if found == "<TEXT>":
            start_collecting = True
        
        ace_indices += match.start()
        pointer += match.end()
        copy_of_complete_text = copy_of_complete_text[match.end():]
    
    return the_friqin_list


l1 = bla("C:/Users/inbaryeh/PycharmProjects/ace05_parser/data/bc/timex2norm/CNN_CF_20030303.1900.00.sgm")
l2 = bla("C:/Users/inbaryeh/PycharmProjects/ace05_parser/data/un/timex2norm/alt.atheism_20041104.2428.sgm")

# TODO
# 1. rewrite for speed up
# 2. on all docs, and combine the rest of the algo
# 3. nlp sentence breaking bug
