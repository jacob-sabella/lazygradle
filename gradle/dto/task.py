class Task:
    """
    Represents a single Gradle task, including its name and description.
    """
    def __init__(self, name: str, description: str) -> None:
        self.name: str = name
        self.description: str = description
