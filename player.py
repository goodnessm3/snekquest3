import generators
import random
import re

from collections import deque

import game_items
import combat_engine


class Player:

    command_aliases = {
        "on_look": ["look", "examine", "check", "investigate", "view", "see"],
        "on_use": ["use"],
        "on_take": ["take", "grab", "get", "pick"],
        "on_go": ["go", "travel", "venture", "walk"],
        "on_quit": ["quit"],
        "on_status": ["inventory", "status", "stats", "level", "character sheet"],
        "on_drop": ["drop", "discard", "leave"],
        "on_open": ["open"],
        "on_attack": ["attack", "fight", "hit", "stab", "battle"],
        "on_exits": ["exits"],
        "on_equip": ["equip"],
        "on_deequip": ["deequip", "de-equip", "remove", "unequip"],
        "on_loot": ["loot"],
        "on_debug": ["debug"],
        "on_suicide": ["suicide"],
    }

    def __init__(self):

        self.item_queue = deque()  # queued-up special items to be injected into the game at various times
        self.registered_countdowns = []  # objects to send a "tick" signal every time a command is processed
        # used for items with limited duration. Each item keeps track of its own countdown.
        self.known_characters = {}
        self.command_dict = self.setup_command_dict()
        self.current_character = None  # the character currently invoking commands. This is used to pass a reference
        # to that character to any new entities that are created and need to know about the player

    def get_character_reference(self):

        """return the character who is currently invoking commands, to pass a reference to
        newly-created game objects"""

        return self.current_character

    def setup_command_dict(self):

        """Uses the command_alisases to make a mapping of strings to functions that
        are invoked on a game object"""

        out = {}
        for k, v in self.command_aliases.items():
            for i in v:
                out[i] = k  # string typed by player:function of MyThing
        return out

    def request_key(self, colour):

        # TODO: there is no guarantee the same colour key won't turn up twice
        self.enqueue_unique_item(game_items.Key(colour), delay=1)

    def enqueue_unique_item(self, item, delay=None):

        if not delay:
            delay = random.randint(1, 20)

        for x in range(delay):
            self.item_queue.append(None)
            # every "turn", one thing is popped off the list and added to the game, so adding
            # nones delays the addition of an item
            # note USE POPLEFT so it's a queue and not a stack
        self.item_queue.append(item)

    def start_game(self, discord_id):

        """Registers the character in the list of characters in play. The character
        is identified by their numeric discord id for the purposes of routing
        commands, etc"""  # TODO replace with actual interface

        character = self.known_characters[discord_id]
        self.current_character = character
        character.start_game()
        return character.first_output()

    def run_combat(self, monster1, monster2):

        """Used to resolve battles with monsters in dungeon mode"""

        ce = combat_engine.CombatEngine(monster1, monster2, log_ref=self)
        ce.run_combat()

    def log(self, message, *args, newline):

        """This function redirects a message
        to the log of the player who invoked the command or caused the logging to happen"""

        self.current_character.log(message, *args, newline=newline)

    def process_command(self, command, discord_id):

        """Takes in a command string typed by the player and attempts to interpret it. Interpretation
        causes all the game logic to run and the logs to be updated. At the end of the function,
        the updated log is returned to be printed by whatever called it e.g. a discord bot or other interface"""

        try:
            character = self.known_characters[discord_id]
        except KeyError:
            print("Process_command got message from unregistered player, this should not happen")
            return

        character.clear_log()
        self.current_character = character  # this is for directing log messages to the appropriate log
        # it is reset at the start of every turn obviously

        splitted = command.split(" ", maxsplit=1)  # just take off the first verb for use as command
        if len(splitted) == 1:
            cmd = splitted[0]
            words = ""
        else:
            cmd, words = splitted
        if cmd not in self.command_dict.keys():
            character.log("Unrecognised command: {}", cmd)
            return character.print_log()  # return early because couldn't do anything
        else:
            executable_command = self.command_dict[cmd]
            # the name of the command as it appears in the object's __dict__

        if executable_command == "on_status":
            # special command with no target object, just prints player stats and return early
            character.report_status()
            return character.print_log()

        resolution_order = [character.equipped, character.items, character.visible_things]  # reset everytim
        if executable_command == "on_take":
            resolution_order.reverse()  # player wants to take visible things, not equipped things.

        args = []
        target = None

        for ls in resolution_order:
            # the order of these lists is important: items equipped or held by the player
            # must take precedence, otherwise if a player tries to unequip a worn item in a
            # room that contains an item with the same name, the command dispatcher might pick up
            # the room's version of the item first and fail to unequip it. These cases should be rare.
            for k in ls:
                # first check for exact words
                if k.__doc__ in words:
                    if target is None:
                        target = k  # target first, then args, to cope with "use x on y"
                    else:
                        args.append(k)

        if len(args) == 0 and len(words) > 0:
            for ls in resolution_order:
                # then check for partially-typed words if nothing was found
                for k in ls:
                    if words in k.__doc__:
                        if target is None:
                            target = k
                        else:
                            args.append(k)

        if executable_command == "on_go":
            for direction in ["north", "south", "east", "west"]:
                # all directions are permitted because if it's not valid it will be caught by
                # the room's on_go function
                if direction in words:
                    args.append(direction)
                    target = character.location

        if target is None:

            if len(words) > 0:
                character.log("Unrecognised target: {}.", words)
                return character.print_log()

            if executable_command == "on_attack":
                # player might have mistyped a name or just attack with no monster, consistently pick the
                # first monster for them to attack, if present. If not, pass it on to self.location
                # which will of course fail
                if character.check_if_monsters():
                    target = character.monsters_in_play[0]

            else:
                # either the player typed ("look"), which is just to look at the room,
                # or they typed any other no-argument command which is handled by
                # the MyItem class e.g. status, quit
                target = character.location

        try:
            to_run = target.__getattribute__(executable_command)
            # look up the command in target's dictionary

        except AttributeError:
            character.log("Can't {} this.", cmd)
            return character.print_log()

        # THE IMPORTANT PART #
        to_run(*args)  # evaluate the command we looked up, passing the arguments the player typed

        if not (executable_command in ["on_go", "on_look", "on_attack"]):
            # monsters only attack if the player is still, otherwise they'd attack every time the
            # player ran and running would be pointless
            # not really fair to have the look command trigger attacks either, but anything else
            # is fair game e.g. interacting with objects
            for mon in character.monsters_in_play:
                mon.attack_player()

        if not executable_command == "on_look":
            # only process heartbeats if the player command actually did something
            for item in self.registered_countdowns:
                item.heartbeat()

        return character.print_log()
