from qt_py_convert._modules.expand_stars import process as stars_process
from qt_py_convert.general import __supported_bindings__, _color, AliasDict


class Processes(object):
    @staticmethod
    def _get_import_parts(node, binding):
        return node.dumps().replace(binding, "").lstrip(".").split(".")

    @staticmethod
    def _no_second_level_module(node, _parts):
        text = "from Qt import {key}".format(
            key=", ".join([target.value for target in node.targets])
        )
        print(
            "Changing {old} to {new} at line {line}".format(
                old=str(node).strip("\n"),
                new=_color(35, text),
                line=node.absolute_bounding_box.top_left.line-1
            )
        )
        node.replace(text)

    @classmethod
    def _process_import(cls, red, objects):
        binding_aliases = AliasDict
        mappings = {}

        # Replace each node
        for node, binding in objects:
            from_import_parts = cls._get_import_parts(node, binding)
            if len(from_import_parts) and from_import_parts[0]:
                second_level_module = from_import_parts[0]
            else:
                cls._no_second_level_module(node.parent, from_import_parts)
                binding_aliases["bindings"].add(binding)
                for target in node.parent.targets:
                    binding_aliases["root_aliases"].add(target.value)
                continue

            for _from_as_name in node.parent.targets:
                if _from_as_name.type == "star":
                    # TODO: Make this a flag and make use the expand module.
                    _, star_mappings = stars_process.process(
                        red
                    )
                    mappings.update(star_mappings)
                else:
                    key = _from_as_name.target or _from_as_name.value
                    value = ".".join(from_import_parts) + "." + _from_as_name.value
                    mappings[key] = value

            print("Changing {old} to {new} at line {line}".format(
                old=str(node.parent).strip("\n"),
                new=_color(
                    35,
                    "from Qt import {key}".format(key=second_level_module)
                ),
                line=node.parent.absolute_bounding_box.top_left.line - 1
            ))
            node.parent.replace(
                "from Qt import {key}".format(key=second_level_module)
            )
            binding_aliases["bindings"].add(binding)
            for target in node.parent.targets:
                binding_aliases["root_aliases"].add(target.value)
            if binding not in binding_aliases:
                binding_aliases[binding] = set()
            binding_aliases[binding] = binding_aliases[binding].union(
                set([target.value for target in node.parent.targets])
            )
        return binding_aliases, mappings

    FROM_IMPORT_STR = "FROM_IMPORT"
    FROM_IMPORT = _process_import


def import_process(store):
    def filter_function(value):
        """
        filter_function takes an AtomTrailersNode or a DottedNameNode and will filter them out if they match something that
        has changed in psep0101
        """
        _raw_module = value.dumps()
        # See if that import is in our __supported_bindings__
        for supported_binding in __supported_bindings__:
            if _raw_module.startswith(supported_binding):
                store[Processes.FROM_IMPORT_STR].add(
                    (value, supported_binding)
                )
                return True

    return filter_function


def process(red, **kwargs):
    issues = {
        Processes.FROM_IMPORT_STR: set(),
    }
    red.find_all("FromImportNode", value=import_process(issues))

    key = Processes.FROM_IMPORT_STR

    if issues[key]:
        return getattr(Processes, key)(red, issues[key])
    else:
        return AliasDict, {}
