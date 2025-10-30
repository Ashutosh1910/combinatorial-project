import random
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from enum import Enum

class Room:
    def __init__(self, id, width, height):
        self.id = id
        self.width = width
        self.height = height
        self.x = None
        self.y = None
        self.placed_width = None
        self.placed_height = None
        self.rotated = False

    def get_area(self):
        return self.width * self.height

    def place(self, x, y, rotated):
        self.x = x
        self.y = y
        self.rotated = rotated
        if rotated:
            self.placed_width = self.height
            self.placed_height = self.width
        else:
            self.placed_width = self.width
            self.placed_height = self.height

    def copy(self):
        return Room(self.id, self.width, self.height)
    
class CorridorType(Enum):
    VERTICAL = 1
    HORIZONTAL = 2

class Corridor:
    def __init__(self, pos, corridor_type, start, end):
        self.pos = pos
        self.type = corridor_type
        self.start = start
        self.end = end

class Layout:
    def __init__(self, corridors, placed_rooms):
        self.corridors = corridors
        self.placed_rooms = placed_rooms

    def get_room_area(self):
        return sum(room.get_area() for room in self.placed_rooms)

    def get_signature(self):
        room_positions = tuple(sorted(
            (r.id, r.x // 5, r.y // 5, r.rotated) for r in self.placed_rooms
        ))
        corridor_positions = tuple(sorted(
            (c.pos // 5, c.type.value) for c in self.corridors
        ))
        return (room_positions, corridor_positions)
    

def check_70_condition(rooms, plot_width, plot_height):
    rooms_area = sum(room.get_area() for room in rooms)
    return rooms_area <= plot_width * plot_height * 0.7


def place_rooms(rooms, x, y, zone_width, zone_height, randomize=True):
    placed_rooms = []
    unplaced_rooms = [r.copy() for r in rooms]

    if randomize:
        random.shuffle(unplaced_rooms)

    curr_y = y

    while unplaced_rooms and curr_y < y + zone_height:
        curr_x = x
        row_ht = 0
        placed_in_row = False
        i = 0

        while i < len(unplaced_rooms):
            room = unplaced_rooms[i]
            room_placed = False

            orientations = [(False, room.width, room.height),
                          (True, room.height, room.width)]

            if randomize and random.random() < 0.5:
                orientations.reverse()

            for rotated, w, h in orientations:
                if (curr_x + w <= zone_width + x and
                    curr_y + h <= zone_height + y):
                    room.place(curr_x, curr_y, rotated)
                    placed_rooms.append(room)
                    curr_x += w
                    row_ht = max(row_ht, h)
                    unplaced_rooms.pop(i)
                    room_placed = True
                    placed_in_row = True
                    break

            if not room_placed:
                i += 1

        if not placed_in_row:
            break

        curr_y += row_ht

    return placed_rooms, unplaced_rooms


def generate_layouts(rooms, plot_width, plot_height, max_layouts=10, max_attempts=500):
    """Generate multiple diverse layouts with RECURSIVE corridor placement"""
    CORRIDOR_WIDTH = 3
    MIN_ZONE_DIM = min([min(r.width, r.height) for r in rooms])
    layouts = []
    seen_signatures = set()
    attempts = 0

    def recursively_split_zone(x, y, width, height, depth=0, max_depth=4):
        """Recursively split a zone into smaller zones with corridors"""
        corridors = []
        zones = []

        if depth >= max_depth:
            return corridors, [(x, y, width, height)]

        can_split_h = height > 2 * MIN_ZONE_DIM + CORRIDOR_WIDTH
        can_split_v = width > 2 * MIN_ZONE_DIM + CORRIDOR_WIDTH

        if not can_split_h and not can_split_v:
            return corridors, [(x, y, width, height)]

        split_probability = 0.8 - (depth * 0.15)
        if random.random() > split_probability:
            return corridors, [(x, y, width, height)]

        if can_split_h and can_split_v:
            if depth % 2 == 0:
                split_horizontal = random.random() < 0.6
            else:
                split_horizontal = random.random() < 0.4
        elif can_split_h:
            split_horizontal = True
        else:
            split_horizontal = False

        if split_horizontal:
            min_pos = MIN_ZONE_DIM
            max_pos = height - CORRIDOR_WIDTH - MIN_ZONE_DIM
            if max_pos <= min_pos:
                return corridors, [(x, y, width, height)]

            split_pos = random.randint(min_pos, max_pos)
            corridor = Corridor(y + split_pos, CorridorType.HORIZONTAL, x, x + width)
            corridors.append(corridor)

            top_corridors, top_zones = recursively_split_zone(
                x, y, width, split_pos, depth + 1, max_depth
            )
            bottom_corridors, bottom_zones = recursively_split_zone(
                x, y + split_pos + CORRIDOR_WIDTH, width,
                height - split_pos - CORRIDOR_WIDTH, depth + 1, max_depth
            )

            corridors.extend(top_corridors)
            corridors.extend(bottom_corridors)
            zones.extend(top_zones)
            zones.extend(bottom_zones)

        else:
            min_pos = MIN_ZONE_DIM
            max_pos = width - CORRIDOR_WIDTH - MIN_ZONE_DIM
            if max_pos <= min_pos:
                return corridors, [(x, y, width, height)]

            split_pos = random.randint(min_pos, max_pos)
            corridor = Corridor(x + split_pos, CorridorType.VERTICAL, y, y + height)
            corridors.append(corridor)

            left_corridors, left_zones = recursively_split_zone(
                x, y, split_pos, height, depth + 1, max_depth
            )
            right_corridors, right_zones = recursively_split_zone(
                x + split_pos + CORRIDOR_WIDTH, y,
                width - split_pos - CORRIDOR_WIDTH, height, depth + 1, max_depth
            )

            corridors.extend(left_corridors)
            corridors.extend(right_corridors)
            zones.extend(left_zones)
            zones.extend(right_zones)

        return corridors, zones

    def try_layout_with_corridors(seed):
        random.seed(seed)

        max_depth = random.randint(3, 5)
        corridors, zones = recursively_split_zone(
            0, 0, plot_width, plot_height, depth=0, max_depth=max_depth
        )

        all_placed_rooms = []
        remaining_rooms = [r.copy() for r in rooms]
        random.shuffle(zones)

        for x, y, width, height in zones:
            if not remaining_rooms:
                break

            placed, remaining_rooms = place_rooms(
                remaining_rooms, x, y, width, height, randomize=True
            )
            all_placed_rooms.extend(placed)

        if all_placed_rooms and check_70_condition(all_placed_rooms, plot_width, plot_height):
            return Layout(corridors, all_placed_rooms)

        return None

    print(f"Attempting to generate up to {max_layouts} unique layouts...")
    while len(layouts) < max_layouts and attempts < max_attempts:
        seed = attempts
        layout = try_layout_with_corridors(seed)

        if layout:
            signature = layout.get_signature()
            if signature not in seen_signatures:
                layouts.append(layout)
                seen_signatures.add(signature)
                if len(layouts) % 10 == 0:
                    print(f"  Generated {len(layouts)} layouts so far...")

        attempts += 1

    return layouts


def visualize_layouts(layouts, plot_width, plot_height, rooms):
    num_layouts = len(layouts)
    if num_layouts == 0:
        print("No layouts to visualize!")
        return

    # Use 5 columns for better display with many layouts
    cols = min(5, num_layouts)
    rows = (num_layouts + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(5*cols, 4*rows))

    if num_layouts == 1:
        axes = [[axes]]
    elif rows == 1:
        axes = [axes]

    room_info = ", ".join([f"R{r.id}({r.width}x{r.height})" for r in rooms])
    fig.suptitle(f'Plot: {plot_width}x{plot_height} | Rooms: {room_info} | Generated {num_layouts} Layouts',
                 fontsize=16, fontweight='bold')

    for idx, layout in enumerate(layouts):
        row = idx // cols
        col = idx % cols
        ax = axes[row][col] if rows > 1 else axes[0][col]

        ax.set_xlim(0, plot_width)
        ax.set_ylim(0, plot_height)
        ax.set_aspect('equal')
        ax.invert_yaxis()

        boundary = patches.Rectangle((0, 0), plot_width, plot_height,
                                    linewidth=2, edgecolor='black',
                                    facecolor='white')
        ax.add_patch(boundary)

        for corridor in layout.corridors:
            if corridor.type == CorridorType.VERTICAL:
                rect = patches.Rectangle((corridor.pos, corridor.start), 3,
                                        corridor.end - corridor.start,
                                        linewidth=1, edgecolor='gray',
                                        facecolor='lightgray', alpha=0.7)
            else:
                rect = patches.Rectangle((corridor.start, corridor.pos),
                                        corridor.end - corridor.start, 3,
                                        linewidth=1, edgecolor='gray',
                                        facecolor='lightgray', alpha=0.7)
            ax.add_patch(rect)

        colors = plt.cm.Set3.colors
        for i, room in enumerate(layout.placed_rooms):
            color = colors[room.id % len(colors)]
            rect = patches.Rectangle((room.x, room.y), room.placed_width,
                                    room.placed_height, linewidth=2,
                                    edgecolor='darkblue', facecolor=color,
                                    alpha=0.6)
            ax.add_patch(rect)

            cx = room.x + room.placed_width / 2
            cy = room.y + room.placed_height / 2
            label = f"R{room.id}"
            if room.rotated:
                label += "*"
            ax.text(cx, cy, label, ha='center', va='center',
                   fontweight='bold', fontsize=8)

        ax.set_title(f'Layout {idx+1} | Area: {layout.get_room_area()}/{plot_width*plot_height}\n'
                    f'Rooms: {len(layout.placed_rooms)} | Corridors: {len(layout.corridors)}',
                    fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=7)

    total_subplots = rows * cols
    for idx in range(num_layouts, total_subplots):
        row = idx // cols
        col = idx % cols
        ax = axes[row][col] if rows > 1 else axes[0][col]
        ax.axis('off')

    plt.tight_layout()
    plt.savefig('floor_plan_all_layouts.png', dpi=150, bbox_inches='tight')
    print(f"\nSaved visualization to 'floor_plan_all_layouts.png'")
    plt.show()


def draw_layout(ax, layout, plot_width, plot_height, rooms):
    """Draw a single layout onto the provided matplotlib axis (in-place).

    This re-uses the drawing logic from visualize_layouts but targets a single
    axis so it can be embedded in a GUI carousel.
    """
    ax.clear()
    ax.set_xlim(0, plot_width)
    ax.set_ylim(0, plot_height)
    ax.set_aspect('equal')
    ax.invert_yaxis()

    boundary = patches.Rectangle((0, 0), plot_width, plot_height,
                                linewidth=2, edgecolor='black',
                                facecolor='white')
    ax.add_patch(boundary)

    for corridor in layout.corridors:
        if corridor.type == CorridorType.VERTICAL:
            rect = patches.Rectangle((corridor.pos, corridor.start), 3,
                                    corridor.end - corridor.start,
                                    linewidth=1, edgecolor='gray',
                                    facecolor='lightgray', alpha=0.7)
        else:
            rect = patches.Rectangle((corridor.start, corridor.pos),
                                    corridor.end - corridor.start, 3,
                                    linewidth=1, edgecolor='gray',
                                    facecolor='lightgray', alpha=0.7)
        ax.add_patch(rect)

    colors = plt.cm.Set3.colors
    for i, room in enumerate(layout.placed_rooms):
        color = colors[room.id % len(colors)]
        rect = patches.Rectangle((room.x, room.y), room.placed_width,
                                room.placed_height, linewidth=2,
                                edgecolor='darkblue', facecolor=color,
                                alpha=0.6)
        ax.add_patch(rect)

        cx = room.x + room.placed_width / 2
        cy = room.y + room.placed_height / 2
        label = f"R{room.id}"
        if room.rotated:
            label += "*"
        ax.text(cx, cy, label, ha='center', va='center',
               fontweight='bold', fontsize=8)

    ax.grid(True, alpha=0.3)




if __name__ == '__main__':
    # Demo / CLI execution
    rooms = [
        Room(1, 10, 12),
        Room(2, 15, 8),
        Room(3, 7, 14),
        Room(4, 20, 10),
        Room(5, 12, 12)
    ]

    plot_width = 20
    plot_height = 20

    print("=" * 60)
    print("FLOOR PLAN LAYOUT GENERATOR")
    print("=" * 60)
    print(f"Plot dimensions: {plot_width} x {plot_height}")
    print(f"Rooms: {len(rooms)}")
    for room in rooms:
        print(f"  - Room {room.id}: {room.width} x {room.height} (area: {room.get_area()})")
    print(f"Total room area: {sum(r.get_area() for r in rooms)}")
    print(f"Plot area: {plot_width * plot_height}")
    print(f"70% constraint: {plot_width * plot_height * 0.7}")
    print("=" * 60)


    layouts = generate_layouts(rooms, plot_width, plot_height, max_layouts=20, max_attempts=500)

    print("=" * 60)
    print(f"SUCCESSFULLY GENERATED {len(layouts)} UNIQUE LAYOUTS!")
    print("=" * 60)

    if layouts:
        print("\nLayout Summary:")
        for i, layout in enumerate(layouts):
            print(f"  Layout {i+1:2d}: {len(layout.placed_rooms)} rooms, "
                  f"Area: {layout.get_room_area():4d}/{plot_width*plot_height}, "
                  f"Corridors: {len(layout.corridors):2d}")

        print(f"\nVisualizing all {len(layouts)} layouts...")
        visualize_layouts(layouts, plot_width, plot_height, rooms)
    else:
        print("No valid layouts generated!")