<a id="readme-top"></a>

<!-- PROJECT SHIELDS -->
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <h3 align="center">LazyGradle</h3>

  <p align="center">
    A beautiful TUI for managing and running your Gradle tasks
    <br />
    <a href="#usage"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="#usage">View Demo</a>
    ·
    <a href="https://github.com/jsabella/lazygradle/issues/new?labels=bug&template=bug-report---.md">Report Bug</a>
    ·
    <a href="https://github.com/jsabella/lazygradle/issues/new?labels=enhancement&template=feature-request---.md">Request Feature</a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->
## About The Project

LazyGradle is a Terminal User Interface (TUI) application that provides a user-friendly, interactive interface for managing and running Gradle tasks. Say goodbye to memorizing complex Gradle commands and hello to an intuitive, keyboard-driven workflow.

**Key Features:**
* Manage multiple Gradle projects from a single interface
* View all available tasks with descriptions at a glance
* Execute tasks with or without parameters
* Real-time streaming output for task execution
* Persistent configuration across sessions
* Dark mode support
* Fast, keyboard-driven navigation

LazyGradle is perfect for developers who work with multiple Gradle projects and want a faster, more visual way to interact with their build system without leaving the terminal.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Built With

* [![Python][Python-badge]][Python-url]
* [![Textual][Textual-badge]][Textual-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->
## Getting Started

To get LazyGradle up and running on your local machine, follow these simple steps.

### Prerequisites

* Python 3.13 or higher
* A Gradle project (with `gradlew` wrapper or system `gradle` installed)

### Installation

1. Clone the repository
   ```sh
   git clone https://github.com/jsabella/lazygradle.git
   ```
2. Navigate to the project directory
   ```sh
   cd lazygradle
   ```
3. Create and activate a virtual environment
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. Install dependencies
   ```sh
   pip install -r requirements.txt
   ```
5. Run the application
   ```sh
   python app.py
   ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- USAGE EXAMPLES -->
## Usage

### First Launch

When you first launch LazyGradle, you'll need to add a Gradle project:

1. Press `p` to open the project chooser
2. Add your Gradle project directory
3. LazyGradle will automatically detect and cache all available tasks

### Keyboard Shortcuts

* `p` - Open project chooser (switch between projects or add new ones)
* `d` - Toggle dark mode
* `r` - Run the selected task
* `R` - Run the selected task with custom parameters
* `Tab` / `Shift+Tab` - Navigate between UI elements
* `↑` / `↓` - Navigate task list

### Running Tasks

1. Select a task from the list on the left
2. View the task description on the right
3. Press `r` to run, or `R` to run with parameters
4. Watch the real-time output in the output panel

### Managing Projects

LazyGradle stores your project configurations in `~/.config/lazygradle/gradle_cache.json`, so your projects and their task lists are remembered between sessions.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ROADMAP -->
## Roadmap

- [x] Basic task listing and execution
- [x] Multi-project support
- [x] Real-time output streaming
- [x] Task parameters support
- [ ] Search/filter tasks
- [ ] Task favorites/bookmarks
- [ ] Task execution history
- [ ] Custom task aliases
- [ ] Configuration export/import

See the [open issues](https://github.com/jsabella/lazygradle/issues) for a full list of proposed features (and known issues).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTACT -->
## Contact

Your Name - [@your_twitter](https://twitter.com/your_twitter) - your.email@example.com

Project Link: [https://github.com/jsabella/lazygradle](https://github.com/jsabella/lazygradle)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

* [Textual](https://textual.textualize.io/) - The amazing TUI framework that powers LazyGradle
* [Best-README-Template](https://github.com/othneildrew/Best-README-Template) - For this README template
* [Shields.io](https://shields.io/) - For the badges

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
[contributors-shield]: https://img.shields.io/github/contributors/jsabella/lazygradle.svg?style=for-the-badge
[contributors-url]: https://github.com/jsabella/lazygradle/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/jsabella/lazygradle.svg?style=for-the-badge
[forks-url]: https://github.com/jsabella/lazygradle/network/members
[stars-shield]: https://img.shields.io/github/stars/jsabella/lazygradle.svg?style=for-the-badge
[stars-url]: https://github.com/jsabella/lazygradle/stargazers
[issues-shield]: https://img.shields.io/github/issues/jsabella/lazygradle.svg?style=for-the-badge
[issues-url]: https://github.com/jsabella/lazygradle/issues
[license-shield]: https://img.shields.io/github/license/jsabella/lazygradle.svg?style=for-the-badge
[license-url]: https://github.com/jsabella/lazygradle/blob/main/LICENSE
[Python-badge]: https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white
[Python-url]: https://www.python.org/
[Textual-badge]: https://img.shields.io/badge/Textual-000000?style=for-the-badge&logo=python&logoColor=white
[Textual-url]: https://textual.textualize.io/
