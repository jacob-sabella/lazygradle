import logging
from gradle.gradle_manager import GradleManager
from ui.lazy_gradle_app import LazyGradleApp

# Configure logging to file only - no console output to avoid interfering with TUI
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("lazygradleapp.log")  # Log to a file only
    ],
)


def main():
    gradle_manager = GradleManager()
    LazyGradleApp(gradle_manager).run()


if __name__ == "__main__":
    main()
