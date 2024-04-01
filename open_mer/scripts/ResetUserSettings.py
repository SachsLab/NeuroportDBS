from open_mer.settings.reset import copy_ini_resources_from_package_to_home


def main():
    # We have to call something in the package so it knows its package name.
    # (Here, when called directly, __package__ is None)
    copy_ini_resources_from_package_to_home()


if __name__ == '__main__':
    main()
