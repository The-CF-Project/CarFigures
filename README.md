# CarFigures - The Dex Bot for the Rest of Us

![CarFigures Logo](assets/Banner.png)
[![Lucrative Profile](https://img.shields.io/badge/Lucrative%20Profile-ffffff?style=for-the-badge&logo=codeberg&logoColor=black)](https://codeberg.org/Lucrative/)
[![Python](https://img.shields.io/badge/Discord.py-ffffff?style=for-the-badge&logo=python&logoColor=blue)](https://python.org)
[![Pull Requests](https://img.shields.io/badge/Pull_Request-white?style=for-the-badge&logo=git&logoColor=F1502F)](https://codeberg.org/Lucrative/CarFigures/pulls)
[![Top.gg](https://img.shields.io/badge/Top.gg-white?style=for-the-badge&logo=top.gg&logoColor=ff3366)]()
[![Server Invite](https://img.shields.io/badge/Server_Invite-white?style=for-the-badge&logo=discord&logoColor=7289da&)](https://discord.gg/PVFyN34ykA)

## Introduction

Welcome to CarFigures, the Discord bot for folks who love cars and car-related topics. Join us to discuss everything from classic cars to the latest automotive trends!

You can join our server and invite the bot from [here.](https://discord.com/api/oauth2/authorize?client_id=1127506544578277446&permissions=137439333376&scope=bot%20applications.commands)

## Why CarFigures is the Best Choice for Your Dex Bot Dreams

CarFigures isn't your typical fancy-pants Discord bot base. Here's why it's the bee's knees for your dex bot dreams:

- **No Tech Wizardry Needed**: You don't need to be a tech whiz to use CarFigures. We made it for regular folks like you and me.
- **Join the Fun**: You can jump right in, add your own flair, and make CarFigures your own. No stuffy suits telling you what to do here!
- **Get Help from Real People**: Stuck on something? Our crew is here to help. No bots pretending to be humans – just real, friendly folks.

So, if you're itching to make a dex bot without the headache, CarFigures is the way to go. It's all about having a good time and making something cool together.

## Getting Started with CarFigures

Hey there! Ready to dive into the world of CarFigures? Follow these simple steps to get the bot up and running using Docker and Docker Compose on Windows, macOS, and Linux:

### Prerequisites

- Make sure you have Docker and Docker Compose installed on your machine.

### Installation

1. Clone this repository to your local machine.
2. Create a `config.yml` file in the project directory with the required configuration settings, including your Discord bot token.
3. Open a terminal or command prompt and navigate to the project directory.

#### For Windows

- Run the following command to start the bot using Docker Compose:

     ```powershell
     docker compose up
     ```

#### For macOS and Linux

- Run the following command to start the bot using Docker Compose:

     ```bash
     sudo docker compose up
     ```

### Accessing the Bot and Admin Panel

Once you've completed the installation and configuration steps, the CarFigures bot will be up and running within the Docker environment. You can now access and interact with the bot on your Discord server.

That's it! You're all set to rock and roll with CarFigures using Docker and Docker Compose on Windows, macOS, and Linux. If you run into any trouble along the way, don't hesitate to reach out for help. We're here to make sure you have a smooth ride.

## How to Help Make CarFigures Even Better

Here's how you can jump in and help make this project even better:

### How to Contribute

1. Fork the repository to your CodeBerg account.
2. Create a new branch for your feature or bug fix: `git checkout -b new-feature`.
3. Make your changes and commit them with cool and descriptive messages: `git commit -m 'Add new feature'`.
4. Push your changes to your branch: `git push origin new-feature`.
5. Open a pull request (PR) against the `main` branch of the original repository.

### Pull Request (PR) Guidelines

To make sure your PR can be checked out and merged smoothly, please follow these guidelines:

- Clearly describe the purpose of the PR and the changes made.
- Provide tests and documentation for any new features or changes in functionality.
- If possible, include screenshots showing before/after states of any visual changes.
- Ensure that all existing tests pass without failure.
- Make sure your code follows the project's coding standards and vibes.

### Pull Request (PR) Notes

- **Small PRs are much more likely to be accepted** if they focus on a single topic. A good PR is about 20-40 lines of code.
- **Large PRs are less likely to be accepted** if they focus on multiple topics. A good PR is about 100-200 lines of code.
- **Complex PRs are less likely to be accepted** if they focus on multiple topics with fundamental changes. A good PR is about 300-2000 lines of code.
- **Chaotic PRs are less likely to be accepted** Its better to keep the PR concise and focused.
- **Stale PRs are less likely to be accepted** if they have been open for a long time and have not been merged, or if they have not been reviewed by the maintainers, reviewers, or community members, for reasons including no activity or no feedback.

### Code of Conduct

We're all about creating a welcoming and chill community. Everyone who contributes is expected to stick to the [Code of Conduct](./CODE_OF_CONDUCT.md) when getting involved with the project and its community members.

### Your First Contribution

If you're new to open source and repository hosting, we've tagged some issues as "good first issue" to help you get started. If you need a hand with the contribution process, hit us up – we're here to help.

### Help and Feedback

If you need help, have questions, or want to share your thoughts, don't hesitate to open an issue or reach out to the maintainers. We're here to support you every step of the way.

We're stoked about every contribution from the community. Let's join forces and make CarFigures even more rad!

## Roadmap and Future Plans

### Upcoming Features

- Economy and Modifying Packages.
- Guild Settings Embed
- User Settings Embed
- Leaderboard Embed + Controls
- Customizable Embeds
- Crafting Commands + Embeds + Customizable Through The Admin Panel
- Racing Package

### Future Plans

- Switch from fastapi_admin to our own tech-stack.
- Implement a premium plan inside CF.
- Remake some of the existing commands into 1 command. (/user privacy and /user donation policy into /user settings)
