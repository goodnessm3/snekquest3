class ContainerMixin:

    """Objects that can contain other items"""

    def add_item(self, item):

        self.contents.append(item)
        item.location = self  # so the item knows where it is

    def remove_item(self, item):

        self.contents.remove(item)


class EquippableMixin:

    """Item can be equipped, changing the player's stats"""

    def on_equip(self, *args):

        if not self.held_by_player():
            # in case player sees something in a room and immediately equips it
            # without picking it up first
            self.location.remove_item(self)
            self.location = "PLAYER"
        self.pr.equip(self)

    def on_deequip(self, *args):

        if not self.held_by_player():
            self.log("{} is not equipped.", self.__doc__)
        else:
            if not self.pr.check_if_equipped(self):
                self.log("You are carrying {}, but it's not equipped.", self.__doc__)
            else:
                self.pr.deequip(self)
                # self.on_deequip_logic()
                # self.log("You took off the {}", self.__doc__)

    def on_equip_logic(self):

        """Default method assumes the item just modifies some stat"""
        try:
            stat, modifier = self.__getattribute__("stat_modifier")
            self.pr.adjust_stat(stat, modifier)

        except AttributeError:
            pass

    def on_deequip_logic(self):

        """Default method assumes the item just modifies some stat"""
        try:
            stat, modifier = self.__getattribute__("stat_modifier")
            self.pr.adjust_stat(stat, -modifier)  # minus modifier to revert the change

        except AttributeError:
            pass


class StackableMixin:

    pass

    #def on_take(self, *args):

        #"""Overloads Item.on_take to remove the check about whether the item is already held,
        #just takes it regardless. The items are seperate entities in the inventory list and only
        #appear as a stack e.g. health potion (2) when the inventory is printed, nothing
        #actually changes behind the scenes."""

        #self.pr.add_to_inventory(self)
        #self.location.remove_item(self)
        #self.location = "PLAYER"


class LimitedDurationMixin:

    duration = 0  # define this in the specific item class

    def on_use(self, *args):

        """like using a normal item (or single use item) but also registers the
        countdown to begin"""

        super().on_use(*args)
        self.pr.registered_countdowns.append(self)

    def heartbeat(self):

        print("tick")
        print(self.duration)
        self.duration -= 1
        if self.duration < 0:
            self.on_countdown_finished()
            self.pr.registered_countdowns.remove(self)
            # if single use item,
            # now the item will be garbage collected as nothing else holds a reference to it
            # otherwise it persists

    def on_countdown_finished(self, *args):

        """Overwrite with what happens when the item expires"""

        pass

    def on_use_logic(self, *args):

        """insert item behaviour here"""

        pass
