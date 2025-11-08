from elftools.elf.elffile import ELFFile
from elftools.dwarf.descriptions import describe_DWARF_expr, set_global_machine_arch
from elftools.dwarf.locationlists import LocationEntry, LocationExpr, LocationParser
from elftools.dwarf.dwarf_expr import DWARFExprParser
import sys
from typing import Self
from store import Store, Value, ValueTag


class DwarfDB(Store):
    def __init__(self, die_to_addr=lambda die: 0):
        super().__init__()
        self.mapping = {}
        self.die_to_addr = die_to_addr

        # Add a 'void' value (not present in dwarf for some reason)
        self.void_value = Value()
        self.void_value.id = 0
        self.void_value.tag = ValueTag.BaseType
        self.void_value.name = "void"
        self.put(self.void_value)

    def get_id(self, die) -> int:
        if die.offset not in self.mapping:
            return None
        return self.mapping[die.offset]

    def put_children(self, die, filter: [str] = None, need_name: bool = False) -> [Value]:
        children = []
        for child in die.iter_children():
            # Whitelist some tags
            if filter is not None and child.tag not in filter:
                continue

            if need_name and "DW_AT_name" not in child.attributes:
                continue

            id = self.put_die(child)
            if id is not None:
                children.append(id)
        return children

    def put_value(self, die, tag: ValueTag) -> Value:
        value = Value()
        value.id = len(self.values)
        value.tag = tag

        if "DW_AT_name" in die.attributes:
            value.name = die.attributes["DW_AT_name"].value.decode()
        self.put(value)
        self.mapping[die.offset] = value
        return value

    def put_attr(self, die, attr) -> Value:
        if attr not in die.attributes:
            return None

        id = self.put_die(die.get_DIE_from_attribute(attr))
        if id is None:
            return None

        return id

    def put_type(self, die) -> Value:
        if "DW_AT_type" not in die.attributes:
            return self.void_value
        return self.put_attr(die, "DW_AT_type")

    def put_die(self, die) -> Value:
        # Check if die already exists
        if die.offset in self.mapping:
            return self.mapping[die.offset]
        # Append a value
        if die.tag == "DW_TAG_compile_unit":
            value = self.put_value(die, ValueTag.CompileUnit)
            value.children = self.put_children(die, ["DW_TAG_variable"], need_name=True)
        elif die.tag == "DW_TAG_variable":
            value = self.put_value(die, ValueTag.Variable)
            value.type = self.put_type(die)
            value.value = self.die_to_addr(die)
        elif die.tag == "DW_TAG_typedef":
            value = self.put_value(die, ValueTag.Typedef)
            value.type = self.put_type(die)
        elif die.tag == "DW_TAG_volatile_type":
            value = self.put_value(die, ValueTag.Volatile)
            value.type = self.put_type(die)
        elif die.tag == "DW_TAG_const_type":
            value = self.put_value(die, ValueTag.Const)
            value.type = self.put_type(die)
        elif die.tag == "DW_TAG_pointer_type":
            value = self.put_value(die, ValueTag.Pointer)
            value.type = self.put_type(die)
        elif die.tag == "DW_TAG_array_type":
            value = self.put_value(die, ValueTag.Array)
            value.type = self.put_type(die)
            value.value = 1  # Number of array items
            for child in die.iter_children():
                if "DW_AT_count" in child.attributes:
                    value.value *= child.attributes["DW_AT_count"].value
                elif "DW_AT_upper_bound" in child.attributes:
                    value.value *= child.attributes["DW_AT_upper_bound"].value + 1
        elif die.tag == "DW_TAG_structure_type" or die.tag == "DW_TAG_class_type" or die.tag == "DW_TAG_union_type":
            value = self.put_value(die, ValueTag.Struct)
            value.children = self.put_children(die, ["DW_TAG_member"])
        elif die.tag == "DW_TAG_member":
            value = self.put_value(die, ValueTag.Variable)
            value.type = self.put_type(die)
            value.value = die.attributes["DW_AT_data_member_location"].value
        elif die.tag == "DW_TAG_enumeration_type":
            value = self.put_value(die, ValueTag.Enum)
            value.children = self.put_children(die, ["DW_TAG_enumerator"])
        elif die.tag == "DW_TAG_enumerator":
            value = self.put_value(die, ValueTag.EnumValue)
            value.value = die.attributes["DW_AT_const_value"].value
        elif die.tag == "DW_TAG_base_type":
            value = self.put_value(die, ValueTag.BaseType)
            value.value = die.attributes["DW_AT_byte_size"].value
        elif die.tag == "DW_TAG_subroutine_type":
            value = self.put_value(die, ValueTag.Function)
            value.type = self.put_type(die)
            value.children = self.put_children(die)
        elif die.tag == "DW_TAG_formal_parameter":
            value = self.put_value(die, ValueTag.Variable)
            value.type = self.put_type(die)
        else:
            print(die.tag)
            return self.void_value
        return value

    def load_dwarf(self, file: str):
        with open(file, "rb") as file:
            elf = ELFFile(file)
            dwarf = elf.get_dwarf_info()
            location_list = dwarf.location_lists()
            location_parser = LocationParser(location_list)
            expr_parser = DWARFExprParser(dwarf.structs)

            def die_to_addr(die) -> int:
                if "DW_AT_location" not in die.attributes:
                    return None

                cu = die.cu
                attr = die.attributes["DW_AT_location"]
                parsed = location_parser.parse_from_attribute(attr, cu["version"], die)
                expr = expr_parser.parse_expr(parsed.loc_expr)

                # NOTE: This supports only basic addressing for now
                if len(expr) == 1 and expr[0].op_name == "DW_OP_addr":
                    return expr[0].args[0]

                print("Unknown address expression:", expr)
                return None

            self.die_to_addr = die_to_addr
            for cu in dwarf.iter_CUs():
                self.put_die(cu.get_top_DIE())
            self.die_to_addr = None
