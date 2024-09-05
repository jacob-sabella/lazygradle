import logging

from gradle.gradle_manager import GradleManager
from ui.lazy_gradle_app import LazyGradleApp

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler("lazygradleapp.log")  # Log to a file
    ]
)

if __name__ == "__main__":
    gradle_manager = GradleManager()
    LazyGradleApp(gradle_manager).run()
