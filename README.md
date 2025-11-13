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
  <h3 align="center">lazygradle</h3>

  <p align="center">
    A TUI for managing and running your Gradle tasks
    <br />
    <a href="#usage"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/jacob-sabella/lazygradle/issues/new?labels=bug&template=bug-report---.md">Report Bug</a>
    ·
    <a href="https://github.com/jacob-sabella/lazygradle/issues/new?labels=enhancement&template=feature-request---.md">Request Feature</a>
  </p>
</div>

<!-- ABOUT THE PROJECT -->

## About The Project

LazyGradle is a Terminal User Interface (TUI) application for managing and running Gradle tasks.

![Main Interface](screenshots/home_screen.png)
_Main interface showing task list and details_

![Project Manager](screenshots/project_manager.png)
_Manage multiple Gradle projects_

![Run Gradle Tasks](screenshots/run_gradle_task.png)
_Run Gradle tasks_

![Run Gradle Tasks w/ Parameters](screenshots/run_task_with_parameters.png)
_Run Gradle tasks with parameters_

**Features:**

- Manage multiple Gradle projects
- View all available tasks with descriptions
- Run tasks with or without parameters
- Real-time task output streaming
- Configuration persistence
- Dark mode
- Keyboard navigation
- Task execution history tracking

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Built With

- [![Python][Python-badge]][Python-url]
- [![Textual][Textual-badge]][Textual-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->

## Getting Started

To get LazyGradle up and running on your local machine, follow these simple steps.

### Prerequisites

- Python 3.13 or higher
- A Gradle project (with `gradlew` wrapper or system `gradle` installed)

### Installation

#### Via pip

`pip install lazygradle`

#### Manually

1. Clone the repository

   ```sh
   git clone https://github.com/jacob-sabella/lazygradle.git
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

- `p` - Open project chooser (switch between projects or add new ones)
- `d` - Toggle dark mode
- `r` - Run the selected task
- `R` - Run the selected task with custom parameters
- `Tab` / `Shift+Tab` - Navigate between UI elements
- `↑` / `↓` - Navigate task list

### Running Tasks

1. Select a task from the list on the left
2. View the task description on the right
3. Press `r` to run, or `R` to run with parameters
4. Watch the real-time output in the output panel

### Managing Projects

LazyGradle stores your project configurations in `~/.config/lazygradle/gradle_cache.json`, so your projects and their task lists are remembered between sessions.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ROADMAP -->

## Contributing

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

## Acknowledgments

- [Textual](https://textual.textualize.io/) - The amazing TUI framework that powers LazyGradle
- [Best-README-Template](https://github.com/othneildrew/Best-README-Template) - For this README template
- [Shields.io](https://shields.io/) - For the badges

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## AI Usage in Development

The ability to get this project to a usable state in my free time was definitely made possible through the help of Generative AI tooling to assist with development. This has included the following.

- Claude Code (CLAUDE.MD file included in project)
- ChatGPT Web
- opencode

I do have plans to clean up much of the AI generated comments and code to graduate it a bit above "AI slop" status where its present, but it's certainly been a higher priority for me to get something working and usable for my other purposes (which is primarily Sockbowl development).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->

[contributors-shield]: https://img.shields.io/github/contributors/jacob-sabella/lazygradle.svg?style=for-the-badge
[contributors-url]: https://github.com/jacob-sabella/lazygradle/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/jacob-sabella/lazygradle.svg?style=for-the-badge
[forks-url]: https://github.com/jacob-sabella/lazygradle/network/members
[stars-shield]: https://img.shields.io/github/stars/jacob-sabella/lazygradle.svg?style=for-the-badge
[stars-url]: https://github.com/jacob-sabella/lazygradle/stargazers
[issues-shield]: https://img.shields.io/github/issues/jacob-sabella/lazygradle.svg?style=for-the-badge
[issues-url]: https://github.com/jacob-sabella/lazygradle/issues
[license-shield]: https://img.shields.io/github/license/jacob-sabella/lazygradle.svg?style=for-the-badge
[license-url]: https://github.com/jacob-sabella/lazygradle/blob/main/LICENSE
[Python-badge]: https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white
[Python-url]: https://www.python.org/
[Textual-badge]: https://img.shields.io/badge/Textual-000000?style=for-the-badge&logo=python&logoColor=white
[Textual-url]: https://textual.textualize.io/
