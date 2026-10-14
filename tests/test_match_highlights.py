import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
import random
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from treys import Card
from gui_pygame import PokerPygameApp
from poker_highlights import HighlightDetector, MatchTracker
from game_view import combination_cards


def cards(text):
    return [Card.new(c) for c in text.split()]


class MatchHighlightTests(unittest.TestCase):
    def setUp(self):
        self.app = PokerPygameApp()
        for slot in self.app.custom_screen.slots:
            slot['enabled'] = slot['idx'] == 0
        self.app.apply_custom_config(self.app.custom_screen.get_launch_config())
        self.engine = self.app.engine
        self.app.game_view.update(5, self.engine)

    def showdown(self, hand='Kh Kc', board='8s 8h 7c Ks Ac'):
        winner = self.engine.get_player(4)
        winner.hand = cards(hand)
        self.engine.get_player(0).hand = cards('Qd Jd')
        self.engine.community_cards = cards(board)
        self.engine.stage = 'SHOWDOWN'
        self.engine.hand_ended = True
        self.engine.pot = 2010
        self.engine.winners_info = [{'player': winner, 'amount': 2010}]
        return winner

    def test_full_house_uses_exact_five_and_rgb_in_all_three_rows(self):
        self.showdown()
        self.app.finish_hand()
        hl = self.app.last_highlight
        self.assertEqual(hl.event_type, 'FULL_HOUSE')
        self.assertEqual(set(hl.best_five), set(cards('Kh Kc Ks 8s 8h')))
        self.assertEqual(set(hl.best_five), combination_cards(tuple(hl.best_five)))
        with patch.object(self.app.game_view, 'paint_card') as paint:
            self.app.draw_modal_popup(pygame.Surface((1280,800)))
        lit = [call.args[1] for call in paint.call_args_list if call.kwargs['highlight']]
        self.assertEqual(len(lit), 10)  # 3 board + 2 private + 5 in the explanation
        self.assertEqual(set(lit), set(hl.best_five))

    def test_pair_has_no_rgb_on_unrelated_kickers(self):
        self.showdown('Ah Ad', '2s 5h 7c Ks Qc')
        self.app.finish_hand()
        hl = self.app.last_highlight
        self.assertEqual(len(hl.best_five), 5)
        self.assertEqual(combination_cards(tuple(hl.best_five)), frozenset(cards('Ah Ad')))

    def test_royal_flush_is_detected(self):
        self.showdown('Ah Kh', 'Qh Jh Th 2s 3c')
        self.app.finish_hand()
        self.assertEqual(self.app.last_highlight.event_type, 'ROYAL_FLUSH')

    def test_real_actions_record_actual_payment_and_raise_cap(self):
        p = self.engine.get_player(4)
        self.engine.current_player_idx = 4
        self.engine.raises_this_round = self.engine.max_raises
        cost = self.engine.get_to_call(p)
        self.assertEqual(self.app.apply_and_track_action(4, 'raise', 20), ('call', cost))
        self.assertEqual(self.app.tracker.current_hand_actions[-1]['amount'], cost)
        self.assertIsNone(self.app.tracker.current_hand_actions[-1]['equity'])

    def test_either_final_actor_records_once_in_human_mode(self):
        for actor in (4, 0):
            with self.subTest(actor=actor):
                self.setUp()
                self.engine.current_player_idx = actor
                self.engine.pot = 1000
                if actor == 4:
                    self.app.handle_human_action('fold')
                else:
                    with patch.object(self.app.ai, 'decide', return_value={
                            'action': 'fold', 'raise_amount': 0}):
                        self.app.execute_next_step()
                self.assertTrue(self.engine.hand_ended)
                self.assertTrue(self.app.game_view.pending_highlight)
                self.assertEqual(len(self.app.tracker.recent_highlights), 1)
                self.app.finish_hand()
                self.assertEqual(len(self.app.tracker.recent_highlights), 1)
                self.assertEqual(self.app.tracker.highest_pot['amount'], 1000)

    def test_fold_does_not_invent_combination_bluff_or_reveal_private_cards(self):
        self.engine.get_player(4).hand = cards('2h 3c')
        self.engine.get_player(0).hand = cards('Ah Kh')
        self.engine.community_cards = cards('Qh Jh Th')
        self.engine.current_player_idx = 4
        self.app.handle_human_action('fold')
        hl = self.app.last_highlight
        self.assertEqual(hl.best_five, [])
        self.assertNotIn(hl.event_type, ('ROYAL_FLUSH', 'BLEFE_PERFEITO'))
        with patch.object(self.app.game_view, 'paint_card') as paint:
            self.app.draw_modal_popup(pygame.Surface((1280,800)))
        private = [c for c in paint.call_args_list if c.args[1] in self.engine.get_player(0).hand]
        self.assertEqual(len(private), 2)
        self.assertTrue(all(c.args[3] and not c.kwargs['highlight'] for c in private))

    def test_counterfactual_is_labeled_and_does_not_change_rng_or_deck(self):
        self.engine.get_player(4).hand = cards('Ah Ad')
        self.engine.get_player(0).hand = cards('2h 3c')
        self.engine.community_cards = cards('As Ac 7d')
        self.engine.current_player_idx = 4
        self.app.apply_and_track_action(4, 'fold')
        state = random.getstate()
        deck = list(self.engine.deck.cards)
        hl = HighlightDetector.analyze_round(self.engine, MatchTracker(), human_mode=True)
        self.assertTrue(hl.has_counterfactual)
        self.assertIn('hipotético', hl.counterfactual_disclaimer)
        self.assertEqual(hl.counterfactual_player, self.engine.get_player(4).name)
        self.assertEqual(random.getstate(), state)
        self.assertEqual(self.engine.deck.cards, deck)
        self.assertEqual(len(hl.board_cards), 3)

    def test_history_and_summary_keyboard_navigation(self):
        self.showdown()
        self.app.finish_hand()
        self.app.game_view.update(5, self.engine)
        self.app.open_curiosities()
        self.assertTrue(self.app.show_modal)
        self.app.game_view.pending_highlight = False
        count = self.engine.hand_count
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.app.handle_events()
        self.assertEqual(self.engine.hand_count, count+1)
        self.assertFalse(self.app.show_modal)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_h))
        self.app.handle_events()
        self.assertTrue(self.app.show_history_modal)


if __name__ == '__main__':
    unittest.main()
