import pytest

from backend.main_window import FilePath, DirectoryPath
from backend.main_window import Pipe
from backend.main_window import PipelineManager
from test.test_pipeline.dummy_modules import *
from test.test_pipeline.test_event_manager import DummyPipelineErrorListener, DummyPauseListener


@pytest.fixture(autouse=True)
def clean_up_fixture():
    yield
    for cls in Module.__subclasses__():
        if cls.__name__.startswith("DummyModule"):
            cls.destroy_id_number_manager()

@pytest.fixture
def two_module_pipeline():
    pipeline = PipelineManager()
    mod1 = pipeline.add_module(DummyModule1)
    mod2 = pipeline.add_module(DummyModule2)
    pipe = Pipe(mod1, mod2, ["port1"])
    pipeline.add_connection(pipe)
    assert pipeline.check_ports_occupied(mod1.module_id, ["port1","port2"]) == False, "Something went wrong when adding the connection "
    assert pipeline.check_ports_occupied(mod2.module_id, ["port1"]) == True, "Something went wrong when adding the connection"
    assert str(mod1.outputs["port1"]) == "port_name: 'port1', port_data_type: 'int', opt: False, data: None"
    assert pipeline.modules == [mod1, mod2], "Something went wrong when adding the modules to the pipeline"
    assert pipeline.pipes_in == {"test10": [],
                                 "test20": [pipe]}, "Something went wrong when adding the pipes to the pipeline"
    assert pipeline.pipes_out == {"test10": [pipe],
                                  "test20": []}, "Something went wrong when adding the pipes to the pipeline"
    yield pipeline

def test_add_module():
    pipeline = PipelineManager()
    mod1 = pipeline.add_module(DummyModule1)
    assert pipeline.modules == [mod1], "Something went wrong when adding a module to the pipeline"

def test_add_module_with_id():
    pipeline = PipelineManager()
    mod1 = pipeline.add_module_with_id(DummyModule1,DummyModule1.gui_config().name + "1")
    assert pipeline.modules == [mod1], "Something went wrong with adding a module with a specific id"
    assert mod1.get_id_number() == 1, "Something went wrong with adding a module with a specific id"
    mod2 = pipeline.add_module(DummyModule1)
    mod3 = pipeline.add_module(DummyModule1)
    assert mod2.get_id_number() == 0, "Something went wrong with adding a module with a specific id"
    assert mod3.get_id_number() == 2, "Something went wrong with adding a module with a specific id"
    pipeline.remove_module(mod1)
    mod4 = pipeline.add_module(DummyModule1)
    assert mod4.get_id_number() == 1, "Something went wrong with adding a module with a specific id"
    mod5 = pipeline.add_module_with_id(DummyModule1,DummyModule1.gui_config().name + "5")
    assert mod5.get_id_number() == 5, "Something went wrong with adding a module with a specific id"
    pipeline.get_new_module_id(mod5.module_id)
    assert mod5.get_id_number() == 3, "Something went wrong with adding a module with a specific id"

def test_add_module_with_wrong_id():
    pipeline = PipelineManager()
    with pytest.raises(ValueError):
        pipeline.add_module_with_id(DummyModule1,"lol")
    with pytest.raises(ValueError):
        pipeline.get_new_module_id("lol")

def test_expand_connections():
    pipeline = PipelineManager()
    mod1 = pipeline.add_module(DummyModule1)
    mod2 = pipeline.add_module(DummyModule2)
    pipe = Pipe(mod1, mod2, ["port1"])
    pipeline.expand_connection(pipe,["port2"])
    assert pipe.ports == ["port1", "port2"], "Something went wrong when expanding connections"

def test_add_module_with_all_ready_occupied_id():
    pipeline = PipelineManager()
    pipeline.add_module(DummyModule1)
    with pytest.raises(ValueError):
        pipeline.add_module_with_id(DummyModule1,DummyModule1.gui_config().name + "0")

def test_add_module_next_id_move():
    pipeline = PipelineManager()
    mod1 = pipeline.add_module_with_id(DummyModule1, DummyModule1.gui_config().name + "0")
    assert pipeline.modules == [mod1], "Something went wrong with adding a module with a specific id"
    assert mod1.get_id_number() == 0, "Something went wrong with adding a module with a specific id"
    mod2 = pipeline.add_module(DummyModule1)
    assert mod2.get_id_number() == 1, "Something went wrong with adding a module with a specific id"

def test_add_connection_source_not_added():
    pipeline = PipelineManager()
    mod1 = DummyModule1("")
    mod2 = pipeline.add_module(DummyModule2)
    pipe = Pipe(mod1, mod2,["port1"])
    with pytest.raises(ModuleNotFoundError):
        pipeline.add_connection(pipe)

def test_add_connection_target_not_added():
    pipeline = PipelineManager()
    mod2 = DummyModule2("")
    mod1 = pipeline.add_module(DummyModule1)
    pipe = Pipe(mod1, mod2,["port1"])
    with pytest.raises(ModuleNotFoundError):
        pipeline.add_connection(pipe)

def test_add_connection_already_added(two_module_pipeline):
    with pytest.raises(ValueError):
        two_module_pipeline.add_connection(two_module_pipeline.get_pipe("test10","test20"))

def test_remove_connection_with_error(two_module_pipeline):
    two_module_pipeline.remove_connection("test10", "test20")
    with pytest.raises(ValueError):
        two_module_pipeline.remove_connection("test10", "test20")

def test_remove_connection_valid(two_module_pipeline):
    two_module_pipeline.remove_connection("test10", "test20")
    assert two_module_pipeline.pipes_in == {"test10":[],"test20":[]}, "Something went wrong when removing the pipe from the pipeline"
    assert two_module_pipeline.pipes_out == {"test10":[],"test20":[]}, "Something went wrong when removing the pipes from the pipeline"

def test_remove_module_with_error(two_module_pipeline):
    with pytest.raises(RuntimeError):
        two_module_pipeline.remove_module(two_module_pipeline.module_map["test10"])

def test_remove_module_valid(two_module_pipeline):
    two_module_pipeline.remove_connection("test10", "test20")
    assert two_module_pipeline.pipes_in == {"test10": [],
                                            "test20": []}, "Something went wrong when removing the pipe from the pipeline"
    assert two_module_pipeline.pipes_out == {"test10": [],
                                             "test20": []}, "Something went wrong when removing the pipes from the pipeline"
    two_module_pipeline.remove_module(two_module_pipeline.module_map["test10"])
    assert two_module_pipeline.module_map == {"test20": two_module_pipeline.module_map["test20"],}, "Something went wrong when removing the pipe from the pipeline"
    assert two_module_pipeline.modules == [two_module_pipeline.module_map["test20"]], "Something went wrong when removing the module from the pipeline"
    assert two_module_pipeline.pipes_in == {"test20": [],}, "Something went wrong when removing the pipe from the pipeline"
    assert two_module_pipeline.pipes_out == {
        "test20": [], }, "Something went wrong when removing the pipe from the pipeline"

def test_runnable_false(two_module_pipeline):
    two_module_pipeline.remove_connection("test10", "test20")
    assert two_module_pipeline.check_pipeline_runnable() == False, "Something went wrong when checking the pipeline runnable"


def test_runnable_true(two_module_pipeline):
    assert two_module_pipeline.check_pipeline_runnable() == True, "Something went wrong when checking the pipeline runnable"
    two_module_pipeline.remove_connection("test10", "test20")
    assert two_module_pipeline.check_pipeline_runnable(ignore=["test20"]) == True, "Something went wrong when checking the pipeline runnable"


def test_run_valid(two_module_pipeline):
    mod3 = two_module_pipeline.add_module(DummyModule1)
    two_module_pipeline.run(ignore_modules=[mod3.module_id])
    assert two_module_pipeline.module_map["test10"].outputs["port1"].data == 67, "Something went wrong when running the pipeline"
    assert two_module_pipeline.module_map["test20"].inputs["port1"].data == 67, "Something went wrong when running the pipeline"
    assert two_module_pipeline.module_map["test20"].outputs[
               "port2"].data == "The resulting data is: 67", "Something went wrong when running the pipeline"
    assert two_module_pipeline.modules_executed == 2, "Something went wrong when running the pipeline"

def test_run_with_pause(two_module_pipeline):
    pause_listener = DummyPauseListener(two_module_pipeline)
    two_module_pipeline.event_manager.subscribe(pause_listener)
    mod3 = two_module_pipeline.add_module(DummyPauseModule)
    pipe = Pipe(two_module_pipeline.module_map["test10"], mod3, ["port1"])
    two_module_pipeline.add_connection(pipe)
    two_module_pipeline.run()
    assert pause_listener.count == 2, "Something went wrong when pausing the pipeline"
    assert two_module_pipeline.modules_executed == 3, "Something went wrong when running the pipeline"

def test_run_with_pause_and_cancel(two_module_pipeline):
    pause_listener = DummyPauseListener(two_module_pipeline,cancel=True)
    two_module_pipeline.event_manager.subscribe(pause_listener)
    mod4 = two_module_pipeline.add_module(DummyPauseModule)
    pipe = Pipe(two_module_pipeline.module_map["test10"], mod4, ["port1"])
    two_module_pipeline.add_connection(pipe)
    two_module_pipeline.run()
    assert pause_listener.count == 2, "Something went wrong when pausing the pipeline"

def test_run_n_to_one_module_valid(two_module_pipeline):
    mod1 = two_module_pipeline.module_map["test10"]
    mod2 = two_module_pipeline.module_map["test20"]
    mod3 = two_module_pipeline.add_module(DummyModule4)
    pipe2 = Pipe(mod1, mod3, ["port1"])
    pipe3 = Pipe(mod2, mod3, ["port2"])
    two_module_pipeline.add_connection(pipe2)
    two_module_pipeline.add_connection(pipe3)
    two_module_pipeline.run()
    assert mod1.outputs["port1"].data == 67, "Something went wrong when running the first module"
    assert mod2.inputs[
               "port1"].data == 67, "Something went wrong when transferring the data with the pipe from m1 to m2"
    assert mod2.outputs[
               "port2"].data == "The resulting data is: 67", "Something went wrong when running the second module"
    assert mod3.inputs[
               "port2"].data == "The resulting data is: 67", "Something went wrong when transferring the data with the pipe from the m1 to m4"
    assert mod3.inputs[
               "port1"].data == 67, "Something went wrong when transferring the data with the pipe from m1 to m4"
    assert mod3.outputs[
               "port3"].data == "The resulting data is: 67 == 67", "Something went wrong when running the fourth module"
    for mod in two_module_pipeline.modules:
        assert mod.event_manager is not None, "Something went wrong by setting the event_manager attribute"
    assert two_module_pipeline.modules_executed == 3, "Something went wrong when running the pipeline"


def test_run_one_module_invalid(two_module_pipeline):
    mod1 = two_module_pipeline.module_map["test10"]
    mod2 = two_module_pipeline.module_map["test20"]
    two_module_pipeline.remove_connection("test10", "test20")
    two_module_pipeline.run()
    assert mod1.outputs["port1"].data == 67, "Something went wrong when running the first module"
    assert mod2.inputs[
               "port1"].data is None, "Something went wrong when skipping the second module"
    assert mod2.outputs[
               "port2"].data is None, "Something went wrong when skipping the second module"

def test_cycled_graph(two_module_pipeline):
    mod2 = two_module_pipeline.module_map["test20"]
    mod4 = two_module_pipeline.add_module(DummyModule4)
    two_module_pipeline.add_connection(Pipe(mod2, mod4, ["port2"]))
    two_module_pipeline.add_connection(Pipe(mod4, mod2, ["port1"]))
    pipeline_error= DummyPipelineErrorListener()
    two_module_pipeline.event_manager.subscribe(pipeline_error)
    two_module_pipeline.run()
    assert pipeline_error.last_event.error_name == "Cycle in pipeline", "Something went wrong when detecting the cycle in the pipeline"
    assert two_module_pipeline.modules_executed == 0, "Something went wrong went wrong when detecting the cycle in the pipeline"

def test_free_number(two_module_pipeline):
    mod1 = two_module_pipeline.module_map["test10"]
    two_module_pipeline.remove_connection("test10", "test20")
    assert mod1.module_id == "test10", "Something went wrong when initialing DummyModule1"
    two_module_pipeline.remove_module(mod1)
    mod3 = two_module_pipeline.add_module(DummyModule1)
    assert mod3.module_id == "test10", "Something went wrong when initialing a new instance of DummyModule1"

def test_files_directory():
    file_path = FilePath("test1",["lif","test"])
    assert file_path.path == "test1", "Something went wrong initialising the file path"
    assert file_path.suffix == ["lif","test"], "Something went wrong initialising the file path"
    directory_path = DirectoryPath("test1")
    assert directory_path.path == "test1", "Something went wrong initialising the directory path"

def test_remove_module_not_in_pipeline():
    pipeline = PipelineManager()
    mod = DummyModule1(DummyModule1.gui_config().name)
    with pytest.raises(ValueError):
        pipeline.remove_module(mod)

def test_ports_occupied():
    pipeline = PipelineManager()
    mod1 = pipeline.add_module(DummyModule1)
    mod2 = pipeline.add_module(DummyModule2)
    mod3 = pipeline.add_module(DummyModule1)
    pipe = Pipe(mod1, mod2, ["port1"])
    pipe2 = Pipe(mod3, mod2, ["port5"])
    pipeline.add_connection(pipe)
    pipeline.add_connection(pipe2)
    assert pipeline.check_ports_occupied(mod1.module_id, ["port1",
                                                          "port2"]) == False, "Something went wrong when adding the connection "
    assert pipeline.check_ports_occupied(mod2.module_id,
                                         ["port1"]) == True, "Something went wrong when adding the connection"
    assert pipeline.check_ports_occupied(mod2.module_id,
                                         ["port3"]) == False, "Something went wrong when adding the connection"
    assert str(mod1.outputs["port1"]) == "port_name: 'port1', port_data_type: 'int', opt: False, data: None"
    assert pipeline.modules == [mod1, mod2, mod3], "Something went wrong when adding the modules to the pipeline"
    assert pipeline.pipes_in == {"test10": [],
                                 "test20": [pipe, pipe2],
                                 "test11": [], }, "Something went wrong when adding the pipes to the pipeline"
    assert pipeline.pipes_out == {"test10": [pipe],
                                  "test20": [],
                                  "test11": [pipe2]}, "Something went wrong when adding the pipes to the pipeline"
    pipe3 = pipeline.get_pipe("test11","test20")
    assert pipe3 == pipe2, "Something went wrong when getting the pipe"