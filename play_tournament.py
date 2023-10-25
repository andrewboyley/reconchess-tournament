import os
import glob
from reconchess import load_player, play_local_game, LocalGame
import chess
import traceback
import datetime
import random

class Submission:
    def __init__(self, dir):
        self.name = os.path.basename(student_submission_dir).split('_')[0]
        self.path = dir

        # Get the submission file name that ends in .py
        self.filename = glob.glob(os.path.join(dir, '*.py'))
        # If not an empty list, get the first value, else None
        self.filename = self.filename[0] if len(self.filename) > 0 else None

    def __repr__(self):
        return self.name
    
    def is_valid(self):
        return len(self.filename) == 1

submission_directory = 'COMS4033A-AI4-S2-2023-Improved Agent Submission-22228'

# Get all directories (i.e. student submissions) in the submission directory
student_submission_dirs = glob.glob(os.path.join(submission_directory, '*'))

submissions = []

# Create a Submission object for each student submission
for student_submission_dir in student_submission_dirs:
    submission = Submission(student_submission_dir)
    submissions.append(submission)

# Get all the student names by reading until the '_' character in the directory name
# for i,student in enumerate(submissions):
#     print(f'{i}: {student.name}')

# exit()

num = random.randint(0, len(submissions)-1)

white_bot_name, white_player_cls = load_player(submissions[num].filename)
# black_bot_name, black_player_cls = load_player(submissions[4].filename)
# Have a random bot be black
black_bot_name, black_player_cls = load_player('reconchess.bots.random_bot')

print(f'{submissions[num].name} is playing as white')
# print(f'{submissions[4].name} is playing as black')

game = LocalGame(0.1)

try:
    winner_color, win_reason, history = play_local_game(white_player_cls(), black_player_cls(), game=game)

    winner = 'Draw' if winner_color is None else chess.COLOR_NAMES[winner_color]
except:
    traceback.print_exc()
    game.end()

    # TODO: Check who errored out by looking at the filename
    winner = 'ERROR'
    history = game.get_game_history()


print('Game Over!')
print('Winner: {}!'.format(winner))

# timestamp = datetime.datetime.now().strftime('%Y_%m_%d-%H_%M_%S')

# replay_path = '{}-{}-{}-{}.json'.format(white_bot_name, black_bot_name, winner, timestamp)
# print('Saving replay to {}...'.format(replay_path))
# history.save(replay_path)