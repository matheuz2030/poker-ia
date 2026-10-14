"""Presentation and animation layer. Poker state remains owned by PokerEngine."""
import math
import colorsys
from collections import Counter
from functools import lru_cache
from itertools import combinations
from treys import Card, Evaluator
import os
from dataclasses import dataclass
import pygame

GOLD=(210,174,107)
WHITE=(244,237,220)


@lru_cache(maxsize=1024)
def combination_cards(cards):
    """Cards in the best made combination, without unrelated kickers."""
    if len(cards) < 2:
        return frozenset()
    if len(cards) >= 5:
        evaluator = Evaluator()
        best = min(combinations(cards, 5), key=lambda hand: evaluator.evaluate([], list(hand)))
        score = evaluator.evaluate([], list(best))
        kind = evaluator.class_to_string(evaluator.get_rank_class(score))
        if kind == 'High Card':
            return frozenset()
        if kind in ('Straight', 'Flush', 'Straight Flush', 'Royal Flush', 'Full House'):
            return frozenset(best)
        cards = best
    counts = Counter(Card.get_rank_int(card) for card in cards)
    return frozenset(card for card in cards if counts[Card.get_rank_int(card)] > 1)


@dataclass
class CardFlight:
    index: int
    card: int
    origin: tuple
    destination: tuple
    delay: float
    duration: float
    elapsed: float = 0.0

    @property
    def progress(self):
        return max(0.0,min(1.0,(self.elapsed-self.delay)/self.duration))

    @property
    def done(self):
        return self.elapsed >= self.delay+self.duration


class GameView:
    avatar_keys=('ronaldo','mbappe','messi','neymar')
    names=('Ronaldo','Mbappé','Messi','Neymar Jr.')
    personalities=('Calculista','Agressivo','Cauteloso','Blefador')
    profile_centers=((640,100),(1145,270),(640,661),(135,270))
    hand_centers=((640,201),(1010,385),(640,548),(270,385))
    angles=(0,0,0,0)
    hand_scale=1.12
    board_scale=1.22
    human_profile_centers=((430,100),(1145,270),(850,100),(135,270),(640,661))
    human_hand_centers=((430,207),(1010,385),(850,207),(270,385),(640,548))
    human_angles=(0,0,0,0,0)
    human_seat_order=(0,2,1,4,3)

    def __init__(self,renderer):
        self.renderer=renderer
        root=os.path.join(os.path.dirname(__file__),'assets','game')
        self.room,self.table=self.scene_art()
        self.table_rect=self.table.get_rect(topleft=(80,136))
        self.avatars=[]
        for key in self.avatar_keys:
            image=pygame.image.load(os.path.join(root,key+'.jpg')).convert()
            width,height=image.get_size()
            # Frame the faces near the top of the original portrait, without stretching.
            side=round(width*(.60 if key=='messi' else .70))
            left=round(width*(.27 if key=='messi' else .20))
            region=pygame.Rect(min(left,width-side),round(height*.02),side,side)
            avatar=pygame.transform.smoothscale(image.subsurface(region),(64,64)).convert_alpha()
            mask=pygame.Surface((64,64),pygame.SRCALPHA)
            pygame.draw.circle(mask,(255,255,255),(32,32),31)
            avatar.blit(mask,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
            self.avatars.append(avatar)
        # A neutral person icon represents the actual human, never a footballer.
        human_avatar=pygame.Surface((64,64),pygame.SRCALPHA)
        pygame.draw.circle(human_avatar,(24,40,53),(32,32),31)
        pygame.draw.circle(human_avatar,(210,174,107),(32,23),10)
        pygame.draw.ellipse(human_avatar,(210,174,107),(13,36,38,24))
        self.avatars.append(human_avatar)
        self.fonts={n:pygame.font.SysFont('segoeui',n,bold=n>=17) for n in (10,11,12,13,14,15,16,17,18,20,24,28,30)}
        self.title_font=pygame.font.SysFont('Georgia',25)
        self.flights=[]
        self.board_count=0
        self.hand_key=None
        self.hit_regions=[]
        self.selected=None
        self.on_card_click=None
        self.last_card_event=None
        self.pending_highlight=False
        self.deal_age=0.0
        self.highlighted_cards=set()

    @staticmethod
    def flourish(surface, center, scale=1, color=GOLD):
        """Symmetric engraved scrollwork, drawn as smooth paths and leaves."""
        cx,cy=center
        def point(x,y):
            return (round(cx+x*scale),round(cy+y*scale))
        pygame.draw.polygon(surface,color,[point(0,-6),point(5,0),point(0,6),point(-5,0)],1)
        for side in (-1,1):
            path=[point(side*t, -8*math.sin(t/70*math.pi)) for t in range(7,99)]
            pygame.draw.aalines(surface,color,False,path)
            for offset in (24,52,80):
                for sign in (-1,1):
                    leaf=[point(side*(offset+t),sign*10*math.sin(t/19*math.pi)-5)
                          for t in range(20)]
                    pygame.draw.aalines(surface,color,False,leaf)
            scroll=[point(side*(100+11*r*math.cos(t)), -4+11*r*math.sin(t))
                    for t,r in ((t/14,1-t/130) for t in range(120))]
            pygame.draw.aalines(surface,color,False,scroll)

    @staticmethod
    @lru_cache(maxsize=1)
    def scene_art():
        path=os.path.join(os.path.dirname(__file__),'assets','game','table_classic_ornate_v2.png')
        room=pygame.transform.smoothscale(pygame.image.load(path).convert(),(1280,800))
        # The cropped table shares the exact scene pixels, so geometry and hit
        # regions remain unchanged while the materials gain realistic depth.
        table=room.subsurface(pygame.Rect(80,136,1120,540)).copy()
        return room,table

    @staticmethod
    def panel_rect(center):
        return pygame.Rect(round(center[0]-104),round(center[1]-41),208,82)

    @staticmethod
    @lru_cache(maxsize=128)
    def panel_art(size, color, border, radius):
        art=pygame.Surface(size,pygame.SRCALPHA)
        for y in range(size[1]):
            shine=8*(1-y/max(1,size[1]-1))**2
            pygame.draw.line(art,tuple(min(255,round(c+shine)) for c in color),(0,y),(size[0],y))
        mask=pygame.Surface(size,pygame.SRCALPHA)
        pygame.draw.rect(mask,(255,255,255),mask.get_rect(),border_radius=radius)
        art.blit(mask,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
        pygame.draw.rect(art,border,art.get_rect(),1,border_radius=radius)
        inset=art.get_rect().inflate(-6,-6)
        pygame.draw.rect(art,tuple(round(c*.45) for c in border),inset,1,border_radius=max(3,radius-2))
        if size[1]>=70:
            for x in (10,size[0]-11):
                for y in (10,size[1]-11):
                    pygame.draw.polygon(art,border,[(x-2,y),(x,y-2),(x+2,y),(x,y+2)])
            pygame.draw.line(art,tuple(round(c*.6) for c in border),(72,16),(72,size[1]-16))
        return art

    @staticmethod
    def panel(surface, rect, color=(27,24,25), border=(99,79,54), radius=12):
        shadow=pygame.Surface(rect.inflate(18,18).size,pygame.SRCALPHA)
        pygame.draw.rect(shadow,(0,0,0,65),shadow.get_rect().inflate(-6,-6),border_radius=radius+3)
        surface.blit(shadow,(rect.x-9,rect.y-4))
        surface.blit(GameView.panel_art(rect.size,color,border,radius),rect)

    @staticmethod
    def chip_pile(surface, center, amount):
        x,y=center
        height=min(5,max(1,amount//60))
        for offset in range(height):
            cy=y-offset*3
            pygame.draw.ellipse(surface,(19,13,14),(x-15,cy-4,30,12))
            pygame.draw.ellipse(surface,(112,35,48),(x-14,cy-6,28,11))
            pygame.draw.ellipse(surface,(211,175,105),(x-14,cy-6,28,11),1)
            for dx in (-9,0,9):
                pygame.draw.line(surface,(234,217,178),(x+dx,cy-5),(x+dx+1,cy-2),2)
        pygame.draw.ellipse(surface,(213,181,118),(x-7,cy-4,14,7),1)

    @property
    def busy(self):
        return bool(self.flights) or self.deal_age < .8

    def sync(self,engine):
        key=(id(engine),engine.hand_count)
        if key!=self.hand_key:
            human_mode=any(p.is_human and p.idx==4 for p in engine.players)
            self.profile_centers=self.human_profile_centers if human_mode else type(self).profile_centers
            self.hand_centers=self.human_hand_centers if human_mode else type(self).hand_centers
            self.angles=self.human_angles if human_mode else type(self).angles
            self.hand_key=key
            self.board_count=0
            self.flights=[]
            self.selected=None
            self.last_card_event=None
            self.pending_highlight=False
            self.deal_age=0.0
            self.highlighted_cards.clear()
            for p in engine.players:
                i=p.idx
                if getattr(p, 'custom_name', ''):
                    p.name = p.custom_name
                elif getattr(p, 'is_human', False):
                    p.name = "Você"
                else:
                    p.name = self.names[i]

    def board_destination(self,index):
        return (452+94*index,384)

    def queue_board(self,engine,player_idx,speed):
        self.sync(engine)
        queued={f.index for f in self.flights}
        duration=max(.25,1.15/speed)
        next_delay=0.0
        for index in range(self.board_count,len(engine.community_cards)):
            if index in queued:
                continue
            self.flights.append(CardFlight(index,engine.community_cards[index],self.hand_centers[player_idx],self.board_destination(index),next_delay,duration))
            next_delay+=duration*.55

    def update(self,dt,engine):
        self.sync(engine)
        self.deal_age+=dt
        for flight in self.flights:
            flight.elapsed+=dt
            if flight.done:
                self.board_count=max(self.board_count,flight.index+1)
        self.flights=[flight for flight in self.flights if not flight.done]

    def text(self,surface,message,size,center,color=WHITE,max_width=None):
        image=self.fonts[size].render(message,True,color)
        if max_width and image.get_width()>max_width:
            image=pygame.transform.smoothscale(image,(max_width,image.get_height()))
        surface.blit(image,image.get_rect(center=tuple(map(round,center))))

    def paint_card(self,surface,card,center,hidden,angle=0,scale=1,flip=1,identity=None,highlight=False):
        art=self.renderer.get_card_back() if hidden or flip<0 else self.renderer.get_card_front(card)
        art=pygame.transform.smoothscale(art,(max(2,round(68*scale*abs(flip))),round(98*scale)))
        if angle:
            art=pygame.transform.rotate(art,angle)
        rect=art.get_rect(center=tuple(map(round,center)))
        shadow=pygame.Surface(rect.inflate(12,12).size,pygame.SRCALPHA)
        pygame.draw.rect(shadow,(0,0,0,105),shadow.get_rect(),border_radius=8)
        surface.blit(shadow,(rect.x-2,rect.y+2))
        surface.blit(art,rect)
        if highlight and not hidden and flip >= 1:
            self.draw_rgb_border(surface,rect)
        if identity is not None:
            self.hit_regions.append((rect,identity,card,hidden))
            if self.selected==identity:
                pygame.draw.rect(surface,GOLD,rect.inflate(6,6),2,border_radius=6)

    def draw_rgb_border(self, surface, rect):
        phase=(pygame.time.get_ticks()/2400.0)%1
        glow=pygame.Surface(rect.inflate(20,20).size,pygame.SRCALPHA)
        for padding,alpha in ((14,20),(8,45)):
            color=tuple(round(c*255) for c in colorsys.hsv_to_rgb(phase, .85, 1))
            pygame.draw.rect(glow,(*color,alpha),glow.get_rect().inflate(padding-20,padding-20),
                             4,border_radius=10)
        surface.blit(glow,(rect.x-10,rect.y-10))
        for inset in range(4):
            color=tuple(round(c*255) for c in colorsys.hsv_to_rgb((phase+inset/4)%1,.85,1))
            pygame.draw.rect(surface,color,rect.inflate(6-2*inset,6-2*inset),1,border_radius=7)

    @staticmethod
    def hand_visible(app, player):
        if app.is_human_mode:
            return player.is_human or (app.engine.stage=='SHOWDOWN' and player.is_active)
        return app.god_mode or app.engine.hand_ended

    def update_combination_highlights(self, app):
        board=tuple(app.engine.community_cards[:self.board_count])
        highlighted=set()
        for player in app.engine.players:
            if (not player.is_active or not self.hand_visible(app,player)
                    or (app.is_human_mode and not player.is_human)):
                continue
            hand=tuple(player.hand)
            combo=combination_cards(hand+board)
            # A board-only pair (or a hole card used only as kicker) is not a connection.
            if not combo.intersection(hand):
                continue
            if len(board)==5:
                evaluator=app.engine.evaluator
                if evaluator.evaluate(list(board),list(hand)) >= evaluator.evaluate([],list(board)):
                    continue
            highlighted.update(combo)
        self.highlighted_cards=highlighted

    def draw(self,surface,app):
        engine=app.engine
        self.sync(engine)
        self.hit_regions=[]
        self.update_combination_highlights(app)
        surface.blit(self.room,(0,0))
        surface.blit(self.table,self.table_rect)
        for p in engine.players:
            i=p.idx
            x,y=self.profile_centers[i]
            active=not engine.hand_ended and engine.current_player_idx==i
            panel=self.panel_rect((x,y))
            border=GOLD if active else (92,74,54)
            self.panel(surface,panel,(35,28,28) if active else (25,23,24),border)
            if active:
                pygame.draw.rect(surface,GOLD,(panel.x+1,panel.y+20,3,42),border_radius=2)
            avatar=pygame.transform.smoothscale(self.avatars[i],(48,48))
            surface.blit(avatar,(panel.x+12,panel.y+16))
            pygame.draw.circle(surface,(211,178,113),(panel.x+36,panel.y+40),26,1)
            pygame.draw.circle(surface,(92,65,43),(panel.x+36,panel.y+40),29,1)
            for angle in range(0,360,30):
                theta=math.radians(angle)
                cx,cy=panel.x+36,panel.y+40
                pygame.draw.aaline(surface,border,(cx+27*math.cos(theta),cy+27*math.sin(theta)),
                                   (cx+29*math.cos(theta),cy+29*math.sin(theta)))
            name=p.custom_name or ('Você' if p.is_human else self.names[i])
            self.text(surface,name,16,(x+25,y-21),WHITE,132)
            profiles={'equilibrado':'Calculista','agressivo':'Agressivo','conservador':'Cauteloso','blefador':'Blefador'}
            profile='Jogador humano' if p.is_human else profiles.get(p.personality,p.personality)
            self.text(surface,profile,11,(x+25,y-2),(164,153,135),132)
            self.text(surface,f'{p.stack:,} fichas',17,(x+25,y+21),GOLD,132)
            hx,hy=self.hand_centers[i]
            for j,card in enumerate(p.hand):
                center=(hx+(j-.5)*90,hy)
                age=max(0,min(1,(self.deal_age-j*.12-i*.08)/.5))
                t=age*age*(3-2*age)
                center=(640+(center[0]-640)*t,384+(center[1]-384)*t)
                self.paint_card(surface,card,center,not self.hand_visible(app,p),0,self.hand_scale,
                                identity=('hand',i,j),highlight=card in self.highlighted_cards and p.is_active)
            label=p.last_action or ('SUA VEZ' if active and p.is_human else ('PENSANDO' if active else ''))
            if label:
                action_center=(hx,hy+77) if i in (1,3) else (hx+149,hy)
                tag=pygame.Rect(0,0,126,24)
                tag.center=action_center
                fill=(70,29,38) if 'FOLD' in label else (33,36,28)
                self.panel(surface,tag,fill,(116,94,62),8)
                self.text(surface,label,10,tag.center,GOLD,116)
        pot=pygame.Rect(522,264,236,38)
        self.panel(surface,pot,(12,36,29),(125,108,68),10)
        self.chip_pile(surface,(493,286),engine.pot)
        self.chip_pile(surface,(787,286),engine.pot)
        self.text(surface,'POTE',11,(559,283),(164,157,128))
        self.text(surface,f'{engine.pot:,}',28,(662,281),WHITE,160)
        stages={'PREFLOP':'PRÉ-FLOP','FLOP':'FLOP','TURN':'TURN','RIVER':'RIVER','SHOWDOWN':'SHOWDOWN','ENDED':'ENCERRADA'}
        self.text(surface,stages.get(engine.stage,engine.stage),11,(640,315),GOLD)
        flying_indices={f.index for f in self.flights}
        for j in range(5):
            center=self.board_destination(j)
            if j<len(engine.community_cards) and j<self.board_count and j not in flying_indices:
                self.paint_card(surface,engine.community_cards[j],center,False,scale=self.board_scale,
                                identity=('board',j),highlight=engine.community_cards[j] in self.highlighted_cards)
            else:
                slot=pygame.Rect(0,0,round(68*self.board_scale),round(98*self.board_scale))
                slot.center=center
                pygame.draw.rect(surface,(16,46,36),slot,border_radius=7)
                pygame.draw.rect(surface,(67,91,64),slot,1,border_radius=7)
                self.text(surface,'·',20,center,(91,111,79))
        for flight in self.flights:
            if flight.elapsed<flight.delay:
                continue
            t=flight.progress
            eased=t*t*(3-2*t)
            ox,oy=flight.origin
            dx,dy=flight.destination
            center=(ox+(dx-ox)*eased,oy+(dy-oy)*eased-math.sin(math.pi*t)*65)
            flip=-math.cos(math.pi*t)
            self.paint_card(surface,flight.card,center,False,angle=math.sin(math.pi*t)*18,
                            scale=self.board_scale+.15*math.sin(math.pi*t),flip=flip)
        current=engine.get_player(engine.current_player_idx)
        if engine.hand_ended:
            message='Mão encerrada  ·  '+', '.join(w['player'].name for w in engine.winners_info)
        elif current.is_human:
            message='Sua vez  ·  Escolha sua ação abaixo'
        elif app.auto_play:
            message=current.name+' está pensando…'
        else:
            message='Partida pausada  ·  Espaço para continuar'
        self.text(surface,message,13,(640,465),GOLD if current.is_human else WHITE,480)
        if self.last_card_event is not None:
            event=self.last_card_event
            detail='Carta oculta' if event['hidden'] else 'Carta selecionada: '+app.card_label(event['card'])
            self.text(surface,detail,10,(640,483),(163,167,144),460)
        elif current.last_telemetry:
            telemetry=current.last_telemetry
            self.text(surface,f"Equity {telemetry['equity']:.0f}%  ·  Pot odds {telemetry['pot_odds']:.0f}%",10,(640,483),(163,167,144))

    def click(self,position):
        for rect,identity,card,hidden in reversed(self.hit_regions):
            if rect.collidepoint(position):
                self.selected=identity
                self.last_card_event={'identity':identity,'card':card,'hidden':hidden}
                if self.on_card_click:
                    self.on_card_click(dict(self.last_card_event))
                return True
        return False
