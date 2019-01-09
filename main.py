# TODO's:
# 1. many function are ACE specific, generalize
# 2. some places are not written very smart pythonicaly speaking
# 3. replace ascii art
# 4. maybe replace the entire displacy idea, either all in web or all in CLI but not half-half.

import os
import sys
import re
from pathlib import Path
import multiprocessing
import xml.etree.ElementTree as ET

port_inc = 5000
output_counter = 0
data_types = ['bc', 'bn', 'wl', 'un', 'nw', 'cts']
types = {0: ('ART', ['User-Owner-Inventor-Manufacturer']),
         1: ('GEN-AFF', ['Citizen-Resident-Religion-Ethnicity', 'Org-Location']),
         2: ('METONYMY', [None]),
         3: ('ORG-AFF', ['Employment', 'Founder', 'Ownership', 'Student-Alum', 'Sports-Affiliation', 'Investor-Shareholder', 'Membership']),
         4: ('PART-WHOLE', ['Artifact', 'Geographical', 'Subsidiary']),
         5: ('PER-SOC', ['Business', 'Family', 'Lasting-Personal']),
         6: ('PHYS', ['Located', 'Near'])}


def print_metonymy(relation, entities, data_type, path):
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


def print_first_mention_extent(relation, entities, data_type):
    global output_counter
    start = 0
    head_start = 0
    head_start2 = 0
    head_end = 0
    head_end2 = 0
    
    original_sentence = ''
    
    for cur_child in relation:
        if cur_child.tag == 'relation_mention':
            output_counter += 1
            for sub_rel_mention in cur_child:
                if sub_rel_mention.tag == 'extent':
                    assert(sub_rel_mention[0].tag == 'charseq')
                    original_sentence = sub_rel_mention[0].text
                    start = int(sub_rel_mention[0].attrib['START'])
                elif sub_rel_mention.tag == 'relation_mention_argument' and sub_rel_mention.attrib['ROLE'] == 'Arg-1':
                    head_start, head_end = entities[sub_rel_mention.attrib['REFID']]
                elif sub_rel_mention.tag == 'relation_mention_argument' and sub_rel_mention.attrib['ROLE'] == 'Arg-2':
                    head_start2, head_end2 = entities[sub_rel_mention.attrib['REFID']]
            
            first_head_start, last_head_start, first_head_end, last_head_end, first_color, second_color =   \
                (head_start, head_start2, head_end, head_end2, "\033[1;32;0m", "\033[1;31;0m")              \
                if head_start < head_start2 else                                                            \
                (head_start2, head_start, head_end2, head_end, "\033[1;31;0m", "\033[1;32;0m")
            
            text_to_manipulate =                                                           \
                original_sentence[:first_head_start - start] +                            \
                first_color +                                                              \
                original_sentence[first_head_start - start: first_head_end - start + 1] + \
                "\033[0m" +                                                                \
                original_sentence[first_head_end - start + 1: last_head_start - start] +  \
                second_color +                                                             \
                original_sentence[last_head_start - start: last_head_end - start + 1] +   \
                "\033[0m" +                                                                \
                original_sentence[last_head_end - start + 1:]
            print(str(output_counter) + '(' + data_type + '). ' + text_to_manipulate.replace('\n', ' '))
            return output_counter, text_to_manipulate.replace('\n', ' '), original_sentence # TODO - add Entity types


def extract_doc(subtype, root, data_type, path, sentences):
    entities = {}
    
    # store all entity mentions in a {ID:head} dict
    for child in root[0]:
        if child.tag == 'entity':
            for entity_mentions in child:
                for text in entity_mentions:
                    if text.tag == 'head':
                        assert(text[0].tag == 'charseq')
                        entities[entity_mentions.attrib['ID']] = int(text[0].attrib['START']), int(text[0].attrib['END'])
                        entities[child.attrib['ID']] = int(text[0].attrib['START']), int(text[0].attrib['END'])
    
    # print all relation according to subtype
    search_sub_type = True
    if subtype is None:
        search_sub_type = False
    for child in root[0]:
        if child.tag == 'relation':
            if (search_sub_type and 'SUBTYPE' in child.attrib and child.attrib['SUBTYPE'] == subtype) or \
                    ((not search_sub_type) and 'SUBTYPE' not in child.attrib):
                counter, colored_sentence, orig_sentence = print_first_mention_extent(child, entities, data_type) if search_sub_type else print_metonymy(child, entities, data_type, path)
                sentences[counter] = colored_sentence, orig_sentence


def extract_all(subtype, path, sentences):
    for subdir, dirs, files in os.walk(path):
        if 'timex2norm' in subdir:
            for filename in files:
                if filename.endswith(".apf.xml"):
                    tree = ET.parse(subdir + os.sep + filename)
                    root = tree.getroot()
                    indices = [i for i in data_types if (os.sep + i + os.sep) in subdir]
                    assert(len(indices) == 1)
                    extract_doc(subtype, root, indices[0], subdir + os.sep + filename, sentences)


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
    if types[cur_type][0] != 'METONYMY':
        query = "Choose a subtype (by number):\n"
        for i, subtype in enumerate(types[cur_type][1]):
            query += (str(i + 1) + " " + subtype + "\n")
    
        while subtype not in range(len(types[cur_type][1])):
            subtype = int(input(query)) - 1
    
    print_types(types[cur_type][0], types[cur_type][1][subtype] if subtype is not None else 'None')
    return types[cur_type][1][subtype] if subtype is not None else None


def threaded_displacy(docs, port):
    import sys
    import os
    import spacy
    sys.stdout = open(os.devnull, 'w')
    spacy.displacy.serve(docs, style='dep', options={'compact': True}, port=port)


def dep_view(sentences):
    global port_inc
    import spacy
    
    lines = input("Choose line numbers (space separated), for comparision.\n")
    if lines == 'Q':
        return True, None
    lines =[int(num) for num in lines.split()]
    
    nlp = spacy.load('en_core_web_sm')
    docs = []
    for line in lines:
        docs.append(nlp(sentences[line][1]))
    
    p = multiprocessing.Process(target=threaded_displacy, args=[docs, port_inc])
    p.start()
    port_inc += 1
    return False, p


def dep_views(sentences):
    finished = False
    processes = []
    while not finished:
        finished, p = dep_view(sentences)
        if not finished:
            processes.append(p)
    not_interesting = [process.terminate for process in processes]


def main(path, cmd_subtype=None):
    if not cmd_subtype:
        subtype = get_subtype()
    else:
        subtype = cmd_subtype if cmd_subtype != 'None' else None
        found = False
        for i, (cur_type, subtypes) in types.items():
            if subtype in subtypes:
                print_type(cur_type, subtype if subtype is not None else 'None')
                found = True
        if not found:
            print_usage()
            return
    
    sentences = {}
    extract_all(subtype, path, sentences)
    dep_views(sentences)


def print_usage():
    print("Usage: main.py path_to_data [subtype|None]\n"
          "'None' means Metonymy.\n"
          "If you omit the subtype(or None), you will be prompt to input it afterwards.")


if __name__ == "__main__":
    if len(sys.argv) == 2:
        main(sys.argv[1])
    elif len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        print_usage()
