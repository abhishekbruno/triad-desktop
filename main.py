import sys
from PySide6.QtWidgets import QApplication

from app.core.agent_registry import AgentRegistry
from app.core.app_discovery import AppDiscoveryService
from app.core.message_bridge import MessageExchangeBridge
from app.core.session_manager import SessionManager
from app.core.window_manager import WindowManager
from app.storage.database import DatabaseManager
from app.storage.session_repository import SessionRepository
from app.ui.main_window import MainWindow
from app.utils.logging import get_logger, setup_logging


def main() -> int:
    """Entry point for the TRIAD Desktop Workspace."""
    setup_logging()
    logger = get_logger("main")
    logger.info("Initializing TRIAD Desktop Workspace (Phase 1 & Phase 2A)...")

    # Initialize Core Subsystems
    database = DatabaseManager()
    session_repo = SessionRepository(db=database)
    session_manager = SessionManager(repository=session_repo)
    registry = AgentRegistry()
    discovery = AppDiscoveryService()
    window_manager = WindowManager()
    message_bridge = MessageExchangeBridge(
        registry=registry,
        window_manager=window_manager,
        database=database,
    )

    # Set explicit Windows AppUserModelID so taskbar displays the custom icon
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("triad.desktop.consensus.workspace")
    except Exception:
        pass

    # Launch PySide6 GUI Application
    app = QApplication(sys.argv)
    app.setApplicationName("TRIAD Local AI Workspace")
    app.setOrganizationName("TRIAD Project")

    # Set Application Window & Taskbar Icon
    from pathlib import Path
    from PySide6.QtGui import QIcon

    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    icon_candidates = [
        base_dir / "assets" / "triad.ico",
        base_dir / "assets" / "triad.png",
    ]
    for ic in icon_candidates:
        if ic.exists():
            app.setWindowIcon(QIcon(str(ic)))
            break

    window = MainWindow(
        registry=registry,
        discovery_service=discovery,
        window_manager=window_manager,
        database=database,
        message_bridge=message_bridge,
        session_manager=session_manager,
    )
    window.show()

    logger.info("TRIAD UI event loop running.")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
