import os
import csv
import glob


def read_results(replays_dir="/home-mscluster/aboyley/reconchess-tournament/replays"):
    # Return a dictionary with the results of the tournament
    # Each file in the replays dir looks like <whitename>_<blackname>-ERROR.json
    # The name which is capitalized is the winner
    results = {}
    files = glob.glob(os.path.join(replays_dir, "*.json"))
    for file in files:
        filename = os.path.basename(file)[:-5]
        white, black = filename.split("-")[0].split("_")

        white_key = white.upper()
        black_key = black.upper()
        # Add them to the results if they don't exist
        if white_key not in results:
            results[white_key] = 0
        if black_key not in results:
            results[black_key] = 0

        # Update the results
        if white.upper() == white:
            results[white_key] += 1
        elif black.upper() == black:
            results[black_key] += 1
    return results


def print_leaderboard(points, save_csv=False):
    # Print the final leaderboard in descending order
    print()
    print("-" * 50)
    print("Final Leaderboard")
    print("-" * 50)
    sorted_points = sorted(points.items(), key=lambda x: x[1], reverse=True)

    # Save the leaderboard to a csv file
    if save_csv:
        f = open("leaderboard.csv", "w")
        writer = csv.writer(f)
        writer.writerow(["Rank", "Name", "Surname", "Points"])
    print(
        f"{'#'.rjust(3)} {'Name'.ljust(15)} {'Surname'.ljust(15)} {str('Points').rjust(3)}"
    )
    print()
    for i, point in enumerate(sorted_points):
        # name = submissions[point[0]].name.split(" ")
        name = point[0].split(" ")
        if len(name) == 1:
            surname = ""
            name = name[0]
        elif len(name) > 2:
            surname = " ".join(name[1:])
            name = name[0]
        else:
            name, surname = name
        if save_csv:
            writer.writerow([i + 1, name, surname, point[1]])
        print(
            f"{str(i+1).rjust(3)} {name.ljust(15)} {surname.ljust(15)} {str(point[1]).rjust(3)}"
        )
    if save_csv:
        f.close()


if __name__ == "__main__":
    results = read_results()
    print_leaderboard(results)
