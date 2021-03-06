from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.timezone import now

from game.models import DatesMixin
from world.models import MapSquare, WorldMap

import datetime, random

class InvalidAttackException(Exception):
    pass
    
class InvalidMoveException(Exception):
    pass
    
class PlayerDeadException(Exception):
    pass
        
class PlayerManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, handle, gender, password=None):
        if not email:
            raise ValueError('Players must have an email address')
        
        if not first_name:
            raise ValueError('Players must have a first name')
            
        if not last_name:
            raise ValueError('Players must have a last name')
            
        if not handle:
            raise ValueError('Players must have a handle')
            
        if not gender:
            raise ValueError('Players must have a gender')
        
        user = self.model(
            email=PlayerManager.normalize_email(email),
            first_name=first_name,
            last_name=last_name,
            handle=handle,
            gender=gender
        )
        
        user.set_password(password)
        user.save(using=self._db)
        return user
        
    def create_superuser(self, email, first_name, last_name, handle, gender, password):
        user = self.create_user(
            email,
            first_name,
            last_name,
            handle,
            gender,
            password
        )
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user
        

class Player(AbstractBaseUser, PermissionsMixin, DatesMixin):
    GENDER_CHOICES = (('M', 'Male'),('F', 'Female'))
    MAX_FIGHTS = 10
    MAX_HUMAN_FIGHTS = 10
    
    objects = PlayerManager()
    
    # IRL fields
    email = models.EmailField(max_length=255, unique=True, db_index=True, verbose_name='email address')
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    
    # Player created fields
    handle = models.CharField(max_length=50, unique=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    
    # Experience
    level = models.SmallIntegerField(default=1)
    experience = models.BigIntegerField(default=1)
    player_kills = models.IntegerField(default=0)
    
    # Vitals
    dead = models.BooleanField(default=False)
    inn = models.BooleanField(default=False) # sleeping at inn?
    hit_points = models.IntegerField(default=10)
    hit_points_max = models.IntegerField(default=10)
    defense = models.IntegerField(default=10)
    strength = models.IntegerField(default=10)
    charm = models.IntegerField(default=10)
    king = models.SmallIntegerField(default=0) # number of times game won

    # Love life
    lays = models.IntegerField(default=0)
    married = models.ForeignKey('self', null=True, default=None, blank=True)
    kids = models.SmallIntegerField(default=0)
    
    # Turn data
    fights_left = models.SmallIntegerField(default=10)
    human_fights_left = models.SmallIntegerField(default=10)
    seen_bard = models.BooleanField(default=False)
    seen_dragon = models.BooleanField(default=False)
    seen_master = models.BooleanField(default=False)
    seen_violet = models.BooleanField(default=False)
    weird_event = models.BooleanField(default=False)
    done_special = models.BooleanField(default=False)
    flirted = models.BooleanField(default=False)

    # Inventory
    equipped_armor = models.ForeignKey('Armor', default=1)
    equipped_weapon = models.ForeignKey('Weapon', default=1)
    gold = models.IntegerField(default=10)
    bank = models.IntegerField(default=0)
    gem = models.IntegerField(default=0)
    
    # Life
    last_alive_time = models.DateTimeField(auto_now_add=True, null=True, default=None)
    last_dead_time = models.DateTimeField(null=True, default=None)
    days_played = models.IntegerField(default=0)
    
    # skills
    death_knight_level = models.SmallIntegerField(default=0)
    death_knight_skill = models.SmallIntegerField(default=0)
    mystical_level = models.SmallIntegerField(default=0)
    mystical_skill = models.SmallIntegerField(default=0)
    theif_level = models.SmallIntegerField(default=0)
    theif_skill = models.SmallIntegerField(default=0)
    
    # Location Info
    world_map = models.ForeignKey(WorldMap, default=1)
    map_square = models.ForeignKey(MapSquare, default=1)
    here_since = models.DateTimeField(auto_now_add=True, default=now)
    
    # Permissions
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'handle', 'gender']
    
    def get_pronoun(self):
        if self.gender == 'M': return 'He' 
        else: return 'She'
    
    def get_full_name(self):
        # The user is identified by their handle.
        return self.handle
        
    def get_short_name(self):
        # The user is identified by their handle.
        return self.handle
        
    def get_hp_status(self):
        percent_hp_remaining = int((self.hit_points * 1.0 / self.hit_points_max) * 100)
        if percent_hp_remaining < 20: return ('danger', percent_hp_remaining)
        if percent_hp_remaining < 50: return ('warning', percent_hp_remaining)
        return ('success', percent_hp_remaining)
    
    def get_activity_log(self):
        if self.activitylog_to_player.all():
            self.activitylog_to_player.filter(created_at__lt=(now()-datetime.timedelta(minutes=10)), viewed=True).delete() # purge messages that are older than 10 minutes and have already been seen.
            self.activitylog_to_player.filter(activity_type__in=['arrival','departure'], viewed=True).delete()
            self.activitylog_to_player.all().update(viewed=True)
        return self.activitylog_to_player.all()[:10]
        
    def get_fight_status(self):
        percent_fights_remaining = int((self.fights_left * 1.0 / self.MAX_FIGHTS) * 100)
        return ('info', percent_fights_remaining)
        
    def get_human_fight_status(self):
        percent_fights_remaining = int((self.human_fights_left * 1.0 / self.MAX_HUMAN_FIGHTS) * 100)
        return ('info', percent_fights_remaining)
    
    def add_activity_log(self, from_player, activity_type, message):
        return ActivityLog.objects.create(to_player=self, from_player=from_player, activity_type=activity_type, message=message)
    
    def attack_player(self, defender):
        if self.map_square.safe:
            raise InvalidAttackException('This is a no-fight zone. You can only fight monsters here.')
        
        if defender.map_square != self.map_square:
            raise InvalidAttackException('{defender} seems to have slipped away before you had a chance to attack.'.format(defender=defender.handle))
        
        if self.dead:
            raise PlayerDeadException('You are dead.  You cannot attack.')
            
        if defender.dead:
            raise InvalidAttackException('{defender} is dead.  You can\'t attack a dead person!'.format(defender=defender.handle))
        
        if defender.map_square != self.map_square:
            raise InvalidAttackException('That player has left the area.')

        if defender.status != "Active":
            raise InvalidAttackException('You can\'t attack someone who\'s {status}!  That\'s just wrong.'.format(status=defender.status.lower()))

        if self.strength - defender.strength > 50 or self.level - defender.level > 5:
            raise InvalidAttackException("You quickly realize that you would unfairly destroy {defender} in a match and walk away.".format(defender=defender.handle))

        if defender.strength - self.strength > 50 or defender.level - self.level > 5:
            raise InvalidAttackException("{defender} looks at you. {pronoun} scoffs and walks away.".format(defender=defender.handle, pronoun=defender.get_pronoun()))
        
        # reset the online counter.
        self.here_since = now()
        
        attacker_fight_description = ""
        defender_fight_description = ""
        """ coin toss to see if defender attacking first:  
            50% of the time, use skill selection.
            25% of the time, attacker gets the first attack.
            25% of the time, defender gets the first attack."""
        random.seed()
        first_attacker = random.choice(['me','them','skill','skill'])
        if first_attacker == 'me' or (first_attacker == 'skill' and self.strength > defender.strength): # you fight first.
            
            attacker_fight_description += "You get the jump on {defender} and attack first!\n".format(defender=defender.handle)
            defender_fight_description += "{attacker} attacks you out of nowhere!\n".format(attacker=self.handle)
            
            damage = self.deal_damage(defender)
            if damage == 0:
                attacker_fight_description += "{defender} skillfully blocked your attack!\n".format(defender=defender.handle)
                defender_fight_description += "You skillfully block {attacker}'s attack!\n".format(attacker=self.handle)
            elif defender.dead:
                attacker_fight_description += "You hit {defender} with a deadly blow.  {defender} falls to the ground, spits a bit of blood and lets out one last breath before dieing. You loot {gold} gold coins and {gems} gems from the lifeless body.\n".format(defender=defender, gold=defender.gold, gems=defender.gem)
                defender_fight_description += "{attacker} hits you with a deadly blow.  You fall to the ground and die as {attacker} loots your lifeless body.\n".format(attacker=self.handle)
                self.gold += defender.gold
                self.gem += defender.gem
                self.experience += defender.experience
                self.player_kills += 1
                self.human_fights_left -= 1
                self.save()
                defender.gold = defender.gem = 0
                defender.save()
            else:
                attacker_fight_description += "You hit {defender} with your {weapon} for {damage} damage.\n".format(defender=defender.handle, weapon=self.equipped_weapon.name, damage=damage)
                defender_fight_description += "{attacker} hits you with his {weapon} for {damage} damage.\n".format(attacker=self.handle, weapon=self.equipped_weapon.name, damage=damage)

            if not defender.dead: # defender fights back.
                damage = defender.deal_damage(self)
                if damage == 0:
                    attacker_fight_description += "You skillfully block {defender}'s attack.\n".format(defender=defender.handle)
                    defender_fight_description += "{attacker} skillfully blocks your attack.\n".format(attacker=self.handle)
                elif self.dead:
                    attacker_fight_description += "{defender} attacks you with a deadly blow.  You die.  Your gold and gems have been taken.\n".format(defender=defender.handle)
                    defender_fight_description += "You hit {attacker} with a deadly blow.  He dies and you loot {gold} gold and {gem} gems from his lifeless body.\n".format(attacker=self.handle, gold=self.gold, gem=self.gem)
                    defender.gold += self.gold
                    defender.gem += self.gem
                    defender.experience += self.experience
                    defender.player_kills += 1
                    defender.save()
                    self.gold = self.gem = 0
                    self.save()
                else:
                    attacker_fight_description += "{defender} hits you with the {weapon} for {damage} damage.\n".format(defender=defender.handle, weapon=defender.equipped_weapon.name, damage=damage)
                    defender_fight_description += "You hit {attacker} with your {weapon} for {damage} damage.\n".format(attacker=self, weapon=defender.equipped_weapon.name, damage=damage)
        else: # They fight first.
            attacker_fight_description += "{defender} gets the jump on you and attacks first!\n".format(defender=defender.handle)
            defender_fight_description += "{attacker} tries to swing at you, but you beat him to it and attack first.\n".format(attacker=self.handle)
            damage = defender.deal_damage(self)
            if damage == 0:
                attacker_fight_description += "You skillfully block {defender}'s attack.\n".format(defender=defender.handle)
                defender_fight_description += "{attacker} skillfully blocks your attack.\n".format(attacker=attacker.handle)
            elif self.dead:
                attacker_fight_description += "{defender} attacks you with a deadly blow.  You die.\n".format(defender=defender.handle)
                defender_fight_description += "You deal a deadly blow to {attacker}.  He dies and you loot his body.  You find {gold} gold and {gem} gems!\n".format(attacker=self.handle, gold=self.gold, gem=self.gem)
                defender.gold += self.gold
                defender.gem += self.gem
                defender.experience += self.experience
                defender.player_kills += 1
                defender.save()
                self.gold = self.gem = 0
                self.save()
            else:
                attacker_fight_description += "{defender} hits you with the {weapon} for {damage} damage.\n".format(defender=defender.handle, weapon=defender.equipped_weapon.name, damage=damage)
                defender_fight_description += "You hit {attacker} with your {weapon} for {damage} damage.\n".format(attacker=self.handle, weapon=defender.equipped_weapon.name, damage=damage)
            
            if not self.dead: # you fight back.
                damage = self.deal_damage(defender)
                if damage == 0:
                    attacker_fight_description += "{defender} skillfully blocked your attack!\n".format(defender=defender.handle)
                    defender_fight_description += "You skillfully block {attacker}'s attack!\n".format(attacker=self.handle)
                elif defender.dead:
                    attacker_fight_description += "You hit {defender} with a deadly blow.  {defender} falls to the ground, spits a bit of blood and lets out one last breath before dieing. You loot {gold} gold coins and {gems} gems from the lifeless body.\n".format(defender=defender.handle, gold=defender.gold, gems=defender.gem)
                    defender_fight_description += "{attacker} hits you with a deadly blow. You fall to the ground, spit out a bit of blood and let out one last breath.  {attacker} loots your cold, lifeless body.\n".format(attacker=self.handle)
                    self.gold += defender.gold
                    self.gem += defender.gem
                    self.experience += defender.experience
                    self.player_kills += 1
                    self.human_fights_left -= 1
                    self.save()
                    defender.gold = defender.gem = 0
                    defender.save()
                else:
                    attacker_fight_description += "You hit {defender} with your {weapon} for {damage} damage.\n".format(defender=defender.handle, weapon=self.equipped_weapon.name, damage=damage)
                    defender_fight_description += "{attacker} hits you with his {weapon} for {damage} damage.\n".format(attacker=self.handle, weapon=self.equipped_weapon.name, damage=damage)
        return attacker_fight_description, defender_fight_description
    
    def deal_damage(self, defender):
        random.seed()
        damage = max(0,(((self.strength + self.equipped_weapon.strength) / 2) + random.randint(0, (self.strength + self.equipped_weapon.strength) / 2)) - (defender.defense + defender.equipped_armor.defense)) # actual LORD math
        #damage = choice(range(max(0, (5*(self.strength+self.equipped_weapon.strength))-(4*(defender.defense+defender.equipped_armor.defense))))) # my original faked math
        defender.hit_points -= damage
        if defender.hit_points <= 0:
            defender.dead = True
            defender.last_dead_time = now()
        defender.save()
        return damage
        
        
    def move(self, direction):
        if self.dead:
            raise PlayerDeadException("You are dead.  You're not going anywhere.")
        
        next_y = current_y = self.map_square.y
        next_x = current_x = self.map_square.x
        from_direction_name = direction_name = ''
        
        if direction == 'N':
            next_y -= 1
            direction_name = 'North'
            from_direction_name = 'South'
        elif direction == 'S':
            next_y += 1
            direction_name = 'South'
            from_direction_name = 'North'
        elif direction == 'W':
            next_x -= 1
            direction_name = 'West'
            from_direction_name = 'East'
        elif direction == 'E':
            next_x += 1
            direction_name = 'East'
            from_direction_name = 'West'
        
        try:
            next_map_square = MapSquare.objects.get(world_map=self.world_map, x=next_x, y=next_y)
        except:
            raise InvalidMoveException("You cannot move {direction} from here.".format(direction=direction_name))
            
        if not next_map_square.terrain.passable:
            raise InvalidMoveException("Terrain to the {direction} is not passable.".format(direction=direction_name))
        
        # announce move
        self.map_square.announce_departure(player=self, to_direction=direction_name)
        next_map_square.announce_arrival(player=self, from_direction=from_direction_name)
        
        self.map_square = next_map_square
        self.here_since = now()

        return
    
    def nearby_players(self):
        return self.map_square.player_set.filter(here_since__gt=now()-datetime.timedelta(minutes=10)).exclude(pk=self.pk)
    
    def reset(self):
        self.dead, self.hit_points, self.fights_left, self.human_fights_left, self.seen_bard, self.seen_dragon, self.seen_master, self.seen_violet, self.weird_event, self.done_special, self.flirted = False, self.hit_points_max, self.MAX_FIGHTS, self.MAX_HUMAN_FIGHTS, Player(), False, False, False, False, False, False, False
        self.save()
        return
        
    @property
    def status(self):
        if self.dead:
            return "Dead"
        if self.inn:
            return "Sleeping at Inn"
        if self.here_since < (now() - datetime.timedelta(minutes=10)):
            return "Offline"
        if self.here_since < (now() - datetime.timedelta(minutes=5)):
            return "Idle"
        return "Active"
        
    
    def __unicode__(self):
        return self.handle

class ActivityLog(DatesMixin):
    """Use this model to push messages to any user as needed."""
    ACTIVITY_TYPES = (
        ('pvp_attacker', 'You attack'),
        ('pvp_defender', 'You were attacked'),
        ('event', 'An event occurred'),
        ('arrival', 'A player walked up.'),
        ('departure', 'A player left.'),
    )
    to_player = models.ForeignKey('Player', related_name='activitylog_to_player')
    from_player = models.ForeignKey('Player', related_name='activitylog_from_player')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    message = models.TextField()
    viewed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ('-id',)
        

class Armor(DatesMixin):
    name = models.CharField(max_length=50)
    price = models.IntegerField()
    defense = models.IntegerField()
    
    class Meta:
        verbose_name_plural = "Armor"

    def __unicode__(self):
        return self.name
        
class Weapon(DatesMixin):
    name = models.CharField(max_length=50)
    price = models.IntegerField()
    strength = models.IntegerField()

    def __unicode__(self):
        return self.name
            
class Monster(DatesMixin):
    name = models.CharField(max_length=60)
    level = models.SmallIntegerField(default=1)
    strength = models.IntegerField()
    gold = models.IntegerField()
    weapon = models.CharField(max_length=30, default="")
    experience = models.IntegerField()
    hit_points = models.IntegerField()
    death = models.CharField(max_length=100)
    
    def __unicode__(self):
        return self.name