import player
import character
from things import MyThing

"""Basic testing module to provide a command-line interface to the game. This can be swapped out to run the game
from other interfaces e.g. by connecting it to a Discord bot as originally planned."""

PLAYER = player.Player()  # a fresh instance of the game player object

character.EngineReference.pr = PLAYER
MyThing.er = PLAYER  # set the engine reference for all newly created objects

myid = 55
name = "Abdul"
CHARACTER = character.Character()
CHARACTER.discord_id = myid
CHARACTER.name = name
CHARACTER.random_abilities()

PLAYER.known_characters = {55: CHARACTER}
first_output = PLAYER.start_game(myid)

command = None

print(first_output)
while not CHARACTER.dead:
    command = input(">")
    output = PLAYER.process_command(command, myid)
    print("----------")
    print(output)
