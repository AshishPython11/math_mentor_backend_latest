class AppMessages:
    FAILED = "failed"
    FALSE = False
   


def get_attribute_name(number):
    """This function is to fetch the above attribute name corresponding to a given number"""
    for attr_name in dir(AppMessages):
        if not attr_name.startswith("__") and getattr(AppMessages, attr_name) == number:
            return attr_name
    return None
