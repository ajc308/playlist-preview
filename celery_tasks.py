from celery_app import celery

# Celery status monitoring
celery_inspector = celery.control.inspect()


def wait(function):
    task_count = get_task_count(function)
    while task_count:
        print('Processing waiting for {0} {1} celery tasks to complete'.format(
            task_count,
            function.__name__ if function else ''
        ))
        task_count = get_task_count(function)


def get_task_count(function):
    # reserved are not yet scheduled, scheduled are not yet active
    reserved = get_reserved_tasks().get(function.name, {})
    scheduled = get_scheduled_tasks().get(function.name, {})
    active = get_active_tasks().get(function.name, {})

    return len(reserved) + len(scheduled) + len(active)


def get_reserved_tasks():
    """ This function exists to be called from ipython as part of debugging efforts
    """
    reserved = organize_tasks(celery_inspector.reserved())
    return reserved


def get_scheduled_tasks():
    """ This function exists to be called from ipython as part of debugging efforts
    """
    scheduled = organize_tasks(celery_inspector.scheduled())
    return scheduled


def get_active_tasks():
    """ This function exists to be called from ipython as part of debugging efforts
    """
    active = organize_tasks(celery_inspector.active())
    return active


def organize_tasks(collection):
    """
    This gets all tasks for the given celery_inspector state
    :param collection: celery_inspector state (celery_inspector.active(), celery_inspector.scheduled(), etc.)
    :return: worker and ID#s for the collection
    """
    results = {}
    if collection:
        for worker, tasks in collection.items():
            for task in tasks:
                function = task['name']
                celery_id = task['id']
                celery_worker = task['hostname']
                if function not in results.keys():
                    results[function] = []
                data = {'celery_worker': celery_worker, 'celery_id': celery_id}
                results[function].append(data)
    return results
