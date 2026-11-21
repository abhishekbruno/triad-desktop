import sys
from PySide6.QtWidgets import QApplication

from app.core.agent_registry import AgentRegistry
from app.core.app_discovery import AppDiscoveryService
from app.core.message_bridge import MessageExchangeBridge
from app.core.window_manager import WindowManager
from app.storage.database import DatabaseManager
from app.ui.main_window import MainWindow
from app.utils.logging import get_logger, setup_logging


def main() -> int:
    """Entry point for the TRIAD Desktop Workspace."""
    setup_logging()
    logger = get_logger("main")
    logger.info("Initializing TRIAD Desktop Workspace (Phase 1 & 2)...")

    # Initialize Core Subsystems
    database = DatabaseManager()
    registry = AgentRegistry()
    discovery = AppDiscoveryService()
    window_manager = WindowManager()
    message_bridge = MessageExchangeBridge(
        registry=registry,
        window_manager=window_manager,
        database=database,
    )

    # Launch PySide6 GUI Application
    app = QApplication(sys.argv)
    app.setApplicationName("TRIAD Local AI Workspace")
    app.setOrganizationName("TRIAD Project")

    window = MainWindow(
        registry=registry,
        discovery_service=discovery,
        window_manager=window_manager,
        database=database,
        message_bridge=message_bridge,
    )
    window.show()

    logger.info("TRIAD UI event loop running.")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
