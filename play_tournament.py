import os
import glob
from reconchess import load_player, play_local_game, LocalGame
import chess
import traceback
import datetime
import random
from multiprocessing import Pool


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


reconchess_bots = ["reconchess.bots.random_bot", "reconchess.bots.attacker_bot"]


class Submission:
    def __init__(self,id, dir=None, bot_name=None):
        self.id = id
        if dir is not None:
            self.name = os.path.basename(dir).split("_")[0]
            self.path = dir

            # Get the submission file name that ends in .py
            self.filename = glob.glob(os.path.join(dir, "*.py"))
            # If not an empty list, get the first value, else None
            self.filename = self.filename[0] if len(self.filename) > 0 else None
        else:
            self.name = bot_name.split(".")[2] + "_" + str(random.randint(0, 100))
            self.path = None
            self.filename = bot_name

    def __repr__(self):
        return self.name

    def is_valid(self):
        return len(self.filename) == 1


def play_game(white, black):
    white_bot_name, white_player_cls = load_player(white.filename)
    black_bot_name, black_player_cls = load_player(black.filename)

    # print(f"{white.name} (w) vs {black.name} (b)")

    game = LocalGame(0.1)

    try:
        winner_color, win_reason, history = play_local_game(
            white_player_cls(), black_player_cls(), game=game
        )

        winner = "Draw" if winner_color is None else chess.COLOR_NAMES[winner_color]
    except:
        # traceback.print_exc()

        # Get the traceback as a string
        tb = traceback.format_exc()

        # Check whose traceback it is and assign the winner to the other player
        if white.name in tb:
            winner = "black"
        elif black.name in tb:
            winner = "white"
        else:
            winner = "ERROR"
        game.end()

        winner = "ERROR"
        win_reason = tb
        # history = game.get_game_history()

    # print("Game Over!")
    winner_id = None
    if winner == "white":
        winner_name = white.name
        winner_id = white.id
    elif winner == "black":
        winner_name = black.name
        winner_id = black.id
    elif winner == "ERROR":
        winner_name = "ERROR"
    else:
        winner_name = "Draw"

    # timestamp = datetime.datetime.now().strftime('%Y_%m_%d-%H_%M_%S')

    # replay_path = '{}-{}-{}-{}.json'.format(white_bot_name, black_bot_name, winner, timestamp)
    # print('Saving replay to {}...'.format(replay_path))
    # history.save(replay_path)

    # print('Winner: {}!'.format(winner_name))
    # print('Win Reason: {}'.format(win_reason))

    return winner,winner_id, winner_name, win_reason


if __name__ == "__main__":
    submission_directory = "subs"

    # Get all directories (i.e. student submissions) in the submission directory
    student_submission_dirs = glob.glob(os.path.join(submission_directory, "*"))
    submissions = {}

    # Create a Submission object for each student submission
    # for i, student_submission_dir in enumerate(student_submission_dirs):
    #     submission = Submission(student_submission_dir)
    #     submissions[i] = submission

    for i in range(10):
        submissions[i] = Submission(i, bot_name=random.choice(reconchess_bots))

    # Get all the student names by reading until the '_' character in the directory name
    for i, student in submissions.items():
        print(f"{i}: {student.name}")

    # Create a leaderboard
    points = {i: 0 for i in submissions.keys()}

    tournament = create_balanced_round_robin(list(submissions.keys()))
    for round_num, round in enumerate(tournament):
        # Print the round
        # print("Round {}".format(round_num + 1))
        # print("\n".join(['{} vs. {}'.format(m[0], m[1]) for m in round]))
        # print(round)

        # Play each game in the round in parallel using a pool. Each item in the round list is a tuple of two submissions, white vs black. These are the keys into the submissions dictionary. The values of this dictionary are what are passed into the function
        with Pool() as pool:
            results = pool.starmap(
                play_game, [(submissions[white], submissions[black]) for white, black in round]
            )

        # Print the results of the round
        # print("Round {} Results".format(round_num + 1))
        for result in results:
            # print(result)
            # Update points
            if result[0] != "Draw" and result[0] != "ERROR":
                points[result[1]] += 1




        # print()
    
    # Print the final leaderboard in descending order
    print("Final Leaderboard")
    sorted_points = sorted(points.items(), key=lambda x: x[1], reverse=True)
    for i, point in enumerate(sorted_points):
        print(f"{i+1}: {submissions[point[0]].name} - {point[1]}")