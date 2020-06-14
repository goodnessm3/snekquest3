"""This module contains functions to generate random objects
for populating the game world."""


from game_items import *
from collections import namedtuple
# the following are to do introspection to get the item classes from game_items.py
import sys
import inspect
from os.path import split as pathsplit


chance = MyThing.chance  # convenient name to use the static class method for random rolls here

COMMON_ITEMS = []
RARE_ITEMS = []
UNIQUE_ITEMS = []
# todo: temp variables to prevent closed world
ROOMS = 0
EXITS = 0
GUARANTEE_EXIT = True  # the first time

for name, obj in inspect.getmembers(sys.modules["game_items"]):
    if inspect.isclass(obj):
        _, source = pathsplit(inspect.getsourcefile(obj))
        if source == "game_items.py":
            frequency = "common"
            norandom = False
            try:
                frequency = obj.freq
            except AttributeError:
                # frequency is only defined for rare items, otherwise it's not specified
                # and assumed to be common
                pass

            try:
                norandom = obj.norandom
            except AttributeError:
                pass  # norandom is rarely assigned

            if norandom:
                continue  # don't add the item to the list because it's never generated randomly
                # e.g. keys are only introduced if the corresponding locked door is encountered

            if frequency == "rare":
                RARE_ITEMS.append(obj)
            elif frequency == "unique":
                UNIQUE_ITEMS.append(obj)
            else:
                COMMON_ITEMS.append(obj)


def random_item():

    """Note brackets following random choice, the item list is a list of classes,
    whereas we want to return specific instances of those classes."""

    if chance(10):
        return random.choice(RARE_ITEMS)()
    else:
        return random.choice(COMMON_ITEMS)()


def random_doodad():

    typ, desc = descriptive_strings.generate_doodad()
    doodad = Doodad(typ, desc)
    return doodad


def random_room(came_from, direction, special_item=None):

    """update this later for special rooms etc"""

    global ROOMS
    global EXITS
    global GUARANTEE_EXIT

    if chance(10):
        ld = True
    else:
        ld = False

    nu = Room(came_from, direction, locked_door=ld, guaranteed_exit=GUARANTEE_EXIT)
    if chance(99):
        for x in random_room_contents():
            nu.add_item(x)
    if chance(40):
        nu.add_monster(random_monster())
    if special_item:
        if chance(50):
            nu.add_item(special_item)
        else:
            nu.add_monster(random_monster(special_item))

    ROOMS += 1
    EXITS += (len(nu.neighbours) - 1)
    if ROOMS >= EXITS:
        GUARANTEE_EXIT = True
    else:
        GUARANTEE_EXIT = False

    print(ROOMS, EXITS)

    return nu


def random_contents():

    """Random objects to put in containers and rooms"""

    out = []
    for x in range(random.randint(0, 2)):
        out.append(random_item())
    return out


def random_doodads():

    to_return = []
    for x in range(random.randint(0, 4)):
        to_return.append(random_doodad())

    return to_return


def random_container():

    typ, desc = descriptive_strings.generate_container()
    cont = Container()
    cont.__doc__ = typ
    if not desc == typ:
        cont.desc = desc

    for item in random_contents():
        cont.add_item(item)

    return cont


def random_monster(special_item=None):

    typ, desc, pronoun, pos_pronoun = descriptive_strings.generate_monster()
    mon = Monster(typ, desc, pronoun, pos_pronoun)

    if special_item:
        mon.specific_loot = special_item

    return mon


def random_room_contents():

    out = []
    out.append(random_doodad())
    out.append(generators.Bandages())
    out.append(random_container())

    return out


def get_corpse(typ):

    cor = Corpse()
    cor.__doc__ = "{} corpse".format(typ)
    cor.desc = descriptive_strings.get_corpse_string(typ)

    return cor


def random_key_colour():

    return random.choice(["red", "orange", "yellow", "green", "blue", "purple"])


def random_door_description():

    # TODO: maybe move whole thing into descriptive strings
    doorstr = '''a [ITEM_DESCRIPTORS] door, decorated with [ITEM_MATERIALS].'''
    return descriptive_strings.do_sub_recursive(doorstr)


def random_ability(typ="attack", weak=False):

    """weak abilities are for monsters"""

    if weak:
        power_numerator = 400
    else:
        power_numerator = 1000

    abtup = namedtuple("ability", ("name", "hit_chance", "stat", "power", "typ", "friendly_description"))
    # use named tuple for extensibility later

    hit_chance = random.normalvariate(55, 22)  # not a completely uniform distribution
    while not (20 < hit_chance < 95):
        hit_chance = random.normalvariate(50, 25)

    stat = random.choice(["[MOXIE]", "[STRENGTH]", "[SPEED]"])
    power = power_numerator/hit_chance
    mult = float(random.randint(80, 120))

    hit_chance = int(hit_chance)  # maths is now done and can convert to int

    if typ == "attack":
        true_power = int(power * mult / 100)
    else:
        true_power = int(power * mult / 1000) + 1
        hit_chance = 100  # defense abilities always "hit"

    name_prefix = ""

    if hit_chance > 85:
        name_prefix = "[ABILITY_ACCURATE]"
    if true_power > 29:
        name_prefix = "[ABILITY_STRONG]"
    if name_prefix == "":
        name_prefix = "{}".format(stat)

    if typ == "attack":
        name_string = "{} [ATTACK_NAMES]".format(name_prefix)
    else:
        name_string = "{} [DEFENSE_NAMES]".format(name_prefix)

    true_name = descriptive_strings.do_sub_recursive(name_string)
    friendly_stat = stat[1:-1].lower()
    friendly_desc = make_attribute_description(true_name, hit_chance, friendly_stat, true_power, typ)

    return abtup(true_name, hit_chance, friendly_stat, true_power, typ, friendly_desc)


def make_attribute_description(nam, hit_chance, stat, power, typ):

    out = "{}: ".format(nam)
    if typ == "attack":
        out += "deals {} damage. {}% hit chance. A {}-based attack.".format(power, hit_chance, stat)
    elif typ == "defense":
        out += "boosts {} by {}.".format(stat, power)
    return out
