

def compare_list(list_old: list, list_new: list) -> tuple:
    """
    比较两个列表, 返回新增和删减的元素

    参数:
        list_old(list): 旧列表
        list_new(list): 新列表

    返回:
        add_list(list): 新增的元素
        del_list(list): 删减的元素
    """
    old_set: set = set(list_old)
    new_set: set = set(list_new)
    del_list: list = [item for item in list_old if item not in new_set]
    add_list: list = [item for item in list_new if item not in old_set]
    return add_list, del_list
