
def is_sequence(obj):
    """ Determine whether an object is a sequence, but not a string.

    :param obj: Object to test
    :return: True if the object is a sequence type, but not a string.
    """
    return (not hasattr(obj, "strip") and
            hasattr(obj, "__getitem__") or
            hasattr(obj, "__iter__"))