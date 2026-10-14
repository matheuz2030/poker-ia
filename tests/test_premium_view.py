"""Presentation acceptance checks; no engine decisions are modified."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
import sys
import itertools
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from gui_pygame import PokerPygameApp


class PremiumPresentationTests(unittest.TestCase):
    def setUp(self):
        self.app=PokerPygameApp()

    def test_every_roster_has_readable_nonoverlapping_hands_and_profiles(self):
        for count in range(1,5):
            for selected in itertools.combinations(range(4),count):
                for slot in self.app.custom_screen.slots:
                    slot['enabled']=slot['idx'] in selected
                self.app.apply_custom_config(self.app.custom_screen.get_launch_config())
                self.app.game_view.update(5,self.app.engine)
                self.app.draw()
                view=self.app.game_view
                regions=view.hit_regions
                profiles=[view.panel_rect(view.profile_centers[p.idx]) for p in self.app.engine.players]
                for index,region in enumerate(regions):
                    rect=region[0]
                    self.assertGreater(rect.height,rect.width)
                    self.assertTrue(pygame.Rect(0,48,1280,670).contains(rect))
                    self.assertFalse(any(rect.colliderect(profile) for profile in profiles))
                    self.assertFalse(any(rect.colliderect(other[0]) for other in regions[index+1:]))
                controls=(self.app.btn_human_fold,self.app.btn_human_check_call,
                          self.app.btn_human_raise,self.app.btn_human_allin,self.app.btn_menu)
                self.assertTrue(all(pygame.Rect(0,718,1280,82).contains(r) for r in controls))

    def test_scene_cache_and_draw_do_not_change_engine_state(self):
        self.app.state='GAME'
        self.app.game_view.update(5,self.app.engine)
        before=(self.app.engine.current_player_idx,self.app.engine.pot,
                tuple((p.idx,p.stack,p.personality,tuple(p.hand)) for p in self.app.engine.players))
        room,table=self.app.game_view.scene_art()
        self.assertIs(room,self.app.game_view.room)
        self.assertIs(table,self.app.game_view.table)
        for size in ((1280,800),(1920,1080),(800,600)):
            self.app.screen=pygame.display.set_mode(size)
            self.app.draw()
        after=(self.app.engine.current_player_idx,self.app.engine.pot,
               tuple((p.idx,p.stack,p.personality,tuple(p.hand)) for p in self.app.engine.players))
        self.assertEqual(before,after)
        self.app.show_history_modal=True
        self.app.draw()

    def test_existing_modals_cover_transient_animations(self):
        order=[]
        class Badge:
            def draw(self,surface):
                order.append('badge')
        self.app.state='GAME'
        self.app.show_history_modal=True
        self.app.floating_badges=[Badge()]
        with patch.object(self.app,'draw_history_modal',side_effect=lambda surface: order.append('modal')):
            self.app.draw()
        self.assertEqual(order,['badge','modal'])


if __name__=='__main__':
    unittest.main()
