"""Six short visual lessons. Examples never execute or change a real hand."""
import pygame
from treys import Card
from menu_screen import GOLD, IVORY

GREEN=(109,183,137)
RED=(174,84,101)
MUTED=(180,167,147)


class TutorialScreen:
    def __init__(self, menu, chip_renderer=None):
        self.menu=menu
        self.chip_renderer=chip_renderer
        self.pages=[]
        self.page=0
        self.scroll=0
        self.max_scroll=0
        self.rendered_bottom=0
        self.controls=[]
        self.touch_start=None
        self.touch_last=None
        self.open_cards=0
        self.size=(1280,800)
        self.drawn_cards=[]
        self.drawn_labels=[]

    def configure(self, app, player_config):
        self.renderer=app.game_view.renderer
        self.avatars=app.game_view.avatars
        self.players=[dict(seat=seat,name=app.game_view.names[seat],
                           profile=cfg['engine_personality']) for seat,cfg in player_config.items()]
        self.pages=[
            dict(title='Como se ganha?',text='Combine suas duas cartas com as cinco da mesa para formar a melhor combinação de cinco cartas. Neste exemplo, dois ases formam um par. Também vence quem permanece quando todos os outros desistem.'),
            dict(title='Como as cartas aparecem?',text='Primeiro aparecem três cartas juntas, depois a quarta e a última. Entre essas aberturas, você pode desistir, passar sem apostar, pagar ou aumentar. Apostar todas as fichas compromete o saldo restante.'),
            dict(title='Como a IA pensa?',text='Ela observa suas próprias cartas e testa várias possibilidades para as cartas desconhecidas. Conta os resultados e estima suas chances. Não olha as cartas escondidas dos rivais. Os dez testes desenhados aqui são fictícios.'),
            dict(title='Vale pagar para continuar?',text='Há 100 fichas no centro. Pagar 25 forma um total de 125. Nesse modelo simples, precisa vencer pelo menos 20% das vezes para compensar. A chance estimada de 30% supera esse preço; o perfil decide como agir.'),
            dict(title='Por que os personagens agem diferente?',text='No mesmo cenário, cada perfil aceita um risco diferente. Você pode trocar os perfis no lobby.'),
            dict(title='Quem controla as regras?',text='A IA sugere uma ação. O motor confere a vez, o saldo e as regras, depois atualiza a mesa. Pedir 200 com apenas 100 permite apostar só 100. A IA não adivinha cartas nem garante vitória.')]
        self.page=0
        self.scroll=0
        self.open_cards=0
        self.layout(app.screen.get_size())

    def layout(self,size):
        self.size=size
        w,h=size
        self.wide=w>=700
        margin=24 if self.wide else 16
        self.back=pygame.Rect(margin,16,108 if self.wide else 90,32)
        self.viewport=pygame.Rect(margin,148,w-margin*2,h-222)
        width=min(190,(w-112)//2)
        self.prev=pygame.Rect(margin,h-57,width,40)
        self.next=pygame.Rect(w-margin-width,h-57,width,40)

    def select(self,index):
        self.page=max(0,min(len(self.pages)-1,index))
        self.scroll=0
        self.open_cards=0

    def advance(self,direction):
        if direction>0 and self.page==len(self.pages)-1:
            return 'BACK'
        self.select(self.page+direction)
        return 'CHANGED'

    def reveal(self):
        sequence=(0,3,4,5)
        self.open_cards=sequence[(sequence.index(self.open_cards)+1)%len(sequence)]

    def click(self,pos):
        for rect,action,value in self.controls:
            if not rect.collidepoint(pos):
                continue
            if action=='back': return 'BACK'
            if action=='prev': return self.advance(-1)
            if action=='next': return self.advance(1)
            if action=='reveal': self.reveal()
            return 'CHANGED'
        return 'NONE'

    def handle_event(self,event):
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1 and not getattr(event,'touch',False):
            return self.click(event.pos)
        if event.type==pygame.KEYDOWN:
            if event.key==pygame.K_ESCAPE: return 'BACK'
            if event.key in (pygame.K_RIGHT,pygame.K_SPACE,pygame.K_RETURN): return self.advance(1)
            if event.key==pygame.K_LEFT: return self.advance(-1)
            if event.key==pygame.K_o and self.page==1: self.reveal()
            elif event.key in (pygame.K_DOWN,pygame.K_PAGEDOWN):
                self.scroll=min(self.max_scroll,self.scroll+80)
            elif event.key in (pygame.K_UP,pygame.K_PAGEUP):
                self.scroll=max(0,self.scroll-80)
        elif event.type==pygame.MOUSEWHEEL:
            self.scroll=max(0,min(self.max_scroll,self.scroll-event.y*48))
        elif event.type==pygame.FINGERDOWN:
            self.touch_start=self.touch_last=(event.x*self.size[0],event.y*self.size[1])
        elif event.type==pygame.FINGERMOTION and self.touch_last is not None:
            point=(event.x*self.size[0],event.y*self.size[1])
            self.scroll=max(0,min(self.max_scroll,self.scroll+self.touch_last[1]-point[1]))
            self.touch_last=point
        elif event.type==pygame.FINGERUP and self.touch_start is not None:
            point=(event.x*self.size[0],event.y*self.size[1])
            start=self.touch_start
            self.touch_start=self.touch_last=None
            if abs(start[0]-point[0])+abs(start[1]-point[1])<12:
                return self.click(point)
        return 'NONE'

    def wrap(self,text,size,width,bold=False):
        font=self.menu.font(size,bold)
        line=''
        for word in text.split():
            proposed=(line+' '+word).strip()
            if line and font.size(proposed)[0]>width:
                yield line
                line=word
            else:
                line=proposed
        if line: yield line

    def label(self,surface,text,center,size=20,color=IVORY,bold=False,width=None):
        width=width or surface.get_width()-24
        lines=list(self.wrap(text,size,width,bold))
        line_h=size+6
        top=center[1]-line_h*(len(lines)-1)/2
        for index,line in enumerate(lines):
            self.menu.text(surface,line,size,color,(round(center[0]),round(top+index*line_h)),bold)
        self.drawn_labels.append(text)

    def panel(self,surface,rect,color=(38,30,32),border=(117,93,58)):
        pygame.draw.rect(surface,color,rect,border_radius=12)
        pygame.draw.rect(surface,border,rect,1,border_radius=12)

    def card_row(self,surface,codes,center,height,hidden=(),marked=()):
        width=round(height*68/98)
        gap=max(7,round(width*.15))
        start=center[0]-(len(codes)*width+(len(codes)-1)*gap)/2
        rects=[]
        for index,code in enumerate(codes):
            secret=index in hidden
            art=self.renderer.get_card_back() if secret else self.renderer.get_card_front(Card.new(code))
            art=pygame.transform.smoothscale(art,(width,height))
            rect=art.get_rect(topleft=(round(start+index*(width+gap)),round(center[1]-height/2)))
            pygame.draw.rect(surface,(12,16,15),rect.move(3,5),border_radius=6)
            surface.blit(art,rect)
            if index in marked and not secret:
                pygame.draw.rect(surface,GREEN,rect.inflate(6,6),3,border_radius=7)
            rects.append(rect)
            self.drawn_cards.append(dict(code=code,hidden=secret,rect=rect,marked=index in marked))
        return rects

    def chips(self,surface,center,count=3):
        # Use the same chip artwork as the live table.
        if self.chip_renderer:
            art=self.chip_renderer.get_chip((151,48,64),30)
            for index in range(count):
                surface.blit(art,(round(center[0]-15),round(center[1]-index*4-15)))
        else:
            pygame.draw.circle(surface,GOLD,tuple(map(round,center)),14,3)

    def draw_winning_hand(self,surface,w,h):
        if self.wide:
            self.label(surface,'SUAS DUAS CARTAS',(w*.22,28),19,GOLD,True)
            self.card_row(surface,('As','7c'),(w*.22,h*.54),min(144,h-95),marked=(0,))
            self.label(surface,'CINCO CARTAS DA MESA',(w*.67,28),19,GOLD,True)
            self.card_row(surface,('Ad','Kh','9s','3d','2c'),(w*.67,h*.54),min(124,round(w*.13)),marked=(0,))
            self.label(surface,'Os dois ases formam um par',(w/2,h-22),21,GREEN,True)
        else:
            self.label(surface,'Suas duas cartas',(w/2,18),17,GOLD,True)
            self.card_row(surface,('As','7c'),(w/2,85),86,marked=(0,))
            self.label(surface,'Cinco cartas da mesa',(w/2,156),17,GOLD,True)
            self.card_row(surface,('Ad','Kh','9s','3d','2c'),(w/2,211),min(68,round((w-48)/5*98/68)),marked=(0,))
            self.label(surface,'Dois ases = um par',(w/2,270),18,GREEN,True)

    def draw_opening(self,surface,w,h):
        self.label(surface,'Mesa compartilhada por todos',(w/2,26),21 if self.wide else 17,GOLD,True)
        card_h=min(130,h-150) if self.wide else 70
        self.card_row(surface,('Ad','Kh','9s','3d','2c'),(w/2,h*.38 if self.wide else 91),card_h,
                      hidden=tuple(range(self.open_cards,5)))
        groups=(('Três primeiras',3),('Quarta carta',4),('Última carta',5))
        cell_w=min(230,(w-30)//3)
        for index,(text,count) in enumerate(groups):
            rect=pygame.Rect(0,0,cell_w-8,38 if self.wide else 50)
            rect.center=(round(w/2+(index-1)*cell_w),round(h*.72 if self.wide else 169))
            self.panel(surface,rect,(32,70,48) if self.open_cards>=count else (38,30,32))
            self.label(surface,text,rect.center,16 if self.wide else 13,GREEN if self.open_cards>=count else MUTED,width=rect.width-8)
        button=pygame.Rect(0,0,min(310,w-36),42)
        button.center=(w//2,round(h-25 if self.wide else 241))
        self.menu.button(surface,button,'Recomeçar exemplo' if self.open_cards==5 else 'Abrir próxima carta',primary=True,size=16 if self.wide else 14)
        self.local_controls.append((button,'reveal',None))

    def draw_thinking(self,surface,w,h):
        card_h=min(78,round(h*.25)) if self.wide else 57
        for x,label,secret in ((w*.27,'Cartas da IA',False),(w*.73,'Cartas dos rivais',True)):
            self.label(surface,label,(x,21),19 if self.wide else 15,GOLD,True,width=w*.45)
            self.card_row(surface,('As','Qs'),(x,min(80,round(h*.25)) if self.wide else 68),card_h,hidden=(0,1) if secret else ())
        labels=('Observa','Testa possibilidades','Estima chances','Escolhe')
        if self.wide:
            cell_w=(w-44)/4
            for index,label in enumerate(labels):
                rect=pygame.Rect(round(16+index*cell_w),round(h*.43),round(cell_w-12),min(49,max(46,round(h*.15))))
                self.panel(surface,rect)
                self.label(surface,label,rect.center,17,GOLD,True,width=rect.width-12)
                if index<3: self.label(surface,'→',(rect.right+6,rect.centery),17,GOLD)
            circles_y=round(h*.72)
        else:
            for index,label in enumerate(labels):
                rect=pygame.Rect(24,112+index*36,w-48,30)
                self.panel(surface,rect)
                self.label(surface,label,rect.center,15,GOLD,True)
            circles_y=282
        spacing=min(70,(w-40)/10)
        for index in range(10):
            x=round(w/2+(index-4.5)*spacing)
            pygame.draw.circle(surface,GREEN if index<6 else RED,(x,circles_y),17 if self.wide else 10)
        self.label(surface,'10 testes fictícios: 6 vitórias e 4 derrotas',(w/2,circles_y+39),18 if self.wide else 14,GOLD,width=w-24)

    def draw_price(self,surface,w,h):
        labels=('Fichas no centro','Para continuar','Total após pagar')
        numbers=(100,25,125)
        for index,(label,value) in enumerate(zip(labels,numbers)):
            if self.wide:
                cell_w=(w-60)//3
                rect=pygame.Rect(20+index*(cell_w+10),16,cell_w,min(125,round(h*.40)))
            else:
                rect=pygame.Rect(16,10+index*77,w-32,67)
            self.panel(surface,rect)
            self.chips(surface,(rect.x+35,rect.centery+8))
            self.label(surface,label,(rect.centerx+15,rect.y+23),17 if self.wide else 14,MUTED,width=rect.width-65)
            self.label(surface,str(value),(rect.centerx+15,rect.y+(round(rect.height*.65) if self.wide else 48)),36 if self.wide else 24,IVORY,True)
        top=round(h*.51) if self.wide else 265
        bar_x=24
        bar_w=w-48
        for index,(label,value,color) in enumerate((('Preço: 25 de 125 = 20%',20,GOLD),('Chance estimada neste exemplo: 30%',30,GREEN))):
            y=top+index*62
            self.label(surface,label,(w/2,y),19 if self.wide else 14,color,True)
            pygame.draw.rect(surface,(61,52,47),(bar_x,y+19,bar_w,13),border_radius=6)
            pygame.draw.rect(surface,color,(bar_x,y+19,round(bar_w*value/100),13),border_radius=6)

    def draw_profiles(self,surface,w,h):
        self.label(surface,'Exemplo: chance de 30% · preço de 20%',(w/2,21),20 if self.wide else 14,GOLD,True,width=w-20)
        columns=4 if self.wide else 2
        cell_w=(w-28)//columns
        row_h=h-55 if self.wide else 205
        compact=self.wide and h<300
        details={
            'equilibrado':('PAGA','Segue o preço e a chance.'),
            'agressivo':('AUMENTA','Pressiona com apostas maiores.'),
            'conservador':('DESISTE','Prefere uma margem de segurança.'),
            'blefador':('PAGA OU TENTA ASSUSTAR','Pode apostar para fazer outros desistirem.')}
        for index,player in enumerate(self.players):
            rect=pygame.Rect(14+index%columns*cell_w,47+index//columns*row_h,cell_w-10,row_h-10)
            self.panel(surface,rect)
            avatar_h=(48 if compact else 64) if self.wide else 43
            image=pygame.transform.smoothscale(self.avatars[player['seat']],(avatar_h,avatar_h))
            surface.blit(image,image.get_rect(center=(rect.centerx,rect.y+avatar_h/2+12)))
            self.label(surface,player['name'],(rect.centerx,rect.y+avatar_h+27),(17 if compact else 21) if self.wide else 16,IVORY,True,width=rect.width-10)
            action,body=details[player['profile']]
            self.label(surface,action,(rect.centerx,rect.y+avatar_h+(52 if compact else 65)),(14 if compact else 19) if self.wide else 13,GREEN if index<2 else GOLD,True,width=rect.width-12)
            self.label(surface,body,(rect.centerx,rect.bottom-(39 if compact else 38)),(13 if compact else 17) if self.wide else 13,MUTED,width=rect.width-14)

    def draw_rules(self,surface,w,h):
        data=(('A IA sugere','Apostar 200'),('O motor confere','Saldo: 100'),('A mesa atualiza','Aposta: 100'))
        for index,(label,value) in enumerate(data):
            if self.wide:
                width=(w-60)//3
                rect=pygame.Rect(18+index*(width+12),24,width,min(170,round(h*.55)))
            else:
                rect=pygame.Rect(18,index*97+10,w-36,80)
            self.panel(surface,rect)
            self.label(surface,label,(rect.centerx,rect.y+27),22 if self.wide else 17,GOLD,True)
            self.label(surface,value,(rect.centerx,rect.y+(round(rect.height*.63) if self.wide else 57)),28 if self.wide else 20,IVORY,True)
            if index<2:
                self.label(surface,'→' if self.wide else '↓',(rect.right+6,rect.centery) if self.wide else (rect.centerx,rect.bottom+9),19,GOLD)
        self.label(surface,'Apenas as fichas disponíveis podem ser apostadas.',(w/2,h-34 if self.wide else 323),21 if self.wide else 16,GREEN,True,width=w-30)

    def draw(self,surface):
        self.layout(surface.get_size())
        w,h=self.size
        self.menu.layout(self.size)
        surface.blit(self.menu.background,(0,0))
        shade=pygame.Surface(self.size,pygame.SRCALPHA)
        shade.fill((12,9,12,230))
        surface.blit(shade,(0,0))
        self.drawn_labels=[]
        self.drawn_cards=[]
        self.controls=[(self.back,'back',None),(self.prev,'prev',None),(self.next,'next',None)]
        self.menu.button(surface,self.back,'VOLTAR',size=12)
        self.label(surface,'GUIA VISUAL',(w-98,32),13,GOLD,True,width=145)
        title_size=36 if self.wide else 23
        self.label(surface,self.pages[self.page]['title'],(w/2,84),title_size,IVORY,True,width=w-36)
        self.label(surface,'Exemplos ilustrativos · cerca de 5 minutos',(w/2,128),14 if self.wide else 12,MUTED)
        chart_h=min(330,max(210,self.viewport.height-140)) if self.wide else (300,280,350,385,465,360)[self.page]
        body_size=24 if w>=1100 else 20 if self.wide else 17
        body_lines=list(self.wrap(self.pages[self.page]['text'],body_size,self.viewport.width-40))
        body_top=chart_h+30
        content_h=body_top+len(body_lines)*(body_size+9)+20
        content=pygame.Surface((self.viewport.width,max(content_h,self.viewport.height)),pygame.SRCALPHA)
        self.panel(content,content.get_rect(),(29,23,26),(87,69,47))
        self.local_controls=[]
        drawers=(self.draw_winning_hand,self.draw_opening,self.draw_thinking,self.draw_price,self.draw_profiles,self.draw_rules)
        drawers[self.page](content,self.viewport.width,chart_h)
        for index,line in enumerate(body_lines):
            self.menu.text(content,line,body_size,IVORY,(self.viewport.width//2,body_top+index*(body_size+9)))
        self.max_scroll=max(0,content_h-self.viewport.height)
        self.scroll=max(0,min(self.scroll,self.max_scroll))
        surface.blit(content,self.viewport,pygame.Rect(0,int(self.scroll),self.viewport.width,self.viewport.height))
        for rect,action,value in self.local_controls:
            mapped=rect.move(self.viewport.x,self.viewport.y-int(self.scroll)).clip(self.viewport)
            if mapped.height: self.controls.append((mapped,action,value))
        self.rendered_bottom=content_h
        if self.max_scroll:
            height=max(28,round(self.viewport.height*self.viewport.height/content_h))
            y=self.viewport.y+round((self.viewport.height-height)*self.scroll/self.max_scroll)
            pygame.draw.rect(surface,GOLD,(self.viewport.right-4,y,3,height),border_radius=2)
        self.menu.button(surface,self.prev,'ANTERIOR',size=13)
        self.menu.button(surface,self.next,'CONCLUIR' if self.page==5 else 'PRÓXIMO',primary=True,size=13)
        self.label(surface,f'{self.page+1} / 6',(w/2,h-36),17,GOLD,True)
