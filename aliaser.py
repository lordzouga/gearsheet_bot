import util

def fix(aliases):
    fixed = dict()
    lowered = dict()
    table_rows = []

    for i in aliases.keys():
        lowered[i.lower()] = aliases[i].lower()

    for value in lowered.values():
        for key in lowered.keys():
            if lowered[key] == value:
                if value not in fixed.keys():
                    fixed[value] = [key]
                elif key not in fixed[value]:
                    fixed[value].append(key)
    
    fixed_keys = sorted(fixed.keys())
    for key in fixed_keys:
        table_rows.append('| %s | %s |' % (key.capitalize(), ", ".join("`%s`" % i for i in fixed[key])))
    
    for row in table_rows:
        print(row)

fix(util.vendor_aliases)
