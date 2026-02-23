#!/usr/bin/env python3
"""
Oregon Trail v2 (terminal, from-scratch rebuild)

Run:
  python3 oregon_trail_v2.py

What changed from the base clone:
- Multiple professions with different starting money/risk modifiers.
- Named landmarks with milestone events.
- Party morale system (affects health and event risk).
- More event variety (weather, robbery, animal attack, wagon damage).
- Forts (shops) at selected landmarks.
- Cleaner architecture and balancing constants in one place.
"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple


# ---------------------------
# Utilities
# ---------------------------

def clamp(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, x))


def ask_choice(prompt: str, choices: Dict[str, str], default: str | None = None) -> str:
    keys = list(choices.keys())
    while True:
        print(prompt)
        for k, desc in choices.items():
            print(f"  [{k}] {desc}")

        if default:
            raw = input(f"Select ({'/'.join(keys)}) [default {default}]: ").strip().lower()
            if raw == "":
                return default
        else:
            raw = input(f"Select ({'/'.join(keys)}): ").strip().lower()

        if raw in choices:
            return raw
        print("Invalid choice. Try again.\n")


def ask_int(prompt: str, lo: int, hi: int, default: int | None = None) -> int:
    while True:
        label = f"{prompt} ({lo}-{hi})"
        if default is not None:
            label += f" [default {default}]"
        raw = input(label + ": ").strip()
        if raw == "" and default is not None:
            return default
        try:
            val = int(raw)
            if lo <= val <= hi:
                return val
        except ValueError:
            pass
        print("Invalid number. Try again.\n")


def press_enter(msg: str = "Press Enter to continue...") -> None:
    input(msg)


# ---------------------------
# Balancing data
# ---------------------------

MONTHS = ["March", "April", "May", "June", "July", "August", "September", "October", "November"]

WEATHER_BY_MONTH = {
    "March": ("Cold", 0.85),
    "April": ("Cool", 0.95),
    "May": ("Mild", 1.05),
    "June": ("Warm", 1.10),
    "July": ("Hot", 1.05),
    "August": ("Hot", 1.00),
    "September": ("Mild", 0.95),
    "October": ("Cool", 0.90),
    "November": ("Cold", 0.80),
}

LANDMARKS: List[Tuple[int, str, bool]] = [
    (120, "Kansas River", False),
    (310, "Big Blue River", False),
    (540, "Fort Kearney", True),
    (800, "Chimney Rock", False),
    (1030, "Fort Laramie", True),
    (1280, "Independence Rock", False),
    (1530, "South Pass", False),
    (1770, "Fort Hall", True),
    (2000, "Willamette Valley", False),
]

DISEASES = [
    ("Dysentery", 18),
    ("Cholera", 24),
    ("Measles", 14),
    ("Typhoid", 20),
    ("Fever", 16),
]

PRICES = {
    "food": 1,
    "ammo": 2,
    "clothing": 15,
    "spare_parts": 25,
    "medicine": 40,
}

PROFESSIONS = {
    "b": ("Banker", 1200, 0.95),
    "c": ("Carpenter", 900, 1.00),
    "f": ("Farmer", 700, 1.08),
}


# ---------------------------
# Core model
# ---------------------------

@dataclass
class Party:
    names: List[str]
    health: int = 100
    morale: int = 75
    alive: bool = True


@dataclass
class Inventory:
    money: int = 0
    food: int = 0
    ammo: int = 0
    clothing: int = 0
    spare_parts: int = 0
    medicine: int = 0


@dataclass
class GameState:
    total_miles: int = 2000
    miles_traveled: int = 0
    month_index: int = 0
    day: int = 1

    party: Party = field(default_factory=lambda: Party(["You", "Alex", "Sam", "Jordan", "Casey"]))
    inv: Inventory = field(default_factory=Inventory)

    profession_key: str = "c"
    profession_name: str = "Carpenter"
    risk_modifier: float = 1.0

    pace: str = "steady"      # slow, steady, grueling
    rations: str = "meager"   # bare, meager, filling
    last_landmark_idx: int = -1

    rng: random.Random = field(default_factory=random.Random)
    death_reason: str = ""

    def month(self) -> str:
        return MONTHS[self.month_index]

    def weather(self) -> Tuple[str, float]:
        return WEATHER_BY_MONTH[self.month()]

    def date_str(self) -> str:
        return f"{self.month()} {self.day}"

    def finished(self) -> bool:
        return self.miles_traveled >= self.total_miles

    def advance_days(self, days: int) -> None:
        self.day += days
        while self.day > 30:
            self.day -= 30
            self.month_index = min(self.month_index + 1, len(MONTHS) - 1)

    def status(self) -> None:
        wx, _ = self.weather()
        print("\n" + "=" * 64)
        print(f"Date: {self.date_str():<15} Weather: {wx:<6}  Miles: {self.miles_traveled}/{self.total_miles}")
        print(f"Health: {self.party.health}/100  Morale: {self.party.morale}/100  Pace: {self.pace}  Rations: {self.rations}")
        print("-" * 64)
        print(
            "Money: ${} | Food: {} lbs | Ammo: {} | Clothing: {} | Parts: {} | Med: {}".format(
                self.inv.money,
                self.inv.food,
                self.inv.ammo,
                self.inv.clothing,
                self.inv.spare_parts,
                self.inv.medicine,
            )
        )
        print(f"Profession: {self.profession_name}")
        print("=" * 64 + "\n")


# ---------------------------
# Setup and stores
# ---------------------------

def choose_profession(gs: GameState) -> None:
    c = ask_choice(
        "Choose your profession:",
        {
            "b": "Banker (most money, lower score bonus)",
            "c": "Carpenter (balanced)",
            "f": "Farmer (least money, higher score bonus)",
        },
        default="c",
    )
    name, money, risk_mod = PROFESSIONS[c]
    gs.profession_key = c
    gs.profession_name = name
    gs.risk_modifier = risk_mod

    gs.inv.money = money
    gs.inv.food = 250
    gs.inv.ammo = 30
    gs.inv.clothing = 4
    gs.inv.spare_parts = 1
    gs.inv.medicine = 0


def choose_party(gs: GameState) -> None:
    print("\nEnter party member names (press Enter to keep defaults):")
    defaults = gs.party.names[:]
    names = []
    for i in range(5):
        raw = input(f"Member {i + 1} [{defaults[i]}]: ").strip()
        names.append(raw if raw else defaults[i])
    gs.party = Party(names=names)


def choose_departure(gs: GameState) -> None:
    options = {str(i + 1): m for i, m in enumerate(MONTHS[:6])}  # March-August
    c = ask_choice("Choose departure month:", options, default="3")
    gs.month_index = MONTHS.index(options[c])
    gs.day = 1


def shop(gs: GameState, intro: bool = False) -> None:
    inv = gs.inv
    if intro:
        print(f"\nYou have ${inv.money} to prepare for the trail.")
        print("Food is survival, ammo supports hunting, medicine helps during disease.")

    while True:
        print(f"\n--- Store --- Money: ${inv.money}")
        print(
            f"Food ${PRICES['food']}/lb | Ammo ${PRICES['ammo']}/bullet | "
            f"Clothing ${PRICES['clothing']} | Parts ${PRICES['spare_parts']} | Med ${PRICES['medicine']}"
        )
        print(
            f"Current: Food {inv.food} | Ammo {inv.ammo} | Clothing {inv.clothing} | "
            f"Parts {inv.spare_parts} | Med {inv.medicine}"
        )

        action = ask_choice("Action:", {"b": "Buy", "l": "Leave"}, default="l")
        if action == "l":
            return

        item = ask_choice(
            "Buy what?",
            {
                "food": "Food (lbs)",
                "ammo": "Ammo (bullets)",
                "clothing": "Clothing",
                "spare_parts": "Spare parts",
                "medicine": "Medicine",
                "x": "Cancel",
            },
            default="x",
        )
        if item == "x":
            continue

        max_afford = inv.money // PRICES[item]
        if max_afford <= 0:
            print("You cannot afford that.")
            continue

        qty = ask_int(f"How many {item}?", 1, max_afford, default=min(50, max_afford))
        cost = qty * PRICES[item]
        inv.money -= cost
        setattr(inv, item, getattr(inv, item) + qty)
        print(f"Bought {qty} {item} for ${cost}.")


def setup_game() -> GameState:
    print("=== Oregon Trail v2 ===")
    print("Terminal remake with landmarks, professions, and morale.\n")

    gs = GameState()
    seed = input("Optional random seed (or Enter): ").strip()
    if seed:
        gs.rng = random.Random(seed)

    choose_profession(gs)
    choose_party(gs)
    choose_departure(gs)
    shop(gs, intro=True)

    return gs


# ---------------------------
# Travel systems
# ---------------------------

def food_use_per_day(rations: str) -> int:
    return {"bare": 6, "meager": 10, "filling": 14}[rations]


def pace_miles_per_day(pace: str) -> int:
    return {"slow": 12, "steady": 18, "grueling": 26}[pace]


def base_event_risk(gs: GameState) -> float:
    risk = 0.10
    if gs.pace == "grueling":
        risk += 0.06
    if gs.rations == "bare":
        risk += 0.04
    if gs.party.morale < 45:
        risk += 0.05
    if gs.party.health < 50:
        risk += 0.05
    return risk * gs.risk_modifier


def set_pace(gs: GameState) -> None:
    c = ask_choice(
        "Choose pace:",
        {
            "slow": "Slow (safer, fewer miles)",
            "steady": "Steady (balanced)",
            "grueling": "Grueling (fast, dangerous)",
        },
        default=gs.pace,
    )
    gs.pace = c


def set_rations(gs: GameState) -> None:
    c = ask_choice(
        "Choose rations:",
        {
            "bare": "Bare bones (save food, worse health)",
            "meager": "Meager (normal)",
            "filling": "Filling (better health, heavy food use)",
        },
        default=gs.rations,
    )
    gs.rations = c


def apply_daily_wear(gs: GameState, days: int) -> None:
    health_delta = 0
    morale_delta = 0

    if gs.rations == "bare":
        health_delta -= 5 * days
        morale_delta -= 3 * days
    elif gs.rations == "meager":
        health_delta -= 2 * days
        morale_delta -= 1 * days
    else:
        health_delta += 1 * days
        morale_delta += 1 * days

    if gs.pace == "grueling":
        health_delta -= 4 * days
        morale_delta -= 2 * days
    elif gs.pace == "steady":
        health_delta -= 1 * days

    wx, _ = gs.weather()
    if wx == "Cold" and gs.inv.clothing < 5:
        health_delta -= 3 * days

    # small random fatigue
    if gs.rng.random() < 0.20:
        health_delta -= gs.rng.randint(2, 8)
        morale_delta -= gs.rng.randint(1, 5)

    gs.party.health = clamp(gs.party.health + health_delta, 0, 100)
    gs.party.morale = clamp(gs.party.morale + morale_delta, 0, 100)


def check_starvation(gs: GameState) -> None:
    if gs.inv.food > 0:
        return
    gs.inv.food = 0
    gs.party.health = clamp(gs.party.health - 25, 0, 100)
    gs.party.morale = clamp(gs.party.morale - 15, 0, 100)
    print("Food is gone. The party weakens from starvation.")


def maybe_disease(gs: GameState) -> None:
    chance = 0.05 + base_event_risk(gs)
    if gs.rng.random() >= chance:
        return

    name, severity = gs.rng.choice(DISEASES)
    print(f"\n*** Illness: {name} ***")

    if gs.inv.medicine > 0:
        use = ask_choice("Use medicine?", {"y": "Yes (1 medicine)", "n": "No"}, default="y")
        if use == "y":
            gs.inv.medicine -= 1
            recover = gs.rng.randint(10, 24)
            gs.party.health = clamp(gs.party.health + recover, 0, 100)
            gs.party.morale = clamp(gs.party.morale + 6, 0, 100)
            print(f"Treatment helped. Health +{recover}.")
            return

    gs.party.health = clamp(gs.party.health - severity, 0, 100)
    gs.party.morale = clamp(gs.party.morale - (severity // 2), 0, 100)
    print(f"The party suffers. Health -{severity}.")


def maybe_wagon_break(gs: GameState) -> None:
    chance = 0.07 if gs.pace != "grueling" else 0.13
    chance *= gs.risk_modifier
    if gs.rng.random() >= chance:
        return

    print("\n*** Wagon breakdown ***")
    if gs.inv.spare_parts > 0:
        c = ask_choice("Use a spare part?", {"y": "Yes", "n": "No"}, default="y")
        if c == "y":
            gs.inv.spare_parts -= 1
            gs.party.morale = clamp(gs.party.morale + 2, 0, 100)
            print("You repaired the wagon quickly.")
            return

    delay = gs.rng.randint(1, 3)
    gs.advance_days(delay)
    gs.party.health = clamp(gs.party.health - 7 * delay, 0, 100)
    gs.party.morale = clamp(gs.party.morale - 5 * delay, 0, 100)
    print(f"Makeshift repairs cost {delay} day(s).")


def maybe_bad_weather(gs: GameState) -> None:
    wx, _ = gs.weather()
    chance = 0.06
    if wx in ("Cold", "Hot"):
        chance += 0.07
    if gs.rng.random() >= chance * gs.risk_modifier:
        return

    event = gs.rng.choice(["storm", "heat", "cold_snap"])
    if event == "storm":
        lost = min(gs.inv.food, gs.rng.randint(15, 70))
        gs.inv.food -= lost
        gs.party.morale = clamp(gs.party.morale - 8, 0, 100)
        gs.advance_days(1)
        print(f"\nA storm batters the wagon. You lose {lost} lbs of food and 1 day.")
    elif event == "heat":
        gs.party.health = clamp(gs.party.health - gs.rng.randint(6, 14), 0, 100)
        gs.party.morale = clamp(gs.party.morale - 6, 0, 100)
        print("\nHeat wave drains the party.")
    else:
        if gs.inv.clothing >= 6:
            print("\nA cold snap hits, but warm clothing protects the party.")
            gs.party.morale = clamp(gs.party.morale - 2, 0, 100)
        else:
            dmg = gs.rng.randint(8, 18)
            gs.party.health = clamp(gs.party.health - dmg, 0, 100)
            gs.party.morale = clamp(gs.party.morale - 10, 0, 100)
            print(f"\nCold snap harms the party. Health -{dmg}.")


def maybe_robbery_or_animals(gs: GameState) -> None:
    if gs.rng.random() >= (0.06 * gs.risk_modifier):
        return

    event = gs.rng.choice(["robbery", "wolves"])
    if event == "robbery":
        stolen_money = min(gs.inv.money, gs.rng.randint(20, 90))
        stolen_food = min(gs.inv.food, gs.rng.randint(20, 80))
        gs.inv.money -= stolen_money
        gs.inv.food -= stolen_food
        gs.party.morale = clamp(gs.party.morale - 12, 0, 100)
        print(f"\nThieves strike at night. Lost ${stolen_money} and {stolen_food} food.")
    else:
        ammo_loss = min(gs.inv.ammo, gs.rng.randint(5, 20))
        gs.inv.ammo -= ammo_loss
        hurt = gs.rng.randint(4, 12)
        gs.party.health = clamp(gs.party.health - hurt, 0, 100)
        print(f"\nWolves attack camp. You use {ammo_loss} ammo and suffer minor injuries.")


def river_crossing(gs: GameState) -> None:
    depth = gs.rng.randint(2, 8)
    print(f"\n~~~ River crossing ({depth} ft) ~~~")

    c = ask_choice(
        "How do you cross?",
        {
            "ford": "Ford it (fast, risky)",
            "caulk": "Caulk and float (1 day, moderate risk)",
            "ferry": "Ferry ($40, safest)",
            "wait": "Wait for better conditions",
        },
        default="ford",
    )

    if c == "ferry":
        if gs.inv.money >= 40:
            gs.inv.money -= 40
            print("Ferry crossing successful.")
            return
        print("Not enough money for ferry.")
        return river_crossing(gs)

    if c == "wait":
        wait_days = gs.rng.randint(1, 3)
        gs.advance_days(wait_days)
        gs.party.morale = clamp(gs.party.morale - 2 * wait_days, 0, 100)
        print(f"You wait {wait_days} day(s).")
        return

    risk = 0.10 + (0.05 * (depth - 2)) if c == "ford" else 0.08 + (0.03 * (depth - 2))
    if c == "caulk":
        gs.advance_days(1)

    if gs.rng.random() < risk * gs.risk_modifier:
        lost_food = min(gs.inv.food, gs.rng.randint(35, 130))
        lost_ammo = min(gs.inv.ammo, gs.rng.randint(5, 25))
        gs.inv.food -= lost_food
        gs.inv.ammo -= lost_ammo
        dmg = gs.rng.randint(8, 24)
        gs.party.health = clamp(gs.party.health - dmg, 0, 100)
        gs.party.morale = clamp(gs.party.morale - 10, 0, 100)
        print(f"Crossing disaster. Lost {lost_food} food, {lost_ammo} ammo. Health -{dmg}.")
    else:
        print("Crossing successful.")


def maybe_random_events(gs: GameState) -> None:
    maybe_wagon_break(gs)
    maybe_disease(gs)
    maybe_bad_weather(gs)
    maybe_robbery_or_animals(gs)

    # river chance higher in first 80% of trail
    progress = gs.miles_traveled / gs.total_miles
    river_chance = 0.10 if progress < 0.8 else 0.05
    if gs.rng.random() < river_chance:
        river_crossing(gs)


def hunting(gs: GameState) -> None:
    if gs.inv.ammo <= 0:
        print("No ammo available for hunting.")
        return

    print("\n--- Hunting ---")
    print("Type 'BANG' within 3 attempts. Success brings meat.")

    success = False
    for idx in range(3):
        if input(f"Try {idx + 1}/3: ").strip().upper() == "BANG":
            success = True
            break

    spent = min(gs.inv.ammo, gs.rng.randint(5, 14))
    gs.inv.ammo -= spent

    if not success:
        gs.party.morale = clamp(gs.party.morale - 4, 0, 100)
        print(f"Unsuccessful hunt. Ammo spent: {spent}.")
        return

    gain = gs.rng.randint(80, 220)
    food_cap = 1000
    new_food = min(food_cap, gs.inv.food + gain)
    actual = new_food - gs.inv.food
    gs.inv.food = new_food
    gs.party.morale = clamp(gs.party.morale + 6, 0, 100)
    print(f"Successful hunt. Ammo used: {spent}. Food gained: {actual} (cap {food_cap}).")


def rest(gs: GameState) -> None:
    days = ask_int("Rest for how many days", 1, 5, default=2)
    gs.advance_days(days)
    food_needed = food_use_per_day(gs.rations) * days
    gs.inv.food = max(0, gs.inv.food - food_needed)
    gs.party.health = clamp(gs.party.health + 4 * days, 0, 100)
    gs.party.morale = clamp(gs.party.morale + 5 * days, 0, 100)
    print(f"The party rests for {days} day(s).")
    check_starvation(gs)


def current_landmark(gs: GameState) -> Tuple[int, str, bool] | None:
    for idx, lm in enumerate(LANDMARKS):
        if idx <= gs.last_landmark_idx:
            continue
        if gs.miles_traveled >= lm[0]:
            gs.last_landmark_idx = idx
            return lm
    return None


def handle_landmark(gs: GameState) -> None:
    lm = current_landmark(gs)
    if not lm:
        return

    miles, name, has_fort = lm
    print(f"\n=== Landmark reached: {name} ({miles} miles) ===")
    gs.party.morale = clamp(gs.party.morale + 7, 0, 100)

    # Small chance of celebratory find.
    if gs.rng.random() < 0.25:
        found = gs.rng.randint(10, 45)
        gs.inv.food += found
        print(f"You forage nearby and gain {found} food.")

    if has_fort:
        c = ask_choice("A fort with supplies is available.", {"y": "Shop", "n": "Continue"}, default="y")
        if c == "y":
            shop(gs, intro=False)


def death_check(gs: GameState) -> None:
    if gs.party.health > 0:
        return

    gs.party.alive = False
    if gs.inv.food == 0:
        gs.death_reason = "starvation"
    elif gs.party.morale <= 10:
        gs.death_reason = "exhaustion"
    else:
        gs.death_reason = "illness"

    print("\n" + "!" * 64)
    print("Your party has perished on the trail.")
    print(f"Cause of death: {gs.death_reason}")
    print("!" * 64)
    tombstone(gs.party.names[0], gs.death_reason)


def tombstone(name: str, reason: str) -> None:
    art = [
        "  _____________  ",
        " /             \\ ",
        "/   R. I. P.     \\",
        f"|   {name[:13]:<13} |",
        "|               |",
        f"| {reason[:13]:<13} |",
        "|               |",
        "|_______________|",
    ]
    print("\n".join(art))


def score(gs: GameState) -> int:
    profession_bonus = {"b": 0.8, "c": 1.0, "f": 1.25}[gs.profession_key]
    base = gs.party.health + gs.party.morale
    supplies = (gs.inv.food // 5) + (gs.inv.money // 10) + (gs.inv.medicine * 10)
    return int((base + supplies) * profession_bonus)


def win_screen(gs: GameState) -> None:
    print("\n" + "=" * 64)
    print("You made it to Oregon!")
    print(f"Arrival date: {gs.date_str()}")
    print(f"Final health: {gs.party.health}/100")
    print(f"Final morale: {gs.party.morale}/100")
    print(
        f"Supplies left: Food {gs.inv.food} | Ammo {gs.inv.ammo} | "
        f"Clothing {gs.inv.clothing} | Parts {gs.inv.spare_parts} | Med {gs.inv.medicine} | Money ${gs.inv.money}"
    )
    print(f"Final score: {score(gs)}")
    print("=" * 64 + "\n")


def travel(gs: GameState) -> None:
    days = ask_int("Travel how many days", 3, 14, default=7)

    food_needed = food_use_per_day(gs.rations) * days
    gs.inv.food = max(0, gs.inv.food - food_needed)

    gs.advance_days(days)

    base_miles = pace_miles_per_day(gs.pace)
    _, wx_factor = gs.weather()
    miles = int(base_miles * wx_factor * days)
    gs.miles_traveled = min(gs.total_miles, gs.miles_traveled + miles)

    apply_daily_wear(gs, days)
    check_starvation(gs)
    maybe_random_events(gs)
    handle_landmark(gs)


def player_turn(gs: GameState) -> None:
    gs.status()

    action = ask_choice(
        "What do you want to do?",
        {
            "t": "Travel",
            "r": "Change rations",
            "p": "Change pace",
            "h": "Hunt",
            "o": "Rest",
            "s": "Look for shop in nearby town",
            "q": "Quit",
        },
        default="t",
    )

    handlers: Dict[str, Callable[[GameState], None]] = {
        "r": set_rations,
        "p": set_pace,
        "h": hunting,
        "o": rest,
    }

    if action == "q":
        print("You end your journey.")
        sys.exit(0)

    if action == "s":
        if gs.rng.random() < 0.35:
            shop(gs, intro=False)
        else:
            print("No town with a trading post nearby.")
        return

    if action == "t":
        travel(gs)
        return

    handlers[action](gs)


def main() -> None:
    gs = setup_game()
    press_enter()

    while gs.party.alive and not gs.finished():
        player_turn(gs)
        death_check(gs)

    if gs.party.alive and gs.finished():
        win_screen(gs)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting.")
