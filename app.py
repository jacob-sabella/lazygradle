from gradle.gradle_manager import GradleManager
from logging_config import configure_logging
from ui.lazy_gradle_app import LazyGradleApp

configure_logging()


def main():
    gradle_manager = GradleManager()
    LazyGradleApp(gradle_manager).run()


if __name__ == "__main__":
    main()
