import pytest
from app.core.app_discovery import AppDiscoveryService
from app.models.agent import WindowCandidate


def test_classify_native_chatgpt():
    service = AppDiscoveryService()
    cand = WindowCandidate(
        hwnd=1001,
        pid=5001,
        title="ChatGPT",
        executable_name="chatgpt.exe",
        executable_path="C:\\Program Files\\ChatGPT\\chatgpt.exe",
        is_visible=True,
    )
    agent_id, conf, reason = service.classify_window(cand)
    assert agent_id == "chatgpt"
    assert conf >= 0.90
    assert "chatgpt.exe" in reason


def test_classify_native_claude():
    service = AppDiscoveryService()
    cand = WindowCandidate(
        hwnd=1002,
        pid=5002,
        title="Claude",
        executable_name="Claude.exe",
        executable_path="C:\\Users\\User\\AppData\\Local\\Programs\\Claude\\Claude.exe",
        is_visible=True,
    )
    agent_id, conf, reason = service.classify_window(cand)
    assert agent_id == "claude"
    assert conf >= 0.90
    assert "Claude.exe" in reason


def test_classify_gemini_pwa_mode(mocker):
    service = AppDiscoveryService()
    cand = WindowCandidate(
        hwnd=1003,
        pid=5003,
        title="Gemini",
        executable_name="chrome.exe",
        executable_path="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        is_visible=True,
    )
    # Mock command line to include PWA flag
    mocker.patch.object(
        service,
        "_get_process_cmdline",
        return_value=["chrome.exe", "--app=https://gemini.google.com"],
    )

    agent_id, conf, reason = service.classify_window(cand)
    assert agent_id == "gemini"
    assert conf >= 0.85
    assert "gemini.google.com" in reason


def test_reject_unrelated_process_with_misleading_title():
    service = AppDiscoveryService()
    # E.g. Chrome browser tab searching on Google for ChatGPT comparison
    cand = WindowCandidate(
        hwnd=2001,
        pid=6001,
        title="ChatGPT vs Claude - Google Search - Google Chrome",
        executable_name="chrome.exe",
        executable_path="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        is_visible=True,
    )
    agent_id, conf, reason = service.classify_window(cand)
    assert agent_id is None
    assert conf == 0.0


def test_reject_generic_code_editor_with_ai_title():
    service = AppDiscoveryService()
    cand = WindowCandidate(
        hwnd=2002,
        pid=6002,
        title="chatgpt_test.py - Visual Studio Code",
        executable_name="Code.exe",
        executable_path="C:\\Users\\User\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe",
        is_visible=True,
    )
    agent_id, conf, reason = service.classify_window(cand)
    assert agent_id is None
    assert conf == 0.0

