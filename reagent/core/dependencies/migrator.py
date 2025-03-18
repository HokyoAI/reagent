from reagent.migrations.manager import MigrationManager

migrator = MigrationManager()


def get_migrator():
    """
    Returns the global migrator instance.
    """
    global migrator
    return migrator
