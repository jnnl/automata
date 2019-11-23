#!/usr/bin/env python
# Cellular automata with curses

import argparse
import collections
import curses
import os
import random
import sys
import time


class OverpopulationException(Exception):
    pass

class HaltedException(Exception):
    pass

class Life:
    def __init__(self, width=64, height=64, live='.', dead=' '):
        self.width = width
        self.height = height
        self.universe = None
        self.live = live
        self.dead = dead
        self.universe = [[self.dead for _ in range(self.width)] for _ in range(self.height)]
        self.history = collections.deque(maxlen=8)
        self.generations = 0

    def fill_random(self, n=10):
        if n < 0:
            n = (self.width * self.height) // 2
        if n >= self.width * self.height:
            raise OverpopulationException('number of random cells cannot exceed universe size'
                                          ' (max: {})'.format(self.width * self.height))
            sys.exit(1)

        full_universe = [col for row in self.universe for col in row]
        for i in range(n):
            full_universe[i] = self.live
        random.shuffle(full_universe)
        self.universe = [full_universe[i:i + self.width] for i in range(0, len(full_universe), self.width)]

    def fill_from_file(self, infile):
        with open(infile) as f:
            lines = f.readlines()

        for y, row in enumerate(lines):
            if row.count(self.live) > 0:
                for x, col in enumerate(row):
                    if col == self.live:
                        self.universe[y][x] = col

    def in_bounds(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def neighbors(self, x, y):
        coords = ((x, y+1), (x+1, y+1), (x+1, y), (x+1, y-1),
                  (x, y-1), (x-1, y-1), (x-1, y), (x-1, y+1))

        return sum(self.universe[y][x] == self.live
                   for x, y in coords if self.in_bounds(x, y))

    def get_changes(self):
        changes = []
        for y, row in enumerate(self.universe):
            for x, col in enumerate(row):
                n = self.neighbors(x, y)
                if col == self.live and (n < 2 or n > 3):
                    changes.append((x, y, self.dead))
                elif col == self.dead and n == 3:
                    changes.append((x, y, self.live))

        return changes

    def apply_changes(self, changes):
        for x, y, new_state in changes:
            self.universe[y][x] = new_state

    def advance(self, eternal=False):
        self.generations += 1
        changes = self.get_changes()
        self.apply_changes(changes)

        if not eternal and (not len(changes) or changes in self.history):
            raise HaltedException(self.generations)

        self.history.append(changes[:])


def draw(stdscr, args):
    if args.auto_size:
        if sys.version_info[0] >= 3:
            width, height = os.get_terminal_size()
        else:
            import subprocess
            width = int(subprocess.check_output(['tput', 'cols']))
            height = int(subprocess.check_output(['tput', 'lines']))
    else:
        width, height = args.width, args.height

    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_RED)
    curses.curs_set(0)
    halt_msg = 'Universe halted after {} generations ({:.2f}s)'

    while True:
        ca = Life(width=width, height=height, live=args.live, dead=args.dead)

        if args.in_file:
            ca.fill_from_file(args.in_file)
        else:
            ca.fill_random(args.cells)

        start = time.perf_counter()

        while True:
            stdscr.clear()
            for i, row in enumerate(ca.universe):
                try:
                    stdscr.addstr(i, 0, args.fill.join(row))
                except:
                    continue

            stdscr.refresh()

            try:
                ca.advance(eternal=args.eternal)
            except HaltedException as he:
                if args.eternal:
                    continue
                end = time.perf_counter()
                if args.repeat:
                    if not args.quiet:
                        stdscr.addstr(0, 0, halt_msg.format(he, end-start), curses.color_pair(1))
                        stdscr.refresh()
                    time.sleep(args.delay)
                    break
                else:
                    if not args.quiet:
                        stdscr.addstr(0, 0,
                                      halt_msg.format(he, end-start) + '\nPress any key to exit',
                                      curses.color_pair(1))
                        stdscr.refresh()
                    stdscr.getch()
                    return

            time.sleep(1 / args.rate)


def parse_args():
    parser = argparse.ArgumentParser(description='Cellular automata in the CLI')
    parser.add_argument('-A', '--automaton', nargs='?', default='life', choices=['life'],
                        help='automaton to run (choices: life)')
    parser.add_argument('-x', '--width', type=int, default=64,
                        help='width of the universe (default: 64)')
    parser.add_argument('-y', '--height', type=int, default=64,
                        help='height of the universe (default: 64)')
    parser.add_argument('-a', '--auto-size', action='store_true',
                        help='set universe size to terminal width * height')
    parser.add_argument('-r', '--rate', type=float, default=10.0,
                        help='generations per second (default: 10)')
    parser.add_argument('-c', '--cells', type=int, default=-1,
                        help='number of initial live cells (default: (width * height) / 2)')
    parser.add_argument('-l', '--live', type=str, default='.',
                        help='live cell character (default: \'.\')')
    parser.add_argument('-d', '--dead', type=str, default=' ',
                        help='dead cell character (default: \' \')')
    parser.add_argument('-f', '--fill', type=str, default=' ',
                        help='fill space character (default: \' \')')
    parser.add_argument('-w', '--wrap', action='store_true',
                        help='wrap cells around the universe (NOT IMPLEMENTED YET)')
    parser.add_argument('-i', '--in-file',
                        help='read initial universe state from file')
    parser.add_argument('-R', '--repeat', action='store_true',
                        help='re-initialize universe and restart if halt is detected')
    parser.add_argument('-D', '--delay', type=float, default=1.0,
                        help='number of seconds to wait before restarting automaton (default: 1)')
    parser.add_argument('-E', '--eternal', action='store_true',
                        help='keep running even if universe halt is detected (overrides -R)')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='don\'t show info messages')

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    try:
        curses.wrapper(draw, args)
    except KeyboardInterrupt:
        sys.exit()
