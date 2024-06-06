import os
import glob
import argparse


def remove_duplicates(replay_dir, duplicates):
    for duplicate in duplicates:
        player1, player2 = duplicate
        player2_files = [
            f
            for f in glob.glob(os.path.join(replay_dir, "*.json"))
            if player2.lower() in f.lower()
        ]
        for player2_file in player2_files:
            print(player2_file, "DELETED")
            os.remove(player2_file)


def fix_timeouts(replay_dir, duplicates):

    for duplicate in duplicates:
        player1, player2 = duplicate
        player1_files = [
            f
            for f in glob.glob(os.path.join(replay_dir, "*.json"))
            if player1.lower() in f.lower()
        ]
        player2_files = [
            f
            for f in glob.glob(os.path.join(replay_dir, "*.json"))
            if player2.lower() in f.lower()
        ]

        for player1_file in player1_files:
            basename = os.path.basename(player1_file)[:-5]
            p1_names = basename.split("-")[0].split("_")
            opponent = (
                p1_names[1] if player1.lower() in p1_names[0].lower() else p1_names[0]
            )
            p1_name = (
                p1_names[0] if player1.lower() in p1_names[0].lower() else p1_names[1]
            )

            # The game where they play against themselves
            if player2.lower() in opponent.lower():
                print(player1_file, "SELF DELETED")
                os.remove(player1_file)
                print()
                continue

            for player2_file in player2_files:
                if player1.lower() in player2_file.lower():
                    continue

                p2_names = os.path.basename(player2_file)[:-5].split("-")[0].split("_")
                p2_name = (
                    p2_names[0]
                    if player2.lower() in p2_names[0].lower()
                    else p2_names[1]
                )
                if opponent.lower() in player2_file.lower():
                    # Check if one of them times out
                    p1_times_out = False
                    p2_times_out = False
                    try:
                        with open(player1_file, "r") as f:
                            if "TIMEOUT" in f.read():
                                p1_times_out = True
                        with open(player2_file, "r") as f:
                            if "TIMEOUT" in f.read():
                                p2_times_out = True
                    except:
                        # If the file is not found, skip it. It would have been deleted
                        continue

                    # Use xor to check if exactly 1 has timed out
                    if p1_times_out ^ p2_times_out:
                        # Delete the match that timed out
                        if p1_times_out:
                            print(player1_file, "TIMED OUT")
                            # Delete the timed out match
                            os.remove(player1_file)
                            print(player2_file)
                            # Rename the p2 file to p1
                            # Check if p2 won
                            if player2.upper() in player2_file:
                                new_name = player2_file.replace(
                                    p2_name.upper(), p1_name.upper()
                                )
                            else:
                                new_name = player2_file.replace(
                                    p2_name.lower(), p1_name.lower()
                                )
                            print(new_name, "RENAMED")
                            os.rename(player2_file, new_name)
                        else:
                            print(player1_file)
                            print(player2_file, "TIMED OUT")
                            # Delete the timed out match
                            os.remove(player2_file)
                        print()
                        continue


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "replay_dir",
        type=str,
        help="Path to the replay directory",
        # default="./replays",
        default="/home/andrew/Documents/reconchess-tournament/replays",
        nargs="?",
    )

    args = parser.parse_args()

    # The first name in the tuple is the preferred name and will be kept
    duplicates = [("Phuti", "Lesego"), ("Shephard", "Thapelo"), ("Yonatan", "Aharon")]

    fix_timeouts(args.replay_dir, duplicates)
    remove_duplicates(args.replay_dir, duplicates)
