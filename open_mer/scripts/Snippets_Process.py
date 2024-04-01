from pathlib import Path
import typing

import typer
from open_mer.dbsgui.process import parse_ini, build_ini_paths, SnippetWorker


def main(ini_path: typing.Optional[Path] = None, procedure_id: typing.Optional[int] = None):
    ini_paths = build_ini_paths()
    if ini_path is not None:
        ini_paths.append(ini_path)
    ipc_settings, buffer_settings, feature_settings = parse_ini(ini_paths)

    worker = SnippetWorker(ipc_settings, buffer_settings, procedure_id=procedure_id)
    worker.run_forever()


if __name__ == '__main__':
    typer.run(main)
