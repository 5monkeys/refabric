import inspect


def resolve_member(path):
    """
    Resolves member string path into target (module|class) and member pointers.

    :param path: String member path, i.e 'foo.bar.baz'
    :return: tuple(module, function, function name)
    """
    path, _, method = path.partition(':')
    package, name = path.rsplit('.', 1)
    target = __import__(package, fromlist=['*'])
    member = getattr(target, name)

    if method:
        target = member
        member = getattr(member, method, None)
        name = method

    return target, member, name


def patch(original_path, patch_path=None, keep=True):
    """
    Patches fabric functions or class methods.

    :param original_path: String path of target, i.e 'foo.bar.baz'
    :param patch_path: Optional string path of patch. If not given, original_path prefixed with `refabric.` is used
    :param keep: Keep original member as a .original attribute reference on patch (Default: True)
    :return:
    """
    original_target, original_member, original_name = resolve_member(original_path)

    if not patch_path:
        # Patch path not given, assume same location but within refabric package
        patch_path = '.'.join(('refabric', original_path.split('.', 1)[1]))

    patch_target, patch_member, patch_name = resolve_member(patch_path)

    if inspect.isclass(original_member):
        # Target member is a class, patch each method
        methods = inspect.getmembers(patch_member, predicate=inspect.isfunction)
        for method, _ in methods:
            original_method_path = '{}:{}'.format(original_path, method)
            patch_method_path = '{}:{}'.format(patch_path, method)
            patch(original_method_path, patch_method_path, keep=keep)

    else:
        if keep:
            patch_member.original = original_member

        # Patch
        setattr(original_target, original_name, patch_member)
