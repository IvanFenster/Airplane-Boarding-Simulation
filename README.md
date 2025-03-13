# Airplane-Boarding-Simulation

Overview
This program simulates airplane boarding using Pygame. It animates passengers moving down the aisle (one tile per tick), stowing their luggage, and moving to their seats. It supports six different boarding methods, plus an option to have late-arriving passengers who do not arrive in their original place in the queue. 

<img width="804" alt="Снимок экрана 2025-03-13 в 11 07 58" src="https://github.com/user-attachments/assets/27d13ed2-6e5d-46da-a317-c06edcf745a2" />

## Boarding Methods:
(0) Fully Random: Each seat is assigned at random for each passenger.  
(1) Back-to-Front (within each row randomly): Rows are processed from the back to the front, but seat letters are shuffled inside each row.  
(2) Back-to-Front, Window to Aisle: Strict seat-letter order in each row: A, F, B, E, C, D.  
(3) Skip Rows: Passengers fill odd rows first (from the back), then even rows (from the back). Inside each row, seat letters are shuffled.  
(4) Zones (3 zones: back, middle, front). Each zone’s seats are randomly ordered among themselves, but the entire back zone goes first, then middle, then front.  
(5) Special: A custom grouping method with 4 sub-groups, each occupying seats in a special pattern (skipping rows, switching sides).  

## Late Arrivals:
The user inputs a percentage of late passengers (0 to 100).  
The user chooses whether late arrivals are:  
“Immediate” (they come as soon as they appear, but with random unique offsets in the queue so no two late passengers arrive at exactly the same slot), or
“After everyone” (they wait until all normal passengers have boarded, then all late passengers board in a random order).  

## Animation:
Each passenger moves through the aisle by discrete tiles, one tile per tick.
You can adjust the simulation speed via a slider at the bottom.  
Passengers are shown as circles:  
Red = normal passenger who is still walking,  
Green = normal passenger who has sat down (done),  
Blue = late passenger who is still walking,  
Light Blue = late passenger who has sat down (done).  

## Timing:
The simulation runs in ticks. A passenger can only move one tile per tick.  
Stowing luggage (if they have overhead bags) costs a couple of ticks.  
The program tracks how many ticks elapsed until everyone is seated.  

## Requirements
Python 3  
Pygame installed (pip install pygame).  

## How to Run
1. Clone or download this repository.  
2. Run python simulation.py (or python3 simulation.py).  
After you set settings of simulation in console, a Pygame window appears.  
Use the slider at the bottom to adjust the simulation speed (frames per second).  

## License / Usage
Feel free to use or modify for educational or demonstration purposes.  
