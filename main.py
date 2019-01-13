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
from enum import Enum
from collections import namedtuple
from pathlib import Path
import multiprocessing
import xml.etree.ElementTree as ET

port_inc = 5000
output_counter = 0
data_types = ['bc', 'bn', 'wl', 'un', 'nw', 'cts']
Entity = namedtuple("Entity", "id type start end head extent")
Relation = namedtuple("Entity", "rel_type data_type orig colored_text")
Sentence = namedtuple("Sentence", "text tree start end")
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
        docs.append(nlp(relations[line][Relation.orig]))
    
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
        print(str(i) + '(' + relation[Relation.data_type] + '). ' + relation[Relation.colored_text])


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


def find_tree(text, out, g_index):
    d = nlp(text)
    
    for s2 in d.sents:
        out.append(Sentence(s2.text, nlp(s2.text).print_tree(), g_index + text.find(s2.text), g_index + text.find(s2.text) + len(s2.text) - 1))
        # TODO - for debugging: print_mod(nlp(s2).print_tree())


def break_sgm(path):
    import spacy
    nlp = spacy.load('en_core_web_sm')
    
    f = io.open(path, "r", encoding="utf-8").read()
    complete_text = f.strip().replace("\n", " ")
    pointer = 0
    ace_indices = 0
    sentences = []  # list of (sentence, syntax_tree, ace_start_position, ace_end_position) elements
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
                sentences.append(
                    Sentence(text_to_tree, [], ace_indices + spaces_len, ace_indices + spaces_len + len(text_to_tree) - 1))
            elif len(text_to_tree) > 0:
                find_tree(text_to_tree, sentences, ace_indices + spaces_len)
        
        if found == "<TEXT>":
            start_collecting = True
        
        ace_indices += match.start()
        pointer += match.end()
        copy_of_complete_text = copy_of_complete_text[match.end():]
    
    return sentences


def check_rule(tree, lhs, rhs):
    # TODO
    return True


def main_rule(subtype, sgm_path, entities, relations, counters):
    sentences = break_sgm(sgm_path)
    prev_entity_index = 0
    entity_index = 0

    for sentence in sentences:
        in_sentence = True
        
        while in_sentence:
            if entities[entity_index].start > sentence.end:
                in_sentence = False
            else:
                assert(entities[entity_index].end <= sentence.end)
                entity_index += 1
        
        for lhs in entities[prev_entity_index: entity_index]:
            for rhs in entities[prev_entity_index: entity_index]:
                if lhs.id == rhs.id:
                    continue
                if (lhs.type + "-" + rhs.type) in relation_arg_combos[subtype]:
                    pair = (lhs.id, rhs.id)
                    did_match = check_rule(sentence.tree, lhs, rhs)
                    if did_match:
                        if pair not in relations:
                            counters[Counters.FPN] += 1
                        elif relations[pair].type == subtype:
                            counters[Counters.TP] += 1
                        else:
                            counters[Counters.FPO] += 1
                    else:  # did not match
                        if pair not in relations:
                            counters[Counters.TNN] += 1
                        elif relations[pair].type == subtype:
                            counters[Counters.FN] += 1
                        else:
                            counters[Counters.TNO] += 1
        
        prev_entity_index = entity_index


# TODO - fix
def extract_metonymy(relation, entities, data_type, path):
    global output_counter
    head_start = 0
    head_start2 = 0
    head_end = 0
    head_end2 = 0

    output_counter += 1
    
    for cur_child in relation:
        if cur_child.tag == 'relation_argument' and cur_child.attrib['ROLE'] == 'Arg-1':
            head_start, head_end = entities[cur_child.attrib['REFID']]
        elif cur_child.tag == 'relation_argument' and cur_child.attrib['ROLE'] == 'Arg-2':
            head_start2, head_end2 = entities[cur_child.attrib['REFID']]
    
    sgm = open(path.replace('apf.xml', 'sgm')).read()
    sgm = re.sub('<.*?>', '', sgm)
    first = "{0}\033[1;31;0m{1}\033[0m{2}".format(sgm[sgm.rfind('\n', 0, head_start): head_start],
                                                      sgm[head_start: head_end + 1],
                                                      sgm[head_end + 1: sgm.find('\n', head_end, len(sgm))])
    second = "{0}\033[1;31;0m{1}\033[0m{2}".format(sgm[sgm.rfind('\n', 0, head_start2): head_start2],
                                                       sgm[head_start2: head_end2 + 1],
                                                       sgm[head_end2 + 1: sgm.find('\n', head_end2, len(sgm))])
    
    print(str(output_counter) + '(' + data_type + '). ' + "..." + first.replace('\n', '') + "..." + " <--> " + "..." + second.replace('\n', '') + "...")
    return


def extract_relations(xml_relation, entities, rel_type, data_type, relations):
    global output_counter
    start = 0
    head_start = 0
    head_start2 = 0
    head_end = 0
    head_end2 = 0
    
    original_sentence = ''
    
    for cur_child in xml_relation:
        if cur_child.tag == 'relation_mention':
            output_counter += 1
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
            relations[(arg1_id, arg2_id)] = rel_type, data_type, original_sentence, colored_text.replace('\n', ' ')


def extract_doc(root, data_type, path):
    entities_by_id = {}
    entities_by_idx = []
    relations_by_pair = {}
    
    # store all entity mentions in a {ID:(start,end)} dict, and Entity ordered list
    for child in root[0]:
        if child.tag == 'entity':
            for entity_mentions in child:
                for entity_mention in entity_mentions:
                    if entity_mention.tag == 'head':
                        assert(entity_mention[0].tag == 'charseq')
                        entities_by_id[entity_mentions.attrib['ID']] =\
                            int(entity_mention[0].attrib['START']), int(entity_mention[0].attrib['END'])
                        # for metonymy
                        entities_by_id[child.attrib['ID']] =\
                            int(entity_mention[0].attrib['START']), int(entity_mention[0].attrib['END'])
                        entities_by_idx.append(Entity(
                            entity_mention.attrib['ID'],
                            child.attrib['TYPE'],
                            entity_mention[1].attrib['START'],
                            entity_mention[1].attrib['END'],
                            entity_mention[1][0].text,
                            entity_mention[0][0].text
                        ))
    
    for child in root[0]:
        if child.tag == 'relation':
            extract_relations(
                child, entities_by_id, 'None' if 'SUBTYPE' not in child.attrib else child.attrib['SUBTYPE'], data_type, relations)
    
    return entities_by_idx, relations_by_pair


def walk_all(subtype, path, wanted_relation_list, counters):
    for subdir, dirs, files in os.walk(path):
        if 'timex2norm' in subdir:
            for filename in files:
                if filename.endswith(".apf.xml"):
                    tree = ET.parse(subdir + os.sep + filename)
                    root = tree.getroot()
                    data_type = [i for i in data_types if (os.sep + i + os.sep) in subdir]
                    assert(len(data_type) == 1)
                    data_type = data_type[0]
                    entities, relations_by_pair = extract_doc(root, data_type, subdir + os.sep + filename)
                    for relation in relations_by_pair.values():
                        if relation[Relation.type] == subtype:
                            wanted_relation_list.append(relation)
                    main_rule(subtype, (subdir + os.sep + filename).replace('apf.xml', 'sgm'), entities, relations_by_pair, counters)


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
    if not cmd_subtype:
        subtype = get_subtype()
    else:
        subtype = cmd_subtype if cmd_subtype != 'None' else None
    
    found = False
    for i, (cur_type, subtypes) in relation_types.items():
        if subtype in subtypes:
            print_type(cur_type, subtype if subtype is not None else 'None')
            found = True
    if not found:
        print_usage()
        return
    
    relations = {}
    counters = [0] * 6
    walk_all(subtype, path, relations, counters)
    print_statistics(counters)
    print_relations(relations)
    dep_views(relations)


if __name__ == "__main__":
    if len(sys.argv) == 2:
        main(sys.argv[1])
    elif len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        print_usage()
