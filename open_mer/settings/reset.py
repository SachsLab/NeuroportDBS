from pathlib import Path
import importlib.resources as pkg_resources
from shutil import copyfile


def copy_ini_resources_from_package_to_home():
    """
    Copies ini files from this package's resource directory to the user's home/.__package__ directory.
    """
    root_pkg = __package__.split(".")[0]
    dest_root = Path.home() / f".{root_pkg}"
    dest_root.mkdir(exist_ok=True)
    with pkg_resources.path(f"{root_pkg}.resources", "settings") as path:
        for resource_file in path.iterdir():
            if not resource_file.name.lower().endswith(".ini"):
                continue
            destination_path = dest_root / resource_file.name
            if resource_file.is_file():
                print(f"Copying {resource_file} to {destination_path}")
                copyfile(resource_file, destination_path)
