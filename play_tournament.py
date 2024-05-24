import os
import sys
import time
import csv
import glob
from reconchess import load_player, play_local_game, LocalGame
import chess
import traceback
import datetime
from functools import wraps
from contextlib import redirect_stdout, redirect_stderr
import random
import multiprocessing
import multiprocessing.pool
from colorama import Fore, Back, Style
from dotenv import load_dotenv
import re

load_dotenv()

SECONDS_PER_PLAYER = 60


def redirect_output(filename):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with open(filename, "w") as f:
                with redirect_stdout(f), redirect_stderr(f):
                    return func(*args, **kwargs)

        return wrapper

    return decorator


# Wrap play_local_game so that I can get rid of stdout
@redirect_output("/dev/null")
def play_local_game_wrapper(white_player, black_player, game=None):
    return play_local_game(white_player, black_player, game=game)


class NoDaemonProcess(multiprocessing.Process):
    @property
    def daemon(self):
        return False

    @daemon.setter
    def daemon(self, value):
        pass


class NoDaemonContext(type(multiprocessing.get_context())):
    Process = NoDaemonProcess


# We sub-class multiprocessing.pool.Pool instead of multiprocessing.Pool
# because the latter is only a wrapper function, not a proper class.
class MyPool(multiprocessing.pool.Pool):
    def __init__(self, *args, **kwargs):
        kwargs["context"] = NoDaemonContext()
        super(MyPool, self).__init__(*args, **kwargs)


# https://gist.github.com/ih84ds/be485a92f334c293ce4f1c84bfba54c9
def create_balanced_round_robin(players):
    """Create a schedule for the players in the list and return it"""
    s = []
    if len(players) % 2 == 1:
        players = players + [None]
    # manipulate map (array of indexes for list) instead of list itself
    # this takes advantage of even/odd indexes to determine home vs. away
    n = len(players)
    map = list(range(n))
    mid = n // 2
    for i in range(n - 1):
        l1 = map[:mid]
        l2 = map[mid:]
        l2.reverse()
        round = []
        for j in range(mid):
            t1 = players[l1[j]]
            t2 = players[l2[j]]
            if j == 0 and i % 2 == 1:
                # flip the first match only, every other round
                # (this is because the first match always involves the last player in the list)
                round.append((t2, t1))
            else:
                round.append((t1, t2))
        s.append(round)
        # rotate list by n/2, leaving last element at the end
        map = map[mid:-1] + map[:mid] + map[-1:]
    return s


reconchess_bots = [
    "reconchess.bots.random_bot",
    "reconchess.bots.trout_bot",
    "reconchess.bots.attacker_bot",
]


class Submission:
    def __init__(self, id, dir=None, bot_name=None):
        self.id = id
        if dir is not None:
            # Check if dir is a file
            if os.path.isfile(dir):
                
                self.name = os.path.basename(dir).split("_")[0][:-3]
                self.path = None
                self.filename = dir
                self.is_bot = False
            else:
                self.name = os.path.basename(dir).split("_")[0]
                self.path = dir

                # Get the submission file name that ends in .py
                self.filename = glob.glob(os.path.join(dir, "*.py"))
                # If not an empty list, get the first value, else None
                self.filename = self.filename[0] if len(self.filename) > 0 else None
                self.is_bot = False
        else:
            self.name = bot_name.split(".")[2]
            self.path = None
            self.filename = bot_name
            self.is_bot = True

    def __repr__(self):
        return self.name

    def is_valid(self):
        return self.filename or self.is_bot


def load_submission(filename):
    sub_name = None
    sub_class = None
    error = None
    try:
        sub_name, sub_class = load_player(filename)
    except:
        tb = traceback.format_exc()
        error = tb

    return sub_name, sub_class, error


def save_replay(white_sub, black_sub, winner, history=None, tb=None):
    """
    winner is either "white", "black", or "draw"
    """
    root_dir = os.path.dirname(os.path.abspath(__file__))
    replay_dir = os.path.join(root_dir, "replays")

    if not os.path.exists(replay_dir):
        os.makedirs(replay_dir)

    # replay_path = "{}-{}-{}.json".format(white_sub.name, black_sub.name, winner)
    if winner == white_sub:
        white_name = white_sub.name.upper()
        black_name = black_sub.name.lower()
    elif winner == black_sub:
        black_name = black_sub.name.upper()
        white_name = white_sub.name.lower()
    else:
        white_name = white_sub.name.lower()
        black_name = black_sub.name.lower()

    replay_name = f"{white_name}_{black_name}.json"
    replay_path = os.path.join(replay_dir, replay_name)

    if history:
        history.save(replay_path)
    elif tb:
        replay_name = f"{white_name}_{black_name}-ERROR.json"
        replay_path = os.path.join(replay_dir, replay_name)
        # Just save the traceback in the json file
        with open(replay_path, "w") as f:
            f.write(tb)
            f.close()


def play_game(white_submission, black_submission):
    """
    returns winner_submission
    """

    #  Load the white submission and black submission
    white_cls_name, white_player_cls, white_error = load_submission(
        white_submission.filename
    )
    black_cls_name, black_player_cls, black_error = load_submission(
        black_submission.filename
    )

    win_reason = None
    winner = None
    history = None

    # Check if there were problems loading the submissions
    if white_error is not None or black_error is not None:
        tb = None
        win_reason = "Load Error"
        if white_error is not None and black_error is not None:
            # Both submissions failed to load. Consider it a draw
            winner = None
        elif white_error is not None:
            # Give black the win
            winner = black_submission
            tb = white_error
        elif black_error is not None:
            # Give white the win
            winner = white_submission
            tb = black_error

        if tb:
            save_replay(white_submission, black_submission, winner, tb=tb)

    else:

        # Create the game
        game = LocalGame(
            seconds_per_player=SECONDS_PER_PLAYER, full_turn_limit=50
        )  # Make this 60 * 7 seconds for the full one

        # Play the game
        print(
            f"{Style.DIM}Playing {white_submission.name} vs {black_submission.name}{Style.RESET_ALL}"
        )
        try:
            white_obj = white_player_cls()
            black_obj = black_player_cls()
            winner_color, win_reason, history = play_local_game_wrapper(
                white_obj, black_obj, game=game
            )
            winner = (
                white_submission if winner_color == chess.WHITE else black_submission
            )

            save_replay(white_submission, black_submission, winner, history)
        except:
            tb = traceback.format_exc()
            win_reason = "Runtime Error"
            # One of the submissions had an error in their execution. Give the win to the other player
            winner = None
            if white_submission.name in tb:
                winner = black_submission
            elif black_submission.name in tb:
                winner = white_submission

            if winner is None:
                print(
                    f"{white_submission.name} vs {black_submission.name}-{Fore.RED}INTERNAL ERROR{Style.RESET_ALL}"
                )
            
            save_replay(white_submission, black_submission, winner, tb=tb)

            game.end()

    if winner:
        print(
            f"{Fore.GREEN}Winner: {Style.BRIGHT}{winner.name}{Style.NORMAL}, Reason: {win_reason}{Style.RESET_ALL}"
        )
    else:
        pass

    return winner


if __name__ == "__main__":
    submission_directory = "/home/andrew/Documents/reconchess-tournament/subs"

    # Get all directories (i.e. student submissions) in the submission directory
    student_submission_dirs = glob.glob(os.path.join(submission_directory, "*"))
    submissions = {}

    # Create a Submission object for each student submission
    for i, student_submission_dir in enumerate(student_submission_dirs):
        submission = Submission(i, student_submission_dir)
        submissions[i] = submission

    # Add all the bots
    num_human_subs = len(submissions)
    for i, bot in enumerate(reconchess_bots):
        bot_id = i + num_human_subs
        submissions[bot_id] = Submission(bot_id, bot_name=bot)

    # Get all the student names by reading until the '_' character in the directory name
    for i, student in submissions.items():
        print(f"{i}: {student.name}")

    # Create a leaderboard
    points = {i: 0 for i in submissions.keys()}

    tournament = create_balanced_round_robin(list(submissions.keys()))
    playable_round = []
    results = []
    for round_num, round in enumerate(tournament):
        for i, (white, black) in enumerate(round):
            # if white is None or black is None or ('Katlego' not in submissions[white].name and 'Katlego' not in submissions[black].name):
            if white is None or black is None:
                results.append(None)
            else:
                # Check to see if subs are valid
                if submissions[white].is_valid() and submissions[black].is_valid():
                    playable_round.append((white, black))

    print(f"Playing {len(playable_round)} games")
    games_left = len(playable_round)

    pool = MyPool(processes=os.cpu_count() - 1, maxtasksperchild=1)

    for result in pool.starmap(
        play_game,
        [(submissions[white], submissions[black]) for white, black in playable_round],
        chunksize=1,
    ):
        results.append(result)

    pool.close()

    # for white, black in playable_round:
    #     winner = play_game(submissions[white], submissions[black])
    #     results.append(winner)

    # Print the results of the round
    for winner in results:
        # Update points
        if winner:
            points[winner.id] += 1

    # Print the final leaderboard in descending order
    print()
    print("-" * 50)
    print("Final Leaderboard")
    print("-" * 50)
    sorted_points = sorted(points.items(), key=lambda x: x[1], reverse=True)

    # Save the leaderboard to a csv file
    f = open("leaderboard.csv", "w")
    writer = csv.writer(f)
    writer.writerow(["Rank", "Name", "Surname", "Points"])
    print(
        f"{'#'.rjust(3)} {'Name'.ljust(15)} {'Surname'.ljust(15)} {str('Points').rjust(3)}"
    )
    print()
    for i, point in enumerate(sorted_points):
        name = submissions[point[0]].name.split(" ")
        if len(name) == 1:
            surname = ""
            name = name[0]
        else:
            name, surname = name
        writer.writerow([i + 1, name, surname, point[1]])
        print(
            f"{str(i+1).rjust(3)} {name.ljust(15)} {surname.ljust(15)} {str(point[1]).rjust(3)}"
        )
    f.close()
