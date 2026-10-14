import os
os.environ['SDL_VIDEODRIVER']='dummy'
import sys
import random
import re
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from treys import Card
from gui_pygame import PokerPygameApp, PLAYER_CONFIG
from poker_engine import PokerEngine, Player


class TutorialTests(unittest.TestCase):
    def setUp(self):
        self.app=PokerPygameApp()
        self.guide=self.app.tutorial_screen
        pygame.event.clear()

    def snapshot(self):
        e=self.app.engine
        return (id(e),e.pot,e.hand_count,e.current_player_idx,tuple(e.history_log),
                tuple((p.idx,p.stack,tuple(p.hand),p.personality) for p in e.players),random.getstate())

    def test_menu_entry_and_every_example_leave_the_game_untouched(self):
        self.app.draw()
        before=self.snapshot()
        self.app.menu_screen.click(self.app.menu_screen.tutorial_button.center,self.app)
        self.assertEqual(self.app.state,'TUTORIAL')
        with patch.object(self.app.ai,'decide',side_effect=AssertionError('No tutorial AI decisions')):
            for page in range(6):
                self.guide.select(page)
                self.app.draw()
                self.app.update()
                if page==1:
                    for _ in range(4):
                        self.guide.reveal()
                        self.app.draw()
        self.assertEqual(before,self.snapshot())
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE))
        self.app.handle_events()
        self.assertEqual(self.app.state,'MENU')

    def test_return_preserves_custom_lobby_selection_profiles_and_speed(self):
        self.app.open_custom_setup()
        slot=self.app.custom_screen.slots[2]
        slot['enabled']=True
        slot['personality']='blefador'
        self.app.custom_screen.game_speed=5
        before=self.app.custom_screen.get_launch_config()
        self.app.draw()
        button=next(r for r,a,v in self.app.custom_screen.controls if a=='tutorial')
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,pos=button.center,button=1))
        self.app.handle_events()
        self.assertEqual(self.app.state,'TUTORIAL')
        self.guide.select(5)
        self.app.draw()
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,pos=self.guide.next.center,button=1))
        self.app.handle_events()
        self.assertEqual(self.app.state,'CUSTOM_LOBBY')
        self.assertEqual(before,self.app.custom_screen.get_launch_config())

    def test_six_short_screens_without_technical_vocabulary(self):
        self.app.open_tutorial()
        self.assertEqual(len(self.guide.pages),6)
        forbidden=re.compile(r'\b(fold|flop|turn|river|equity|pot odds|raise|call|all-in|showdown|monte carlo)\b',re.I)
        for index,page in enumerate(self.guide.pages):
            self.assertLessEqual(len(page['text'].split()),45)
            self.guide.select(index)
            self.app.draw()
            visible=' '.join((page['title'],page['text'],*self.guide.drawn_labels))
            self.assertIsNone(forbidden.search(visible),visible)
        self.assertFalse(hasattr(self.guide,'presentation'))

    def test_opening_button_keyboard_and_reset(self):
        self.app.open_tutorial()
        self.guide.select(1)
        before=self.snapshot()
        for expected in (0,3,4,5):
            self.app.draw()
            self.assertEqual(sum(not c['hidden'] for c in self.guide.drawn_cards),expected)
            button=next(r for r,a,v in self.guide.controls if a=='reveal')
            self.guide.click(button.center)
        self.assertEqual(self.guide.open_cards,0)
        self.guide.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_o))
        self.assertEqual(self.guide.open_cards,3)
        self.guide.select(0)
        self.guide.select(1)
        self.assertEqual(self.guide.open_cards,0)
        self.assertEqual(before,self.snapshot())

    def test_pair_and_fictitious_outcomes_match_the_real_evaluator(self):
        self.app.open_tutorial()
        self.app.draw()
        marked=[c['code'] for c in self.guide.drawn_cards if c['marked']]
        self.assertEqual(marked,['As','Ad'])
        self.assertEqual(len(self.guide.drawn_cards),7)
        evaluator=self.app.engine.evaluator
        score=evaluator.evaluate([Card.new(c) for c in ('Ad','Kh','9s','3d','2c')],
                                 [Card.new(c) for c in ('As','7c')])
        self.assertEqual(evaluator.class_to_string(evaluator.get_rank_class(score)),'Pair')
        self.app.ai.simulations=10
        win=[Card.new('Kh'),Card.new('Kd')]
        loss=[Card.new('6h'),Card.new('7c')]
        with patch('poker_ai.random.sample',side_effect=[win]*6+[loss]*4):
            chance,_=self.app.ai.calculate_multiway_equity(
                [Card.new('As'),Card.new('Ad')],[Card.new(c) for c in ('2c','3d','4h','5s','9c')],1)
        self.assertEqual(chance,60)

    def test_real_roster_and_comparison_actions(self):
        self.app.open_tutorial()
        self.guide.select(4)
        self.app.draw()
        self.assertEqual({p['seat'] for p in self.guide.players},set(PLAYER_CONFIG))
        expected={'equilibrado':('call',0),'agressivo':('raise',25),'conservador':('fold',0),'blefador':('call',0)}
        for p in self.guide.players:
            self.assertEqual(p['name'],self.app.game_view.names[p['seat']])
            self.assertIn(p['name'],self.guide.drawn_labels)
            player=Player(p['seat'],p['name'],p['profile'])
            player.hand=[Card.new('As'),Card.new('Kd')]
            with patch.object(self.app.ai,'calculate_multiway_equity',return_value=(30,2)),patch('poker_ai.random.random',return_value=.9):
                decision=self.app.ai.decide(player,[],25,100,1)
            self.assertEqual((decision['action'],decision['raise_amount']),expected[p['profile']])
        with patch.object(self.app.ai,'calculate_multiway_equity',return_value=(30,2)),patch('poker_ai.random.random',return_value=.1):
            decision=self.app.ai.decide(Player(3,'Neymar Jr.','blefador'),[],25,100,1)
        self.assertEqual((decision['action'],decision['raise_amount']),('raise',100))
        self.assertEqual(self.app.ai.calculate_pot_odds(25,100),20)

    def test_motor_limits_the_example_request_to_available_chips(self):
        e=PokerEngine(players=[Player(0,'A','equilibrado',100),Player(1,'B','conservador',100)])
        e.pot=0
        e.current_high_bet=0
        e.current_player_idx=0
        for p in e.players:
            p.stack=100
            p.current_bet=p.total_bet_this_hand=0
        e.player_action(0,'raise',200)
        self.assertEqual(e.get_player(0).stack,0)
        self.assertTrue(e.get_player(0).is_all_in)
        self.assertEqual(e.pot,100)

    def test_desktop_no_scroll_mobile_content_reachable_and_controls_fit(self):
        self.app.open_tutorial()
        for size in ((1280,800),(1920,1080),(800,600),(360,640)):
            self.app.screen=pygame.display.set_mode(size)
            for index in range(6):
                self.guide.select(index)
                self.app.draw()
                bounds=pygame.Rect((0,0),size)
                self.assertTrue(bounds.contains(self.guide.viewport))
                for rect,action,value in self.guide.controls:
                    self.assertTrue(bounds.contains(rect),(size,index,action))
                if size[0]>=700:
                    self.assertEqual(self.guide.max_scroll,0,(size,index))
                self.guide.handle_event(pygame.event.Event(pygame.MOUSEWHEEL,y=-1000))
                self.assertEqual(self.guide.scroll,self.guide.max_scroll)
                self.app.draw()
                self.assertGreaterEqual(self.guide.scroll+self.guide.viewport.height,self.guide.rendered_bottom)

    def test_touch_keyboard_navigation_and_final_return(self):
        self.app.screen=pygame.display.set_mode((360,640))
        self.app.open_tutorial()
        self.app.draw()
        x,y=self.guide.next.center
        for kind in (pygame.FINGERDOWN,pygame.FINGERUP):
            pygame.event.post(pygame.event.Event(kind,x=x/360,y=y/640,finger_id=1,touch_id=1))
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,pos=(x,y),button=1,touch=True))
        self.app.handle_events()
        self.assertEqual(self.guide.page,1)
        for key,expected in ((pygame.K_SPACE,2),(pygame.K_RIGHT,3),(pygame.K_LEFT,2),(pygame.K_RETURN,3)):
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=key))
            self.app.handle_events()
            self.assertEqual(self.guide.page,expected)
        self.guide.select(5)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE))
        self.app.handle_events()
        self.assertEqual(self.app.state,'MENU')


if __name__=='__main__':
    unittest.main()
