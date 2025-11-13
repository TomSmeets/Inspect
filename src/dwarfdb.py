from elftools.elf.elffile import ELFFile
from elftools.dwarf.descriptions import describe_DWARF_expr, set_global_machine_arch
from elftools.dwarf.locationlists import LocationEntry, LocationExpr, LocationParser, LocationLists
from elftools.dwarf.dwarf_expr import DWARFExprParser
from elftools.dwarf.dwarfinfo import DWARFInfo
from elftools.dwarf.compileunit import CompileUnit
from elftools.dwarf.die import DIE
from value import Value, ValueTag


def load(path: str) -> Value:
    elf = ELFFile(open(path, "rb"))
    dwarf: DWARFInfo = elf.get_dwarf_info()
    location_list: LocationLists = dwarf.location_lists()
    location_parser = LocationParser(location_list)
    expr_parser = DWARFExprParser(dwarf.structs)

    # ==== Helpers ====
    def die_name(die: DIE) -> str:
        if "DW_AT_name" not in die.attributes:
            return ""
        return die.attributes["DW_AT_name"].value.decode()

    def value_from_die(die: DIE, tag: ValueTag) -> Value:
        return Value(tag, die_name(die))

    def die_to_addr(die: DIE) -> int:
        if "DW_AT_location" not in die.attributes:
            return None

        parsed = location_parser.parse_from_attribute(die.attributes["DW_AT_location"], die.cu["version"], die)
        expr = expr_parser.parse_expr(parsed.loc_expr)

        # NOTE: This supports only basic addressing for now
        if len(expr) == 1 and expr[0].op_name == "DW_OP_addr":
            return expr[0].args[0]

        print("Unknown address expression:", expr)
        return None

    # Mapping from die offset to value
    value_cache: dict[int, Value] = {}
    void_type = Value(ValueTag.BaseType, "void")

    def value_new(die: DIE, tag: ValueTag, value: int = 0) -> Value:
        value = Value(tag, die_name(die), value)
        value_cache[die.offset] = value
        return value

    def visit_typeof(die: DIE) -> Value:
        # Special case
        if "DW_AT_type" not in die.attributes:
            return void_type
        value = visit(die.get_DIE_from_attribute("DW_AT_type"))
        print(value, value.name)
        return value

    def visit_children(die: DIE, filter: list[str] = None) -> list[Value]:
        result = []
        for child_die in die.iter_children():  # type: DIE
            if filter is not None and child_die.tag not in filter:
                continue

            child_value = visit(child_die)

            if child_value is None:
                continue

            result.append(child_value)
        return result

    def visit(die: DIE) -> Value:
        # Check cache
        if die.offset in value_cache:
            return value_cache[die.offset]

        # Append a value
        if die.tag == "DW_TAG_compile_unit":
            value = value_new(die, ValueTag.CompileUnit)
            value.children = visit_children(die, ["DW_TAG_variable"])
        elif die.tag == "DW_TAG_variable":
            if "DW_AT_name" not in die.attributes:
                return None
            addr = die_to_addr(die)
            if not addr:
                return None
            value = value_new(die, ValueTag.Variable, addr)
            value.children = [visit_typeof(die)]
        elif die.tag == "DW_TAG_typedef":
            value = value_new(die, ValueTag.Typedef)
            value.children = [visit_typeof(die)]
        elif die.tag == "DW_TAG_pointer_type":
            value = value_new(die, ValueTag.Pointer)
            value.children = [visit_typeof(die)]
        elif die.tag == "DW_TAG_array_type":
            value = value_new(die, ValueTag.Array)
            value.children = [visit_typeof(die)]

            # Count number of array items
            value.value = 1
            for child_die in die.iter_children():
                if "DW_AT_count" in child_die.attributes:
                    value.value *= child_die.attributes["DW_AT_count"].value
                elif "DW_AT_upper_bound" in child_die.attributes:
                    value.value *= child_die.attributes["DW_AT_upper_bound"].value + 1

        elif die.tag == "DW_TAG_structure_type" or die.tag == "DW_TAG_class_type" or die.tag == "DW_TAG_union_type":
            value = value_new(die, ValueTag.Struct)
            value.children = visit_children(die, ["DW_TAG_member"])
        elif die.tag == "DW_TAG_member":
            value = value_new(die, ValueTag.Variable)
            value.value = die.attributes["DW_AT_data_member_location"].value if "DW_AT_data_member_location" in die.attributes else 0
            value.children = [visit_typeof(die)]
        elif die.tag == "DW_TAG_enumeration_type":
            value = value_new(die, ValueTag.Enum)
            value.children = visit_children(die, ["DW_TAG_enumerator"])
        elif die.tag == "DW_TAG_enumerator":
            value = value_new(die, ValueTag.EnumValue)
            value.value = die.attributes["DW_AT_const_value"].value
        elif die.tag == "DW_TAG_base_type":
            value = value_new(die, ValueTag.BaseType)
            value.value = die.attributes["DW_AT_byte_size"].value
        elif die.tag == "DW_TAG_subroutine_type":
            value = void_type
        elif die.tag == "DW_TAG_volatile_type":
            value = visit_typeof(die)
        elif die.tag == "DW_TAG_const_type":
            value = visit_typeof(die)
        elif die.tag == "DW_TAG_atomic_type":
            value = visit_typeof(die)
        else:
            value = None
            print("UNKNOWN TYPE:", die.tag)
        return value

    # ==== Parsing ====
    root = Value(ValueTag.Root, path)
    for cu in dwarf.iter_CUs():  # type: CompileUnit
        cu_die: DIE = cu.get_top_DIE()
        value = visit(cu_die)
        if value is not None:
            root.children.append(value)
    elf.close()
    return root
