import random
import descriptive_strings
from sys import exit
import generators
from mixins import *  # classes that add extra behaviours
import pdb

class MyThing:

    """base class for deriving rooms, monsters and items etc. Behaviour is added
    with functions named on_x which come from either mixins or classes that inherit
    from and extend this class. A simple error is shown to the player if they
    try to call a command that doesn't exist in the target object."""

    # OLD: pr = None  # replace this with a reference to the player object so that
    # mythings can invoke functions in the player to change state

    er = None  # this is replaced with a reference to the engine running the commands
    # the engine provides a reference to the character, the init method retrieves a ref
    # to the character who is interacting with the MyThing

    def __init__(self):

        self.pr = self.er.get_character_reference()

    def log(self, astring, *args):

        """Convenience function to take a string and some arguments, substitute
        in the arguments and add it to the output log of the player object. The
        player object prints out this log every interaction to tell what
        has happened."""

        self.pr.log(astring, *args)  # send the string and args to be processed by
        # the player object

    def on_look(self, *args):

        """If a descriptive docstring has been added, print that.
        If not, just use the name of the object's class"""

        if "desc" in dir(self):
            self.log(self.desc)
        else:
            self.log("You see a {}.", self.__doc__)

    def on_go(self, *args):
        self.log("Please enter a direction to go in.")

    def on_quit(self, *args):
        print("Bye bye")
        exit()

    def on_suicide(self, *args):
        self.pr.die()

    def on_exits(self, *args):
        self.log("No exits")

    @staticmethod
    def chance(prob):

        """All MyTthings have a simple method to get a true/false value based on
        a percentage probability"""

        if random.randint(0, 100) < prob:
            return True
        else:
            return False

    def on_debug(self, *args):
        pdb.set_trace()


class Doodad(MyThing):

    """Generic doodad"""

    def __init__(self, name=None, desc=None):

        super().__init__()
        if name:
            self.__doc__ = name
        if desc:
            self.desc = desc

    def on_attack(self, *args):

        outcomes = [("You slightly damage the {}.", self.__doc__),
                    ("You attacked the {}, but it didn't have much of an effect...",
                     self.__doc__),
                    ("That doesn't seem like a very good idea.",),
                    ("You lightly scuff the {}.", self.__doc__),
                    ("You leave a scratch on the surface of the {}.", self.__doc__),
                    ("You severely dented the {}.", self.__doc__),
                    ("You raise your weapon above your head, but then come to your senses and stop.",),
                    ]

        self.log(*random.choice(outcomes))


class Corpse(Doodad):

    def on_take(self, *args):

        self.log(descriptive_strings.random_corpse_take_string())

    def on_loot(self, *args):

        self.log("You don't need to loot corpses, the items are dropped on the floor.")


class Room(MyThing, ContainerMixin):

    def __init__(self, came_from, direction, locked_door=False, guaranteed_exit=False):

        super().__init__()
        self.neighbours = {self.flip_direction(direction): came_from}
        # hold a reference to the prev room, note that the direction is flipped so that if
        # we used the EAST exit of the previous room, that previous room is the
        # current room's WESTERN exit.
        self.contents = []
        self.monsters = []
        self.desc = descriptive_strings.generate_room_description()
        self.locked_door = None  # by default, a direction str e.g. "north" if it has one
        self.lock_colour = None
        self.locked_description = generators.random_door_description()

        for direct in ["north", "south", "east", "west"]:
            if not direct == self.flip_direction(direction): #TODO aaaa
                # don't re-generate a room whence we came, and keep the locked door for
                # special generation after
                if random.randint(0, 100) > 80:
                    self.neighbours[direct] = None  # only generate when moved to

        if guaranteed_exit:  # todo: better way of avoiding closed world
            # force an exit at the first available direction, to prevent a closed world
            for direct in ["north", "south", "east", "west"]:
                if not direct == self.flip_direction(direction):
                    self.neighbours[direct] = None
                    break

        if locked_door:
            locked = direction
            # the locked door is always opposite where the player came in. Makes the
            # generation logic a lot simpler, lol
            self.neighbours[locked] = None  # might have been generated anyway but no harm
            self.locked_door = locked
            colour = generators.random_key_colour()
            self.pr.request_key(colour)
            self.lock_colour = colour

            if len(self.neighbours) < 3:
                # always make sure a room with a locked door has at least one other exit
                # to avoid a dead-end scenario
                for direct in ["north", "south", "east", "west"]:
                    if direct not in self.neighbours.keys():
                        self.neighbours[direct] = None
                        break

    def get_printable_contents_list(self):

        if len(self.contents) > 0:
            return ", ".join([x.__doc__ for x in self.contents])
        else:
            return "Nothing of interest"

    def get_printable_exit_list(self):

        dirs = [x for x in self.neighbours.keys()]
        if len(dirs) == 1:
            out = "There is an exit to the {}".format(dirs[0])
        else:
            out = "There are exits to the {} and {}.".format(", ".join(dirs[:-1]), dirs[-1])

        if self.locked_door:
            out += " The exit to the {} is coloured {}: {}".format(
                self.locked_door,
                self.lock_colour,
                self.locked_description)

        return out

    def on_look(self, *args):

        self.log(self.desc)
        self.log("The room contains: {}", self.get_printable_contents_list())
        if len(self.monsters) > 0:
            for mon in self.monsters:
                name = mon.__doc__
                desc = mon.desc
                if not mon.seen:
                    self.log("You have encountered a {}! {}", name, desc)
                    mon.seen = True
                else:
                    self.log("A {}.", name)  # so that it doesn't always say "you have encountered"
                    # TODO: make it so that monsters aren't described immediately after chasing player

        self.log(self.get_printable_exit_list())

    def on_exits(self, *args):

        """player might type 'exits' to see where he can go"""
        self.log(self.get_printable_exit_list())

    def on_go(self, *args):

        if args == ():
            # player probably made a typo with the direction so it wasn't
            # recognised by the command dispatcher
            self.log("Please enter a valid direction.")
            return

        direction = args[0]

        try:
            dest = self.neighbours[direction]

            if direction == self.locked_door:
                if self.pr.has_key(self.lock_colour):
                    self.log("You used a key to unlock the {} door!", self.lock_colour)
                    self.pr.destroy_key(self.lock_colour)
                    self.locked_door = None
                    self.lock_colour = None
                else:
                    self.log("This door is locked, and needs a {} key.", self.lock_colour)
                    return

            self.log("You travel to the {}.", direction)
            self.pr.relocate(self, dest, direction)
        except KeyError:
            self.log("There is no exit to the {}. {}", direction, self.get_printable_exit_list())

    def flip_direction(self, direction):

        """north -> south, etc"""

        if direction == "north":
            return "south"
        elif direction == "south":
            return "north"
        elif direction == "east":
            return "west"
        elif direction == "west":
            return "east"

    def add_monster(self, monster):

        self.monsters.append(monster)
        monster.location = self

    def remove_monster(self, monster):

        self.monsters.remove(monster)


class Item(MyThing):

    """An item that can be added to inventory, dropped, etc, like a key, weapon or macguffin"""

    def __init__(self):

        super().__init__()
        self.location = None
        # a reference to where the item is, so it can delete itself from a room's contents
        # this isn't defined in the init method but is set when a room runs the add_item command

    def on_take(self, *args):

        if self.held_by_player():
            self.log("You already have this.")
            return
        else:
            self.pr.add_to_inventory(self)
            self.location.remove_item(self)
            self.location = "PLAYER"

    def held_by_player(self):

        if self.location == "PLAYER":
            return True
        else:
            return False

    def on_drop(self, *args):

        self.pr.drop_item(self)

    def destroy(self):

        if not self.location == "PLAYER":
            # item is being destroyed but is elsewhere like in a room or container
            self.location.remove_item(self)

        self.pr.destroy_item(self)

    def on_use(self, *args):

        self.log("You used the {}.", self.__doc__)
        self.on_use_logic(*args)

    def on_use_logic(self, *args):

        """override this"""
        self.log("Nothing happened.")


class SingleUseItem(Item):

    def on_use(self, *args):

        super().on_use(*args)
        self.destroy()


class Container(MyThing, ContainerMixin):

    """Generic container"""

    def __init__(self):

        super().__init__()
        self.contents = []
        self.opened = False
        self.locked = False
        self.location = None
        self.fill_random()

    def on_open(self, *args):

        if not self.locked:
            if len(self.contents) == 0:
                self.log("{} is empty", self.__doc__)
                return
            catenated_list = ", ".join([x.__doc__ for x in self.contents])
            self.log("Inside the {} there is: {}".format(self.__doc__, catenated_list))
            if not self.opened:  # only do this the first time
                for x in self.contents:
                    self.pr.make_item_visible(x)
                self.opened = True

        else:
            self.log("You need a key to open this.")

    def fill_random(self):

        for x in generators.random_contents():
            self.add_item(x)


class Monster(MyThing):

    """Generic monster"""

    def __init__(self, name=None, desc=None, pronoun="it", pos_pronoun="its"):

        """All these values are set post-instantiation by the monster generator"""

        super().__init__()
        if not name:
            self.name = self.__doc__  # the combat engine expects combatants to have a "name" attribute
        else:
            self.__doc__ = name
            self.name = name

        self.pronoun = pronoun
        self.pos_pronoun = pos_pronoun

        # these stats are essentially the same as a player character but are kept separate
        # stats are overwritten by specific monsters inheriting this template but these
        # are some default values
        self.weapon = Claws()
        self.strength = random.randint(4, 12)  # some generic weak stats
        self.armour = 0
        self.speed = random.randint(4, 12)
        self.health = random.randint(20, 50)
        self.moxie = random.randint(4, 12)
        self.buffs = {x: 0 for x in ("strength", "armour", "speed", "health", "moxie")}
        self.abilities = [generators.random_ability("attack", weak=True) for x in range(5)]
        # just some random attack
        # monster-specific stuff starts here
        self.seen = False  # first time seen, "you have encountered:", after that just "an x"
        self.location = None  # the room where the monster is, for loot dropping and so on
        # this will be set by the room's add_item method when the monster is added to the room
        self.specific_loot = None  # a special item like a key, inserted by monster generator
        if desc:
            self.desc = desc
        if name:
            self.__doc__ = name

    def on_attack(self, *args):

        self.er.run_combat(self.pr, self)  # get the engine to start a combat between player and self

    def attack_player(self):

        self.log("\nThe {} attacks you!\n", self.__doc__)  # extra newlines to make the message stand out
        self.er.run_combat(self.pr, self)

    def attack_player_logic(self):

        """Default behaviour is just a random weak attack, this can be overridden
        for specific monsters"""

        if self.chance(50):
            self.log("monster is attacking tbh")
        else:
            self.log("The attack missed!")

    def die(self):

        self.log(descriptive_strings.random_death_string(self.__doc__))
        self.location.remove_monster(self)
        self.pr.monsters_in_play.remove(self)
        self.pr.make_item_invisible(self)

        corpse = generators.get_corpse(self.__doc__)
        self.location.add_item(corpse)
        self.pr.make_item_visible(corpse)

        if random.choice((0, 1)) == 1:
            loot = generators.random_item()
            self.drop_loot(loot)

        if self.specific_loot:
            self.drop_loot(self.specific_loot)

    def drop_loot(self, loot):

        self.location.add_item(loot)
        self.pr.make_item_visible(loot)
        self.log("The {} has dropped some loot: {}!", self.__doc__, loot.__doc__)

    def decrement_health(self):

        self.hp -= 1
        if self.hp < 1:
            self.die()

    def relocate(self, new_location):

        self.location.remove_monster(self)
        new_location.add_monster(self)

    def randomly_follow(self, new_location):

        """if a player leaves a room with a monster, a random chance that the monster
        relocates to the next room along with the player"""

        if self.chance(90):
            self.log("The {} chases you!", self.__doc__)
            self.relocate(new_location)

    def unbuff(self):

        """combat engine expects combatants to have this method, although really it's only
        useful to remove temp stat buffs from players, it's invoked regardless though."""

        pass


class DelayedFunction(LimitedDurationMixin, MyThing):

    duration = 2  # by default, it happens next turn

    """Object that is passed to the player reference. After the countdown
    completes, it runs the function it was passed on creation."""

    def __init__(self, func, *args):

        super().__init__()
        self.func = func
        self.fnargs = args
        self.pr.registered_countdowns.append(self)

    def on_countdown_finished(self, *args):

        self.func(*self.fnargs)  # evaluate the function


class Weapon(EquippableMixin, Item):

    damage = 10
    slot = "right hand"
    """generic weapon"""

    def on_equip_logic(self):

        if self.pr.weapon is None:
            self.pr.weapon = self
        else:
            self.log("You are already holding {}", self.pr.weapon.__doc__)

    def on_deequip_logic(self):

        self.pr.weapon = None

    def on_look(self, *args):

        """slightly re-used code from the MyThing class, but need to add an extra bit
        in the description that mentions the weapon's damage"""

        out = ""
        if "desc" in dir(self):
            out += self.desc
        else:
            out += self.__doc__

        out += " ({} damage)"
        self.log(out, self.damage)


class Claws(Weapon):

    """claws"""

    damage = 5
