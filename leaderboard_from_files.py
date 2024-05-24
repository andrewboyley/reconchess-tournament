import os

def read_results(replays_dir='replays'):
    # Return a dictionary with the results of the tournament
    # Each file in the replays dir looks like <whitename>_<blackname>-ERROR.json
    # The name which is capitalized is the winner
    results = {}
    for file in os.listdir(replays_dir):
        if file.endswith(".json"):
            white, black = file.split("-")[0].split("_")
            if white.upper() == white:
                results[white] = results.get(white, 0) + 1
            else:
                results[black] = results.get(black, 0) + 1
    return results

def print_leaderboard(points, save_csv=True):
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

if __name__ == "__main__":
    results = read_results()
    print_leaderboard(results)