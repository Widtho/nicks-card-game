from flask import Flask, jsonify, request
import random
import os

app = Flask(__name__)

# ====================== GAME STATE ======================
full_deck = []
ready_players = {1: False, 2: False}
fight_active = False
current_turn = None
hp = {1: 300, 2: 300}
energy = {1: 100, 2: 100}
fight_log = []
players_pools = {1: [], 2: []}
players_equipped = {1: {}, 2: {}}
player_names = {1: "Player 1", 2: "Player 2"}

# Name pools for cool card names
name_prefixes = ["Ugar's", "Void", "Shadow", "Frost", "Crimson", "Dragon", "Eternal", "Chaos", "Blood", "Storm", "Rune", "Phantom"]
name_suffixes = ["of Pain", "of Eternity", "of Ruin", "of Fury", "of the Void", "of Shadows", "of Frost", "of Chaos", "of Power", "of Doom", "of the Ancients"]
uber_suffixes = ["of the Eternal", "of Absolute Power", "of Infinite Rage", "of the Forgotten God"]

# Special ability pool (you can expand this later)
special_ability_pool = [
    "Trigger: On Hit - Opponent loses 10 energy",
    "Trigger: On Miss - Gain 15 HP",
    "Call-out: Once per game - Ignore opponent's next defense flip",
    "Trigger: When opponent heals - Steal 20 HP",
    "Trigger: On Crit - Extra 30 damage",
    "Call-out: Once per game - Double your next attack damage",
    "Trigger: When you take damage - 25% chance to reflect half",
]

def create_card(card_id):
    tiers = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Unique"]
    tier = random.choice(tiers)

    slot_types = ["Head", "Chest", "Bracers", "Gloves", "Pants", "Boots", "Necklace", "Ring", "Main-hand", "Off-hand", "Familiar", "Ability"]
    slot = random.choice(slot_types)

    # Base stat
    if slot in ["Main-hand", "Off-hand"]:
        base_stat = {"type": random.choice(["phys_attack", "mag_attack"]), "value": random.randint(25, 75)}
    elif slot == "Ability":
        base_stat = {"type": random.choice(["phys_attack", "mag_attack"]), "value": random.randint(30, 85)}
    elif slot == "Familiar":
        base_stat = {"type": "special", "value": 0}
    else:
        base_stat = {"type": random.choice(["ac", "magdef"]), "value": random.randint(8, 35)}

    # Bonus stats based on rarity
    bonus_count = {"Common": 0, "Uncommon": 1, "Rare": 2, "Epic": 3, "Legendary": 4, "Unique": 4}.get(tier, 0)
    stat_types = ["ac", "magdef", "phys_attack", "mag_attack", "hp", "energy"]
    tier_ranges = {"Uncommon": (5,15), "Rare": (10,20), "Epic": (15,25), "Legendary": (20,30), "Unique": (25,35)}
    min_val, max_val = tier_ranges.get(tier, (5,15))

    bonus_stats = []
    for _ in range(bonus_count):
        stat_type = random.choice(stat_types)
        value = random.randint(min_val, max_val)
        bonus_stats.append({"type": stat_type, "value": value})

    # Uber check
    is_uber = False
    if bonus_count > 0 and all(b["value"] == max_val for b in bonus_stats):
        is_uber = True
        for b in bonus_stats:
            b["value"] = max_val

    # Special ability for Unique or Uber
    special_ability = None
    if tier == "Unique" or is_uber:
        special_ability = random.choice(special_ability_pool)

    # Cool name
    if is_uber:
        name = f"{random.choice(name_prefixes)} {slot} {random.choice(uber_suffixes)}"
    else:
        name = f"{random.choice(name_prefixes)} {slot} {random.choice(name_suffixes)}"

    return {
        "id": card_id,
        "name": name,
        "tier": tier,
        "slot": slot,
        "base_stat": base_stat,
        "bonus_stats": bonus_stats,
        "is_uber": is_uber,
        "special_ability": special_ability
    }

# Generate the full deck once
full_deck = [create_card(i) for i in range(200)]

def reset_game():
    global fight_active, current_turn, hp, energy, fight_log, players_pools, players_equipped, ready_players
    fight_active = False
    current_turn = None
    hp = {1: 300, 2: 300}
    energy = {1: 100, 2: 100}
    fight_log = []
    players_pools = {1: [], 2: []}
    players_equipped = {1: {}, 2: {}}
    ready_players = {1: False, 2: False}

@app.route('/')
def index():
    try:
        with open('templates/index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error loading index.html: {str(e)}", 500

@app.route('/api/start_game', methods=['POST'])
def start_game():
    data = request.get_json()
    player = data.get('player')
    personal_deck = random.sample(full_deck, 40)
    pool = random.sample(personal_deck, 25)
    players_pools[player] = pool
    return jsonify({"status": "started"})

@app.route('/api/pool/<int:player>')
def get_pool(player):
    return jsonify({"cards": players_pools.get(player, [])})

@app.route('/api/set_name', methods=['POST'])
def set_name():
    data = request.get_json()
    player = data.get('player')
    name = data.get('name', f"Player {player}")
    player_names[player] = name
    return jsonify({"success": True, "name": name})

@app.route('/api/ready/<int:player>', methods=['POST'])
def set_ready(player):
    global fight_active, current_turn
    ready_players[player] = True
    if ready_players[1] and ready_players[2] and not fight_active:
        fight_active = True
        current_turn = random.choice([1, 2])
        fight_log.append(f"Coin flip! {player_names[current_turn]} goes first.")
    return jsonify({
        "ready1": ready_players[1],
        "ready2": ready_players[2],
        "fight_active": fight_active,
        "current_turn": current_turn,
        "player_names": player_names
    })

@app.route('/api/fight_status')
def get_fight_status():
    return jsonify({
        "fight_active": fight_active,
        "current_turn": current_turn,
        "hp": hp,
        "energy": energy,
        "log": fight_log,
        "player_names": player_names
    })

@app.route('/api/apply_damage', methods=['POST'])
def apply_damage():
    global hp
    data = request.get_json()
    defender = data['defender']
    damage = data['damage']
    hp[defender] = max(0, hp[defender] - damage)
    fight_log.append(f"→ {damage} damage! {player_names[defender]} HP now: {hp[defender]}")
    return jsonify({"hp": hp})

@app.route('/api/end_turn', methods=['POST'])
def end_turn():
    global current_turn
    if fight_active and current_turn:
        current_turn = 3 - current_turn
    return jsonify({"current_turn": current_turn})

@app.route('/api/reset', methods=['POST'])
def reset():
    reset_game()
    return jsonify({"status": "reset"})

if __name__ == '__main__':
    print("Nick's Card Game Server running on http://0.0.0.0:5000")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
