# TODO's:
# 1. many function are ACE specific, generalize
# 2. some places are not written very smart pythonicaly speaking
# 3. replace ascii art
# 4. maybe replace the entire displacy idea, either all in web or all in CLI but not half-half.
# 5. rewrite for speed up
# 6. nlp sentence breaking bug

import os
import sys
import io
import re
import operator
from enum import Enum
from collections import namedtuple
from pathlib import Path
import multiprocessing
import xml.etree.ElementTree as ET

port_inc = 5000
data_types = ['bc', 'bn', 'wl', 'un', 'nw', 'cts']
Entity = namedtuple("Entity", "id type start end head extent")
Relation = namedtuple("Relation", "rel_type data_type orig colored_text")
Sentence = namedtuple("Sentence", "span start end")
relation_types = {0: ('ART', ['User-Owner-Inventor-Manufacturer']),
         1: ('GEN-AFF', ['Citizen-Resident-Religion-Ethnicity', 'Org-Location']),
         2: ('METONYMY', [None]),
         3: ('ORG-AFF', ['Employment', 'Founder', 'Ownership', 'Student-Alum', 'Sports-Affiliation', 'Investor-Shareholder', 'Membership']),
         4: ('PART-WHOLE', ['Artifact', 'Geographical', 'Subsidiary']),
         5: ('PER-SOC', ['Business', 'Family', 'Lasting-Personal']),
         6: ('PHYS', ['Located', 'Near'])}
relation_arg_combos = {
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
# (list_arg1, list_arg2): (same_verb, arg1_from_left, arg2_from_right, arg1_before_arg2)
rule_paths = {
    ("nsubj", "prep-pobj"): (False, True, True, True),
    ("nsubjpass", "prep-pobj") : (False, True, True, True),
    ("nsubj", "dobj") : (False, True, True, True),
    ("nsubj", "advmod") : (True, True, True, True),
    ("dobj", "dobj") : (False, False, False, False),
    ("poss-attr", "prep-pobj") : (False, True, True, True),
    ("pobj", "nsubj") : (True, False, False, False),
    ("nsubj", "nsubj") : (False, False, False, False),
    ("nsubj", "poss-prep-nsubj") : (False, False, False, False),
    ("dobj", "nsubjpass") : (False, True, False, False)
}

class Counters(Enum):
    TP = 0,
    FN = 1,
    FPN = 2,
    FPO = 3,
    TNO = 4,
    TNN = 5


def threaded_displacy(docs, port):
    import sys
    import os
    import spacy
    sys.stdout = open(os.devnull, 'w')
    spacy.displacy.serve(docs, style='dep', options={'compact': True}, port=port)


def dep_view(relations):
    global port_inc
    import spacy
    
    lines = input("Choose line numbers (space separated), for comparision.\n")
    if lines == 'Q':
        return True, None
    lines =[int(num) for num in lines.split()]
    
    nlp = spacy.load('en_core_web_sm')
    docs = []
    for line in lines:
        docs.append(nlp(relations[line - 1].orig))
    
    p = multiprocessing.Process(target=threaded_displacy, args=[docs, port_inc])
    p.start()
    port_inc += 1
    return False, p


def dep_views(relations):
    finished = False
    processes = []
    while not finished:
        finished, p = dep_view(relations)
        if not finished:
            processes.append(p)
    not_interesting = [process.terminate for process in processes]


def print_relations(relations):
    for i, relation in enumerate(relations):
        print(str(i + 1) + '(' + relation.data_type + '). ' + relation.colored_text)


def print_statistics(counters):
    print("Recall: %.2f" % (counters[Counters.TP] / (counters[Counters.TP] + counters[Counters.FN])))
    print("Precision: %.2f" % (counters[Counters.TP] / (counters[Counters.TP] + counters[Counters.FPO] + counters[Counters.FPN])))
    print("FPR(other relations): %.2f" % (counters[Counters.FPO] / (counters[Counters.FPO] + counters[Counters.TNO])))
    print("FPR(non relations): %.2f" % (counters[Counters.FPN] / (counters[Counters.FPN] + counters[Counters.TNN])))


def print_mod(cur, count=0):
    if len(cur['modifiers']) == 0:
        print('\t' * count + '<--- ' + cur['arc'] + ' \"' + cur['word'] + '\"')
    else:
        print('\t' * count + '<--- ' + cur['arc'] + ' \"' + cur['word'] + '\"')
        for mi in cur['modifiers']:
            print_mod(mi, count + 1)


def print_my_tree(unicode_text):
    import spacy
    nlp = spacy.load('en_core_web_sm')
    d = nlp(unicode_text)
    d2 = d.print_tree()
    for s in d2:
        print_mod(s)


def find_tree(text, out, g_index, nlp):
    d = nlp(text)

    for span in d.sents:
        out.append(Sentence(span, g_index + text.find(span.text), g_index + text.find(span.text) + len(span.text) - 1))


def break_sgm(path, nlp):
    f = io.open(path, "r", encoding="utf-8").read()
    complete_text = f.strip().replace("\n", " ")
    pointer = 0
    ace_indices = 0
    sentences = []  # list of (sentence, syntax_tree, ace_start_position, ace_end_position) elements
    start_collecting = False
    copy_of_complete_text = complete_text
    relevant_text = []
    while pointer != len(complete_text):
        match = re.search("<.*?>", copy_of_complete_text)
        found = copy_of_complete_text[match.start(): match.end()]
        
        if start_collecting:
            text_to_tree = copy_of_complete_text[:match.start()]
            text_to_tree = text_to_tree.rstrip()
            text_with_trail_spaces_len = len(text_to_tree)
            text_to_tree = text_to_tree.lstrip()
            spaces_len = text_with_trail_spaces_len - len(text_to_tree)
            if len(text_to_tree) != 0 and found not in ["</POSTER>", "</SPEAKER>", "</POSTDATE>", "</SUBJECT>"]:
                find_tree(text_to_tree, sentences, ace_indices + spaces_len, nlp)
                # relevant_text.append((text_to_tree, ace_indices + spaces_len))
                # sentences.append(
                #     Sentence(text_to_tree, [], ace_indices + spaces_len, ace_indices + spaces_len + len(text_to_tree) - 1))
            # elif len(text_to_tree) > 0:
        
        if found == "<TEXT>":
            start_collecting = True
        
        ace_indices += match.start()
        pointer += match.end()
        copy_of_complete_text = copy_of_complete_text[match.end():]
    
    # i = 0
    # pointer = 0
    # broken_sentences = nlp(u" ".join([text for (text, start) in relevant_text]).replace(" \"", " {").replace("\" ", "} ").replace(" ... ", " ~#*"))
    # for broken_sentence in broken_sentences.sents:
    #     text_to_copy = broken_sentence.text.replace(" {", " \"").replace("} ", "\" ").replace("}", "\"").replace("{", "\"").replace("~#*", "... ")
    #     find_pos = relevant_text[i][0][pointer:].find(text_to_copy)
    #     if find_pos == -1:
    #         i += 1
    #         pointer = 0
    #         sentence_start = relevant_text[i][1]
    #     else:
    #         sentence_start = relevant_text[i][1] + pointer + find_pos
    #     sentences.append(Sentence(text_to_copy, [], sentence_start, sentence_start + len(text_to_copy) - 1))
    #     pointer += len(text_to_copy)
    return sentences


def check_rule(sentence, arg1, arg2):
    arg1_word = None
    arg2_word = None
    for word in sentence.span:
        if arg1.start == word.idx + sentence.start:
            arg1_word = word
        if arg2.start == word.idx + sentence.start:
            arg2_word = word
    
    # find arg1 first verb
    list_of_arg1_arcs = []
    w = arg1_word
    while w.pos != "VERB":
        list_of_arg1_arcs.append(w.dep_)
        w = w.head
    # find arg2 first verb
    list_of_arg2_arcs = []
    w = arg2_word
    while w.pos != "VERB":
        list_of_arg2_arcs.append(w.dep_)
        w = w.head
    # check if valid paths to verbs by rule table
    if ("-".join(list_of_arg1_arcs), "-".join(list_of_arg2_arcs)) in rule_paths:
        verb1 = list_of_arg1_arcs[-1]
        verb2 = list_of_arg2_arcs[-1]
        
        # get the value of that dict which is the indicator for same verb
        should_be_same_verb, should_arg1_from_left, should_arg2_from_right, should_arg1_before_arg2 =\
            rule_paths[(list_of_arg1_arcs, list_of_arg2_arcs)]
        if should_be_same_verb:
            # validate its the same verb
            if verb1 != verb2:
                return False
        else:
            # check if their path is valid
            verbs = [verb1]
            found_good_path = False
            w = verb1
            while w.dep_ != "ROOT":
                if (w.dep_ not in ["xcomp", "ccomp", "conj", "dep", "advcl", "relcl"]) and not ((w.dep_ == "prep") and (w.head.dep_ == "pcomp")):
                    return False
                w = w.head
                if w == verb2:
                    found_good_path = True
                    break
                verbs.append(w)
            
            if not found_good_path:
                w = verb2
                while w.dep_ != "ROOT":
                    if (w.dep_ not in ["xcomp", "ccomp", "conj", "dep", "advcl", "relcl"]) and not ((w.dep_ == "prep") and (w.head.dep_ == "pcomp")):
                        return False
                    w = w.head
                    if w in verbs:
                        break
        
        if should_arg1_from_left and (verb1.idx < arg1_word.idx):
            return False
        
        if should_arg2_from_left and (verb2.idx < arg2_word.idx):
            return False
        
        if should_arg1_before_arg2 and (arg1_word.idx > arg2_word.idx):
            return False
    
    return True
    # verbal = []
    # level = 0
    # # TODO build verbal using BFS
    # bfs()
    #
    # # assume we get a head list from one to the other, or from both to common ancestor
    # if arg1_word.is_ancestor(arg2_word):
    #
    # elif arg2_word.is_ancestor(arg1_word):
    #
    # else:
    #     lca = list(set(arg1_word.ancestors) & set(arg1_word.ancestors))[0]
    #
    #     children
    #     head
    #     left_edge
    #     lefts
    #     right_edge
    #     rights
    #     n_lefts
    #     n_rights
    #     subtree
    #     dep_
    #
    # # test the rule
    # is_arg1_left = arg1.start > arg2.start
    # # if (((arg1_word.dep_ in ["nsubj", "nsubjpass", "poss"] and is_arg1_left) or (arg1_word.dep_ in ["nsubj", "dobj", "pobj"] and not is_arg1_left)) and
    # #     ((arg2_word.dep_ in ["nsubj", "nsubjpass", "poss", "advmod", "dobj"] and not is_arg1_left) or (arg2_word.dep_ in ["nsubj", "dobj", "pobj", "advmod"] and is_arg1_left)) and
    # #     )
    # if
    #     return True
    # else:
    #     return False


def main_rule(subtype, sgm_path, nlp, entities, relations, counters):
    sentences = break_sgm(sgm_path, nlp)
    prev_entity_index = 0
    entity_index = 0

    for sentence in sentences:
        in_sentence = True
        
        while in_sentence and entity_index < len(entities):
            if entities[entity_index].start > sentence.end:
                in_sentence = False
            else:
                if entities[entity_index].end > sentence.end:
                    print("Entity was broken by wrong sentence splitting:"
                          "\n\tFilePath=%s,\n\tEntityID=%s,\n\tSplitedSentence=%s" % (sgm_path, entities[entity_index].id, sentence.text))
                    del entities[entity_index]
                    continue
                entity_index += 1
        
        for arg1 in entities[prev_entity_index: entity_index]:
            for arg2 in entities[prev_entity_index: entity_index]:
                if arg1.id == arg2.id:
                    continue
                if (arg1.type + "-" + arg2.type) in relation_arg_combos[subtype]:
                    pair = (arg1.id, arg2.id)
                    did_match = check_rule(sentence, arg1, arg2)
                    if did_match:
                        if pair not in relations:
                            counters[Counters.FPN] += 1
                        elif relations[pair].rel_type == subtype:
                            counters[Counters.TP] += 1
                        else:
                            counters[Counters.FPO] += 1
                    else:  # did not match
                        if pair not in relations:
                            counters[Counters.TNN] += 1
                        elif relations[pair].rel_type == subtype:
                            counters[Counters.FN] += 1
                        else:
                            counters[Counters.TNO] += 1
        
        prev_entity_index = entity_index


# TODO - fix
# def extract_metonymy(relation, entities, data_type, path):
#     global output_counter
#     head_start = 0
#     head_start2 = 0
#     head_end = 0
#     head_end2 = 0
#
#     output_counter += 1
#
#     for cur_child in relation:
#         if cur_child.tag == 'relation_argument' and cur_child.attrib['ROLE'] == 'Arg-1':
#             head_start, head_end = entities[cur_child.attrib['REFID']]
#         elif cur_child.tag == 'relation_argument' and cur_child.attrib['ROLE'] == 'Arg-2':
#             head_start2, head_end2 = entities[cur_child.attrib['REFID']]
#
#     sgm = open(path.replace('apf.xml', 'sgm')).read()
#     sgm = re.sub('<.*?>', '', sgm)
#     first = "{0}\033[1;31;0m{1}\033[0m{2}".format(sgm[sgm.rfind('\n', 0, head_start): head_start],
#                                                       sgm[head_start: head_end + 1],
#                                                       sgm[head_end + 1: sgm.find('\n', head_end, len(sgm))])
#     second = "{0}\033[1;31;0m{1}\033[0m{2}".format(sgm[sgm.rfind('\n', 0, head_start2): head_start2],
#                                                        sgm[head_start2: head_end2 + 1],
#                                                        sgm[head_end2 + 1: sgm.find('\n', head_end2, len(sgm))])
#
#     print(str(output_counter) + '(' + data_type + '). ' + "..." + first.replace('\n', '') + "..." + " <--> " + "..." + second.replace('\n', '') + "...")
#     return


def extract_relations(xml_relation, entities, rel_type, data_type, relations):
    start = 0
    head_start = 0
    head_start2 = 0
    head_end = 0
    head_end2 = 0
    
    original_sentence = ''
    
    for cur_child in xml_relation:
        if cur_child.tag == 'relation_mention':
            arg1_id = -1
            arg2_id = -1
            for sub_rel_mention in cur_child:
                if sub_rel_mention.tag == 'extent':
                    assert(sub_rel_mention[0].tag == 'charseq')
                    original_sentence = sub_rel_mention[0].text
                    start = int(sub_rel_mention[0].attrib['START'])
                elif sub_rel_mention.tag == 'relation_mention_argument' and sub_rel_mention.attrib['ROLE'] == 'Arg-1':
                    head_start, head_end = entities[sub_rel_mention.attrib['REFID']]
                    arg1_id = sub_rel_mention.attrib['REFID']
                elif sub_rel_mention.tag == 'relation_mention_argument' and sub_rel_mention.attrib['ROLE'] == 'Arg-2':
                    head_start2, head_end2 = entities[sub_rel_mention.attrib['REFID']]
                    arg2_id = sub_rel_mention.attrib['REFID']
            
            first_head_start, last_head_start, first_head_end, last_head_end, first_color, second_color =   \
                (head_start, head_start2, head_end, head_end2, "\033[1;32;0m", "\033[1;31;0m")              \
                if head_start < head_start2 else                                                            \
                (head_start2, head_start, head_end2, head_end, "\033[1;31;0m", "\033[1;32;0m")
            
            colored_text =                                                                \
                original_sentence[:first_head_start - start] +                            \
                first_color +                                                             \
                original_sentence[first_head_start - start: first_head_end - start + 1] + \
                "\033[0m" +                                                               \
                original_sentence[first_head_end - start + 1: last_head_start - start] +  \
                second_color +                                                            \
                original_sentence[last_head_start - start: last_head_end - start + 1] +   \
                "\033[0m" +                                                               \
                original_sentence[last_head_end - start + 1:]
            if (arg1_id, arg2_id) in relations:
                if relations[(arg1_id, arg2_id)].rel_type == "Membership" and rel_type == "Employment":
                    continue
                elif relations[(arg1_id, arg2_id)].rel_type == "Employment" and rel_type == "Membership":
                    print("Notification: relation Employment was overridden by Membership of ID: %s" % cur_child.attrib["ID"])
                else:
                    print("Notification: bad duplicate found, ID: %s, Type: %s" % (cur_child.attrib["ID"], rel_type))
                    #import pdb;pdb.set_trace()  # TODO - remove this in the future
            relations[(arg1_id, arg2_id)] = Relation(rel_type, data_type, original_sentence.replace('\n', ' '), colored_text.replace('\n', ' '))


def extract_doc(root, data_type, path):
    entities_by_id = {}
    entities_by_idx = []
    relations_by_pair = {}
    
    # store all entity mentions in a {ID:(start,end)} dict, and Entity ordered list
    for child in root[0]:
        if child.tag == 'entity':
            for grandchild in child:
                if grandchild.tag == 'entity_mention':
                    entity_mention = grandchild
                    assert(
                        (entity_mention[0].tag == 'extent') and
                        (entity_mention[0][0].tag == 'charseq') and
                        (entity_mention[1].tag == 'head') and
                        (entity_mention[1][0].tag == 'charseq'))
                    extent = entity_mention[0][0].text
                    head = entity_mention[1][0].text
                    head_start = int(entity_mention[1][0].attrib['START'])
                    head_end = int(entity_mention[1][0].attrib['END'])
                    
                    entities_by_id[entity_mention.attrib['ID']] =\
                        int(head_start), int(head_end)
                    entities_by_id[child.attrib['ID']] =\
                        int(head_start), int(head_end)
                    entities_by_idx.append(Entity(
                        entity_mention.attrib['ID'], child.attrib['TYPE'], head_start, head_end, head, extent))
    
    # order the entities_by_idx by start and then by end
    entities_by_idx = sorted(entities_by_idx, key=operator.attrgetter('start', 'end'))
    
    # extract relations
    for child in root[0]:
        if child.tag == 'relation':
            extract_relations(
                child, entities_by_id, 'None' if 'SUBTYPE' not in child.attrib else child.attrib['SUBTYPE'], data_type, relations_by_pair)
    
    return entities_by_idx, relations_by_pair


def walk_all(subtype, path, wanted_relation_list, counters):
    import spacy
    nlp = spacy.load('en_core_web_sm')
    for subdir, dirs, files in os.walk(path):
        if 'timex2norm' in subdir:
            for filename in files:
                if filename.endswith(".apf.xml"):
                    tree = ET.parse(subdir + os.sep + filename)
                    root = tree.getroot()
                    data_type = [i for i in data_types if (os.sep + i + os.sep) in subdir]
                    assert(len(data_type) == 1)
                    data_type = data_type[0]
                    entities_by_idx, relations_by_pair = extract_doc(root, data_type, subdir + os.sep + filename)
                    for k, relation in relations_by_pair.items():
                        if relation.rel_type == subtype:
                            wanted_relation_list.append(relation)
                    main_rule(subtype, (subdir + os.sep + filename).replace('apf.xml', 'sgm'), nlp, entities_by_idx, relations_by_pair, counters)


def print_type(cur_type, subtype):
    print("Showing all search result for type=%s~subtype=%s:" % (cur_type, subtype))
    print("Legend: \033[1;32;0mhead of Arg-1\033[0m. \033[1;31;0mhead of Arg-2\033[0m.")
    print()


def get_subtype():
    query = "Choose a type (by number):\n"  \
            "1. ART(artifact)\n"            \
            "2. GEN-AFF(Gen-affiliation)\n" \
            "3. METONYMY\n"                 \
            "4. ORG-AFF(org-affiliation)\n" \
            "5. PART-WHOLE\n"               \
            "6. PER-SOC(person-social)\n"   \
            "7. PHYS(physical)\n"
    
    cur_type = None
    while cur_type not in range(7):
        cur_type = int(input(query)) - 1

    subtype = None
    if relation_types[cur_type][0] != 'METONYMY':
        query = "Choose a subtype (by number):\n"
        for i, subtype in enumerate(relation_types[cur_type][1]):
            query += (str(i + 1) + " " + subtype + "\n")
    
        while subtype not in range(len(relation_types[cur_type][1])):
            subtype = int(input(query)) - 1
    
    print_types(relation_types[cur_type][0], relation_types[cur_type][1][subtype] if subtype is not None else 'None')
    return relation_types[cur_type][1][subtype] if subtype is not None else None


def print_usage():
    print("Usage: main.py path_to_data [subtype|None]\n"
          "'None' means Metonymy.\n"
          "If you omit the subtype(or None), you will be prompt to input it afterwards.")


def main(path, cmd_subtype=None):
    import time
    start = time.time()
    if not cmd_subtype:
        subtype = get_subtype()
    else:
        subtype = cmd_subtype if cmd_subtype != 'None' else None
    
    meta_type = ""
    found = False
    for i, (cur_type, subtypes) in relation_types.items():
        if subtype in subtypes:
            meta_type = cur_type
            found = True
    if not found:
        print_usage()
        return
    
    relations = []
    counters = {Counters.TP: 0, Counters.FN: 0, Counters.TNN: 0, Counters.TNO: 0, Counters.FPN: 0, Counters.FPO: 0}
    walk_all(subtype, path, relations, counters)
    print_statistics(counters)
    print_type(meta_type, str(subtype))
    print_relations(relations)
    dep_views(relations)
    print("Run time: %.2f" % (time.time() - start))


if __name__ == "__main__":
    if len(sys.argv) == 2:
        main(sys.argv[1])
    elif len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        print_usage()
