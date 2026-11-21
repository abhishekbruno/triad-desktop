import pytest
from app.core.window_manager import WindowManager


def test_is_window_valid_invalid_inputs():
    assert not WindowManager.is_window_valid(None)
    assert not WindowManager.is_window_valid(0)
    assert not WindowManager.is_window_valid(-1)


def test_focus_window_invalid_handle():
    success, msg = WindowManager.focus_window(99999999)
    assert not success
    assert "invalid" in msg.lower() or "not available" in msg.lower()


def test_focus_window_restores_and_activates(mocker):
    # Mock win32 APIs
    mocker.patch("app.core.window_manager.HAS_WIN32", True)
    mock_gui = mocker.patch("app.core.window_manager.win32gui")
    mock_process = mocker.patch("app.core.window_manager.win32process")
    mock_api = mocker.patch("app.core.window_manager.win32api")

    mock_gui.IsWindow.return_value = True
    mock_gui.IsIconic.return_value = True
    mock_api.GetCurrentThreadId.return_value = 100
    mock_process.GetWindowThreadProcessId.return_value = (200, 500)

    success, msg = WindowManager.focus_window(12345)

    assert success
    assert "success" in msg.lower()
    # Confirm ShowWindow was called with SW_RESTORE
    mock_gui.ShowWindow.assert_called_once()
    mock_gui.SetForegroundWindow.assert_called_once_with(12345)


def test_focus_window_foreground_restriction_handled_cleanly(mocker):
    mocker.patch("app.core.window_manager.HAS_WIN32", True)
    mock_gui = mocker.patch("app.core.window_manager.win32gui")
    mock_process = mocker.patch("app.core.window_manager.win32process")
    mock_api = mocker.patch("app.core.window_manager.win32api")

    mock_gui.IsWindow.return_value = True
    mock_gui.IsIconic.return_value = False
    mock_api.GetCurrentThreadId.return_value = 100
    mock_process.GetWindowThreadProcessId.return_value = (100, 500)

    # Simulate Windows foreground lock restriction exception
    mock_gui.SetForegroundWindow.side_effect = Exception("Access is denied (foreground locked)")

    success, msg = WindowManager.focus_window(12345)
    assert not success
    assert "foreground restriction" in msg.lower()

