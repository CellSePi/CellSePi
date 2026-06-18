import pytest
import os
import flet as ft
import logging
from unittest.mock import MagicMock, patch
from backend.error_manager import ErrorManager


@pytest.fixture(autouse=True)
def reset_error_singleton():
    ErrorManager._instance = None
    ErrorManager._initialized = False
    logging.getLogger("cellsepi").handlers.clear()
    yield
    ErrorManager._instance = None
    ErrorManager._initialized = False
    logging.getLogger("cellsepi").handlers.clear()


@pytest.fixture
def mock_app_dir(tmp_path):
    with patch("backend.error_manager.APP_DIR", tmp_path):
        yield tmp_path


def test_singleton_and_init(mock_app_dir):
    mock_page = MagicMock(spec=ft.Page)
    em1 = ErrorManager(page=mock_page)
    em2 = ErrorManager()

    assert em1 is em2
    assert em2.page is mock_page
    assert (mock_app_dir / "logs").exists()


def test_log_method(mock_app_dir):
    em = ErrorManager()
    test_error = ValueError("Simulated error")
    em.log(test_error)

    log_content = em.log_path.read_text()
    assert "Simulated error" in log_content
    assert "ValueError" in log_content


def test_show_methods(mock_app_dir):
    mock_page = MagicMock(spec=ft.Page)
    em = ErrorManager(page=mock_page)

    em.show("Test Show")
    mock_page.show_dialog.assert_called()
    mock_page.update.assert_called()

    em.show_without_button("Test show no button")
    assert mock_page.show_dialog.call_count == 2


def test_show_methods_no_page(mock_app_dir):
    em = ErrorManager(page=None)

    try:
        em.show("Test Show without page")
        em.show_without_button("Test Show without button and page")
    except Exception as e:
        pytest.fail(f"The methods throw an error when page = None is set: {e}")

def test_log_and_show_with_page(mock_app_dir):
    mock_page = MagicMock(spec=ft.Page)
    em = ErrorManager(page=mock_page)

    em.log_and_show("User test message", ValueError("Crash"))

    mock_page.show_dialog.assert_called_once()
    log_content = em.log_path.read_text()
    assert "User test message" in log_content


def test_log_and_show_no_page(mock_app_dir):
    em = ErrorManager(page=None)

    with patch.object(em, 'log') as mock_log:
        ex = ValueError("Crash")
        em.log_and_show("User test message", ex)
        mock_log.assert_called_once_with(ex)


def test_open_log_file_windows(mock_app_dir):
    em = ErrorManager()
    with patch("sys.platform", "win32"), patch("os.startfile", create=True) as mock_startfile:
        em.open_log_file()
        mock_startfile.assert_called_once_with(str(em.log_path))


def test_open_log_file_mac(mock_app_dir):
    em = ErrorManager()
    with patch("sys.platform", "darwin"), patch("subprocess.call") as mock_call:
        em.open_log_file()
        mock_call.assert_called_once_with(["open", str(em.log_path)])


def test_open_log_file_linux(mock_app_dir):
    em = ErrorManager()
    with patch("sys.platform", "linux"), patch("subprocess.call") as mock_call:
        em.open_log_file()
        mock_call.assert_called_once_with(["xdg-open", str(em.log_path)])


def test_open_log_file_bare_except(mock_app_dir):
    em = ErrorManager()
    with patch("sys.platform", "win32"), patch("os.startfile", side_effect=Exception("Not allowed, to do that"),
                                               create=True):
        em.open_log_file()

