import importlib
import inspect
import pathlib


def load_plugin_class(class_name, subfolder, interface_class=None):
    search_path = pathlib.Path(__file__).parents[1].absolute() / subfolder
    for entry in search_path.iterdir():
        if not str(entry).endswith('.py'):
            continue
        module_path = entry.resolve()
        spec = importlib.util.spec_from_file_location(inspect.getmodulename(module_path), module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        objs = [obj for name, obj in inspect.getmembers(module, inspect.isclass)
                if (class_name is None or name == class_name)]
        if interface_class is not None:
            objs = [obj for obj in objs if (issubclass(obj, interface_class) and (obj is not interface_class))]
        if len(objs) > 0:
            obj = objs[0]
            obj.__file__ = str(entry)
            return obj

    return None
