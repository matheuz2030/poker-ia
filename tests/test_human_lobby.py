import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
import sys
import itertools
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from gui_pygame import PokerPygameApp
from poker_engine import PokerEngine, Player, PERSONALITY_CONFIG


class HumanLobbyTests(unittest.TestCase):
    def setUp(self):
        self.app = PokerPygameApp()
        self.lobby = self.app.custom_screen

    def launch(self, seats=(0, 1, 2, 3)):
        for slot in self.lobby.slots:
            slot['enabled'] = slot['is_human'] or slot['idx'] in seats
        self.app.apply_custom_config(self.lobby.get_launch_config())
        self.app.game_view.update(5, self.app.engine)

    def test_direct_entry_shared_assets_and_real_profiles(self):
        self.app.menu_screen.click(self.app.menu_screen.versus.center, self.app)
        self.assertEqual(self.app.state, 'CUSTOM_LOBBY')
        self.assertFalse(self.app.menu_screen.info_open)
        self.assertIs(self.lobby.cards, self.app.menu_screen.cards)
        self.assertIs(self.lobby.profiles, PERSONALITY_CONFIG)
        for slot in self.lobby.slots:
            self.assertEqual(slot['name'], self.app.game_view.names[slot['idx']])
        before = self.lobby.pose(0)[0]
        self.lobby.update(.5, (-1,-1))
        self.assertNotEqual(before, self.lobby.pose(0)[0])
        surface = pygame.Surface((1280,800))
        self.lobby.draw(surface)
        for slot in self.lobby.slots:
            self.assertFalse(slot['enabled'])
            self.assertEqual(self.lobby.pose(slot['art'])[3],0)
        start=next(r for r,a,v in self.lobby.controls if a=='start')
        self.assertNotEqual(self.lobby.click(start.center),'START')
        for slot in self.lobby.slots:
            self.lobby.click(self.lobby.rects[slot['art']].center)
            self.assertTrue(slot['enabled'])
            pose=self.lobby.pose(slot['art'])
            self.assertEqual(pose[3],1)
            self.lobby.update(.7,self.lobby.rects[slot['art']].center)
            self.assertEqual(pose,self.lobby.pose(slot['art']))
        self.lobby.draw(surface)
        for rect, action, slot in list(self.lobby.controls):
            if action == 'profile':
                previous = slot['personality']
                self.lobby.click((rect.right-2, rect.centery))
                self.assertNotEqual(previous, slot['personality'])
                self.assertIn(slot['personality'], PERSONALITY_CONFIG)
            elif action == 'speed':
                self.lobby.click(rect.center)
                self.assertEqual(self.lobby.game_speed, slot)
        for rect, action, slot in self.lobby.controls:
            if action == 'toggle':
                self.lobby.click(rect.center)
        self.assertEqual(self.lobby.get_active_count(), 0)
        config=self.lobby.get_launch_config()
        self.assertEqual(len(config['players']),1)
        self.assertEqual(config['players'][0]['idx'],4)
        self.assertTrue(config['players'][0]['is_human'])

    def test_every_roster_runs_to_showdown_with_stable_seats_and_fresh_chips(self):
        self.app.ai.simulations = 20
        for count in (1,2,3,4):
            for seats in itertools.combinations((0,1,2,3),count):
                with self.subTest(seats=seats):
                    old = self.app.engine
                    self.launch(seats)
                    engine = self.app.engine
                    self.assertIsNot(engine, old)
                    self.assertEqual({p.idx for p in engine.players}, set(seats)|{4})
                    self.assertEqual(engine.hand_count, 1)
                    expected_order=[i for i in (0,2,1,4,3) if i in set(seats)|{4}]
                    self.assertEqual(engine.seat_order,expected_order)
                    self.assertTrue(engine.get_player(4).is_human)
                    if 2 in seats:
                        self.assertFalse(engine.get_player(2).is_human)
                        self.assertEqual(engine.get_player(2).name,'Messi')
                    self.assertEqual(sum(p.stack for p in engine.players)+engine.pot,1000*(count+1))
                    self.assertEqual(len({c for p in engine.players for c in p.hand}),2*(count+1))
                    self.assertEqual(self.app.tracker.current_hand_actions, [])
                    for _ in range(200):
                        if engine.hand_ended:
                            break
                        self.app.game_view.update(10,engine)
                        p=engine.get_player(engine.current_player_idx)
                        action='call' if engine.get_to_call(p) else 'check'
                        if p.is_human:
                            self.app.handle_human_action(action)
                        else:
                            with patch.object(self.app.ai,'decide',return_value={
                                'action':action,'raise_amount':0,'equity':50,
                                'pot_odds':0,'is_bluff':False,'justification':'',
                                'hand_class':'','blockers_count':2}):
                                self.app.execute_next_step()
                    self.assertTrue(engine.hand_ended)
                    self.assertEqual(engine.stage,'SHOWDOWN')
                    self.assertEqual(sum(p.stack for p in engine.players),1000*(count+1))
                    self.assertEqual(self.app.game_view.pending_highlight,
                                     self.app.last_highlight.is_major_event or self.app.last_highlight.has_counterfactual)
                    self.app.draw()
                    engine.start_new_hand()
                    self.assertEqual({p.idx for p in engine.players},set(seats)|{4})

    def test_human_wait_and_animation_lock(self):
        self.launch((0,))
        engine=self.app.engine
        engine.current_player_idx=4
        before=(engine.pot,engine.current_player_idx,tuple(engine.history_log))
        with patch.object(self.app.ai,'decide',side_effect=AssertionError('AI called for human')):
            self.app.auto_play=True
            self.app.update()
            self.app.execute_next_step()
        self.assertEqual(before,(engine.pot,engine.current_player_idx,tuple(engine.history_log)))
        self.app.game_view.deal_age=0
        self.app.handle_human_action('all-in',1000)
        self.assertEqual(before,(engine.pot,engine.current_player_idx,tuple(engine.history_log)))

    def test_privacy_even_when_god_mode_is_changed(self):
        self.launch((3,))
        self.app.god_mode=True
        self.app.draw()
        hands=[r for r in self.app.game_view.hit_regions if r[1][0]=='hand']
        self.assertEqual({r[1][1] for r in hands},{4,3})
        self.assertTrue(all(r[3] == (r[1][1]!=4) for r in hands))
        self.app.engine.stage='ENDED'
        self.app.engine.hand_ended=True
        self.app.draw()
        self.assertTrue(all(r[3] for r in self.app.game_view.hit_regions if r[1][:2]==('hand',3)))
        self.app.engine.stage='SHOWDOWN'
        self.app.draw()
        self.assertFalse(any(r[3] for r in self.app.game_view.hit_regions))

    def test_human_mouse_actions_use_event_position(self):
        for action, attr in (('fold','btn_human_fold'),('check','btn_human_check_call'),('call','btn_human_check_call'),
                             ('raise','btn_human_raise'),('all-in','btn_human_allin')):
            with self.subTest(action=action):
                self.launch((0,))
                engine=self.app.engine
                engine.current_player_idx=4
                if action=='call':
                    engine.current_high_bet=engine.get_player(4).current_bet+20
                pygame.event.clear()
                before=engine.get_player(4).stack
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                   pos=getattr(self.app,attr).center,button=1))
                self.app.handle_events()
                human=engine.get_player(4)
                if action=='fold':
                    self.assertFalse(human.is_active)
                elif action=='check':
                    self.assertEqual(human.stack,before)
                else:
                    self.assertLess(human.stack,before)
                self.assertTrue(engine.hand_ended or engine.current_player_idx!=4)

    def test_responsive_controls_and_touch_start(self):
        for size in ((1280,800),(800,600),(390,844),(360,640)):
            self.app.screen=pygame.display.set_mode(size)
            self.lobby.slots[0]['enabled']=True
            self.app.open_custom_setup()
            self.app.draw()
            bounds=pygame.Rect((0,0),size)
            for rect,action,value in self.lobby.controls:
                self.assertTrue(bounds.contains(rect), (size,action,rect))
            start=next(r for r,a,v in self.lobby.controls if a=='start')
            x,y=start.center
            pygame.event.clear()
            pygame.event.post(pygame.event.Event(pygame.FINGERDOWN,x=x/size[0],y=y/size[1],finger_id=1,touch_id=1))
            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,pos=(x,y),button=1,touch=True))
            self.app.handle_events()
            self.assertEqual(self.app.state,'GAME')
            self.assertEqual(self.app.engine.hand_count,1)

    def test_reset_preserves_selection_and_regular_play_restores_ais(self):
        self.launch((3,))
        self.app.engine.get_player(4).stack=50
        self.app.reset_match()
        self.assertEqual({p.idx for p in self.app.engine.players},{4,3})
        self.assertEqual(self.app.engine.get_player(4).stack,1000-self.app.engine.get_player(4).current_bet)
        self.app.state='MENU'
        self.app.start_play()
        self.assertFalse(self.app.is_human_mode)
        self.assertEqual(len(self.app.engine.players),4)
        self.assertFalse(any(p.is_human for p in self.app.engine.players))


class HumanEngineTests(unittest.TestCase):
    def test_short_allin_call_does_not_lower_high_bet(self):
        engine=PokerEngine(players=[Player(0,'A','agressivo'),Player(2,'B','conservador'),Player(3,'C','blefador')])
        engine.current_player_idx=2
        player=engine.get_player(2)
        engine.current_high_bet=100
        player.current_bet=20
        player.stack=30
        engine.acted_this_round={0}
        engine.player_action(2,'all-in',30)
        self.assertEqual(engine.current_high_bet,100)
        self.assertIn(0,engine.acted_this_round)
        self.assertTrue(player.is_all_in)

    def test_invalid_roster_rejected_before_deal(self):
        with self.assertRaises(ValueError):
            PokerEngine(players=[Player(2,'Você','conservador',is_human=True)])


if __name__=='__main__':
    unittest.main()
