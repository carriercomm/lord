from django.core.urlresolvers import reverse
from django.db import models
from django.utils.timezone import now

from game.models import DatesMixin

import datetime

class Terrain(DatesMixin):
    name = models.CharField(max_length=20)
    fg_color = models.CharField(max_length=6)
    bg_color = models.CharField(max_length=6)
    character = models.CharField(max_length=1) # what character to use on the map
    turns = models.IntegerField(default=1)
    passable = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = 'Terrain'
        
    def __unicode__(self):
        return self.name
    
class WorldMap(DatesMixin):
    name = models.CharField(max_length=20)
    level_min = models.SmallIntegerField()
    x_size = models.SmallIntegerField(default=10)
    y_size = models.SmallIntegerField(default=10)
    start = models.ForeignKey('MapSquare', default=1)
    
    class Meta:
        ordering = ['level_min',]
        
    def __unicode__(self):
        return self.name
        
    def map_editor_url(self):
        return "<a href='{url}' target='_blank'>edit</a>".format(url=reverse("world_map_edit", kwargs={ "world_map_id": self.id }))
    map_editor_url.allow_tags = True
        
    def full_map_layout(self):
        map_layout = []
        for y in xrange(self.y_size):
            map_layout.append([])
            for x in xrange(self.x_size):
                try:
                    map_layout[y].append(self.mapsquare_set.get(x=x,y=y))
                except:
                    map_layout[y].append(None)

        return map_layout

class MapSquare(DatesMixin):
    world_map = models.ForeignKey('WorldMap')
    x = models.SmallIntegerField()
    y = models.SmallIntegerField()

    terrain = models.ForeignKey('Terrain')
    battle_odds = models.IntegerField() # how likely will a battle occur?
    safe = models.BooleanField(default=False) # can players fight here or not?
    
    class Meta:
        ordering = ('world_map', 'x', 'y')
        unique_together = ('world_map', 'x', 'y') # only one X/Y coordinate per map.
        
    def announce_arrival(self, player, from_direction):
        from players.models import ActivityLog
        activity_logs = []
        for active_player in self.active_players().exclude(pk=player.pk):
            activity_logs.append(ActivityLog(to_player=active_player, from_player=player, activity_type='arrival', message="You see {player} appear from the {from_direction}.".format(player=player.handle, from_direction=from_direction)))
        ActivityLog.objects.bulk_create(activity_logs)
        return
    
    def announce_departure(self, player, to_direction):
        from players.models import ActivityLog
        activity_logs = []
        for active_player in self.active_players().exclude(pk=player.pk):
            activity_logs.append(ActivityLog(to_player=active_player, from_player=player, activity_type='departure', message="You see {player} wander off to the {to_direction}.".format(player=player.handle, to_direction=to_direction)))
        ActivityLog.objects.bulk_create(activity_logs)
        return
        
    def active_players(self):
        return self.player_set.filter(here_since__gt=now()-datetime.timedelta(minutes=10))
    
    def get_surrounding_squares(self):
        return MapSquare.objects.filter(world_map=self.world_map, x__gt=self.x-2, x__lt=self.x+2, y__gt=self.y-2, y__lt=self.y+2)
        
    def get_possible_moves(self):
        possible_moves = {}
        try:
            possible_moves['N'] = MapSquare.objects.get(world_map=self.world_map, x=self.x, y=self.y-1)
        except:
            pass

        try:
            possible_moves['S'] = MapSquare.objects.get(world_map=self.world_map, x=self.x, y=self.y+1)
        except:
            pass
            
        try:
            possible_moves['W'] = MapSquare.objects.get(world_map=self.world_map, x=self.x-1, y=self.y)
        except:
            pass
            
        try:
            possible_moves['E'] = MapSquare.objects.get(world_map=self.world_map, x=self.x+1, y=self.y)
        except:
            pass
            
        return possible_moves
    
    @property
    def is_passable(self):
        return self.terrain.passable

    def __unicode__(self):
        return "{map}/{x}/{y}".format(map=self.world_map, x=self.x, y=self.y)