import random
import things
import character


class CombatEngine:

    """This is instantiated to run a combat, then deleted at the end of the combat"""

    def __init__(self, monster1, monster2, rounds=5, log_ref=None):

        # each round from this list. So, abilities that need to do something in the future can put a function
        # on this list to be evaluated in x turns' time. Extra round is added at the end to evaluate delayed stuff
        self.combat_queue = []
        self.mon1 = monster1
        self.mon2 = monster2
        self.rounds = rounds
        self.current_round = 0
        self.log_ref = log_ref  # need this to log combat messages in dungeon mode, or if none
        # just prints it to the channel because the combat engine isn't associated with any one
        # particular game

    def chance(self, prob):

        if random.randint(0, 100) < prob:
            return True
        else:
            return False

    def log(self, template, *args, newline=True):

        self.log_ref.log(template, *args, newline=newline)

    def inflict_damage(self, target, amount):

        ori_amount = amount
        amount = float(amount) * (100 - target.armour)/100
        amount = int(amount)
        if amount < 0:
            amount = 0
        target.health -= amount
        return amount, ori_amount - amount  # so that the damage reduction can be printed

    def defensive_ability(self, target, stat, amount):

        val = target.__getattribute__(stat)
        val += amount
        target.__setattr__(stat, val)
        target.buffs[stat] += amount  # a dictionary used to reset the buffs at the end of combat

    def setup_combat_queue(self):

        m1abs = self.mon1.abilities[:]
        m2abs = self.mon2.abilities[:]

        random.shuffle(m1abs)
        random.shuffle(m2abs)

        unpacked = [x for x in zip(m1abs, m2abs)]
        # generator is expanded into list so we know the total length

        self.combat_queue = unpacked[:self.rounds]
        # monsters might have lots of abilities but a max number of rounds is specified

    def run_combat(self):

        self.log("{} ({} HP) vs. {} ({} HP):\n",
                 self.mon1.name,
                 self.mon1.health,
                 self.mon2.name,
                 self.mon2.health)

        winner = loser = None  # determined in the while loop

        self.setup_combat_queue()
        while self.mon1.health > 0 and self.mon2.health > 0:
            if len(self.combat_queue) > 0:
                self.combat_turn()
            else:
                self.log("The battle ends with {} on {} HP and {} on {} HP!\n",
                         self.mon1.name,
                         self.mon1.health,
                         self.mon2.name,
                         self.mon2.health)
                return

        # now we have fallen out of the while loop and need to work out what happened
        # will only drop out of the loop if one monster's health has gome below 0
        if self.mon1.health <= 0:
            winner = self.mon2
            loser = self.mon1
        elif self.mon2.health <= 0:
            winner = self.mon1
            loser = self.mon2

        self.log("{} is victorious!", winner.name)
        self.end_combat_logic(winner, loser)

    def end_combat_logic(self, winner, loser):

        self.mon1.unbuff()
        self.mon2.unbuff()  # remove stat effects accumulated over combat

        if type(loser) == things.Monster:
            loser.die()
        elif type(loser) == character.Character:
            loser.die()

    def compare_stat(self, stat, mon1, mon2):

        """first returns the monster that has the highest score in the given stat,
        or none if they are equal"""

        m1stat = mon1.__getattribute__(stat)
        m2stat = mon2.__getattribute__(stat)

        if m1stat == m2stat:
            return None, None
        elif m1stat > m2stat:
            return mon1, mon2
        else:
            return mon2, mon1

    def combat_turn(self):

        ab1, ab2 = self.combat_queue.pop()

        winner, loser = self.compare_ability_tuples(ab1, ab2)
        # function returns both so we have references to both
        if winner is None:
            self.log("{} and {} were equally matched", ab1.name, ab2.name, newline=False)
            relevant_stat = ab1.stat  # it's the same for both which is why there was no winner
            strongest, weakest = self.compare_stat(relevant_stat, self.mon1, self.mon2)
            if strongest is not None:
                if strongest.weapon is not None:
                    damage_caused = strongest.weapon.damage
                    self.log(", but {}'s {} is superior, dealing {} damage with {}!",
                             strongest.name, relevant_stat, damage_caused, strongest.weapon.__doc__)
                    self.inflict_damage(weakest, damage_caused)
                else:
                    self.log("!")  # player or monster has no weapon to attack with

            else:
                self.log(", causing no damage to each other!")
        else:
            if winner is ab1:
                winmon = self.mon1
                losemon = self.mon2
            else:
                winmon = self.mon2
                losemon = self.mon1
            self.log("{}'s {} beat {}'s {}",
                     winmon.name,
                     winner.name,
                     losemon.name,
                     loser.name,
                     newline=False)  # TODO: replace with nice descriptions

        if winner is ab1:
            if ab1.typ == "attack":
                self.execute_ability(ab1, target=self.mon2, source=self.mon1)
            elif ab1.typ == "defense":
                self.execute_ability(ab1, target=self.mon1)
        elif winner is ab2:
            if ab2.typ == "attack":
                self.execute_ability(ab2, target=self.mon1, source=self.mon2)
            elif ab2.typ == "defense":
                self.execute_ability(ab2, target=self.mon2)
        else:
            pass  # draw

    def execute_ability(self, ability, target, source=None):

        if source:
            hit_probability = ability.hit_chance + source.__getattribute__(ability.stat)
        else:
            hit_probability = ability.hit_chance

        if not self.chance(hit_probability):
            self.log(", but the attack missed!")
            return

        if ability.typ == "attack":
            actual, delta = self.inflict_damage(target, ability.power)
            self.log(", dealing {} damage!", actual, newline=False)
            if not delta == 0:
                self.log(" (Armour reduced the damage by {})", delta)
            else:
                self.log("")  # didn't add the armour string but still want a newline
        elif ability.typ == "defense":
            self.defensive_ability(target, ability.stat, ability.power)
            self.log(", boosting {}'s {} by {}!", target.name, ability.stat, ability.power)

    def compare_ability_tuples(self, tup1, tup2):

        # strength beaten by speed beaten by moxie beaten by strength

        result = self.rps(tup1, tup2)

        if result == 1:
            winner = tup1
            loser = tup2
        elif result == -1:
            winner = tup2
            loser = tup1
        else:
            winner = None  # a draw because both abilities use the same stat
            loser = None

        return winner, loser

    def rps(self, tup1, tup2):

        """Determines if tup1 beats tup2
        there has to be a better way to do this and I'm so ashamed that I can't work it out"""

        ab1 = tup1.stat  # tup1 and tup2 are namedtuples so can access the stat by label
        ab2 = tup2.stat

        if ab1 == "strength":
            if ab2 == "moxie":
                return 1
            elif ab2 == "speed":
                return -1
            else:
                return 0
        elif ab1 == "speed":
            if ab2 == "strength":
                return 1
            elif ab2 == "moxie":
                return -1
            else:
                return 0
        elif ab1 == "moxie":
            if ab2 == "speed":
                return 1
            elif ab2 == "strength":
                return -1
            else:
                return 0
