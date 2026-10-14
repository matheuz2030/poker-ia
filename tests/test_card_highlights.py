import os
os.environ['SDL_VIDEODRIVER']='dummy'
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from treys import Card
from game_view import combination_cards
from gui_pygame import PokerPygameApp


def cards(text):
    return tuple(Card.new(card) for card in text.split())


class CombinationTests(unittest.TestCase):
    def test_made_hands_and_only_relevant_cards(self):
        cases=(
            ('As Kd 9c 6h 3s',''),
            ('As Ad','As Ad'),
            ('As Ad 9c 6h 3s','As Ad'),
            ('As Ad 9c 9h 3s','As Ad 9c 9h'),
            ('As Ad Ac 6h 3s','As Ad Ac'),
            ('As Ad Ac Ah Ks 3d 2c','As Ad Ac Ah'),
            ('As Ad Ac Kh Ks 3d 2c','As Ad Ac Kh Ks'),
            ('As 2d 3c 4h 5s Kd Qc','As 2d 3c 4h 5s'),
            ('As Js 8s 6s 3s Kd Qc','As Js 8s 6s 3s'),
            ('9s Ts Js Qs Ks 2d 3c','9s Ts Js Qs Ks'),
            ('As Ks Qs Js Ts 2d 3c','As Ks Qs Js Ts'),
            ('As Ad Ks Kd Qs Qd 2c','As Ad Ks Kd'),
        )
        for source,expected in cases:
            with self.subTest(hand=source):
                self.assertEqual(combination_cards(cards(source)),frozenset(cards(expected)))


class CardHighlightViewTests(unittest.TestCase):
    def setUp(self):
        self.app=PokerPygameApp()
        for slot in self.app.custom_screen.slots:
            slot['enabled']=True
        self.app.apply_custom_config(self.app.custom_screen.get_launch_config())
        self.engine=self.app.engine
        self.view=self.app.game_view
        self.view.update(5,self.engine)
        for p,hand in zip(self.engine.players,('Kc Qs','Jc Td','6c 7s','4c 5s','8s 9d')):
            p.hand=list(cards(hand))
        self.engine.community_cards=list(cards('Kh 2c 3d'))
        self.view.board_count=3

    def test_hidden_opponents_and_undealt_board_never_contribute(self):
        self.app.god_mode=True
        self.app.draw()
        self.assertEqual(self.view.highlighted_cards,set())
        self.engine.get_player(4).hand=list(cards('As Ad'))
        self.engine.community_cards=list(cards('Ah 2c 3d'))
        self.view.board_count=0
        self.app.draw()
        self.assertEqual(self.view.highlighted_cards,set(cards('As Ad')))
        self.view.board_count=3
        self.app.draw()
        self.assertEqual(self.view.highlighted_cards,set(cards('As Ad Ah')))

    def test_showdown_and_ai_modes(self):
        self.engine.stage='SHOWDOWN'
        self.app.draw()
        self.assertEqual(self.view.highlighted_cards,set())
        self.engine.stage='FLOP'
        self.app.is_human_mode=False
        self.app.god_mode=False
        self.app.draw()
        self.assertEqual(self.view.highlighted_cards,set())
        self.app.god_mode=True
        self.app.draw()
        self.assertEqual(self.view.highlighted_cards,set(cards('Kh Kc')))

    def test_board_pair_does_not_glow_but_connected_hole_cards_do(self):
        self.engine.get_player(4).hand=list(cards('Qs 3h'))
        self.engine.community_cards=list(cards('Kh 9c 2c 2d 6c'))
        self.view.board_count=5
        self.app.draw()
        self.assertEqual(self.view.highlighted_cards,set())
        self.engine.get_player(4).hand=list(cards('Ks 3h'))
        with patch.object(self.view,'draw_rgb_border',wraps=self.view.draw_rgb_border) as border:
            self.app.draw()
            self.assertEqual(self.view.highlighted_cards,set(cards('Kh Ks 2c 2d')))
            hand_rect=next(r[0] for r in self.view.hit_regions if r[1]==('hand',4,0))
            self.assertTrue(any(call.args[1]==hand_rect for call in border.call_args_list))

    def test_board_straight_is_not_a_hole_card_combination(self):
        self.engine.get_player(4).hand=list(cards('8h 2h'))
        self.engine.community_cards=list(cards('8c 9c Td Jh Qs'))
        self.view.board_count=5
        self.app.draw()
        self.assertEqual(self.view.highlighted_cards,set())

    def test_enlarged_cards_remain_clickable_and_rgb_animates(self):
        self.engine.get_player(4).hand=list(cards('As Ad'))
        self.app.draw()
        hand=next(r for r in self.view.hit_regions if r[1]==('hand',4,0))
        board=[r for r in self.view.hit_regions if r[1][0]=='board']
        self.assertGreater(hand[0].height,84)
        self.assertGreater(board[0][0].height,98)
        self.assertTrue(self.view.click(hand[0].center))
        self.assertEqual(self.view.selected,('hand',4,0))
        for previous,current in zip(board,board[1:]):
            self.assertLess(previous[0].right,current[0].left)
        surface=pygame.Surface((120,150))
        rect=pygame.Rect(20,20,76,110)
        with patch('game_view.pygame.time.get_ticks',return_value=0):
            self.view.draw_rgb_border(surface,rect)
        first=pygame.image.tobytes(surface,'RGB')
        surface.fill((0,0,0))
        with patch('game_view.pygame.time.get_ticks',return_value=800):
            self.view.draw_rgb_border(surface,rect)
        self.assertNotEqual(first,pygame.image.tobytes(surface,'RGB'))
        with patch.object(self.view,'draw_rgb_border') as border:
            self.view.paint_card(surface,cards('As')[0],(50,70),True,highlight=True)
            border.assert_not_called()


if __name__=='__main__':
    unittest.main()
