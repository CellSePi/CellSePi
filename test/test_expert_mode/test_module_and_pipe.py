from backend.expert_mode.module import Module, Port
from test.test_expert_mode.dummy_modules import *
from backend.expert_mode.pipe import Pipe, copy_data, IMMUTABLES
import flet as ft
import pytest

@pytest.fixture(autouse=True)
def clean_up_fixture():
    yield
    for cls in Module.__subclasses__():
        if cls.__name__.startswith("DummyModule"):
            cls.destroy_id_number_manager()

def test_set_port_wrong():
    mod = DummyModule1()
    with pytest.raises(TypeError):
        mod.outputs["port1"].data = "hi"
    mod.destroy()

def test_set_port_right():
    mod = DummyModule1()
    mod.outputs["port1"].data = 42
    assert  mod.outputs["port1"].data == 42 , "Something went wrong when setting the port data"
    mod.destroy()

def test_pipe_same_modules():
    mod1 = DummyModule1()
    with pytest.raises(ValueError):
        Pipe(mod1,mod1,["Port1"])

def test_pipe_same_names():
    mod1 = DummyModule1()
    mod2 = DummyModule2()
    mod2.module_id = mod1.module_id
    with pytest.raises(ValueError):
        Pipe(mod1,mod2,["Port1"])

def test_pipe_wrong_type_mod1():
    mod1 = DummyModule1()
    mod3 = DummyModule3()
    pipe = Pipe(mod1, mod3, ["port1"])
    with pytest.raises(TypeError):
        pipe.run()

def test_pipe_source_without_port():
    mod1 = DummyModule1()
    mod1.outputs = {}
    mod3 = DummyModule3()
    pipe = Pipe(mod1, mod3, ["port1"])
    with pytest.raises(KeyError):
        pipe.run()

def test_pipe_target_without_port():
    mod1 = DummyModule1()
    mod1.outputs["port1"].data = 42
    mod3 = DummyModule3()
    mod3.inputs = {}
    pipe = Pipe(mod1, mod3, ["port1"])
    with pytest.raises(KeyError):
        pipe.run()

def test_empty_ports_pipe():
    mod1 = DummyModule1()
    mod1.outputs["port1"].data = 42
    mod2 = DummyModule2()
    with pytest.raises(ValueError):
        Pipe(mod1, mod2,[])

def test_none_ports_pipe():
    mod1 = DummyModule1()
    mod1.outputs["port1"].data = 42
    mod2 = DummyModule2()
    with pytest.raises(ValueError):
        Pipe(mod1, mod2, None)

def test_correct_pipe():
    mod1 = DummyModule1()
    mod1.outputs["port1"].data = 42
    mod2 = DummyModule2()
    pipe = Pipe(mod1, mod2,["port1"])
    pipe.run()
    assert mod2.inputs["port1"].data == 42, "Something went wrong when transferring the data with the pipe"

def test_running_module_pipe():
    mod1 = DummyModule1()
    mod2 = DummyModule2()
    pipe = Pipe(mod1, mod2,["port1"])
    pipeline = [mod1,pipe,mod2]
    for step in pipeline:
        step.run()
    assert mod1.outputs["port1"].data == 67, "Something went wrong when running the first module"
    assert mod2.inputs["port1"].data == 67, "Something went wrong when transferring the data with the pipe"
    assert mod2.outputs["port2"].data == "The resulting data is: 67" , "Something went wrong by running the second module"

def test_n_to_one_module():
    mod1 = DummyModule1()
    mod2 = DummyModule2()
    mod4 = DummyModule4()
    pipe1 = Pipe(mod1, mod2,["port1"])
    pipe2 = Pipe(mod1, mod4,["port1"])
    pipe3 = Pipe(mod2, mod4,["port2"])
    pipeline = [mod1, pipe1, mod2, pipe2, pipe3, mod4]
    for step in pipeline:
        step.run()
    assert mod1.outputs["port1"].data == 67, "Something went wrong when running the first module"
    assert mod2.inputs["port1"].data == 67, "Something went wrong when transferring the data with the pipe from m1 to m2"
    assert mod2.outputs["port2"].data == "The resulting data is: 67", "Something went wrong when running the second module"
    assert mod4.inputs["port2"].data == "The resulting data is: 67", "Something went wrong when transferring the data with the pipe from the m1 to m4"
    assert mod4.inputs["port1"].data == 67, "Something went wrong when transferring the data with the pipe from m1 to m4"
    assert mod4.outputs["port3"].data == "The resulting data is: 67 == 67", "Something went wrong when running the fourth module"

def test_find_mandatory_inputs():
    mod4 = DummyModule4()
    mandatory_inputs = mod4.get_mandatory_inputs()
    assert mandatory_inputs == ["port1", "port2"], "Something went wrong when getting the mandatory inputs"

def test_find_no_mandatory_inputs():
    mod1 = DummyModule1()
    mandatory_inputs = mod1.get_mandatory_inputs()
    assert mandatory_inputs == [], "Something went wrong when getting the mandatory inputs"

def test_user_attributes():
    mod1 = DummyModule1(DummyModule1.gui_config().name)
    user_attr =mod1.get_user_attributes
    assert user_attr == ["user_test1","user_test2","user_test3","user_test4"] , "Something went wrong when getting the user attributes"
    assert str(mod1) == f"module_id: {mod1.gui_config().name}, category: {mod1.gui_config().category}, module_name: {mod1.gui_config().name}, inputs: {mod1.inputs}, outputs: {mod1.outputs}, user_attributes: {mod1.get_user_attributes}"

def test_setting():
    mod1 = DummyModule1()
    assert mod1.settings is None, "Settings should be None"
    mod1._settings = ft.Stack([ft.Text("test")])
    assert mod1.settings is not None, "Something went wrong when setting settings"
    mod1.on_settings_dismiss()
    assert mod1.user_test4 == 5, "Something went wrong when using the on_settings_dismiss function"


def test_pipe_formating():
    mod1 = DummyModule1()
    mod2 = DummyModule2()
    pipe1 = Pipe(mod1, mod2, ["port1"])
    assert str(pipe1) == f"source: {mod1.module_id}, target: {mod2.module_id}, ports: {["port1"]}", "Something went wrong converting pipe to string"
    assert pipe1.to_dict() == {
            "source": mod1.module_id,
            "target": mod2.module_id,
            "ports": ["port1"],
        }, "Something went wrong converting pipe to dict"

def _is_copy(original, candidate): #pragma: no cover
    if isinstance(original, IMMUTABLES):
        return True
    if isinstance(original, (tuple,frozenset)):
        if not any(_is_mutable_recursive(v) for v in original):
           return True
    if original is candidate:
        return False
    if original == candidate:
        return True
    return False

def _is_mutable_recursive(obj): #pragma: no cover
    if isinstance(obj, IMMUTABLES):
        return False
    if isinstance(obj, (tuple, frozenset)):
        return any(_is_mutable_recursive(v) for v in obj)
    if isinstance(obj, (list, dict, set)):
        return True
    return True

def test_copy_data():
    test_data = [
        42,  #int -> IMMUTABLES case
        3.14,  #float -> IMMUTABLES case
        "hello",  #str -> IMMUTABLES case
        True,  #bool -> IMMUTABLES case
        None,  #NoneType -> IMMUTABLES case
        (1, 2, 3),  # tuple -> deepcopy() case -> IMMUTABLES case
        ((1,2),3,4), #tuple nested -> deepcopy() case -> copy
        (((1,[1,2]), 2), 3, 4),  # tuple nested -> deepcopy() case -> copy
        [1, 2, 3],  #list -> deepcopy() case
        {"a": 1},  #dict -> deepcopy() case
        {1, 2, 3},  #set -> deepcopy() case
    ]
    for test in test_data:
        assert _is_copy(test, copy_data(test)) == True, f"Something went wrong when copying data of typen: {type(test).__name__}"

def test_error_module():
    mod = DummyModule1(DummyModule1.gui_config().name)
    with pytest.raises(ValueError):
        mod.free_id_number(10)
    with pytest.raises(ValueError):
        mod.occupy()
    with pytest.raises(ValueError):
        mod.destroy()

def test_on_setting_dismiss():
    mod1 = DummyModule4()
    mod1.on_settings_dismiss()
    mod1._on_settings_dismiss = None
    with pytest.raises(TypeError):
        mod1.on_settings_dismiss()


def test_multi_port_setter_errors():
    """
    Tests if the Port.data setter raises the correct TypeErrors
    when provided with the wrong container type for multi ports.
    """
    port_tagged = InputPort("port1", int, multi=["cat", "dog"])

    with pytest.raises(TypeError) as exc_info:
        port_tagged.data = [1, 2, 3]
    assert "multi_tagged needs a Dictionary" in str(exc_info.value)

    port_list = InputPort("port2", int, multi=True)

    with pytest.raises(TypeError) as exc_info:
        port_list.data = {"cat": [1, 2]}
    assert "multi_list needs a List" in str(exc_info.value)


def test_multi_port_add_data_errors():
    """
    Tests if the Port.add_data method raises the correct TypeErrors
    and ValueErrors for invalid data types and unknown tags.
    """
    from backend.expert_mode.module import InputPort

    port_tagged = InputPort("port1", int, multi=["cat", "dog"])

    with pytest.raises(TypeError) as exc_info:
        port_tagged.add_data("not an int", tag="dog")
    assert "Expected data of type <class 'int'>" in str(exc_info.value)

    with pytest.raises(ValueError) as exc_info:
        port_tagged.add_data(42, tag="bird")
    assert "Tag bird is not valid for this port!" in str(exc_info.value)

    with pytest.raises(ValueError) as exc_info:
        port_tagged.add_data(42)
    assert "Tag None is not valid for this port!" in str(exc_info.value)


def test_port_data_setter_validations():
    port_single = Port("p1", int)
    port_tagged = Port("p2", int, multi=["tag1"])
    port_list = Port("p3", int, multi=True)

    with pytest.raises(TypeError) as exc_info:
        port_single.data = "not an int"
    assert "single needs int" in str(exc_info.value), "Wrong TypeError message for single port"

    with pytest.raises(TypeError) as exc_info:
        port_tagged.data = [1, 2, 3]
    assert "multi_tagged needs a Dictionary" in str(exc_info.value), "Wrong TypeError message for multi_tagged port"

    with pytest.raises(TypeError) as exc_info:
        port_list.data = {"tag": [1]}
    assert "multi_list needs a List" in str(exc_info.value), "Wrong TypeError message for multi_list port"

    port_single.data = 42
    assert port_single.data == 42

    port_tagged.data = {"tag1": [42]}
    assert port_tagged.data == {"tag1": [42]}

    port_list.data = [42]
    assert port_list.data == [42]


def test_port_clear_and_none_setter():
    port_single = Port("p1", int)
    port_tagged = Port("p2", int, multi=["a", "b"])
    port_list = Port("p3", int, multi=True)

    # Daten füllen
    port_single.data = 42
    port_tagged.data = {"a": [1], "b": [2]}
    port_list.data = [1, 2, 3]

    port_single.clear()
    assert port_single.data is None, "Single port not cleared properly"

    port_tagged.clear()
    assert port_tagged.data == {"a": [], "b": []}, "Multi_tagged port not cleared properly"

    port_list.clear()
    assert port_list.data == [], "Multi_list port not cleared properly"

    port_single.data = 99
    port_tagged.data = {"a": [99], "b": [99]}
    port_list.data = [99]

    port_single.data = None
    assert port_single.data is None, "Setter with None failed for single"

    port_tagged.data = None
    assert port_tagged.data == {"a": [], "b": []}, "Setter with None failed for multi_tagged"

    port_list.data = None
    assert port_list.data == [], "Setter with None failed for multi_list"

    port_invalid = Port("p4", int)
    port_invalid.mode = "invalid_mode_for_test"
    with pytest.raises(ValueError) as exc_info:
        port_invalid.clear()

    assert "Parameter multi must be False, True, or a collection of tags." in str(exc_info.value)

def test_pipe_to_dict_with_tuples():
    mod1 = DummyModule1()
    mod2 = DummyModule2()

    pipe = Pipe(mod1, mod2, ["port_normal", ("port1", "dog")])

    expected_dict = {
        "source": mod1.module_id,
        "target": mod2.module_id,
        "ports": ["port_normal", ["port1", "dog"]],
    }

    assert pipe.to_dict() == expected_dict, "Pipe.to_dict() failed to convert tuples to lists!"


def test_module_id_without_number_errors():
    mod1 = DummyModule1()

    mod1.module_id = f"{DummyModule1.gui_config().name}_"

    with pytest.raises(ValueError) as exc_info:
        mod1.occupy()
    assert "contain a number" in str(exc_info.value), "Wrong error message in occupy()"

    with pytest.raises(ValueError) as exc_info:
        mod1.destroy()
    assert "contain a number" in str(exc_info.value), "Wrong error message in destroy()"


def test_port_init_invalid_multi_parameter():
    with pytest.raises(ValueError) as exc_info:
        Port("p1", int, multi="invalid_string_parameter")

    assert "Parameter multi must be False, True, or a collection of tags." in str(exc_info.value)


def test_port_multi_set_sorting():
    port = Port("p1", int, multi={"z", "a", "m"})

    assert port.mode == "multi_tagged"
    assert port.allowed_tags == ["a", "m", "z"], "Set was not sorted correctly into a list!"

    assert list(port.data.keys()) == ["a", "m", "z"], "Dictionary keys are not in sorted order!"


def test_pipe_port_names_property_with_tuples():
    mod1 = DummyModule1()
    mod2 = DummyModule2()

    pipe = Pipe(mod1, mod2, ["port_normal", ("port_tagged", "dog")])
    names = pipe.port_names

    assert names == ["port_normal", "port_tagged"], "Pipe.port_names failed to extract names from tuples!"
