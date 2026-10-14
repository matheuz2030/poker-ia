"""Classic ivory playing cards rendered without external artwork."""
import pygame

SIZE = (340, 490)
IVORY = (250, 244, 226)
GOLD = (184, 150, 91)
SUITS = {'h': '♥', 'd': '♦', 'c': '♣', 's': '♠'}


class AntiqueDeck:
    def __init__(self):
        self.font = pygame.font.SysFont('Georgia', 86, bold=True)
        self.suit_font = pygame.font.SysFont('segoeuisymbol', 78)
        self.hero_font = pygame.font.SysFont('Georgia', 132, bold=True)
        self.hero_suit = pygame.font.SysFont('segoeuisymbol', 132)
        self.cache = {}
        self.mask = pygame.Surface(SIZE, pygame.SRCALPHA)
        pygame.draw.rect(self.mask, (255,255,255), self.mask.get_rect(), border_radius=19)
        self.back = self._base((74, 25, 36))
        for x in range(-480, 820, 32):
            pygame.draw.line(self.back,(104,46,53),(x,22),(x+450,468),2)
            pygame.draw.line(self.back,(104,46,53),(x,468),(x+450,22),2)
        pygame.draw.rect(self.back,GOLD,(19,19,302,452),5,border_radius=12)
        pygame.draw.rect(self.back,GOLD,(30,30,280,430),2,border_radius=9)
        pygame.draw.ellipse(self.back,(74,25,36),(87,163,166,166))
        pygame.draw.ellipse(self.back,GOLD,(87,163,166,166),3)
        emblem=self.hero_suit.render('♠',True,(225,201,152))
        self.back.blit(emblem,emblem.get_rect(center=(170,245)))
        self.back.blit(self.mask,(0,0),special_flags=pygame.BLEND_RGBA_MULT)

    def _base(self, color):
        surface=pygame.Surface(SIZE,pygame.SRCALPHA)
        pygame.draw.rect(surface,color,surface.get_rect(),border_radius=19)
        pygame.draw.rect(surface,(205,190,159),surface.get_rect().inflate(-3,-3),3,border_radius=18)
        return surface

    def front(self, rank, kind):
        key=(rank,kind)
        if key in self.cache:
            return self.cache[key]
        surface=self._base(IVORY)
        color=(161,30,48) if kind in 'hd' else (28,34,32)
        index=pygame.Surface((108,172),pygame.SRCALPHA)
        number=self.font.render(rank,True,color)
        if number.get_width()>98:
            number=pygame.transform.smoothscale(number,(98,number.get_height()))
        index.blit(number,number.get_rect(center=(54,48)))
        suit=self.suit_font.render(SUITS[kind],True,color)
        index.blit(suit,suit.get_rect(center=(54,125)))
        surface.blit(index,(8,6))
        surface.blit(pygame.transform.rotate(index,180),(224,312))
        if rank in ('J','Q','K'):
            pygame.draw.rect(surface,(226,214,187),(112,134,116,224),2,border_radius=48)
            letter=self.hero_font.render(rank,True,color)
            letter=pygame.transform.smoothscale(letter,(min(100,letter.get_width()),112))
            surface.blit(letter,letter.get_rect(center=(170,216)))
            motif=self.suit_font.render(SUITS[kind],True,color)
            surface.blit(motif,motif.get_rect(center=(170,304)))
        else:
            motif=self.hero_suit.render(SUITS[kind],True,color)
            surface.blit(motif,motif.get_rect(center=(170,245)))
            for y in (188,304):
                pygame.draw.line(surface,(217,203,171),(128,y),(212,y),2)
        surface.blit(self.mask,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
        self.cache[key]=surface
        return surface
