from reagent.core.taskable import taskable_registry


def get_taskable_registry():
    global taskable_registry
    return taskable_registry
