entity_types = ["FAC", "GPE", "LOC", "ORG", "PER", "VEH", "WEA"]
d = {}
for entity_type_lhs in entity_types:
    for entity_type_rhs in entity_types:
        d[(entity_type_lhs, entity_type_rhs)] = set()


def f(lhs, rhs, relation, is_symmetric=False):
    for i in lhs:
        for j in rhs:
            d[(i, j)].add(relation)
            if is_symmetric:
                d[(j, i)].add(relation)


f(["PER", "FAC", "GPE", "LOC"], ["FAC", "GPE", "LOC"], "Near", True)
f(["PER"], ["FAC", "GPE", "LOC"], "Located", True)
f(["PER"], ["PER"], "Business", True)
f(["PER"], ["PER"], "Family", True)
f(["PER"], ["PER"], "Lasting-Personal", True)
f(["FAC", "GPE", "LOC"], ["FAC", "GPE", "LOC"], "Geographical")
f(["ORG"], ["ORG", "GPE"], "Subsidiary")
f(["VEH"], ["VEH"], "Artifact")
f(["WEA"], ["WEA"], "Artifact")
f(["PER"], ["ORG", "GPE"], "Employment")
f(["PER"], ["ORG"], "Ownership")
f(["PER", "ORG"], ["ORG", "GPE"], "Founder")
f(["PER"], ["ORG"], "Student-Alum")
f(["PER"], ["ORG"], "Sports-Affiliation")
f(["PER", "ORG", "GPE"], ["ORG", "GPE"], "Investor-Shareholder")
f(["PER", "ORG", "GPE"], ["ORG"], "Membership")
f(["PER", "ORG", "GPE"], ["WEA", "VEH", "FAC"], "User-Owner-Inventor-Manufacturer")
f(["PER"], ["PER", "LOC", "GPE", "ORG"], "Citizen-Resident-Religion-Ethnicity")
f(["ORG"], ["LOC", "GPE"], "Org-Location-Origin")


ordered_list = [(len(v), (k, v)) for k, v in d.items()]
ordered_list.sort(reverse=True)
file = open(r"C:\projects\GitHub\ACE05-searcher\bla.dat", "w")
for o in ordered_list:
    file.write("%d\t%s %s\t" % (o[0], o[1][0][0], o[1][0][1]))
    for o2 in o[1][1]:
        file.write("%s " % o2)
    file.write("\n")

f2.close()
