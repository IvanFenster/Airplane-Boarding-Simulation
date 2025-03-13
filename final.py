import pygame
import sys
import random

# ------------------- HELPER FUNCTIONS -------------------

def input_rows():
    """Read the number of rows from console."""
    while True:
        try:
            val = int(input("Enter the number of rows (for example, 33): "))
            if val > 0:
                return val
        except:
            pass
        print("Invalid input. Please enter an integer > 0.")

def letter_to_col(letter):
    """Map seat letters 'A'..'C' to columns 0..2, 'D'..'F' to columns 4..6."""
    mapping = {'A': 0, 'B': 1, 'C': 2, 'D': 4, 'E': 5, 'F': 6}
    return mapping[letter]

def generate_unique_seats(num_rows, num_people):
    """
    For boarding method 0: fully random seat distribution (row, seat).
    We gather all possible seats, shuffle, then take the first num_people.
    """
    letters = ['A', 'B', 'C', 'D', 'E', 'F']
    all_seats = []
    for r in range(num_rows):
        for l in letters:
            all_seats.append((r, l))
    random.shuffle(all_seats)
    return all_seats[:num_people]

# ------------------- GLOBAL PARAMETERS -------------------

COLS = 7
AISLE_COL = 3
OVERHEAD_BIN_CAPACITY = 2
MAX_BAGS = 3

TICKS_FOR_OVERHEAD = 2
PEOPLE_COUNT = 50
TILE_SIZE = 20

ENTRANCE_ROW = -1

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (160, 160, 160)
BLUE = (30, 144, 255)        # late passenger moving
GREEN = (34, 139, 34)        # normal passenger done
RED = (220, 20, 60)          # normal passenger moving
ORANGE = (255, 165, 0)
LIGHT_BLUE = (173, 216, 230) # late passenger done

# ------------------- PLANE CLASS -------------------

class Plane:
    def __init__(self, num_rows):
        self.num_rows = num_rows
        # overhead[row][col] = how many bags are in the overhead bin above seat (col != AISLE_COL)
        self.overhead = [[0] * COLS for _ in range(num_rows)]

    def can_stow_bag(self, row, bags_needed):
        """Check if there's enough space for 'bags_needed' in overhead bins of this row."""
        total_in_row = sum(self.overhead[row][c] for c in range(COLS) if c != AISLE_COL)
        # each row has 6 seats, each seat has capacity OVERHEAD_BIN_CAPACITY
        if total_in_row + bags_needed <= 6 * OVERHEAD_BIN_CAPACITY:
            return True
        return False

    def place_bags_in_bin(self, row, bags):
        """Place 'bags' overhead in a simplified way."""
        bags_left = bags
        for c in range(COLS):
            if c == AISLE_COL:
                continue
            can_add = OVERHEAD_BIN_CAPACITY - self.overhead[row][c]
            if can_add > 0:
                put_now = min(can_add, bags_left)
                self.overhead[row][c] += put_now
                bags_left -= put_now
                if bags_left == 0:
                    break

# ------------------- FIND PASSENGER / TILE OCCUPIED -------------------

def find_passenger_at(row, col, passengers):
    """
    Find a passenger who occupies (row,col) and is not done.
    We can also consider a 'done' passenger in the aisle as blocking, if needed.
    """
    for p in passengers:
        if p.y == row and p.x == col:
            if p.state != "done":
                return p
            if p.state == "done" and col == AISLE_COL:
                return p
    return None

def is_tile_occupied(row, col, passengers):
    occ = find_passenger_at(row, col, passengers)
    return (occ is not None)

# ------------------- PASSENGER CLASS -------------------

class Passenger:
    """
    States:
      - "queue": not yet in the plane (y = -1)
      - "walking": walking down the aisle
      - "stowing": placing bags overhead (takes TICKS_FOR_OVERHEAD ticks)
      - "looking_bin": walking forward to find overhead space if row is full
      - "move_to_seat": from aisle col=3 to target seat col
      - "done": seated
    """
    def __init__(self, seat_row, seat_letter, bags_count, queue_index, is_late=False):
        self.seat_row = seat_row
        self.seat_letter = seat_letter
        self.bags_count = bags_count
        self.overhead_bags = max(0, bags_count - 1)

        self.x = AISLE_COL
        self.y = ENTRANCE_ROW
        self.state = "queue"

        self.ticks_stowing = 0
        self.delay_counter = 0
        self.passed_occupants = set()
        self.target_col = letter_to_col(self.seat_letter)

        self.queue_index = queue_index

        # Flag to indicate a late passenger
        self.is_late = is_late

    def propose_action(self, plane, passengers_in_aisle, leaving_map, current_tick):
        """
        Propose an action for 1 sub-step, based on the old positions/states of others.
        'leaving_map' is a dict {(row,col): True} meaning that occupant will leave.
        We do not actually change self here; we return a plan dict.
        """
        plan = {
            'x': self.x,
            'y': self.y,
            'state': self.state,
            'ticks_stowing': self.ticks_stowing,
            'delay_counter': self.delay_counter,
            'passed_occupants': set(self.passed_occupants)
        }

        if self.state == "done":
            return plan

        # If in queue
        if self.state == "queue":
            # Check if there's a queue passenger with a smaller index
            for other in passengers_in_aisle:
                if other.state == "queue" and other.queue_index < self.queue_index:
                    return plan
            # Try to enter the plane at (0, AISLE_COL)
            if not is_tile_occupied(0, AISLE_COL, passengers_in_aisle):
                plan['y'] = 0
                plan['state'] = "walking"
            else:
                if leaving_map.get((0, AISLE_COL), False):
                    plan['y'] = 0
                    plan['state'] = "walking"
            return plan

        if self.state == "walking":
            # Move down the aisle row by row
            if self.y < self.seat_row:
                next_y = self.y + 1
                occ = find_passenger_at(next_y, AISLE_COL, passengers_in_aisle)
                if occ is None:
                    plan['y'] = next_y
                else:
                    if leaving_map.get((next_y, AISLE_COL), False):
                        plan['y'] = next_y
            else:
                # Reached our row
                if self.overhead_bags > 0:
                    if plane.can_stow_bag(self.y, self.overhead_bags):
                        plan['state'] = "stowing"
                        plan['ticks_stowing'] = TICKS_FOR_OVERHEAD
                    else:
                        plan['state'] = "looking_bin"
                else:
                    plan['state'] = "move_to_seat"
            return plan

        if self.state == "stowing":
            # Overhead stow
            if self.ticks_stowing > 0:
                plan['ticks_stowing'] = self.ticks_stowing - 1
                if plan['ticks_stowing'] == 0:
                    plane.place_bags_in_bin(self.y, self.overhead_bags)
                    self.overhead_bags = 0
                    plan['state'] = "move_to_seat"
            return plan

        if self.state == "looking_bin":
            # Searching forward for overhead space
            if self.y < plane.num_rows - 1:
                next_y = self.y + 1
                occ = find_passenger_at(next_y, AISLE_COL, passengers_in_aisle)
                if occ is None:
                    plan['y'] = next_y
                    if plane.can_stow_bag(next_y, self.overhead_bags):
                        plan['state'] = "stowing"
                        plan['ticks_stowing'] = TICKS_FOR_OVERHEAD
                else:
                    if leaving_map.get((next_y, AISLE_COL), False):
                        plan['y'] = next_y
                        if plane.can_stow_bag(next_y, self.overhead_bags):
                            plan['state'] = "stowing"
                            plan['ticks_stowing'] = TICKS_FOR_OVERHEAD
            else:
                plan['state'] = "move_to_seat"
            return plan

        if self.state == "move_to_seat":
            if self.delay_counter > 0:
                plan['delay_counter'] = self.delay_counter - 1
                return plan

            if self.x == self.target_col:
                plan['state'] = "done"
                return plan

            step = 1 if self.x < self.target_col else -1
            next_x = self.x + step
            occ = find_passenger_at(self.y, next_x, passengers_in_aisle)
            if occ is not None:
                if occ.state == "done":
                    if occ not in self.passed_occupants:
                        plan['delay_counter'] = 1
                        newp = set(self.passed_occupants)
                        newp.add(occ)
                        plan['passed_occupants'] = newp
                    else:
                        if leaving_map.get((self.y, next_x), False):
                            plan['x'] = next_x
                else:
                    if leaving_map.get((self.y, next_x), False):
                        plan['x'] = next_x
            else:
                plan['x'] = next_x

            return plan

        return plan

# ------------------- BOARDING METHODS 0..5 (NO LATE) -------------------
# Each returns a list of Passenger in a certain order.

def generate_boarding_0_random(plane, n):
    # (0) fully random
    seats = generate_unique_seats(plane.num_rows, n)
    passengers = []
    for i,(r,l) in enumerate(seats):
        bags = random.randint(1,MAX_BAGS)
        p = Passenger(r,l,bags,i)
        passengers.append(p)
    return passengers

def generate_boarding_1_back_to_front(plane, n):
    # (1) back to front, random seat letters in each row
    letters = ['A','B','C','D','E','F']
    rows_desc = list(range(plane.num_rows-1,-1,-1))
    all_seats=[]
    for r in rows_desc:
        row_letters= letters[:]
        random.shuffle(row_letters)
        for l in row_letters:
            all_seats.append((r,l))
    all_seats = all_seats[:n]
    passengers=[]
    for i,(r,l) in enumerate(all_seats):
        bags = random.randint(1,MAX_BAGS)
        p= Passenger(r,l,bags,i)
        passengers.append(p)
    return passengers

def generate_boarding_2_back_to_front_window_to_aisle(plane, n):
    # (2) back to front, seat order: A,F,B,E,C,D
    seat_order = ['A','F','B','E','C','D']
    all_seats=[]
    for r in range(plane.num_rows-1,-1,-1):
        for l in seat_order:
            all_seats.append((r,l))
    all_seats= all_seats[:n]
    passengers=[]
    for i,(r,l) in enumerate(all_seats):
        bags= random.randint(1,MAX_BAGS)
        p= Passenger(r,l,bags,i)
        passengers.append(p)
    return passengers

def generate_boarding_3_skip_rows(plane, n):
    # (3) skip rows
    letters=['A','B','C','D','E','F']
    odd_rows_desc=[]
    even_rows_desc=[]
    for r in range(plane.num_rows-1,-1,-1):
        if r%2==1:
            odd_rows_desc.append(r)
        else:
            even_rows_desc.append(r)
    all_seats=[]
    for r in odd_rows_desc:
        row_letters= letters[:]
        random.shuffle(row_letters)
        for l in row_letters:
            all_seats.append((r,l))
    for r in even_rows_desc:
        row_letters= letters[:]
        random.shuffle(row_letters)
        for l in row_letters:
            all_seats.append((r,l))
    all_seats=all_seats[:n]
    passengers=[]
    for i,(r,l) in enumerate(all_seats):
        bags= random.randint(1,MAX_BAGS)
        p= Passenger(r,l,bags,i)
        passengers.append(p)
    return passengers

def generate_boarding_4_zones(plane, n):
    # (4) zones: 3 zones (back/middle/front), fully random inside each zone
    letters=['A','B','C','D','E','F']
    row_desc= list(range(plane.num_rows))
    row_desc.sort(reverse=True)
    total_rows=len(row_desc)
    zone_size= total_rows//3
    zone1_rows= row_desc[:zone_size]           # back zone
    zone2_rows= row_desc[zone_size:2*zone_size]
    zone3_rows= row_desc[2*zone_size:]         # front zone

    # gather seats for each zone
    zone1_seats=[]
    for r in zone1_rows:
        for l in letters:
            zone1_seats.append((r,l))
    random.shuffle(zone1_seats)

    zone2_seats=[]
    for r in zone2_rows:
        for l in letters:
            zone2_seats.append((r,l))
    random.shuffle(zone2_seats)

    zone3_seats=[]
    for r in zone3_rows:
        for l in letters:
            zone3_seats.append((r,l))
    random.shuffle(zone3_seats)

    # combine
    all_seats= zone1_seats + zone2_seats + zone3_seats
    all_seats= all_seats[:n]
    passengers=[]
    for i,(r,l) in enumerate(all_seats):
        bags_count= random.randint(1,MAX_BAGS)
        p=Passenger(r,l,bags_count,i)
        passengers.append(p)
    return passengers

def generate_boarding_5_4groups(plane, n):
    # (5) 4 groups approach
    left_side=['A','B','C']
    right_side=['D','E','F']

    def build_group_seats(start_row, start_side):
        result=[]
        row=start_row
        side=start_side
        while row>=0:
            if side=='left':
                seats3= left_side[:]
            else:
                seats3= right_side[:]
            random.shuffle(seats3)
            for seat in seats3:
                result.append((row, seat))
            row-=2
            side='right' if side=='left' else 'left'
        return result

    last_row= plane.num_rows-1
    group1= build_group_seats(last_row, 'left')
    group2= build_group_seats(last_row, 'right')
    group3= build_group_seats(last_row-1, 'left')
    group4= build_group_seats(last_row-1, 'right')

    all_seats= group1 + group2 + group3 + group4
    all_seats= all_seats[:n]
    passengers=[]
    for i,(r,l) in enumerate(all_seats):
        bags= random.randint(1,MAX_BAGS)
        p= Passenger(r,l,bags,i)
        passengers.append(p)
    return passengers

# ------------------- LATE ARRIVALS MANAGEMENT -------------------

def apply_late_arrivals(base_passengers, late_percent, late_immediate):
    """
    Given a base list of passengers (with their seat assignments and order),
    mark 'late_percent' of them as late, and reorder if needed.

    If late_immediate = False, all late passengers go after the normal ones
    in a random order among themselves.

    If late_immediate = True, each late passenger gets a random unique offset
    so that no two late appear at the exact same position in the queue.
    Then we sort by (original_index + offset).
    """
    n= len(base_passengers)
    late_count= int(n* late_percent/100.0)
    if late_count<=0:
        return base_passengers  # no late

    indices= list(range(n))
    late_indices= random.sample(indices, late_count)

    # Mark them
    for i in late_indices:
        base_passengers[i].is_late= True

    if not late_immediate:
        # They go after everyone else
        normal_pass= [p for p in base_passengers if not p.is_late]
        late_pass= [p for p in base_passengers if p.is_late]
        random.shuffle(late_pass)
        new_list= normal_pass + late_pass
        for i,p in enumerate(new_list):
            p.queue_index= i
        return new_list
    else:
        # They come as soon as possible but with unique random offsets
        max_delay= n+10
        used_delays= set()

        def get_unique_delay():
            while True:
                d= random.randint(0, max_delay)
                if d not in used_delays:
                    used_delays.add(d)
                    return d

        passenger_arr= []
        for p in base_passengers:
            if p.is_late:
                extra= get_unique_delay()
                passenger_arr.append((p.queue_index, extra, p))
            else:
                passenger_arr.append((p.queue_index, 0, p))

        # sort by base_index + offset
        passenger_arr.sort(key=lambda x: x[0]+ x[1])

        new_list= []
        for i,(_,_,p) in enumerate(passenger_arr):
            p.queue_index= i
            new_list.append(p)
        return new_list

# ------------------- SIMULATION CLASS -------------------

class Simulation:
    def __init__(self):
        pygame.init()

        self.num_rows= input_rows()

        # Late arrivals input
        self.late_percent= float(input("Enter the percentage of late passengers (0..100): "))
        ans= input("Immediate arrivals (yes) or after all (no)? (yes/no): ").strip().lower()
        self.late_immediate= (ans=="yes")

        self.boarding_method= self.select_boarding_method()

        self.people_count= self.num_rows*6
        self.plane= Plane(self.num_rows)

        # Generate base passengers
        if self.boarding_method == 0:
            base_pass= generate_boarding_0_random(self.plane, self.people_count)
        elif self.boarding_method == 1:
            base_pass= generate_boarding_1_back_to_front(self.plane, self.people_count)
        elif self.boarding_method == 2:
            base_pass= generate_boarding_2_back_to_front_window_to_aisle(self.plane, self.people_count)
        elif self.boarding_method == 3:
            base_pass= generate_boarding_3_skip_rows(self.plane, self.people_count)
        elif self.boarding_method == 4:
            base_pass= generate_boarding_4_zones(self.plane, self.people_count)
        else:
            base_pass= generate_boarding_5_4groups(self.plane, self.people_count)

        # Apply late arrivals logic
        self.passengers_queue= apply_late_arrivals(base_pass, self.late_percent, self.late_immediate)

        self.passengers_in_aisle= []

        self.plane_width= COLS*TILE_SIZE
        self.plane_height= self.num_rows*TILE_SIZE
        min_width=800
        min_height=600
        screen_w= max(self.plane_width+200, min_width)
        screen_h= max(self.plane_height+150, min_height)
        self.screen_width= screen_w
        self.screen_height= screen_h
        self.screen= pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Simulation: 6 boarding methods + late arrivals")

        self.offset_x= (self.screen_width- self.plane_width)//2
        self.offset_y= 50

        self.clock= pygame.time.Clock()
        self.tick_count= 0
        self.final_tick_count= None
        self.running= True

        # Slider
        self.slider_rect= pygame.Rect(self.screen_width//2 - 100, self.screen_height - 50, 200, 10)
        self.slider_handle_x= self.slider_rect.left
        self.slider_dragging= False
        self.min_speed=1
        self.max_speed=60
        self.current_speed= 10

    def select_boarding_method(self):
        print("Choose a boarding method:")
        print("0 - Fully random")
        print("1 - Back-to-front (random within each row)")
        print("2 - Back-to-front (window->aisle seats)")
        print("3 - Skip rows (odd first, then even, from back)")
        print("4 - Zones (back/middle/front), random inside each zone")
        print("5 - 4 groups approach, skipping rows and switching sides")
        while True:
            try:
                choice= int(input("Enter a number (0..5): "))
                if 0<= choice <=5:
                    return choice
            except:
                pass
            print("Invalid choice, please try again.")

    def run(self):
        while self.running:
            self.handle_events()
            self.update_in_parallel()
            self.draw()
            self.clock.tick(self.current_speed)
        pygame.quit()
        sys.exit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                self.running=False
            elif event.type==pygame.MOUSEBUTTONDOWN:
                if event.button==1:
                    mx,my= event.pos
                    handle_rect= pygame.Rect(self.slider_handle_x-5,
                                             self.slider_rect.centery-5,
                                             10,10)
                    if handle_rect.collidepoint(mx,my):
                        self.slider_dragging= True
            elif event.type==pygame.MOUSEBUTTONUP:
                if event.button==1:
                    self.slider_dragging= False
            elif event.type==pygame.MOUSEMOTION:
                if self.slider_dragging:
                    mx,my= event.pos
                    left=self.slider_rect.left
                    right=self.slider_rect.right
                    self.slider_handle_x= max(left, min(right, mx))
                    self.update_speed_from_slider()

    def update_speed_from_slider(self):
        sw= self.slider_rect.width
        relx= self.slider_handle_x- self.slider_rect.left
        fraction= relx/float(sw)
        speed= self.min_speed + fraction*(self.max_speed - self.min_speed)
        self.current_speed= max(self.min_speed, min(self.max_speed, int(speed)))

    def update_in_parallel(self):
        all_done= all(p.state=="done" for p in self.passengers_queue)
        if all_done and self.final_tick_count is None:
            self.final_tick_count= self.tick_count

        if not all_done:
            self.tick_count+= 1

        for p in self.passengers_queue:
            if p.state!="done" and p not in self.passengers_in_aisle:
                self.passengers_in_aisle.append(p)

        max_substeps= 10
        moved_this_tick= set()

        for _ in range(max_substeps):
            any_move= self.do_substep(moved_this_tick)
            if not any_move:
                break

        self.passengers_in_aisle= [p for p in self.passengers_in_aisle if p.state!="done"]

    def do_substep(self, moved_this_tick):
        candidates= [p for p in self.passengers_in_aisle if p not in moved_this_tick]
        if not candidates:
            return False

        # Sort by queue_index
        cand_sorted= sorted(candidates, key=lambda pp: pp.queue_index)

        draft_plans= {}
        for p in cand_sorted:
            draft_plans[p]= p.propose_action(self.plane, self.passengers_in_aisle,
                                             leaving_map={}, current_tick=self.tick_count)
        leaving_map={}
        for p,plan in draft_plans.items():
            oldpos=(p.y,p.x)
            newpos=(plan['y'], plan['x'])
            if oldpos!= newpos:
                leaving_map[oldpos]= True

        final_plans={}
        for p in cand_sorted:
            final_plans[p]= p.propose_action(self.plane, self.passengers_in_aisle,
                                             leaving_map, current_tick=self.tick_count)

        desired_positions={}
        for p,plan in final_plans.items():
            np= (plan['y'], plan['x'])
            desired_positions.setdefault(np,[]).append(p)

        final_updates={}
        for pos, p_list in desired_positions.items():
            if len(p_list)==1:
                final_updates[p_list[0]]= final_plans[p_list[0]]
            else:
                srt= sorted(p_list, key=lambda pp: pp.queue_index)
                winner= srt[0]
                final_updates[winner]= final_plans[winner]
                for loser in srt[1:]:
                    final_updates[loser]= {
                        'x': loser.x,
                        'y': loser.y,
                        'state': loser.state,
                        'ticks_stowing': loser.ticks_stowing,
                        'delay_counter': loser.delay_counter,
                        'passed_occupants': set(loser.passed_occupants)
                    }

        moved_anyone= False
        for p in cand_sorted:
            upd= final_updates[p]
            old_xy=(p.x,p.y)
            p.x= upd['x']
            p.y= upd['y']
            p.state= upd['state']
            p.ticks_stowing= upd['ticks_stowing']
            p.delay_counter= upd['delay_counter']
            p.passed_occupants= upd['passed_occupants']
            if (p.x,p.y)!=old_xy:
                moved_anyone= True
                moved_this_tick.add(p)

        return moved_anyone

    def draw(self):
        self.screen.fill(WHITE)

        # Draw plane grid
        for r in range(self.num_rows):
            for c in range(COLS):
                rx= self.offset_x + c*TILE_SIZE
                ry= self.offset_y + r*TILE_SIZE
                color= GRAY if c==AISLE_COL else (200,230,250)
                pygame.draw.rect(self.screen, color, (rx,ry,TILE_SIZE,TILE_SIZE), 1)

        # Draw passengers
        for p in self.passengers_queue:
            scr_x= self.offset_x + p.x*TILE_SIZE + TILE_SIZE//2
            scr_y= self.offset_y + p.y*TILE_SIZE + TILE_SIZE//2
            if p.y<0:
                scr_y= self.offset_y + p.y*TILE_SIZE + TILE_SIZE//2

            rad= TILE_SIZE//2 -2

            # If p.is_late => blue or light blue
            if p.is_late:
                if p.state=="done":
                    color= LIGHT_BLUE
                else:
                    color= BLUE
            else:
                if p.state=="done":
                    color= GREEN
                else:
                    color= RED

            pygame.draw.circle(self.screen, color, (scr_x, scr_y), rad)

        font= pygame.font.SysFont(None, 24)
        if self.final_tick_count is not None:
            txt= f"Ticks (frozen): {self.final_tick_count}"
        else:
            txt= f"Ticks: {self.tick_count}"
        surf= font.render(txt, True, BLACK)
        self.screen.blit(surf, (10,10))

        # Slider
        pygame.draw.rect(self.screen, BLACK, self.slider_rect)
        handle= pygame.Rect(0,0,10,20)
        handle.centerx= self.slider_handle_x
        handle.centery= self.slider_rect.centery
        pygame.draw.rect(self.screen, ORANGE, handle)
        speed_txt= font.render(f"Speed: {self.current_speed} FPS", True, BLACK)
        self.screen.blit(speed_txt, (self.slider_rect.right+10, self.slider_rect.top-5))

        pygame.display.flip()


if __name__=="__main__":
    sim= Simulation()
    sim.run()
