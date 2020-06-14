from things import *


class Spade(Item):

    """spade"""
    slot = "left hand"

    def on_look(self, *args):

        self.log("A rusty spade with a wooden handle")


class HealthPotion(StackableMixin, SingleUseItem):

    """health potion"""

    def on_use_logic(self, *args):

        self.pr.heal_damage(20)


class LightArmour(EquippableMixin, Item):

    """light armour"""
    slot = "body"
    stat_modifier = ("armour", 10)

    def on_look(self, *args):

        self.log("A light suit of armour made from chainmail.")


class Hat(EquippableMixin, Item):

    """hat"""

    slot = "head"
    desc = "A fashionable hat. Chicks dig it."
    stat_modifier = ("moxie", 10)


class HeavyArmour(EquippableMixin, Item):

    """heavy armour"""

    freq = "rare"
    slot = "body"
    desc = "A sturdy suit of armour made from metal plates."
    stat_modifier = ("armour", 20)


class Bandages(StackableMixin, SingleUseItem):

    """bandages"""

    desc = "These could be used to patch up some wounds."

    def on_use_logic(self, *args):
        self.pr.heal_damage(10)


class OrbOfInvulnerability(LimitedDurationMixin, SingleUseItem):

    """orb of invulnerability"""

    desc = "A metallic orb about the size of an orange. It is warm to the touch. Your reflection"
    "looks strangely distorted in its surface."
    freq = "unique"
    duration = 3

    def on_use_logic(self, *args):

        self.log("You feel invincible!")
        self.pr.adjust_stat("armour", 50)

    def on_countdown_finished(self, *args):

        self.log("The invincibility wore off...")
        self.pr.adjust_stat("armour", -50)


class Key(Item):

    norandom = True
    desc = "This looks important. Better keep hold of it."

    def __init__(self, colour):

        super().__init__()
        self.colour = colour
        self.__doc__ = '''{} key'''.format(colour)

    def on_take(self, *args):

        super().on_take(*args)
        self.pr.keys_in_play[self.colour] = self


class Sword(Weapon):

    """sword"""
    damage = 20
    desc = "A lightweight sword made of aluminium."


class Hammer(Weapon):

    """hammer"""
    damage = 40
    desc = ('''An enormous hammer with a tungsten head mounted on a stainless steel shaft.'''
            '''It weighs about 40 kg.''')
