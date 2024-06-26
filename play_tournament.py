import os
import glob
from reconchess import load_player, play_local_game, LocalGame
import chess
import traceback
from functools import wraps
from contextlib import redirect_stdout, redirect_stderr
import multiprocessing
import multiprocessing.pool
from colorama import Fore, Back, Style
from dotenv import load_dotenv
import re
from leaderboard_from_files import print_leaderboard, read_results
import argparse

load_dotenv()

SECONDS_PER_PLAYER = 60 * 7


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
            # Replace the underscores with spaces
            self.name = re.sub("_", " ", self.name)
            self.path = None
            self.filename = bot_name
            self.is_bot = True

    def __repr__(self):
        return self.name

    def is_valid(self):
        return self.filename or self.is_bot

args = None

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
    if args.replay_dir:
        replay_dir = args.replay_dir
    else:
        root_dir = os.path.dirname(os.path.abspath(__file__))
        # TODO: Use args.replay_dir
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

            # If it was a TURN_LIMIT, it is a draw
            if win_reason.name == "TURN_LIMIT":
                winner = None
            else:
                winner = (
                    white_submission
                    if winner_color == chess.WHITE
                    else black_submission
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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "submission_directory",
        help="Directory containing student submissions",
        nargs="?",
        default="/home-mscluster/aboyley/reconchess-tournament/subs",
    )
    parser.add_argument(
        "--single-submission",
        help="Directory containing a single submission that will play against all other submissions",
        default=None,
    )
    parser.add_argument(
        "--rerun-timeouts", help="Rerun games that timed out", default="./replays"
    )
    parser.add_argument(
        "--replay-dir", help="Directory to save replays", default="./replays"
    )
    args = parser.parse_args()

    submissions = {}
    playable_round = []

    # Get all directories (i.e. student submissions) in the submission directory
    student_submission_dirs = glob.glob(os.path.join(args.submission_directory, "*"))

    # Create a Submission object for each student submission
    for i, student_submission_dir in enumerate(student_submission_dirs):
        submission = Submission(i, student_submission_dir)
        submissions[i] = submission

    # Add all the bots
    num_human_subs = len(submissions)
    for i, bot in enumerate(reconchess_bots):
        bot_id = i + num_human_subs
        submissions[bot_id] = Submission(bot_id, bot_name=bot)

        # Check if we have to run a tournament with just the games that timed out
    if args.rerun_timeouts:
        # Read in every file in the replay directory
        replay_files = glob.glob(os.path.join(args.rerun_timeouts, "*.json"))
        for replay_file in replay_files:
            # Check if TIMEOUT is in the file
            with open(replay_file, "r") as f:
                contents = f.read()
                if "TIMEOUT" in contents:
                    # Get the names of the submissions
                    white_name = os.path.basename(replay_file).split("_")[0]
                    black_name = (
                        os.path.basename(replay_file).split("_")[1].split(".")[0]
                    )

                    # Get the submission objects
                    white_sub = None
                    black_sub = None
                    for sub in submissions.values():
                        if sub.name.lower() == white_name.lower():
                            white_sub = sub
                        elif sub.name.lower() == black_name.lower():
                            black_sub = sub

                    # Add the game to the playable_round
                    playable_round.append((white_sub.id, black_sub.id))
    else:
        # Get all the student names by reading until the '_' character in the directory name
        for i, student in submissions.items():
            print(f"{i}: {student.name}")

        tournament = create_balanced_round_robin(list(submissions.keys()))

        # results = []
        for round_num, round in enumerate(tournament):
            for i, (white, black) in enumerate(round):
                if white is None or black is None:
                    # results.append(None)
                    continue
                else:

                    # If we have a single submission argument, only include games with them
                    if args.single_submission:
                        white_path = submissions[white].path
                        black_path = submissions[black].path
                        if (
                            white_path != args.single_submission
                            and black_path != args.single_submission
                        ):
                            continue
                    # Check to see if subs are valid
                    if submissions[white].is_valid() and submissions[black].is_valid():
                        playable_round.append((white, black))

    print(f"Playing {len(playable_round)} games")

    pool = MyPool(processes=10, maxtasksperchild=1)
    # Create a leaderboard
    points = {i: 0 for i in submissions.keys()}

    try:
        for winner in pool.starmap(
            play_game,
            [
                (submissions[white], submissions[black])
                for white, black in playable_round
            ],
            chunksize=1,
        ):
            if winner:
                points[winner.id] += 1
        # Convert from id to name
        points = {submissions[k].name: v for k, v in points.items()}
    except KeyboardInterrupt:
        print("Caught KeyboardInterrupt, terminating workers")
        pool.terminate()

        points = read_results()
    finally:
        pool.close()

    # for white, black in playable_round:
    #     winner = play_game(submissions[white], submissions[black])
    #     results.append(winner)

    print_leaderboard(points, save_csv=True)
