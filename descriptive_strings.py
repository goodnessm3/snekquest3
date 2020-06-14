import random
import re
import os
from collections import defaultdict

quest_text = {}

choice_finder = re.compile('''<[^<^>]*>|\[.*\]|%''')
list_finder = re.compile("\[[^\[^\]]*\]")
opt_finder = re.compile("<[^<^>]*>")
rand_finder = re.compile('''([0-9]{2})(%[^%]*%)''')
a_vowel_finder = re.compile('''(\s|^)a\s([aeiou])''')
heading_finder = re.compile('''\*([A-Z_]*)\*''')


def antoand(func):

    """Decorator that replaces 'a' with 'an' if the following word starts with a vowel"""

    def wrapper(*args):
        out = func(*args)
        out = a_vowel_finder.sub(r'\1an \2', out)  # need to use raw string so capture group works
        return out
    return wrapper


def my_loader(path):

    """returns a dict based on a text doc where *HEADING* lines delineate dictionary keys"""

    category_dict = defaultdict(lambda: [])
    current_heading = None
    with open(path, "r") as f:
        for line in f.readlines():
            head = heading_finder.findall(line)
            if head:
                current_heading = head[0]
            else:
                category_dict[current_heading].append(line.rstrip("\n"))
    return category_dict


def load_quest_text():

    global quest_text

    out = {}
    with open("quest_text.txt", "r") as f:
        for line in f.readlines():
            line = line.rstrip("\n")
            key, to_split = line.split(":")
            vals = to_split.split("|")
            out[key] = vals

    for fname in os.listdir("descriptions"):
        category, _ = os.path.splitext(fname)
        fullpath = os.path.join("descriptions", fname)
        out[category] = my_loader(fullpath)

    quest_text = out

    # extra code to merge and cross-reference dictionaries with each other, to avoid having the same
    # string or description in multiple files

    # builds a lookup so that gendered monsters can find their pronouns

    quest_text["all_monster_names"] = (quest_text["monster_names"]["MALE"] +
                                       quest_text["monster_names"]["FEMALE"] +
                                       quest_text["monster_names"]["NEUTRAL"])
    quest_text["monster_genders"] = {}
    for k, v in quest_text["monster_names"].items():
        for mon in v:
            quest_text["monster_genders"][mon] = k

    # merge common descriptions into the humanoid- or monster-specific dictionaries

    generic_common = quest_text["common_creature_descriptions"]["COMMON"]
    generic_rare = quest_text["common_creature_descriptions"]["RARE"]
    for category in "monster_descriptions", "humanoid_descriptions":
        quest_text[category]["COMMON"].extend(generic_common)
        quest_text[category]["RARE"].extend(generic_rare)

    print("Quest text loaded.")


@antoand
def do_sub_recursive(astr):

    cnt = 0
    while choice_finder.search(astr):
        astr = do_sub(astr)
        cnt += 1
        if cnt > 10:
            print(astr)
            raise Exception("string substitution took too long and was cancelled")
    return astr


def do_sub(astr):

    opts = opt_finder.findall(astr)
    for q in opts:
        choice = chooser(q)
        astr = astr.replace(q, choice)

    from_big_list = list_finder.findall(astr)
    for r in from_big_list:
        source = r[1:-1]
        astr = astr.replace(r, random.choice(quest_text[source]), 1)
        # limited to one replacement otherwise one thing will be picked and subbed in to
        # all the places where the string picks from that list

    rand_strings = rand_finder.findall(astr)
    for prob, randstr in rand_strings:
        astr = astr.replace(prob, "")  # get rid of the probability whatever happens
        if random.randint(0, 100) > int(prob):
            astr = astr.replace(randstr, "")
        else:
            astr = astr.replace(randstr, randstr[1:-1])  # just trim off the % signs

    return astr


def do_pronoun_sub(astr, pro, pos):

    """avoid offending monsters by making sure we use their correct pronouns"""

    astr = astr.replace("@pro", pro)
    astr = astr.replace("@pos", pos)
    return astr


def get_pronouns(gender):

    if gender == "NEUTRAL":
        pronoun = "it"
        pos_pronoun = "its"
    elif gender == "MALE":
        pronoun = "he"
        pos_pronoun = "his"
    elif gender == "FEMALE":
        pronoun = "she"
        pos_pronoun = "her"
    else:
        pronoun = "it"
        pos_pronoun = "its"

    return pronoun, pos_pronoun


def chooser(astr):
    astr = astr[1:-1]
    opts = astr.split("|")
    return random.choice(opts)


def generate_room_description():

    base = '''You are in a 50%[QUALIFIERS]% [ROOM_DESCRIPTORS] room. '''
    extra = generate_description("room_descriptions")
    base += extra

    return do_sub_recursive(base)


def generate_description(source, pro=None, pos_pro=None):

    """source is a description list e.g. doodad_descriptions. This function
    picks a random number of strings, does the substitution and returns the
    generated description.

    This optionally takes pronoun and posessive pronoun, for use when
    generating descriptions of creatures."""

    num_strings = random.randint(1, 4)
    picked = random.sample(quest_text[source]["COMMON"], num_strings)
    if random.choice((0, 1)) == 1:
        picked.append(random.choice(quest_text[source]["RARE"]))
    random.shuffle(picked)
    caps = []
    for sentence in picked:
        out = sentence
        if pro:
            out = do_pronoun_sub(sentence, pro, pos_pro)
        caps.append(out[0].upper() + out[1:])
        # can't use str.capitalize because that converts other uppercase letters to lower case
    base = " ".join(caps)

    return do_sub_recursive(base)


def generate_doodad():

    """returns type, description string"""

    typ = random.choice(quest_text["DOODADS"])
    if typ == "painting" or typ == "tapestry" or type == "drawing":
        # these doodads have special descriptions because they show a picture
        montyp, mondesc, _, _ = generate_monster()
        if montyp[0].lower() in ["a", "e", "i", "o", "u"]:
            # maybe there's a better way
            conj = "an"
        else:
            conj = "a"
        base = "A {} depicting {} {}. {}"
        desc = base.format(typ, conj, montyp, mondesc)
    else:
        desc = generate_description("doodad_descriptions")

    return typ, desc


def generate_container():

    """returns type and description string, for instantiation by the generator"""

    if random.choice((0, 1)) == 1:
        typ = random.choice(quest_text["CONTAINERS_FANCY"])
        desc = generate_description("doodad_descriptions")  # a container is a kind of doodad
    else:
        typ = random.choice(quest_text["CONTAINERS"])
        desc = typ

    return typ, desc


def generate_monster():

    typ = random.choice(quest_text["all_monster_names"])
    gender = quest_text["monster_genders"][typ]
    pro, pos_pro = get_pronouns(gender)
    if gender == "NEUTRAL":
        desc = generate_description("monster_descriptions", pro, pos_pro)
    else:
        desc = generate_description("humanoid_descriptions", pro, pos_pro)

    return typ, desc, pro, pos_pro


@antoand
def get_corpse_string(typ):

    return "The corpse of a {}.".format(typ)


def random_corpse_take_string():

    return random.choice(quest_text["RANDOM_CORPSE_TAKE"])


def random_death_string(name):

    return "The {} died!".format(name)


# load the text when the module is imported
print("Loading quest text...")
load_quest_text()
