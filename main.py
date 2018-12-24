import os
import xml.etree.ElementTree as ET

output_counter = 0


def print_first_mention_extent(relation, entities):
    global output_counter
    head = ''
    head2 = ''
    
    text_to_manipulate = ''
    
    for cur_child in relation:
        if cur_child.tag == 'relation_mention':
            output_counter += 1
            for sub_rel_mention in cur_child:
                if sub_rel_mention.tag == 'extent':
                    assert(sub_rel_mention[0].tag == 'charseq')
                    text_to_manipulate = sub_rel_mention[0].text
                elif sub_rel_mention.tag == 'relation_mention_argument' and sub_rel_mention.attrib['ROLE'] == 'Arg-1':
                    head = entities[sub_rel_mention.attrib['REFID']]
                elif sub_rel_mention.tag == 'relation_mention_argument' and sub_rel_mention.attrib['ROLE'] == 'Arg-2':
                    head2 = entities[sub_rel_mention.attrib['REFID']]
            
            print(str(output_counter) + '. ' + text_to_manipulate.replace(head, "\033[1;32;0m" + head + "\033[0m").replace(head2, "\033[1;31;0m" + head2 + "\033[0m").replace('\n', ' '))
            return


def extract_doc(subtype, root):
    entities = {}
    
    # store all entity mentions in a {ID:head} dict
    for child in root[0]:
        if child.tag == 'entity':
            for entity_mentions in child:
                for text in entity_mentions:
                    if text.tag == 'head':
                        assert(text[0].tag == 'charseq')
                        entities[entity_mentions.attrib['ID']] = text[0].text
    
    # print all relation according to subtype
    search_sub_type = True
    if subtype is None:
        search_sub_type = False
    for child in root[0]:
        if child.tag == 'relation':
            if (search_sub_type and 'SUBTYPE' in child.attrib and child.attrib['SUBTYPE'] == subtype) or \
                    ((not search_sub_type) and 'SUBTYPE' not in child.attrib):
                print_first_mention_extent(child, entities)


def extract_all(subtype, path):
    for subdir, dirs, files in os.walk(path):
        for filename in files:
            if filename.endswith(".apf.xml"):
                tree = ET.parse(subdir + os.sep + filename)
                root = tree.getroot()
                extract_doc(subtype, root)


def get_subtype():
    types = {0:('ART', ['User-Owner-Inventor-Manufacturer']), 1:('GEN-AFF',['Citizen-Resident-Religion-Ethnicity', 'Org-Location']), 2:('METONOMY', []), 3:('ORG-AFF',['Employment', 'Founder', 'Ownership', 'Student-Alum', 'Sports-Affiliation', 'Investor-Shareholder', 'Membership']), 4:('PART-WHOLE',['Artifact', 'Geographical', 'Subsidiary']), 5:('PER-SOC',['Business', 'Family', 'Lasting-Personal']), 6:('PHYS',['Located', 'Near'])}
    query = "Choose a type (by number):\n"  \
            "1. ART(artifact)\n"            \
            "2. GEN-AFF(Gen-affiliation)\n" \
            "3. METONOMY\n"                 \
            "4. ORG-AFF(org-affiliation)\n" \
            "5. PART-WHOLE\n"               \
            "6. PER-SOC(person-social)\n"   \
            "7. PHYS(physical)\n"
    
    cur_type = None
    while cur_type not in range(7):
        cur_type = int(input(query)) - 1

    subtype = None
    if types[cur_type][0] != 'METONOMY':
        query = "Choose a subtype (by number):\n"
        for i, subtype in enumerate(types[cur_type][1]):
            query += (str(i + 1) + " " + subtype + "\n")
    
        while subtype not in range(len(types[cur_type][1])):
            subtype = int(input(query)) - 1
    
    print("Showing all search result for type=%s~subtype=%s:" % (types[cur_type][0], types[cur_type][1][subtype] if subtype is not None else 'None'))
    print("Legend: \033[1;32;0mhead of Arg-1\033[0m. \033[1;31;0mhead of Arg-2\033[0m.")
    print()
    return types[cur_type][1][subtype] if subtype is not None else None


def main(path):
    subtype = get_subtype()
    extract_all(subtype, path)


if __name__ == "__main__":
    main(r"C:\Users\inbar&aryeh\PycharmProjects\ace05_parser\data")
