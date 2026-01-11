from flask import Flask, render_template, jsonify, request
import random
import json
import threading
import time

app = Flask(__name__)

# LED control - will be replaced with real implementation when hardware is ready
LED_ENABLED = True
pixels = None

if LED_ENABLED:
    import board
    import neopixel
    pixels = neopixel.NeoPixel(board.D12, 18, brightness=0.5, auto_write=False)

# Resource colors (RGB)
RESOURCE_COLORS = {
    'brick': (130, 3, 3),      # Brownish red
    'wood': (0, 120, 0),        # Dark green
    'sheep': (0, 100, 30),    # Light green
    'wheat': (130, 85, 0),      # Gold
    'ore': (10, 10, 128),      # Gray
    'desert': (0, 0, 0)          # No light for desert (always center, no LED)
}

# Standard Catan resource distribution (18 resources + 1 desert in center = 19)
# Desert is always in center (index 0) and has no LED
STANDARD_RESOURCES = {
    'brick': 3,
    'wood': 4,
    'sheep': 4,
    'wheat': 4,
    'ore': 3
}
# Note: desert is not in this dict - it's always fixed at center

# Standard Catan number tokens (no 7, desert gets none)
STANDARD_NUMBERS = [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12]

# Hex positions (index corresponds to LED index)
# Adjacency map for checking 6/8 rule
ADJACENCIES = {
    0: [1, 2, 3, 4, 5, 6],      # Center connects to ring 1
    1: [0, 2, 6, 7, 8, 12],     # Ring 1
    2: [0, 1, 3, 8, 9, 10],
    3: [0, 2, 4, 10, 11, 12],
    4: [0, 3, 5, 12, 13, 14],
    5: [0, 4, 6, 14, 15, 16],
    6: [0, 1, 5, 16, 17, 7],
    7: [1, 6, 8, 17, 18, 12],   # Ring 2
    8: [1, 2, 7, 9, 18, 19],
    9: [2, 8, 10, 19, 20, 21],
    10: [2, 3, 9, 11, 21, 22],
    11: [3, 10, 12, 22, 23, 24],
    12: [1, 3, 4, 7, 11, 13],
    13: [4, 12, 14, 24, 25, 26],
    14: [4, 5, 13, 15, 26, 27],
    15: [5, 14, 16, 27, 28, 29],
    16: [5, 6, 15, 17, 29, 30],
    17: [6, 7, 16, 18, 30, 31],
    18: [7, 8, 17, 19, 31, 32]
}

# Simplified adjacency for 19-hex board (0 = center, 1-6 = ring 1, 7-18 = ring 2)
# Re-mapping to match actual 19 hexes
ADJACENCIES_19 = {
    0: [1, 2, 3, 4, 5, 6],           # Center
    1: [0, 2, 6, 7, 8, 12],          # Ring 1
    2: [0, 1, 3, 8, 9, 10],
    3: [0, 2, 4, 10, 11, 12],
    4: [0, 3, 5, 12, 13, 14],
    5: [0, 4, 6, 14, 15, 16],
    6: [0, 1, 5, 16, 17, 7],
    7: [1, 6, 17, 18],               # Ring 2 (corners have fewer neighbors)
    8: [1, 2, 9, 7],
    9: [2, 8, 10, 18],
    10: [2, 3, 9, 11],
    11: [3, 10, 12, 18],
    12: [3, 4, 11, 13],
    13: [4, 12, 14, 18],
    14: [4, 5, 13, 15],
    15: [5, 14, 16, 18],
    16: [5, 6, 15, 17],
    17: [6, 7, 16, 18],
    18: [7, 9, 11, 13, 15, 17]       # This doesn't exist in standard - we have 19 hexes 0-18
}

# Correct adjacency for 19 hexes (center=0, ring1=1-6, ring2=7-18)
HEX_ADJACENCIES = {
    0: [1, 2, 3, 4, 5, 6],
    1: [0, 2, 6, 7, 8, 9],
    2: [0, 1, 3, 9, 10, 11],
    3: [0, 2, 4, 11, 12, 13],
    4: [0, 3, 5, 13, 14, 15],
    5: [0, 4, 6, 15, 16, 17],
    6: [0, 1, 5, 17, 18, 7],
    7: [1, 6, 8, 18],
    8: [1, 7, 9],
    9: [1, 2, 8, 10],
    10: [2, 9, 11],
    11: [2, 3, 10, 12],
    12: [3, 11, 13],
    13: [3, 4, 12, 14],
    14: [4, 13, 15],
    15: [4, 5, 14, 16],
    16: [5, 15, 17],
    17: [5, 6, 16, 18],
    18: [6, 7, 17]
}

# Current board state
board_state = {
    'tiles': [],  # List of {resource, number, led_index}
    'mode': 'setup',  # 'setup' or 'play'
    'config': {
        'resources': STANDARD_RESOURCES.copy(),
        'numbers': STANDARD_NUMBERS.copy(),
        'prevent_adjacent_68': False
    }
}

# Track which LEDs are currently flashing
flashing_leds = set()

# Track rainbow animation state
rainbow_animation_running = False

# Track red flash state (for 7 rolls)
red_flash_in_progress = False


def get_rainbow_color(hue):
    """Convert hue (0-1) to RGB color"""
    # hue: 0=red, 0.166=yellow, 0.333=green, 0.5=cyan, 0.666=blue, 0.833=magenta, 1=red
    if hue < 0 or hue > 1:
        hue = hue % 1
    
    h = hue * 6
    c = 200  # Chroma (brightness)
    
    if h < 1:
        r, g, b = c, int(c * h), 0
    elif h < 2:
        r, g, b = int(c * (2 - h)), c, 0
    elif h < 3:
        r, g, b = 0, c, int(c * (h - 2))
    elif h < 4:
        r, g, b = 0, int(c * (4 - h)), c
    elif h < 5:
        r, g, b = int(c * (h - 4)), 0, c
    else:
        r, g, b = c, 0, int(c * (6 - h))
    
    return (int(r), int(g), int(b))


def rainbow_cycle_animation():
    """Cycle all LEDs through rainbow colors"""
    global rainbow_animation_running
    
    if not LED_ENABLED or pixels is None:
        return
    
    hue = 0
    while rainbow_animation_running:
        for i in range(18):
            pixels[i] = get_rainbow_color(hue + (i / 18.0))
        pixels.show()
        hue += 0.01  # Increment hue for smooth cycling
        time.sleep(0.05)  # Update every 50ms


def init_board():
    """Initialize board with empty tiles"""
    global rainbow_animation_running
    
    board_state['tiles'] = [
        {'resource': None, 'number': None, 'led_index': i}
        for i in range(19)
    ]
    
    # Start rainbow animation
    if LED_ENABLED and pixels is not None:
        rainbow_animation_running = True
        thread = threading.Thread(target=rainbow_cycle_animation, daemon=True)
        thread.start()


def check_adjacent_68(tiles):
    """Check if any 6 and 8 are adjacent"""
    for i, tile in enumerate(tiles):
        if tile['number'] in [6, 8]:
            for adj_idx in HEX_ADJACENCIES.get(i, []):
                if adj_idx < len(tiles) and tiles[adj_idx]['number'] in [6, 8]:
                    return True
    return False


def randomize_board(config, max_attempts=100):
    """Randomize the board with given configuration"""
    global rainbow_animation_running
    
    # Stop rainbow animation
    rainbow_animation_running = False
    time.sleep(0.1)  # Give animation thread time to stop
    
    resources = config['resources']
    numbers = config['numbers'].copy()
    prevent_68 = config['prevent_adjacent_68']

    # Build resource list for the 18 non-center tiles
    resource_list = []
    for resource, count in resources.items():
        resource_list.extend([resource] * count)

    # Verify we have exactly 18 resources
    if len(resource_list) != 18:
        raise ValueError(f"Resources must add up to 18, got {len(resource_list)}")

    # Shuffle resources
    random.shuffle(resource_list)

    # Create tiles - desert always at center (index 0), no LED there
    tiles = [{'resource': 'desert', 'number': None, 'led_index': None}]  # Center

    # Add the 18 resource tiles (indices 1-18, LED indices 0-17)
    for i in range(18):
        tiles.append({
            'resource': resource_list[i],
            'number': None,
            'led_index': i  # LED 0-17 maps to tile 1-18
        })

    # Assign numbers to non-desert tiles (indices 1-18)
    for attempt in range(max_attempts):
        random.shuffle(numbers)
        number_list = numbers.copy()

        for i in range(1, 19):
            tiles[i]['number'] = number_list.pop(0)

        # Check 6/8 adjacency if required
        if prevent_68 and check_adjacent_68(tiles):
            # Reset numbers and try again
            for i in range(1, 19):
                tiles[i]['number'] = None
            continue
        else:
            # Success
            break

    return tiles


def set_led_colors():
    """Update LED colors based on current board state"""
    if not LED_ENABLED or pixels is None:
        return

    for tile in board_state['tiles']:
        led_idx = tile['led_index']
        resource = tile['resource']
        # Skip desert (center) which has no LED
        if led_idx is not None and resource and resource != 'desert':
            color = RESOURCE_COLORS.get(resource, (0, 0, 0))
            pixels[led_idx] = color

    pixels.show()


def blink_tiles(number, times=10, on_time=0.3, off_time=0.2):
    """Blink tiles that match the rolled number"""
    if not LED_ENABLED or pixels is None:
        return

    matching_indices = [
        tile['led_index'] for tile in board_state['tiles']
        if tile['number'] == number and tile['led_index'] is not None
    ]

    # Store original colors
    original_colors = [pixels[i] for i in range(18)]

    for _ in range(times):
        # Turn on matching tiles bright white
        for led_idx in matching_indices:
            pixels[led_idx] = (255, 255, 255)
        pixels.show()
        time.sleep(on_time)

        # Return to resource colors
        for led_idx in matching_indices:
            # Find the tile with this LED index
            for tile in board_state['tiles']:
                if tile['led_index'] == led_idx:
                    resource = tile['resource']
                    pixels[led_idx] = RESOURCE_COLORS.get(resource, (0, 0, 0))
                    break
        pixels.show()
        time.sleep(off_time)


def flash_all_leds_red(times=5, on_time=0.3, off_time=0.2):
    """Flash all LEDs red and off (for rolling a 7)"""
    global red_flash_in_progress
    
    if not LED_ENABLED or pixels is None:
        return

    red_flash_in_progress = True
    try:
        # Store original colors
        original_colors = [pixels[i] for i in range(18)]

        for _ in range(times):
            # Turn all LEDs red
            for i in range(18):
                pixels[i] = (255, 0, 0)
            pixels.show()
            time.sleep(on_time)

            # Turn off
            for i in range(18):
                pixels[i] = (0, 0, 0)
            pixels.show()
            time.sleep(off_time)

        # Restore original colors
        for i in range(18):
            pixels[i] = original_colors[i]
        pixels.show()
    finally:
        red_flash_in_progress = False


# Routes
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/state')
def get_state():
    return jsonify(board_state)


@app.route('/api/randomize', methods=['POST'])
def randomize():
    config = request.json if request.json else board_state['config']
    board_state['config'] = config
    board_state['tiles'] = randomize_board(config)
    board_state['mode'] = 'setup'
    set_led_colors()
    return jsonify(board_state)


@app.route('/api/start_game', methods=['POST'])
def start_game():
    board_state['mode'] = 'play'
    return jsonify(board_state)


@app.route('/api/back_to_setup', methods=['POST'])
def back_to_setup():
    board_state['mode'] = 'setup'
    return jsonify(board_state)


@app.route('/api/roll', methods=['POST'])
def roll_dice():
    global red_flash_in_progress
    
    # Ignore rolls if red flash is in progress
    if red_flash_in_progress:
        return jsonify({'error': 'Red flash in progress, please wait'}), 409
    
    data = request.json

    if data.get('auto'):
        # Simulate 2d6
        die1 = random.randint(1, 6)
        die2 = random.randint(1, 6)
        total = die1 + die2
    else:
        total = data.get('value')
        if not total or total < 2 or total > 12:
            return jsonify({'error': 'Invalid roll value'}), 400
        die1 = None
        die2 = None

    # Find matching tiles - use enumerate to get the actual tile index for UI highlighting
    matching = [
        {'index': idx, 'resource': tile['resource']}
        for idx, tile in enumerate(board_state['tiles'])
        if tile['number'] == total
    ]

    # Flash LEDs in background thread
    if LED_ENABLED:
        if total == 7:
            # Flash all LEDs red for a 7
            thread = threading.Thread(target=flash_all_leds_red)
        else:
            # Blink matching number tiles
            thread = threading.Thread(target=blink_tiles, args=(total,))
        thread.start()

    return jsonify({
        'die1': die1,
        'die2': die2,
        'total': total,
        'matching': matching
    })


@app.route('/api/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        new_config = request.json

        # Validate resources add up to 18 (desert is always in center, not counted)
        total_tiles = sum(new_config.get('resources', {}).values())
        if total_tiles != 18:
            return jsonify({'error': f'Resources must add up to 18, got {total_tiles}'}), 400

        board_state['config'] = new_config
        return jsonify(board_state['config'])
    else:
        return jsonify(board_state['config'])


@app.route('/api/flash_led', methods=['POST'])
def flash_led():
    """Flash a single LED for testing during setup"""
    # Ignore flash commands if red flash is in progress
    if red_flash_in_progress:
        return jsonify({'status': 'red_flash_in_progress', 'message': 'Red flash in progress, please wait'}), 409
    
    data = request.json
    tile_index = data.get('tile_index')

    if tile_index is None or tile_index < 0 or tile_index >= 19:
        return jsonify({'error': 'Invalid tile index'}), 400

    # Get the LED index for this tile
    tile = board_state['tiles'][tile_index] if board_state['tiles'] else None
    led_index = tile.get('led_index') if tile else None

    # Desert (center) has no LED
    if led_index is None:
        return jsonify({'status': 'no_led', 'message': 'This tile has no LED (desert)'})

    # Check if this LED is already flashing
    if led_index in flashing_leds:
        return jsonify({'status': 'already_flashing', 'message': 'This LED is already flashing'}), 409

    # Flash the LED in background thread
    if LED_ENABLED and pixels is not None:
        def flash_single_led():
            flashing_leds.add(led_index)
            try:
                original_color = pixels[led_index]
                for _ in range(3):
                    pixels[led_index] = (255, 255, 255)
                    pixels.show()
                    time.sleep(0.2)
                    pixels[led_index] = original_color
                    pixels.show()
                    time.sleep(0.15)
            finally:
                flashing_leds.discard(led_index)

        thread = threading.Thread(target=flash_single_led)
        thread.start()
    else:
        # Even without hardware, track the flashing state
        flashing_leds.add(led_index)
        def flash_without_hardware():
            try:
                time.sleep(0.2 * 3 + 0.15 * 3)
            finally:
                flashing_leds.discard(led_index)
        thread = threading.Thread(target=flash_without_hardware)
        thread.start()

    return jsonify({'status': 'ok', 'tile_index': tile_index, 'led_index': led_index})


@app.route('/api/colors')
def get_colors():
    return jsonify(RESOURCE_COLORS)


# Initialize on startup
init_board()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=False)
