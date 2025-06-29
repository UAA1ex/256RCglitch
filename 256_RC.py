import shutil
import json
import glob
import os
from pathlib import Path
import time
import sys

data = None
iteration_count = 0  # Global iteration counter

# Locate the most recently modified blueprint file
def find_latest_blueprint():
    home_path = str(Path.home())
    path = os.path.join(home_path, "AppData", "Roaming", "Axolot Games", "Scrap Mechanic", "User", "*", "Blueprints")
    list_of_files = glob.glob(os.path.join(path, '**', 'blueprint.json'), recursive=True)
    if not list_of_files:
        raise FileNotFoundError("No blueprint.json files found")
    latest_file = max(list_of_files, key=os.path.getctime)
    blueprint_name = fetch_blueprint_name(os.path.dirname(latest_file))
    print(f"Found the latest file: {latest_file} (\"{blueprint_name}\")")
    return latest_file

# Extract the blueprint name from its description file
def fetch_blueprint_name(blueprint_folder):
    description_file = os.path.join(blueprint_folder, "description.json")
    if os.path.exists(description_file):
        with open(description_file, 'r', encoding='utf-8') as file:
            description_data = json.load(file)
            return description_data.get("name", "Unknown name")
    return "Unknown name"

# Load blueprint data and create a backup if it differs from the current data
def load_and_backup():
    while True:
        blueprint_file_path = find_latest_blueprint()
        with open(blueprint_file_path, 'r') as file:
            new_data = json.load(file)

        blueprint_name = fetch_blueprint_name(os.path.dirname(blueprint_file_path))
        response = input(f"Is the file name \"{blueprint_name}\" the desired one? Y / N: ").strip().upper()
        if response == "Y":
            print("Continuing processing...")
            break
        elif response == "N":
            print("Searching for another blueprint...")
            time.sleep(0.2)  # Small delay before searching again
            continue
        else:
            print("Invalid response. Searching for another blueprint...")
            time.sleep(0.2)  # Small delay before searching again
            continue

    global data
    if data == new_data:
        return data, blueprint_file_path, False

    backup_path = os.path.dirname(blueprint_file_path)
    backup_number = 1
    backup_filename = os.path.join(backup_path, f'backup_{backup_number}_blueprint.json')
    while os.path.exists(backup_filename):
        backup_number += 1
        backup_filename = os.path.join(backup_path, f'backup_{backup_number}_blueprint.json')

    shutil.copy(blueprint_file_path, backup_filename)
    print(f"Created backup: {backup_filename}")
    data = new_data
    return data, blueprint_file_path, True

# Collect all controller IDs for a given color and shape ID
def gather_connections(data, color_to_find, shape_id_to_find):
    all_connections = []
    for body in data['bodies']:
        if 'childs' in body:
            connections = [child['controller']['id'] for child in body['childs']
                          if 'controller' in child and child.get('color') == color_to_find
                          and child.get('shapeId') == shape_id_to_find]
            all_connections.extend(connections)
    return all_connections

# Apply a processing function to all bodies in the blueprint data
def update_bodies(data, func, *args):
    for body in data['bodies']:
        if 'childs' in body:
            body['childs'] = func(body['childs'], *args)
    return data

# Link all specified target colors to a source color's connections
def link_all(children, all_connection_ids=None):
    shape_id_to_find = "9f0f56e8-2c31-4d83-996c-d00a9b296c3f"
    color_to_connect_from = "222222"
    colors_to_connect_to = ["68FF88", "19E753", "0E8031", "064023",
                           "68FF88", "19E753", "0E8031", "064023",
                           "4C6FE3", "0A3EE2", "0F2E91", "0A1D5A",
                           "4C6FE3", "0A3EE2", "0F2E91", "0A1D5A"]

    if all_connection_ids is None:
        all_connection_ids = gather_connections(data, color_to_connect_from, shape_id_to_find)

    for color_to in colors_to_connect_to:
        targets = [child for child in children if child.get('shapeId') == shape_id_to_find and child.get('color') == color_to]

        for child in targets:
            child_id = child.get('controller', {}).get('id', 'unknown')
            if 'controller' not in child:
                child['controller'] = {}
            if 'controllers' not in child['controller'] or not child['controller']['controllers']:
                child['controller']['controllers'] = [{"id": cid} for cid in all_connection_ids]
            else:
                for cid in all_connection_ids:
                    if not any(conn['id'] == cid for conn in child['controller']['controllers']):
                        child['controller']['controllers'].append({"id": cid})
    return children

# Connect source colors to target colors with extra color linkage
def link_colors(children, all_extra_color_ids=None):
    input_colors = ["68FF88", "19E753", "0E8031", "064023",
                    "68FF88", "19E753", "0E8031", "064023",
                    "4C6FE3", "0A3EE2", "0F2E91", "0A1D5A",
                    "4C6FE3", "0A3EE2", "0F2E91", "0A1D5A"]
    input_targets = ["7EEDED", "2CE6E6", "118787", "0A4444",
                     "7EEDED", "2CE6E6", "118787", "0A4444",
                     "F06767", "D02525", "7C0000", "560202",
                     "F06767", "D02525", "7C0000", "560202"]
    extra_color = "222222"

    if all_extra_color_ids is None:
        all_extra_color_ids = gather_connections(data, extra_color, "9f0f56e8-2c31-4d83-996c-d00a9b296c3f")

    for child in children:
        if child.get('color') in input_colors:
            color_from = child.get('color')
            if 'controller' not in child:
                child['controller'] = {}
            if 'controllers' not in child['controller'] or not child['controller']['controllers']:
                child['controller']['controllers'] = [{"id": cid} for cid in all_extra_color_ids]
            else:
                for cid in all_extra_color_ids:
                    if not any(conn['id'] == cid for conn in child['controller']['controllers']):
                        child['controller']['controllers'].append({"id": cid})

    all_target_connections = []
    for body in data['bodies']:
        if 'childs' in body:
            target_connections = [child['controller']['id'] for child in body['childs']
                                if 'controller' in child and child.get('color') in input_targets
                                and child.get('shapeId') == "9f0f56e8-2c31-4d83-996c-d00a9b296c3f"]
            all_target_connections.extend(target_connections)

    for index, color_from in enumerate(input_colors):
        color_to = input_targets[index]
        connection_ids_to_color_to = [cid for cid in all_target_connections if any(
            child['controller']['id'] == cid for body in data['bodies'] for child in body['childs']
            if 'controller' in child and child.get('color') == color_to and child.get('shapeId') == "9f0f56e8-2c31-4d83-996c-d00a9b296c3f"
        )]

        for child in children:
            if child.get('color') == color_from:
                if 'controller' not in child:
                    child['controller'] = {}
                if 'controllers' not in child['controller'] or not child['controller']['controllers']:
                    child['controller']['controllers'] = [{"id": cid} for cid in connection_ids_to_color_to]
                else:
                    for cid in connection_ids_to_color_to:
                        if not any(conn['id'] == cid for conn in child['controller']['controllers']):
                            child['controller']['controllers'].append({"id": cid})
    return children

# Connect objects by matching positions along specified axes
def link_by_axis(children, color_to_connect_to, color_to_connect_from, axes_to_match):
    shape_id_to_find = "9f0f56e8-2c31-4d83-996c-d00a9b296c3f"
    all_connection_ids = gather_connections(data, color_to_connect_from, shape_id_to_find)

    coords = {}
    for body in data['bodies']:
        for child in body['childs']:
            if 'controller' in child and child.get('color') == color_to_connect_from and child.get('shapeId') == shape_id_to_find:
                cid = child['controller']['id']
                coords[cid] = tuple(child['pos'][axis] for axis in axes_to_match)

    for child in children:
        if child.get('shapeId') == shape_id_to_find and child.get('color') == color_to_connect_to:
            child_coords = tuple(child['pos'][axis] for axis in axes_to_match)
            for cid in all_connection_ids:
                if child_coords == coords.get(cid):
                    if 'controller' not in child:
                        child['controller'] = {}
                    if 'controllers' not in child['controller'] or not child['controller']['controllers']:
                        child['controller']['controllers'] = [{"id": cid}]
                    else:
                        if not any(conn['id'] == cid for conn in child['controller']['controllers']):
                            child['controller']['controllers'].append({"id": cid})
    return children

# Main function to process the blueprint and update connections
def process_blueprint():
    global iteration_count
    try:
        data, blueprint_file_path, updated = load_and_backup()
        if not updated:
            print("No changes detected in the blueprint.")
            return True

        all_f5f071_ids = gather_connections(data, "222222", "9f0f56e8-2c31-4d83-996c-d00a9b296c3f")
        data = update_bodies(data, link_all, all_f5f071_ids)
        data = update_bodies(data, link_colors, all_f5f071_ids)
        data = update_bodies(data, lambda c: link_by_axis(c, "7F7F7F", "E2DB13", ['z', 'y']))
        data = update_bodies(data, lambda c: link_by_axis(c, "4A4A4A", "817C00", ['z', 'x']))
        data = update_bodies(data, lambda c: link_by_axis(c, "222222", "323000", ['x', 'y']))

        # Calculate total number of connections made
        total_connections = 0
        for body in data['bodies']:
            if 'childs' in body:
                for child in body['childs']:
                    if ('controller' in child and 'controllers' in child['controller'] and 
                        child['controller']['controllers'] and 
                        child.get('shapeId') == "9f0f56e8-2c31-4d83-996c-d00a9b296c3f"):
                        total_connections += len(child['controller']['controllers'])

        # Save the updated blueprint file
        with open(blueprint_file_path, 'w') as file:
            json.dump(data, file, indent=4)

        print("Blueprint successfully updated.")
        print(f"Total connections created: {total_connections}")

        # Increment iteration counter after successful processing
        iteration_count += 1
        print(f"Iteration {iteration_count} completed.")

        # Ask if the user wants to start a new iteration
        while True:
            response = input("Do you want to start the new iteration? Y / N: ").strip().upper()
            if response == "Y":
                print("Starting a new iteration...")
                return True
            elif response == "N":
                print("Exiting program.")
                return False
            else:
                print("Invalid response. Please enter Y or N.")

    except Exception as e:
        print(f"Error in main: {e}")
        return True  # Continue searching in case of an error

# Monitor a directory for changes and reprocess blueprints as needed
def monitor_directory(path_to_watch):
    global iteration_count
    path_to_watch = Path(path_to_watch)
    current_script_path = Path(__file__).resolve()
    seen_files = {}

    for file in path_to_watch.rglob('blueprint.json'):
        if file.resolve() != current_script_path:
            with open(file, 'r') as f:
                seen_files[file] = f.read()

    while True:
        if iteration_count >= 1:
            print("One iteration completed.")
            while True:
                response = input("Чи розпочати нову ітерацію пошуку Y / N: ").strip().upper()
                if response == "Y":
                    print("Starting a new iteration...")
                    iteration_count = 0  # Reset iteration count for a new iteration
                    break
                elif response == "N":
                    print("Exiting program.")
                    input("Press Enter to exit...")
                    return
                else:
                    print("Invalid response. Please enter Y or N.")

        if not process_blueprint():
            break

        current_files = {}
        try:
            for file in path_to_watch.rglob('blueprint.json'):
                if file.resolve() != current_script_path:
                    with open(file, 'r') as f:
                        current_files[file] = f.read()
        except FileNotFoundError:
            print(f"Path {path_to_watch} not found")

        changed_files = {file for file, content in current_files.items() 
                         if file not in seen_files or content != seen_files[file]}
        if changed_files:
            for changed_file in changed_files:
                blueprint_name = fetch_blueprint_name(os.path.dirname(changed_file))
                print(f"Processing modified file: {changed_file} (Name: {blueprint_name})")
                if not process_blueprint():
                    break

        seen_files = current_files
        time.sleep(0.2)

# Identify the most recently modified user folder
def find_latest_user_folder():
    home_path = Path.home()
    user_path = home_path / "AppData" / "Roaming" / "Axolot Games" / "Scrap Mechanic" / "User"
    latest_folder = None
    latest_time = 0

    for folder in user_path.iterdir():
        if folder.is_dir() and folder.name.startswith("User_"):
            folder_time = max(os.path.getmtime(file) for file in folder.rglob('*'))
            if folder_time > latest_time:
                latest_time = folder_time
                latest_folder = folder

    if latest_folder:
        print(f"Found the latest folder: {latest_folder}")
    else:
        print("User folder not found.")
    return latest_folder

if __name__ == "__main__":
    latest_folder = find_latest_user_folder()
    if latest_folder:
        path_to_watch = latest_folder / "Blueprints"
        monitor_directory(path_to_watch)
    else:
        print("Failed to find user folder, exiting.")