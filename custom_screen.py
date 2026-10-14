"""Human match setup using the original lobby's artwork and animation renderer."""
import math
import pygame
from menu_screen import MenuScreen, GOLD, IVORY
from poker_engine import PERSONALITY_CONFIG


class CustomLobbyScreen(MenuScreen):
    def __init__(self, menu, player_config, game_view):
        super().__init__()
        # Share the actual menu textures and font cache, including grayscale art.
        self.cards = menu.cards
        self.background_source = menu.background_source
        self.font_cache = menu.font_cache
        self.slots = []
        for seat, cfg in player_config.items():
            key = game_view.avatar_keys[seat]
            self.slots.append(dict(idx=seat, name=game_view.names[seat],
                                   character=cfg['full_name'],
                                   art=self.character_keys.index(key),
                                   is_human=False, enabled=False,
                                   personality=cfg['engine_personality']))
        self.human_seat = len(player_config)
        self.profiles = PERSONALITY_CONFIG
        self.game_speed = 1
        self.controls = []

    def layout(self, size):
        changed = size != self.size
        super().layout(size)
        if not changed:
            return
        # Reserve space below the original animated cards for per-seat controls.
        if self.portrait:
            self.base_height = min(self.base_height * .64, max(28, self.area.height/2-100))
            self.homes = [(x, y-42) for x,y in self.homes]
        else:
            self.base_height *= .78
            self.homes = [(x, y-46) for x,y in self.homes]
        self.focus_height = self.base_height * 1.12
        self.focus = (self.size[0]/2, self.area.centery-46)
        self.home_rects = [self.card_rect(i, xy, self.base_height) for i,xy in enumerate(self.homes)]

    def get_active_count(self):
        return sum(s['enabled'] for s in self.slots)

    def update(self, dt, pointer=None):
        # Hover never selects, moves, or recolors a character in this lobby.
        self.clock_time += dt

    def pose(self, i):
        slot = next(s for s in self.slots if s['art'] == i)
        x,y = self.homes[i]
        if not slot['enabled']:
            y += math.sin(self.clock_time*.9+i)*2
        return (x,y), self.base_height, 0, float(slot['enabled'])

    def toggle(self, slot):
        slot['enabled'] = not slot['enabled']

    def draw(self, surface):
        self.layout(surface.get_size())
        w,h = self.size
        surface.blit(self.background, (0,0))
        for i in sorted(range(len(self.cards)), key=lambda i:self.progress[i]):
            self.draw_card(surface, i)
        header = pygame.Surface((w,self.header_h), pygame.SRCALPHA)
        header.fill((0,0,0,120))
        surface.blit(header,(0,0))
        self.text(surface, 'IA VS HUMANO', max(23,min(40,w//16)), GOLD,
                  (w//2,self.header_h*.36), True)
        help_button=pygame.Rect(0,0,min(300,w-32),26)
        help_button.center=(w//2,round(self.header_h*.76))
        self.button(surface,help_button,'COMO JOGAR & GUIA DAS IAs',size=11)
        self.controls=[(help_button,'tutorial',None)]
        pointer=pygame.mouse.get_pos()
        for slot in self.slots:
            i=slot['art']
            x,y=self.homes[i]
            width= min(240, (w-52)//2 if self.portrait else (w-100)//4)
            top=round(y+self.base_height/2+12)
            name='VOCÊ' if slot['is_human'] else slot['name']
            self.text(surface,name,14,GOLD,(x,top),True)
            toggle=pygame.Rect(round(x-width/2),top+13,width,30)
            label='VOCÊ · ATIVO' if slot['is_human'] else ('SELECIONADO' if slot['enabled'] else 'DESATIVADO')
            self.button(surface,toggle,label,int(toggle.collidepoint(pointer)),slot['enabled'],size=12)
            if not slot['is_human']:
                self.controls.append((toggle,'toggle',slot))
                profile=pygame.Rect(toggle.x,toggle.bottom+5,width,30)
                title=self.profiles[slot['personality']]['title'].split(' (')[0]
                self.button(surface,profile,'< '+title+' >',int(profile.collidepoint(pointer)),size=12)
                if slot['enabled']:
                    self.controls.append((profile,'profile',slot))
        footer=pygame.Surface((w,self.footer_h),pygame.SRCALPHA)
        footer.fill((0,0,0,220))
        surface.blit(footer,(0,h-self.footer_h))
        speed_y=h-self.footer_h+10
        self.text(surface,'Velocidade das IAs',12,IVORY,(w//2-100,speed_y+16))
        for j,speed in enumerate((1,2,5)):
            rect=pygame.Rect(w//2+j*50,speed_y,44,30)
            self.button(surface,rect,f'{speed}x',primary=self.game_speed==speed,size=12)
            self.controls.append((rect,'speed',speed))
        back=pygame.Rect(22,h-68,max(90,min(210,w//3)),44)
        start=pygame.Rect(back.right+16,h-68,w-back.right-38,44)
        self.button(surface,back,'VOLTAR',size=13)
        ready = self.get_active_count() > 0
        self.button(surface,start,'INICIAR PARTIDA' if ready else 'SELECIONE UMA IA',primary=ready,size=max(10,min(18,start.width//14)))
        self.text(surface, f'VOCÊ · HUMANO  |  {self.get_active_count()+1}/5 jogadores',
                  12, GOLD, (w//2,h-self.footer_h+47), True)
        self.controls.extend(((back,'back',None),(start,'start',None)))

    def click(self, position):
        for rect,action,value in self.controls:
            if not rect.collidepoint(position):
                continue
            if action=='tutorial':
                return 'TUTORIAL'
            if action=='toggle':
                self.toggle(value)
            elif action=='profile':
                keys=list(self.profiles)
                direction=-1 if position[0]<rect.centerx else 1
                value['personality']=keys[(keys.index(value['personality'])+direction)%len(keys)]
            elif action=='speed':
                self.game_speed=value
            elif action=='back':
                return 'BACK'
            elif action=='start' and self.get_active_count():
                return 'START'
            return 'CHANGED'
        i=self.hit(position)
        if i is not None:
            self.toggle(next(s for s in self.slots if s['art']==i))
            return 'CHANGED'
        return 'NONE'

    def get_launch_config(self):
        players = [dict(idx=s['idx'], name=s['name'], personality=s['personality'],
                        is_human=False, enabled=True)
                   for s in self.slots if s['enabled']]
        players.append(dict(idx=self.human_seat, name='Você', personality='',
                            is_human=True, enabled=True))
        return dict(game_speed=self.game_speed, is_human_mode=True, players=players)
