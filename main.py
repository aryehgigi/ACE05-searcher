# TODO's:
# 1. many function are ACE specific, generalize
# 2. some places are not written very smart pythonicaly speaking
# 3. replace ascii art
# 4. maybe replace the entire displacy idea, either all in web or all in CLI but not half-half.
# 5. terminating the process is not clean, the script will not die, fix this

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

DEBUG = False
port_inc = 5000
broken_entities_counter = 0
broken_relations_counter = 0
data_types = ['bc', 'bn', 'wl', 'un', 'nw', 'cts']
Entity = namedtuple("Entity", "id type start end head extent")
Relation = namedtuple("Relation", "id rel_type data_type orig colored_text")
Sentence = namedtuple("Sentence", "span start end")
relation_types = {
    0: ('ART', ['User-Owner-Inventor-Manufacturer']),
    1: ('GEN-AFF', ['Citizen-Resident-Religion-Ethnicity', 'Org-Location']),
    2: ('METONYMY', [None]),
    3: ('ORG-AFF', ['Employment', 'Founder', 'Ownership', 'Student-Alum', 'Sports-Affiliation', 'Investor-Shareholder', 'Membership']),
    4: ('PART-WHOLE', ['Artifact', 'Geographical', 'Subsidiary']),
    5: ('PER-SOC', ['Business', 'Family', 'Lasting-Personal']),
    6: ('PHYS', ['Located', 'Near'])
}
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
    'Org-Location': ['ORG-LOC', 'ORG-GPE']
}
# (list_arg1, list_arg2): (same_verb, arg1_from_left, arg2_from_right, arg1_before_arg2)
rule_paths = {
    ("nsubj",       "pobj-prep"):       (False, True, True, True),
    ("nsubjpass",   "pobj-prep"):       (False, True, True, True),
    ("nsubj",       "dobj"):            (False, True, True, True),
    ("nsubj",       "advmod"):          (False, True, True, True),
    ("dobj",        "dobj"):            (False, False, True, False),
    ("poss-attr",   "pobj-prep"):       (False, False, True, True),
    ("pobj",        "nsubj"):           (True, False, False, False),
    ("nsubj",       "nsubj"):           (False, False, False, False),
    ("nsubj",       "poss-prep-nsubj"): (False, False, False, False),
    ("dobj",        "nsubjpass"):       (False, True, False, False),
    ("dobj",        "nsubj"):            (False, False, False, False)
}
valid_verb_connectors = ["xcomp", "ccomp", "conj", "dep", "advcl", "relcl", ""]
valid_verb_binary_connectors = ["pcomp-prep"]


class Counters(Enum):
    TP = 0,
    FN = 1,
    FPN = 2,
    FPO = 3,
    TNO = 4,
    TNN = 5


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


def threaded_displacy(docs, port):
    import spacy
    spacy.displacy.serve(docs, style='dep', options={'compact': True}, port=port)


def print_web_dependency(nlp, relations):
    global port_inc
    
    # get user line numbers input
    lines = input("Choose line numbers (space separated), for comparision.\n")
    if lines == 'Q':
        return True, None
    lines = [int(num) for num in lines.split()]
    
    # convert text to spaCy Docs
    docs = []
    for line in lines:
        docs.append(nlp(relations[line - 1].orig))
    
    # run Displacy in a new process
    p = multiprocessing.Process(target=threaded_displacy, args=[docs, port_inc])
    p.start()
    port_inc += 1
    return False, p


def print_web_dependencies(relations):
    import spacy
    nlp = spacy.load('en_core_web_sm')
    print("*****************************************************************************************************\n")
    
    finished = False
    processes = []
    # allow multiple web prints asynchronously
    while not finished:
        finished, p = print_web_dependency(nlp, relations)
        if not finished:
            processes.append(p)
    
    # terminate them all
    _ = [process.terminate for process in processes]


def check_rule(sentence, arg1, arg2):
    arg_tokens = find_arg_tokens(sentence, pair[0], pair[1])
    is_nominal1, verb1, list_of_arg1_arcs, arg1_ancestors_pre_verb = find_path_to_verb(arg_tokens[0])
    is_nominal2, verb2, list_of_arg2_arcs, arg2_ancestors_pre_verb = find_path_to_verb(arg_tokens[1])
    
    # if nominal, or one is ancestor of the other (no verb between them) count as non-verbal and return
    if is_nominal1 or is_nominal2 or arg_tokens[1] in arg1_ancestors_pre_verb or arg_tokens[0] in arg2_ancestors_pre_verb:
        
        return False, None
    
    arg1_arcs = re.sub('(pobj-prep(-)*)+', 'pobj-prep-', "-".join(list_of_arg1_arcs))
    arg2_arcs = re.sub('(pobj-prep(-)*)+', 'pobj-prep-', "-".join(list_of_arg2_arcs))
    if len(arg1_arcs) > 0 and arg1_arcs[-1] == '-':
        arg1_arcs = arg1_arcs[:-1]
    if len(arg2_arcs) > 0 and arg2_arcs[-1] == '-':
        arg2_arcs = arg2_arcs[:-1]
    
    # check if valid paths to verbs by rule table
    if (arg1_arcs, arg2_arcs) not in rule_paths:
        return True, False
    
    # get the indicators according to the paths-to-verbs
    should_be_same_verb, should_arg1_from_left, should_arg2_from_right, should_arg1_before_arg2 = \
        rule_paths[(arg1_arcs, arg2_arcs)]
    if verb1 != verb2:
        # validate its the same verb
        if should_be_same_verb:
            return True, False
        
        # check if their path is valid
        verbs = [verb1]
        found_good_path = False
        w = verb1
        need_to_check = True
        
        # find first verb valid-connected-clique
        while w.dep_ != "ROOT":
            if need_to_check:
                if not (w.dep_ in valid_verb_connectors):
                    if not ((w.dep_ + "-" + w.head.dep_) in valid_verb_binary_connectors):
                        break
                    else:
                        need_to_check = False
            else:
                need_to_check = True
            w = w.head
            if w == verb2:
                found_good_path = True
                break
            verbs.append(w)
        
        # if verb2 not in verb1's valid-connected-clique, check if verb1 is in verb2's valid-connected-clique
        need_to_check = True
        if not found_good_path:
            w = verb2
            while w.dep_ != "ROOT":
                if need_to_check:
                    if not (w.dep_ in valid_verb_connectors):
                        if not ((w.dep_ + "-" + w.head.dep_) in valid_verb_binary_connectors):
                            return True, False
                        else:
                            need_to_check = False
                else:
                    need_to_check = True
                w = w.head
                if w in verbs:
                    found_good_path = True
                    break
            
            # if they are both not in each others valid-connected-clique then the path is not valid
            # this means that the trigger cant fire through the broken verb path - as the rules defined it
            if not found_good_path:
                return True, False
    
    # if nothing violated the rules, the entity pair has the relation
    return (True, True) if                                                      \
        not (should_arg1_from_left ^ (arg_words[0].idx < verb1.idx)) and        \
        not (should_arg2_from_right ^ (verb2.idx < arg_words[1].idx)) and       \
        not (should_arg1_before_arg2 ^ (arg_words[0].idx < arg_words[1].idx))   \
        else (True, False)


def find_verbal_path(verbs):
    set_of_verb_arcs = {""}
    paths_verb_to_ancestor = [[], []]
    
    # find paths from verbs to common ancestor
    for i in range(len(verbs)):
        j = (i + 1) % 2
        w = verbs[i]
        try:
            while not (w.is_ancestor(verbs[j]) or (w == verbs[j])):
                set_of_verb_arcs.add(w.dep_)
                paths_verb_to_ancestor[i].append(w.dep_)
                w = w.head
        except:
            import pdb;pdb.set_trace()
    
    return set_of_verb_arcs, paths_verb_to_ancestor


def find_path_to_verb(arg_token):
    list_of_arg_arcs = []
    arg_ancestors_pre_verb = []
    w = arg_token
    verb = None
    
    while w.pos_ != "VERB":
        # store interesting dependencies
        if w.dep_ != "conj" and w.dep_ != "compound":
            list_of_arg_arcs.append(w.dep_)
        
        # store tokens that are arg ancestors, prior reaching the verb
        arg_ancestors_pre_verb.append(w)
        
        # move counters
        w = w.head
        verb = w
        
        # check if it is a Nominal sentence
        if (w.dep_ == "ROOT") and (w.pos_ != "VERB"):
            return True, None, None, None
    
    return False, verb, list_of_arg_arcs, arg_ancestors_pre_verb


def find_arg_tokens(sentence, arg1, arg2):
    arg_tokens = [None, None]
    for word in sentence.span:
        word_start = word.idx - sentence.span.start_char + sentence.start
        word_end = word_start + len(word.text) - 1
        for i, argx in enumerate([arg1, arg2]):
            if argx.start <= word_start <= argx.end or \
                                    argx.start <= word_end <= argx.end or \
                                    word_start <= argx.start <= word_end:
                if (not arg_tokens[i]) or word.is_ancestor(arg_tokens[i]):
                    arg_tokens[i] = word
    return arg_tokens


def apply_rules(sentence, pair, subtype, relations, counters):
    if (pair[0].type + "-" + pair[1].type) in relation_arg_combos[subtype]:
        # check rule and add to counters appropriately
        is_verb, did_match = check_rule(sentence, pair[0], pair[1])
        if not is_verb:
            return
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


def find_rules(sentence, arg1, arg2, subtype, subtypes_by_rules, rules_by_subtype, verbal, non_verbal):
    arg_tokens = find_arg_tokens(sentence, arg1, arg2)
    is_nominal1, verb1, list_of_arg1_arcs, arg1_ancestors_pre_verb = find_path_to_verb(arg_tokens[0])
    is_nominal2, verb2, list_of_arg2_arcs, arg2_ancestors_pre_verb = find_path_to_verb(arg_tokens[1])
    
    # if nominal, or one is ancestor of the other (no verb between them) count as non-verbal and return
    if is_nominal1 or is_nominal2 or (arg_tokens[1] in arg1_ancestors_pre_verb) or (arg_tokens[0] in arg2_ancestors_pre_verb):
        if subtype in non_verbal:
            non_verbal[subtype] += 1
        else:
            non_verbal[subtype] = 1
        return
    
    if (not verb1) or (not verb2):
        if True:  # TODO - DEBUG
            print("%d. Entity was tagged as VERB, continue to next.")
        return
    
    if subtype in verbal:
        verbal[subtype] += 1
    else:
        verbal[subtype] = 1

    set_of_verb_arcs, paths_verb_to_ancestor = find_verbal_path([verb1, verb2])
    
    # TODO - check order features (and any other boolean features)
    # TODO - maybe add in the future: path3 or list_of arcs, and boolean list
    path_pair = ("-".join(list_of_arg1_arcs), "-".join(list_of_arg2_arcs))
    if path_pair in subtypes_by_rules:
        if subtype in subtypes_by_rules[path_pair]:
            subtypes_by_rules[path_pair][subtype] += 1
        else:
            subtypes_by_rules[path_pair][subtype] = 1
    else:
        subtypes_by_rules[path_pair] = {subtype: 1}
    
    if subtype in rules_by_subtype:
        if path_pair in rules_by_subtype[subtype]:
            rules_by_subtype[subtype][path_pair] += 1
        else:
            rules_by_subtype[subtype][path_pair] = 1
    else:
        rules_by_subtype[subtype] = {path_pair: 1}
        
    return set_of_verb_arcs


def find_entities(in_sentence, entity_index, prev_entity_index, entities, sgm_path, sentence):
    global broken_entities_counter
    
    while in_sentence and entity_index < len(entities):
        if entities[entity_index].start < sentence.start:
            prev_entity_index += 1
        if entities[entity_index].start > sentence.end:
            in_sentence = False
        else:
            if entities[entity_index].end > sentence.end:
                broken_entities_counter += 1
                if DEBUG:
                    print("%d. Entity was broken by wrong sentence splitting:"
                          "\n\tFilePath= %s,\n\tEntityID= %s,\n\tSplitedSentence= %s" % (broken_entities_counter, sgm_path, entities[entity_index].id, sentence.span.text))
                del entities[entity_index]
                continue
            entity_index += 1
    return in_sentence, entity_index, prev_entity_index


def break_sgm(path, nlp):
    f = io.open(path, "r", encoding="utf-8").read()
    complete_text = f.strip().replace("\n", " ")
    # this is specific for bug. we replace very non natural occurring of '/"' or '"/' to ' "' or '" ' accordingly
    # it happens in only two files exactly, namely:
    #   data/bn/timex2norm/CNN_ENG_20030605_153000.9.sgm
    #   data//bc//timex2norm//CNN_CF_20030303.1900.02.sgm
    complete_text = complete_text.replace("/\"", " \"").replace("\"/", "\" ")
    pointer = 0
    ace_indices = 0
    sentences = []  # list of (sentence, syntax_tree, ace_start_position, ace_end_position) elements
    consumed_text_tag = False
    consumed_text = complete_text
    
    # while al text is not consumed
    while pointer != len(complete_text):
        # break the sgm by tags
        match = re.search("<.*?>", consumed_text)
        found = consumed_text[match.start(): match.end()]
        
        # if we already reached the text tag, we take the paragraph
        # which is text between tags, break it to sentences and store them with their true indices
        if consumed_text_tag:
            # remove spaces, but keep count of trailing ones
            paragraph = consumed_text[:match.start()]
            paragraph = paragraph.rstrip()
            text_with_trail_spaces_len = len(paragraph)
            paragraph = paragraph.lstrip()
            spaces_len = text_with_trail_spaces_len - len(paragraph)
            
            # give up text in POSTER, SPEAKER, POSTDATE, SUBJECT for now
            if len(paragraph) != 0 and found not in ["</POSTER>", "</SPEAKER>", "</POSTDATE>", "</SUBJECT>", "</ENDTIME>"]:
                # add Sentence object to the list, after breaking to paragraph to sentences
                g_index = ace_indices + spaces_len
                d = nlp(paragraph)
                for span in d.sents:
                    sentences.append(Sentence(span, g_index + paragraph.find(span.text), g_index + paragraph.find(span.text) + len(span.text) - 1))
        
        # found start of interesting text
        if found == "<TEXT>":
            consumed_text_tag = True
        
        # forward pointers
        ace_indices += match.start()
        pointer += match.end()
        consumed_text = consumed_text[match.end():]
    
    return sentences


def main_rule(subtype, nlp, sgm_path, entities, relations, apply_or_find, counters, tot_set_of_verb_arcs, subtypes_by_rules, rules_by_subtype, verbal, non_verbal):
    global broken_entities_counter, broken_relations_counter
    
    # get sentences from sgm file
    sentences = break_sgm(sgm_path, nlp)
    
    # for every sentence
    prev_entity_index = 0
    entity_index = 0
    relations_found = set()
    
    for sentence in sentences:
        # find entities in sentence
        in_sentence = True
        in_sentence, entity_index, prev_entity_index = find_entities(
            in_sentence, entity_index, prev_entity_index, entities, sgm_path, sentence)
        
        # for every pair of entities in sentence, that applies for SUBTYPE
        for arg1 in entities[prev_entity_index: entity_index]:
            for arg2 in entities[prev_entity_index: entity_index]:
                if arg1.id == arg2.id:
                    continue
                pair = (arg1.id, arg2.id)
                
                if apply_or_find:
                    apply_rules(sentence, pair, subtype, relations, counters)
                else:
                    if pair in relations:
                        cur_set_of_verb_arcs = find_rules(sentence, arg1, arg2, relations[pair].rel_type, subtypes_by_rules, rules_by_subtype, verbal, non_verbal)
                        if cur_set_of_verb_arcs:
                            tot_set_of_verb_arcs |= cur_set_of_verb_arcs
                        relations_found.add(pair)
                    else:
                        pass
                        # TODO - do i want to save paths for comparison?
        
        prev_entity_index = entity_index
    
    if True:  # TODO - DEBUG
        for p in set(relations.keys()) - relations_found:
            broken_relations_counter += 1
            print("%d. Relation was broken by wrong sentence splitting:"
                  "\n\tFilePath= %s,\n\tRelationID= %s" % (broken_relations_counter, sgm_path, relations[p].id))


def print_rules_statistics(subtype, doc_triplets, apply_or_find):
    print("*****************************************************************************************************\n")
    import spacy
    nlp = spacy.load('en_core_web_sm')
    counters = {Counters.TP: 0, Counters.FN: 0, Counters.TNN: 0, Counters.TNO: 0, Counters.FPN: 0, Counters.FPO: 0}
    tot_set_of_verb_arcs = set()
    subtypes_by_rules = {}
    rules_by_subtype = {}
    verbal = {}
    non_verbal = {}
    
    for i, doc_triplet in enumerate(doc_triplets):
        if i % 25 == 0:
            print(i)
        main_rule(subtype, nlp, doc_triplet[0], doc_triplet[1], doc_triplet[2], apply_or_find, counters, tot_set_of_verb_arcs, subtypes_by_rules, rules_by_subtype, verbal, non_verbal)
    
    if apply_or_find:
        print("Recall: %.2f" % (counters[Counters.TP] / (counters[Counters.TP] + counters[Counters.FN])))
        print("Precision: %.2f" % (counters[Counters.TP] / (counters[Counters.TP] + counters[Counters.FPO] + counters[Counters.FPN])))
        print("PrecisionOther: %.2f" % ((counters[Counters.TP] + counters[Counters.FPO]) / (counters[Counters.TP] + counters[Counters.FPO] + counters[Counters.FPN])))
        print("FPR(other relations): %.2f" % (counters[Counters.FPO] / (counters[Counters.FPO] + counters[Counters.TNO])))
        print("FPR(non relations): %.2f\n" % (counters[Counters.FPN] / (counters[Counters.FPN] + counters[Counters.TNN])))
    else:
        print("Verbal-NonVerbal ratio:")
        for k, v in verbal.items():
            print("\t%s- %d:%d" % (k, v, non_verbal[k]))
        print("\nUnique path pairs: %d" % len(subtypes_by_rules))
        print("\nRules by subtype:")
        for k, v in rules_by_subtype.items():
            print("\t%s- Unique: %d" % (k, len(v)))
        import pdb;pdb.set_trace()
        print("\nRules found (and their count):")
        for k, v in subtypes_by_rules.items():
            print("\t%s: %s" % (str(k), str(v)))


def print_colored_relations(relations):
    for i, relation in enumerate(relations):
        print(str(i + 1) + '(' + relation.data_type + '). ' + relation.colored_text)
    print("\n")


def print_type(cur_type, subtype):
    print("*****************************************************************************************************\n")
    print("Showing all search result for type=%s~subtype=%s:" % (cur_type, subtype))
    print("Legend: \033[1;32;0mhead of Arg-1\033[0m. \033[1;31;0mhead of Arg-2\033[0m.")
    print()


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


def extract_relations(path, relation_mention, entities, rel_type, data_type, relations):
    start = 0
    head_start = 0
    head_start2 = 0
    head_end = 0
    head_end2 = 0
    original_sentence = ''
    arg1_id = -1
    arg2_id = -1
    arg1_type = None
    arg2_type = None
    
    # find relation arguments and extent
    for sub_rel_mention in relation_mention:
        if sub_rel_mention.tag == 'extent':
            assert(sub_rel_mention[0].tag == 'charseq')
            original_sentence = sub_rel_mention[0].text
            start = int(sub_rel_mention[0].attrib['START'])
        elif sub_rel_mention.tag == 'relation_mention_argument' and sub_rel_mention.attrib['ROLE'] == 'Arg-1':
            head_start, head_end, arg1_type = entities[sub_rel_mention.attrib['REFID']]
            arg1_id = sub_rel_mention.attrib['REFID']
        elif sub_rel_mention.tag == 'relation_mention_argument' and sub_rel_mention.attrib['ROLE'] == 'Arg-2':
            head_start2, head_end2, arg2_type = entities[sub_rel_mention.attrib['REFID']]
            arg2_id = sub_rel_mention.attrib['REFID']
    
    # assign indices and colores according to argument order
    first_head_start, last_head_start, first_head_end, last_head_end, first_color, second_color =   \
        (head_start, head_start2, head_end, head_end2, "\033[1;32;0m", "\033[1;31;0m")              \
        if head_start < head_start2 else                                                            \
        (head_start2, head_start, head_end2, head_end, "\033[1;31;0m", "\033[1;32;0m")
    
    # assemble the original extent text with the colored arguments
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
    
    if DEBUG:
        # notify user in case both arguments already participated in a former relation
        if (arg1_id, arg2_id) in relations:
            print("Notification: bad duplicate found,\n\tPath: %s\n\tSentence: %s,\n\tRe1Types: %s vs %s,\n\tArgTypes: %s -> %s, (%s, %s)\n" %
                  (path, relations[(arg1_id, arg2_id)].colored_text, relations[(arg1_id, arg2_id)].rel_type, rel_type, arg1_type, arg2_type, arg1_id, arg2_id))
    relations[(arg1_id, arg2_id)] = Relation(relation_mention.attrib['ID'], rel_type, data_type, original_sentence.replace('\n', ' '), colored_text.replace('\n', ' '))


def extract_entities(entity_mention, entity, entities_by_id, ordered_entities):
    # validate correct position in xml
    assert(
        (entity_mention[0].tag == 'extent') and
        (entity_mention[0][0].tag == 'charseq') and
        (entity_mention[1].tag == 'head') and
        (entity_mention[1][0].tag == 'charseq'))
    
    # store all entity mentions in a:
    # 1. {ID: (start, end, type)} dict,
    # 2. Entity ordered list (see Entity namedtuple)
    extent = entity_mention[0][0].text
    head = entity_mention[1][0].text
    head_start = int(entity_mention[1][0].attrib['START'])
    head_end = int(entity_mention[1][0].attrib['END'])
    
    entities_by_id[entity_mention.attrib['ID']] =\
        int(head_start), int(head_end), entity.attrib['TYPE']
    entities_by_id[entity.attrib['ID']] =\
        int(head_start), int(head_end), entity.attrib['TYPE']
    ordered_entities.append(Entity(
        entity_mention.attrib['ID'], entity.attrib['TYPE'], head_start, head_end, head, extent))


def extract_doc(root, data_type, path):
    entities_by_id = {}
    ordered_entities = []
    relations_by_pair = {}
    
    # extract all entity mentions
    for child in root[0]:
        if child.tag == 'entity':
            for grandchild in child:
                if grandchild.tag == 'entity_mention':
                    extract_entities(grandchild, child, entities_by_id, ordered_entities)
    
    # order the ordered_entities by start and then by end
    ordered_entities = sorted(ordered_entities, key=operator.attrgetter('start', 'end'))
    
    # extract all relation mentions
    for child in root[0]:
        if child.tag == 'relation':
            for grandchild in child:
                if grandchild.tag == 'relation_mention':
                    extract_relations(
                        path, grandchild, entities_by_id, 'None' if 'SUBTYPE' not in child.attrib else child.attrib['SUBTYPE'], data_type, relations_by_pair)
    
    return ordered_entities, relations_by_pair


def walk_all(subtype, path, wanted_relation_list, doc_triplets):
    # loop on all data files, and choose only apf.xml from timex2norm
    for subdir, dirs, files in os.walk(path):
        if 'timex2norm' in subdir:
            for filename in files:
                if filename.endswith(".apf.xml"):
                    # get xml root and data type (e.g. broadcast news)
                    tree = ET.parse(subdir + os.sep + filename)
                    root = tree.getroot()
                    data_type = [i for i in data_types if (os.sep + i + os.sep) in subdir]
                    assert(len(data_type) == 1)
                    data_type = data_type[0]
                    
                    # extract entities and relations from doc, store them in triplets with corresponding sgm files,
                    # and keep copy of SUBTYPE type relations.
                    ordered_entities, relations_by_pair = extract_doc(root, data_type, subdir + os.sep + filename)
                    doc_triplets.append(((subdir + os.sep + filename).replace('apf.xml', 'sgm'), ordered_entities, relations_by_pair))
                    for k, relation in relations_by_pair.items():
                        if relation.rel_type == subtype:
                            wanted_relation_list.append(relation)


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
    
    print_type(relation_types[cur_type][0], relation_types[cur_type][1][subtype] if subtype is not None else 'None')
    return relation_types[cur_type][1][subtype] if subtype is not None else None


def print_usage():
    print("Usage: main.py path_to_data [subtype|None]\n"
          "'None' means Metonymy.\n"
          "If you omit the subtype(or None), you will be prompt to input it afterwards.")


def main(path, cmd_subtype=None):
    import time
    start = time.time()
    
    # getting subtype from cmd param or user input
    if not cmd_subtype:
        subtype = get_subtype()
    else:
        subtype = cmd_subtype if cmd_subtype != 'None' else None
    
    # validate subtype and find corresponding Type
    meta_type = ""
    found = False
    for i, (cur_type, subtypes) in relation_types.items():
        if subtype in subtypes:
            meta_type = cur_type
            found = True
    if not found:
        print_usage()
        return
    
    # iterate and extract everything from documents
    doc_triplets = []
    relations = []
    walk_all(subtype, path, relations, doc_triplets)
    
    # print (and execute) all missions
    print_type(meta_type, str(subtype))
    print_colored_relations(relations)
    print_rules_statistics(subtype, doc_triplets, False) # TODO - apply_or_find
    print_web_dependencies(relations)
    print("Run time: %.2f" % (time.time() - start))


if __name__ == "__main__":
    # Usage: main.py path_to_data [subtype|None] (None for Metonymy)
    # 2 params means no subtype added
    if len(sys.argv) == 2:
        main(sys.argv[1])
    # 3 params means including subtype
    elif len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        print_usage()
