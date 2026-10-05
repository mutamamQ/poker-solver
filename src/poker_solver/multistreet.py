"""Finite immutable heads-up flop/turn/river GameState."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Literal

from .cards import validate_unique
from .equity import WeightedCombo
from .evaluator import evaluate_seven
from .model import CHANCE, TERMINAL, Action, InfoKey

Street = Literal["flop", "turn", "river"]
BettingMode = Literal["no-limit", "pot-limit"]


@dataclass(frozen=True, slots=True)
class MultiStreetConfig:
    """Immutable configuration for a multi-street heads-up spot."""

    version: str
    starting_street: Street
    starting_board: tuple[int, ...]
    initial_dead_pot: int
    effective_stack: int
    player0_combos: tuple[WeightedCombo, ...]
    player1_combos: tuple[WeightedCombo, ...]
    allowed_runouts: tuple[tuple[int, ...], ...]
    betting_mode: BettingMode
    wager_targets: tuple[int, ...]
    river_betting: bool = False

    def __post_init__(self) -> None:
        if self.version != "multistreet-v1":
            raise ValueError(f"unsupported version {self.version!r}")
        if self.starting_street not in ("flop", "turn", "river"):
            raise ValueError(f"invalid starting_street {self.starting_street!r}")
        street_sizes = {"flop": 3, "turn": 4, "river": 5}
        expected_size = street_sizes[self.starting_street]
        board = validate_unique(self.starting_board)
        if len(board) != expected_size:
            raise ValueError(
                f"{self.starting_street} requires {expected_size} cards, got {len(board)}"
            )
        object.__setattr__(self, "starting_board", board)
        if (
            not isinstance(self.initial_dead_pot, int)
            or isinstance(self.initial_dead_pot, bool)
            or self.initial_dead_pot < 0
        ):
            raise ValueError("initial_dead_pot must be a non-negative integer")
        if (
            not isinstance(self.effective_stack, int)
            or isinstance(self.effective_stack, bool)
            or self.effective_stack <= 0
        ):
            raise ValueError("effective_stack must be a positive integer")
        if self.betting_mode not in ("no-limit", "pot-limit"):
            raise ValueError(f"invalid betting_mode {self.betting_mode!r}")
        for combo in self.player0_combos + self.player1_combos:
            if not isinstance(combo, WeightedCombo):
                raise ValueError("combos must be WeightedCombo instances")
            if not isfinite(combo.weight) or combo.weight < 0:
                raise ValueError("combo weights must be finite and non-negative")
        if len({combo.cards for combo in self.player0_combos}) != len(self.player0_combos):
            raise ValueError("player0_combos contains duplicate hands")
        if len({combo.cards for combo in self.player1_combos}) != len(self.player1_combos):
            raise ValueError("player1_combos contains duplicate hands")
        board_set = set(board)
        for combo in self.player0_combos + self.player1_combos:
            if board_set.intersection(combo.cards):
                raise ValueError("combo cards overlap with board")
        needed_runout_cards = 5 - len(board)
        if needed_runout_cards == 0 and self.allowed_runouts:
            raise ValueError("river configurations do not accept runouts")
        if needed_runout_cards > 0 and not self.allowed_runouts:
            raise ValueError("flop/turn configurations require allowed_runouts")
        if len(set(self.allowed_runouts)) != len(self.allowed_runouts):
            raise ValueError("allowed_runouts must be unique")
        for runout in self.allowed_runouts:
            validated = validate_unique(runout)
            if len(validated) != needed_runout_cards:
                raise ValueError(f"runouts must contain exactly {needed_runout_cards} cards")
            if board_set.intersection(validated):
                raise ValueError("runout overlaps with starting board")
        if not isinstance(self.river_betting, bool):
            raise ValueError("river_betting must be a boolean")
        for target in self.wager_targets:
            if (
                not isinstance(target, int)
                or isinstance(target, bool)
                or target < 0
            ):
                raise ValueError("wager_targets must be non-negative integers")
        if tuple(sorted(set(self.wager_targets))) != self.wager_targets:
            raise ValueError("wager_targets must be unique and increasing")


@dataclass(frozen=True, slots=True)
class MultiStreetState:
    """Immutable snapshot of a multi-street game state."""

    config: MultiStreetConfig
    private_deal: tuple[tuple[int, int], tuple[int, int]] | None
    board: tuple[int, ...]
    street: Street
    acting_player: int
    pot: int
    committed: tuple[int, int]
    total_contributed: tuple[int, int]
    remaining: tuple[int, int]
    last_raise_increment: int
    history: tuple[Action, ...]
    terminal_reason: str | None

    def current_player(self) -> int:
        return self.acting_player

    def legal_actions(self) -> tuple[Action, ...]:
        if self.acting_player == CHANCE:
            return tuple(action for action, _ in self.chance_outcomes())
        if self.acting_player == TERMINAL:
            return ()
        if self.acting_player not in (0, 1):
            raise ValueError(f"invalid acting_player {self.acting_player}")
        to_call = max(self.committed) - self.committed[self.acting_player]
        call_target = min(
            max(self.committed), self.committed[self.acting_player] + self.remaining[self.acting_player]
        )
        actions: list[Action] = []
        if to_call > 0:
            actions.append(Action("FOLD"))
            if call_target > self.committed[self.acting_player]:
                actions.append(Action("CALL", call_target))
        else:
            actions.append(Action("CHECK"))
        if self.remaining[self.acting_player] > 0:
            pot_before_action = self.pot + sum(self.committed)
            for target in self.config.wager_targets:
                if target <= self.committed[self.acting_player]:
                    continue
                additional = target - self.committed[self.acting_player]
                if additional > self.remaining[self.acting_player]:
                    continue
                if self.config.betting_mode == "pot-limit":
                    max_additional = to_call + pot_before_action + to_call
                    max_raise_to = self.committed[self.acting_player] + max_additional
                    if target > max_raise_to:
                        continue
                min_raise = max(self.committed) + self.last_raise_increment
                if to_call > 0 and target < min_raise:
                    if target < self.committed[self.acting_player] + self.remaining[self.acting_player]:
                        continue
                actions.append(Action("RAISE", target))
        return tuple(actions)

    def chance_outcomes(self) -> tuple[tuple[Action, float], ...]:
        if self.acting_player != CHANCE:
            return ()
        if self.private_deal is None:
            board_set = set(self.board)
            pairs: list[tuple[tuple[int, int], tuple[int, int], float]] = []
            for c0 in self.config.player0_combos:
                if board_set.intersection(c0.cards) or c0.weight == 0:
                    continue
                for c1 in self.config.player1_combos:
                    if board_set.intersection(c1.cards) or c1.weight == 0:
                        continue
                    if set(c0.cards).intersection(c1.cards):
                        continue
                    pairs.append((c0.cards, c1.cards, c0.weight * c1.weight))
            total_weight = sum(w for _, _, w in pairs)
            if total_weight <= 0:
                raise ValueError("no compatible private deals")
            return tuple(
                (Action("DEAL", i), w / total_weight) for i, (_, _, w) in enumerate(pairs)
            )
        else:
            dead = set(self.board).union(self.private_deal[0]).union(self.private_deal[1])
            revealed = self.board[len(self.config.starting_board):]
            sequences = [
                runout
                for runout in self.config.allowed_runouts
                if runout[:len(revealed)] == revealed
                and not set(runout[len(revealed):]).intersection(dead)
            ]
            if not sequences:
                raise ValueError("no legal runouts")
            counts: dict[int, int] = {}
            for runout in sequences:
                card = runout[len(revealed)]
                counts[card] = counts.get(card, 0) + 1
            total = len(sequences)
            return tuple((Action("RUNOUT", card), count / total) for card, count in sorted(counts.items()))

    def child(self, action: Action) -> MultiStreetState:
        if action not in self.legal_actions() and action not in (
            a for a, _ in self.chance_outcomes()
        ):
            raise ValueError(f"illegal action {action}")
        if self.acting_player == CHANCE:
            if self.private_deal is None:
                pairs = []
                board_set = set(self.board)
                for c0 in self.config.player0_combos:
                    if board_set.intersection(c0.cards) or c0.weight == 0:
                        continue
                    for c1 in self.config.player1_combos:
                        if board_set.intersection(c1.cards) or c1.weight == 0:
                            continue
                        if set(c0.cards).intersection(c1.cards):
                            continue
                        pairs.append((c0.cards, c1.cards))
                deal = pairs[action.amount]
                return MultiStreetState(
                    config=self.config,
                    private_deal=deal,
                    board=self.board,
                    street=self.street,
                    acting_player=0,
                    pot=self.pot,
                    committed=self.committed,
                    total_contributed=self.total_contributed,
                    remaining=self.remaining,
                    last_raise_increment=self.last_raise_increment,
                    history=self.history + (action,),
                    terminal_reason=None,
                )
            else:
                dead = set(self.board).union(self.private_deal[0]).union(self.private_deal[1])
                revealed = self.board[len(self.config.starting_board):]
                sequences = [
                    runout
                    for runout in self.config.allowed_runouts
                    if runout[:len(revealed)] == revealed
                    and not set(runout[len(revealed):]).intersection(dead)
                ]
                legal_cards = {runout[len(revealed)] for runout in sequences}
                if action.amount not in legal_cards:
                    raise ValueError(f"illegal runout card {action.amount}")
                new_board = self.board + (action.amount,)
                street_map = {3: "flop", 4: "turn", 5: "river"}
                new_street = street_map[len(new_board)]
                if len(new_board) > 5:
                    raise ValueError("runout produces more than five board cards")
                if len(new_board) == 5 and (
                    any(r == 0 for r in self.remaining) or not self.config.river_betting
                ):
                    h0 = evaluate_seven(self.private_deal[0] + new_board)
                    h1 = evaluate_seven(self.private_deal[1] + new_board)
                    contested = self.pot + sum(self.committed)
                    if h0 > h1:
                        award = (contested, 0)
                    elif h1 > h0:
                        award = (0, contested)
                    else:
                        award = (contested // 2, contested - contested // 2)
                    return MultiStreetState(
                        config=self.config,
                        private_deal=self.private_deal,
                        board=new_board,
                        street=new_street,
                        acting_player=TERMINAL,
                        pot=self.pot,
                        committed=self.committed,
                        total_contributed=self.total_contributed,
                        remaining=self.remaining,
                        last_raise_increment=self.last_raise_increment,
                        history=self.history + (action,),
                        terminal_reason=f"showdown-{new_street}",
                    )
                else:
                    return MultiStreetState(
                        config=self.config,
                        private_deal=self.private_deal,
                        board=new_board,
                        street=new_street,
                        acting_player=CHANCE if any(r == 0 for r in self.remaining) else 0,
                        pot=self.pot + sum(self.committed),
                        committed=(0, 0),
                        total_contributed=self.total_contributed,
                        remaining=self.remaining,
                        last_raise_increment=0,
                        history=self.history + (action,),
                        terminal_reason=None,
                    )
        if action.kind == "FOLD":
            winner = 1 - self.acting_player
            contested = self.pot + sum(self.committed)
            award = (contested, 0) if winner == 0 else (0, contested)
            return MultiStreetState(
                config=self.config,
                private_deal=self.private_deal,
                board=self.board,
                street=self.street,
                acting_player=TERMINAL,
                pot=self.pot,
                committed=self.committed,
                total_contributed=self.total_contributed,
                remaining=self.remaining,
                last_raise_increment=self.last_raise_increment,
                history=self.history + (action,),
                terminal_reason=f"fold-{self.acting_player}",
            )
        if action.kind in ("CALL", "RAISE"):
            new_committed = list(self.committed)
            new_remaining = list(self.remaining)
            paid = action.amount - self.committed[self.acting_player]
            new_committed[self.acting_player] = action.amount
            new_remaining[self.acting_player] -= paid
            new_total = list(self.total_contributed)
            new_total[self.acting_player] += paid
            if action.kind == "RAISE":
                new_increment = action.amount - max(self.committed)
            else:
                new_increment = self.last_raise_increment
            opponent = 1 - self.acting_player
            if action.kind == "CALL" and new_committed[0] != new_committed[1]:
                excess = max(new_committed) - min(new_committed)
                if new_remaining[self.acting_player] == 0:
                    refund_to = 0 if new_committed[0] > new_committed[1] else 1
                    new_committed = list(new_committed)
                    new_committed[refund_to] -= excess
                    new_remaining = list(new_remaining)
                    new_remaining[refund_to] += excess
                    new_total = list(new_total)
                    new_total[refund_to] -= excess
            if action.kind == "CALL":
                if self.street == "river":
                    return MultiStreetState(
                        config=self.config,
                        private_deal=self.private_deal,
                        board=self.board,
                        street=self.street,
                        acting_player=TERMINAL,
                        pot=self.pot,
                        committed=tuple(new_committed),
                        total_contributed=tuple(new_total),
                        remaining=tuple(new_remaining),
                        last_raise_increment=new_increment,
                        history=self.history + (action,),
                        terminal_reason="showdown-river",
                    )
                if new_remaining[0] == 0 or new_remaining[1] == 0:
                    return MultiStreetState(
                        config=self.config,
                        private_deal=self.private_deal,
                        board=self.board,
                        street=self.street,
                        acting_player=CHANCE,
                        pot=self.pot,
                        committed=tuple(new_committed),
                        total_contributed=tuple(new_total),
                        remaining=tuple(new_remaining),
                        last_raise_increment=new_increment,
                        history=self.history + (action,),
                        terminal_reason=None,
                    )
                return MultiStreetState(
                    config=self.config,
                    private_deal=self.private_deal,
                    board=self.board,
                    street=self.street,
                    acting_player=CHANCE,
                    pot=self.pot,
                    committed=tuple(new_committed),
                    total_contributed=tuple(new_total),
                    remaining=tuple(new_remaining),
                    last_raise_increment=new_increment,
                    history=self.history + (action,),
                    terminal_reason=None,
                )
            else:
                return MultiStreetState(
                    config=self.config,
                    private_deal=self.private_deal,
                    board=self.board,
                    street=self.street,
                    acting_player=opponent,
                    pot=self.pot,
                    committed=tuple(new_committed),
                    total_contributed=tuple(new_total),
                    remaining=tuple(new_remaining),
                    last_raise_increment=new_increment,
                    history=self.history + (action,),
                    terminal_reason=None,
                )
        if action.kind == "CHECK":
            opponent = 1 - self.acting_player
            previous_was_check = bool(self.history and self.history[-1].kind == "CHECK")
            if previous_was_check and self.street == "river":
                return MultiStreetState(
                    config=self.config,
                    private_deal=self.private_deal,
                    board=self.board,
                    street=self.street,
                    acting_player=TERMINAL,
                    pot=self.pot,
                    committed=self.committed,
                    total_contributed=self.total_contributed,
                    remaining=self.remaining,
                    last_raise_increment=self.last_raise_increment,
                    history=self.history + (action,),
                    terminal_reason="showdown-river",
                )
            if previous_was_check:
                return MultiStreetState(
                    config=self.config,
                    private_deal=self.private_deal,
                    board=self.board,
                    street=self.street,
                    acting_player=CHANCE,
                    pot=self.pot,
                    committed=self.committed,
                    total_contributed=self.total_contributed,
                    remaining=self.remaining,
                    last_raise_increment=self.last_raise_increment,
                    history=self.history + (action,),
                    terminal_reason=None,
                )
            else:
                return MultiStreetState(
                    config=self.config,
                    private_deal=self.private_deal,
                    board=self.board,
                    street=self.street,
                    acting_player=opponent,
                    pot=self.pot,
                    committed=self.committed,
                    total_contributed=self.total_contributed,
                    remaining=self.remaining,
                    last_raise_increment=self.last_raise_increment,
                    history=self.history + (action,),
                    terminal_reason=None,
                )
        raise ValueError(f"unhandled action {action}")

    def information_state_key(self, player: int) -> InfoKey:
        if player not in (0, 1):
            raise ValueError("player must be 0 or 1")
        if self.private_deal is None:
            raise ValueError("information key requires a private deal")
        own_cards = tuple(sorted(self.private_deal[player]))
        public_history = tuple(action for action in self.history if action.kind != "DEAL")
        return (
            self.config.version,
            player,
            own_cards,
            self.board,
            public_history,
            self.pot,
            self.committed,
            self.remaining,
            self.config.betting_mode,
        )

    def returns(self) -> tuple[float, float]:
        if self.acting_player != TERMINAL:
            raise ValueError("returns only available at terminal nodes")
        if self.terminal_reason is None:
            raise ValueError("terminal node missing reason")
        if self.private_deal is None:
            raise ValueError("terminal node missing private deal")
        contested = self.pot + sum(self.committed)
        if self.terminal_reason.startswith("fold-"):
            folder_idx = int(self.terminal_reason.removeprefix("fold-"))
            winner = 1 - folder_idx
            award = (contested, 0) if winner == 0 else (0, contested)
        else:
            h0 = evaluate_seven(self.private_deal[0] + self.board)
            h1 = evaluate_seven(self.private_deal[1] + self.board)
            if h0 > h1:
                award = (contested, 0)
            elif h1 > h0:
                award = (0, contested)
            else:
                award = (contested // 2, contested - contested // 2)
        dead_pot = self.config.initial_dead_pot
        u0 = award[0] - self.total_contributed[0] - dead_pot / 2
        u1 = award[1] - self.total_contributed[1] - dead_pot / 2
        return (u0, u1)


def create_root(config: MultiStreetConfig) -> MultiStreetState:
    """Create the root chance node for a multi-street game."""
    return MultiStreetState(
        config=config,
        private_deal=None,
        board=config.starting_board,
        street=config.starting_street,
        acting_player=CHANCE,
        pot=config.initial_dead_pot,
        committed=(0, 0),
        total_contributed=(0, 0),
        remaining=(config.effective_stack, config.effective_stack),
        last_raise_increment=0,
        history=(),
        terminal_reason=None,
    )
