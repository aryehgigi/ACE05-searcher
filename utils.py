import spacy
nlp = spacy.load('en_core_web_sm')


def print_mod(cur, count=0):
    if len(cur['modifiers']) == 0:
        print('\t' * count + '<--- ' + cur['arc'] + ' \"' + cur['word'] + '\"')
    else:
        print('\t' * count + '<--- ' + cur['arc'] + ' \"' + cur['word'] + '\"')
        for mi in cur['modifiers']:
            print_mod(mi, count + 1)


def print_my_tree(text):
    d = nlp(text)
    d2 = d.print_tree()
    
    print_mod(d2[0])


print_my_tree(u"She tries to blame the U.S. and other members of the Security Council for not sending enough troops to stop it")
