from test.test_pipeline.dummy_modules import *
from backend.main_window import Pipe, copy_data, IMMUTABLES
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
    assert str(mod1) == f"module_id: '{mod1.gui_config().name}', category: '{mod1.gui_config().category}', module_name: {mod1.gui_config().name}, inputs: {mod1.inputs}, outputs: {mod1.outputs}, user_attributes: {mod1.get_user_attributes}"

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
    assert str(pipe1) == f"source: '{mod1.module_id}', target: '{mod2.module_id}', ports: {["port1"]}", "Something went wrong converting pipe to string"
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
