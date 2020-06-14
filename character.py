import random
import generators

from descriptive_strings import a_vowel_finder


class EngineReference:

    pr = None  # overwrite this with a reference to the instantiated game engine object
    # inherit from this class to provide an object with a reference to the game engine


class Character(EngineReference):

    """A playable character with all their stats and abilities"""

    def __init__(self):

        self.discord_id = None  # discord numerical id
        self.name = None  # printable discord screen name for combat logs etc
        self.dead = False
        self.health = "uninjured"  # levels, not numeric
        self.items = []
        self.equipped = []
        self.equipped_slots = {"head": None,
                               "body": None,
                               "right hand": None,
                               "left hand": None}
        self.location = None
        self.weapon = None
        self.log_text = ""  # a buffer of text that is printed every action. Other objects
        # can add messages to this log, then it all gets printed at once.
        self.visible_things = []  # objects the player can interact with
        self.monsters_in_play = []  # monsters that might attack the player
        self.keys_in_play = {}
        self.visible_exits = []
        self.strength = 10
        self.armour = 0
        self.speed = 10
        self.health = 100
        self.moxie = 10
        self.buffs = {x: 0 for x in ("strength", "armour", "speed", "health", "moxie")}
        self.abilities = []  # tuples of name, hit chance, stat used, power

    def unbuff(self):

        for k, v in self.buffs.items():
            old = self.__getattribute__(k)
            new = old - v
            self.__setattr__(k, new)

    def random_abilities(self):

        # todo: this is only a testing function

        ab1 = [generators.random_ability("attack") for x in range(3)]
        ab2 = [generators.random_ability("defense") for x in range(1)]

        self.abilities = ab1 + ab2
        weap = generators.Sword()
        weap.pr = self
        self.force_equip_weapon(weap)

    def force_equip_weapon(self, obj):

        """Equip the player's starting weapon, this is only run at startup"""

        obj.location = "PLAYER"
        slot = obj.slot
        self.equipped_slots[slot] = obj
        self.equipped.append(obj)
        self.weapon = obj

    def log(self, message, *args, newline=True):

        message = message.format(*args)
        message = a_vowel_finder.sub(r'\1an \2', message)  # a to an
        self.log_text += message
        if newline:  # sometimes want to build up a log message from several different functions
            self.log_text += "\n"

    def clear_log(self):

        self.log_text = ""

    def print_log(self):

        return self.log_text

    def report_status(self):

        out = '''Stats:\n{}---\n{}\n---\n{}'''.format(
            self.print_stat_block(), self.print_inventory(), self.print_abilities())
        self.log(out)

    def return_status(self):

        """Required for the discord interface to print the character sheet for the first time
        rather than do it through the log interface"""

        out = '''Stats:\n{}---\n{}\n---\n{}'''.format(
            self.print_stat_block(), self.print_inventory(), self.print_abilities())
        return out

    def heal_damage(self, amount):

        self.health += amount
        if self.health > 100:
            self.health = 100

        self.log("You now have {} HP.", self.health)

    def change_stat(self, stat, amount):

        """unused???"""

        if amount >= 0:
            verb = "increased"
        else:
            verb = "decreased"

        old = self.__getattribute__(stat)
        new = old - amount
        if new < 0:
            self.log("{} died due to {} damage!", self.name, stat)
        else:
            self.log("{} {} by {}!", stat, verb, amount)

    def print_stat_block(self):

        out = ''''''
        for att in ["speed", "strength", "moxie", "health", "armour"]:
            value = self.__getattribute__(att)
            out += "{}: {}\n".format(att, value)

        return out

    def print_inventory(self):

        out = '''Inventory: '''

        name_list = [x.__doc__ for x in self.items]

        for name in set(name_list):
            if name_list.count(name) == 1:
                out += "{}, ".format(name)
            else:
                out += "{} ({}), ".format(name, name_list.count(name))

        out += "\nEquipped: "
        for equipped in self.equipped:
            out += "{}, ".format(equipped.__doc__)
        return out

    def print_abilities(self):

        out = "Abilities:\n"

        for x in self.abilities:
            out += x.friendly_description
            out += "\n"

        return out

    def make_item_visible(self, item):

        self.visible_things.append(item)

    def make_item_invisible(self, item):

        """for when a monster has died, etc"""

        self.visible_things.remove(item)

    def destroy_item(self, item):

        for ls in self.visible_things, self.items, self.equipped:
            if item in ls:
                ls.remove(item)

    def update_visible_things(self):

        """Updated to get lists from self.location rather than have to be told"""

        directions = self.location.neighbours.keys()
        items = self.location.contents
        monsters = self.location.monsters

        self.visible_things = []
        self.visible_exits = []

        for direction in directions:
            self.visible_exits.append(direction)
            # rather than hold a reference to the room, the player only holds the name of a possible
            # exit, because rooms aren't instantiated until the player visits them for the first time.
            # the room object updates the player's current location by passing a new room
            # object to the Player.relocate function.

        for ls in (items, monsters):
            for k in ls:
                self.visible_things.append(k)  # refer to object instances using their docstring name

    def relocate(self, source, dest, came_from):

        """Move the player from source room to dest room if exists, else create one"""

        if dest is None:
            try:
                special_item = self.pr.item_queue.popleft()
                # usually it's None but sometimes it's an item that's been delayed
            except IndexError:
                special_item = None

            # make a new room then make sure they know each other as neighbours
            dest = generators.random_room(source, came_from, special_item=special_item)
            source.neighbours[came_from] = dest  # only source needs to be informed
            # new room is informed of its neighbour on creation

        for mon in self.monsters_in_play:
            mon.randomly_follow(dest)

        self.location = dest
        self.update_visible_things()

        # registers the room's contents with the player object for the purpose of looking
        # up which commands are legal/make sense
        self.update_monsters_in_play(dest.monsters)

        dest.on_look()

    def update_monsters_in_play(self, als):

        self.monsters_in_play = []
        for mon in als:
            self.monsters_in_play.append(mon)

    def add_to_inventory(self, obj):

        self.items.append(obj)
        self.make_item_invisible(obj)  # remove from "visible things" list. If the player wants to
        # use a command on it like use or equip, the item is already present in the equipped or
        # inventory lists that are scanned by the command dispatcher.
        self.log("You picked up a {}", obj.__doc__)

    def equip(self, obj):

        name = obj.__doc__
        try:
            slot = obj.slot
            held = self.equipped_slots[slot]
            if held is None:
                self.equipped_slots[slot] = obj
            else:
                self.log("{} is already equipped in your {} slot.", held.__doc__, slot)
                return  # don't equip
        except AttributeError:
            self.log("{} is an equippable item with no slot, fix this!", name)
            self.add_to_inventory(obj)  # the object's on_equip logic deletes it from the location
            # it was picked up from, so we need to add it to the player's inventory otherwise the
            # item will disappear. This code should never run anyway if the item has a slot attribute.
            return

        self.equipped.append(obj)
        if obj in self.items:
            self.items.remove(obj)  # to avoid item duplication when equipping. but have to check for
            # presence in case the player is equipping something
            # straight off the floor
        self.log("You equipped the {}.", name)
        obj.on_equip_logic()


    def deequip(self, obj):

        name = obj.__doc__
        self.equipped.remove(obj)
        self.items.append(obj)  # de-dequipped but still held
        obj.on_deequip_logic()
        try:
            slot = obj.slot
            self.equipped_slots[slot] = None
        except AttributeError:
            pass
        self.log("You unequipped the {}", name)

    def drop_item(self, obj):

        name = obj.__doc__

        if not (obj in self.items or obj in self.equipped):
            self.log("You aren't holding a {}.", name)
            return

        if obj in self.equipped:
            obj.on_deequip()

        self.items.remove(obj)
        self.location.add_item(obj)
        self.log("Dropped {}.", name)
        self.update_visible_things()

    def destroy_key(self, colour):

        key = self.keys_in_play.pop(colour)
        self.destroy_item(key)

    def check_if_equipped(self, item):

        if item in self.equipped:
            return True
        else:
            return False

    def has_key(self, colour):

        if colour in self.keys_in_play.keys():
            return True
        else:
            return False

    def check_if_monsters(self):

        if len(self.monsters_in_play) > 0:
            return True
        else:
            return False

    def request_key(self, colour):

        self.pr.request_key(colour)

    def start_game(self):

        room = generators.random_room(None, "north")  # generate a new random room
        self.location = room
        weap = generators.Sword()
        room.add_item(weap)
        self.update_visible_things()
        self.update_monsters_in_play(room.monsters)
        # self.report_status() don't need this any more because discord code prints the character
        # sheet as a separate message to the channel
        self.location.on_look()

    def die(self):

        self.log("You have died...")
        self.dead = True

    def first_output(self):

        """Only invoked once when the game starts, to print some initial description"""

        out = self.log_text.replace("You are in", "You awaken in")
        self.log("All commands must be prefixed with ! e.g. !look, !go north, !take item")
        self.log_text = ""  # special case
        return out

    def adjust_stat(self, stat, amount):

        to_mod = self.__getattribute__(stat)
        modded = to_mod + amount
        if modded < 0:
            modded = 0
        if modded > 99:
            modded = 99
        self.__setattr__(stat, modded)

        if amount > 0:
            word = "increased"
        else:
            word = "decreased"

        self.log("{} {} by {}!", stat, word, amount)
