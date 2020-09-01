import os
import subprocess

ARBITRARY_PATH = "c:/temp/sentence.txt"
ARBITRARY_PATH2 = "c:/temp/bla.txt"


def conllu_parse(sentence):
    csentence = dict()
    with open(ARBITRARY_PATH, "w") as f:
        f.write(sentence)
    
    with open(ARBITRARY_PATH2 , "w") as f:
        pop = subprocess.Popen("java -cp \"*\" -mx2000m edu.stanford.nlp.parser.lexparser.LexicalizedParser -outputFormat \"conll2007\" edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz %s" % ARBITRARY_PATH, cwd=r"c:\Users\inbaryeh\Documents\academy\Thesis\ai2\stanford-parser-full-2018-10-17", stdout=f, stderr=subprocess.PIPE)
        pop.wait()
    
    prev_id = -1
    adder = 0

    with open(ARBITRARY_PATH2, "r") as f:
        lines = f.read().split("\n")
        for l in lines:
            splited_token = l.split()
            if len(splited_token) != 10:
                continue
            try:
                new_id, form, lemma, upos, xpos, feats, head, deprel, deps, misc = splited_token
                if int(new_id) < prev_id:
                    adder = prev_id + adder
                csentence[int(new_id) + adder] = Token(int(new_id) + adder, form, lemma if lemma != "_" else form.lower(), xpos if xpos != "_" else upos, int(head) + adder, deprel)
                prev_id = int(new_id)
            except:
                continue
    
    for v in csentence.values():
        v.set_head(csentence[v.head_] if v.head_ != 0 else None)
    
    os.remove(ARBITRARY_PATH)
    os.remove(ARBITRARY_PATH2)
    return csentence


class Token(object):
    def __init__(self, new_id, form, lemma, xpos, head, deprel):
        self.id = new_id
        self.text = form
        self.lemma = lemma
        self.pos_ = xpos
        self.head_ = head
        self.dep_ = deprel
        self.head = None
        self.head_was_set = False
    
    def set_head(self, head):
        self.head = head
        self.head_was_set = True
    
    def is_ancestor(self, t):
        if not self.head_was_set:
            raise
        cur = self
        while cur.head_ != 0:
            if cur.head_ == t.id:
                return True
            cur = cur.head
        return False
