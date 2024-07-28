# CarFigures - The Better Alternative

![CarFigures Logo](assets/logos/Banner.png)
[![Array's Profile](https://img.shields.io/badge/Array's%20Profile-ffffff?style=for-the-badge&logo=github&logoColor=black)](https://github.com/arrayunderscore/)
[![Discord.py](https://img.shields.io/badge/Discord.py-ffffff?style=for-the-badge&logo=python&logoColor=blue)](https://python.org)
[![Pull Requests](https://img.shields.io/badge/Pull_Requests-white?style=for-the-badge&logo=git&logoColor=F1502F)](https://github.com/arrayunderscore/CarFigures/pulls)
[![Top.gg](https://img.shields.io/badge/Top.gg-white?style=for-the-badge&logo=top.gg&logoColor=ff3366)](https://top.gg/bot/1127506544578277446)
[![Server Invite](https://img.shields.io/badge/Server_Invite-white?style=for-the-badge&logo=discord&logoColor=7289da&)](https://discord.gg/PVFyN34ykA)

<h2>
     <sub>
          <img  src="https://www.iconsdb.com/icons/preview/white/bookmark-2-xxl.png"
            height="25"
            width="25">
     </sub>
     History
</h2>

**CarFigures (CF Project)** was born out of frustration with the decisions of the BallsDex team. I didn't really like the idea at first; it was more of a reaction to dissatisfaction. The BallsDex team wasn't very keen on implementing the features that most of us wanted. I knew that just complaining wouldn't lead to any changes, because hundreds of people had already done it to no avail.

Determined to make a difference, I decided to take matters into my own hands. By forking BallsDex and implementing my own changes and preferences, CarFigures was born.

CarFigures aims to address the community's frustrations and provide an alternative foundation to use and build upon their bots. It is a project driven by a desire for improvement and a commitment to providing a better user experience.

<h2>
     <sub>
          <img  src="https://www.iconsdb.com/icons/preview/white/download-2-xxl.png"
            height="25"
            width="25">
     </sub>
     Installation
</h2>

## Prerequisites

Before starting the installation, ensure you have the following softwares installed:

- Git: Used for cloning the project and updating your bot to the latest versions. Download Git [here.](https://git-scm.com/downloads)
- Docker Desktop: Provides an easy way to run your bot in isolated containers. Download Docker Desktop [here.](https://www.docker.com/products/docker-desktop)
- Discord Bot: Required to create and manage your bot on Discord. Create your own Discord bot [here.](https://discord.com/developers/applications)

> **Note:** If you are using Linux as your main desktop or hosting the bot on a Linux server, it is generally better to use [Docker Engine](https://docs.docker.com/engine/install) rather than Docker Desktop.

### Installing

Ensuring you have all the softwares installed and configured, continue reading!

1. Open any terminal of your choice and `git clone` the project: ![demo1](assets/demos/demo1.png)
2. To make it easier for you to know which is which in Docker, change the bot folder name from "CarFigures" to the name of your dex/figures bot (very useful if you work with multiple dexes/figures bots).

> **Note:** The `settings.toml` file isn't updated by default when updating the bot files, you are required to check if any changes happened to the file by yourself. The link will be updated every time an update is released, it is your responsibility to follow.

<h2>
     <sub>
          <img  src="https://www.iconsdb.com/icons/preview/white/settings-11-xxl.png"
            height="25"
            width="25">
     </sub>
     Configuration File
</h2>

CarFigures are designed to be highly customizable, allowing you to customize the bot's behavior and appearance to your liking. You can create your own configuration file to edit various settings, commands, and more!

It's part of CarFigures' philosophy to make customizing your sample as easy as possible. Not too much for now, but I plan on more soon! :3

## Creating The Settings File

- In your bot files, create a new file called `settings.toml`.
![demo2](assets/demos/demo2.png)

Here’s a brief overview of the main configuration sections:

- **[settings]**: General bot settings, such as the bot token and command prefix.
- **[owners]**: Configuration for bot owners and co-owners.
- **[appearance]**: Customizable namings in the bot interface.
- **[commands.groups]**: Names of command groups.
- **[commands.names]**: Names of individual commands.
- **[commands.descs]**: Descriptions of individual commands.
- **[info.links]**: Links to various resources related to the bot.
- **[info.about]**: Information about the project and contributors.
- **[superuser]**: Settings for superuser commands.
- **[prometheus]**: Settings for Prometheus metrics collection.

```markdown
# Configuration file for CarFigures Discord Bot

[settings]
bot_token = ""
bot_name = "CarFigures"
text_prefix = "c."
max_favorites = 50
spawnalert = true
profile_emojis = true
# Default embed color in the bot (hex without #)
default_embed_color = "5865F2"

[owners]
# If enabled and the application is under a team, all team members will be considered as owners
team_members_are_owners = false

# A list of IDs that must be considered owners in addition to the application/team owner
# Separate IDs with commas (,)
co_owners = [877557616094638112]

[appearance]
collectible_name = "carfigure"
cartype = "CarType"
country = "Country"
horsepower = "Horsepower"
weight = "Weight"
kg = "KG"
hp = "HP"

[commands.groups]
cars = "cars"
sudo = "sudo"
info = "info"
player = "player"
server = "server"
trade = "trade"

[commands.names]
garage = "garage"
exhibit = "exhibit"
show = "show"
info = "info"
last = "last"
favorite = "favorite"
give = "give"
count = "count"
rarity = "rarity"
compare = "compare"

[commands.descs]
garage = "Show Your garage!"
exhibit = "Show your showroom in the bot."
show = "Display info from your carfigures collection."
info = "Display info from a specific carfigure."
last = "Display info of your or another user's last caught carfigure."
favorite = "Set favorite carfigures."
give = "Give a carfigure to a user."
count = "Count how many carfigures you have."
rarity = "Show the rarity list of the bot."
compare = "Compare two carfigures."

[info.links]
repository_link = "https://codeberg.org/array_ye/CarFigures"
discord_invite = "https://discord.com/invite/PVFyN34ykA"
terms_of_service = "https://codeberg.org/array_ye/CarFigures/src/branch/stable/assets/TERMS_OF_SERVICE.md"
privacy_policy = "https://codeberg.org/array_ye/CarFigures/src/branch/stable/assets/PRIVACY_POLICY.md"
top_gg = "https://top.gg/bot/1127506544578277446"

[info.about]
description = """
CarFigures (CF) was born out of frustration with the BallsDex team's decisions. Initially, I had no particular liking for the idea; it was more about a response to dissatisfaction. The BallsDex team wasn't keen on implementing features that many of us wanted. I knew that merely complaining wouldn't lead to any change, as hundreds of others had already done so to no avail.

Determined to make a difference, I decided to take matters into my own hands. By forking BallsDex and applying my own changes and preferences, CarFigures came into existence.

CarFigures aims to address the community's frustrations and provide an alternative base to use and build their bots on. It's a project driven by a desire for improvement and a commitment to providing a better user experience.
"""
history = ""

# While this is made to make it easier to include yourself and your team/contributors
# you are NOT allowed to remove El Laggron or Array_YE.
# Separate names with commas (,)
developers = [
    "El Laggron",
    "Array_YE",
]
contributors = [
    "Queen_the_darkner",
    "HiboMan",
    "KingOfTheHill4965",
    "DistinguishedAxolotl"
]

[superuser]
# List of guild IDs where the /sudo command should be registered
# Separate IDs with commas (,)
guild_ids = [1127508116150439958]

# List of role IDs having full access to /sudo
# Separate IDs with commas (,)
root_role_ids = [1127523232933756958]

# List of role IDs having partial access to /sudo (blacklist and guilds)
# Separate IDs with commas (,)
superuser_role_ids = [1206246119043244122]

# Log channel ID for Admin Commands logging
log_channel = 1144639514296459316

[prometheus]
# Enable Prometheus metrics collection (default: false)
enabled = false
# Host for Prometheus metrics (default: 0.0.0.0)
host = "0.0.0.0"
# Port for Prometheus metrics (default: 15260)
port = 15260

```

<h2>
     <sub>
          <img  src="https://www.iconsdb.com/icons/preview/white/arrow-150-xl.png"
            height="30"
            width="30">
     </sub>
     Booting The Bot
</h2>
After configuring and editing the settings file, it's time to start the bot instance and configure it!

1. Start by getting Docker Desktop up and running, then open your file explorer and head to the bot files. ![demo3](assets/demos/demo3.png)

<details>
<summary><strong>For Windows Users</strong></summary>

To access the command prompt in this bot folder go to the navigation bar and edit it (you can do this by clicking once on the empty part)i type `cmd` or `powershell` and press enter, this will open a new command prompt instead of the bot one, for example:
![demo4](assets/demos/demo4.png)
![demo5](assets/demos/demo5.png)

- After opening the terminal or command prompt, you shall be greeted with something like this (don't mind the toml thing, it's git stuff).
![demo6](assets/demos/demo6.png)
Now its time for you to build the project image (the image the contains your database which stores all your bot's progress, the code and more) using `docker compose build`.
![demo7](assets/demos/demo7.png)
=======

Start by getting the Docker Desktop up and running, then open your file explorer and head to the bot files. ![demo4](assets/demos/demo3.png)

And now, it is time to start up your bot!
Using `docker compose up` will make the docker start all the containers and functions, creating connections to Discord's APIs, and allowing the bot to be online!
And after doing it, the final results should be like this, with the end line saying "(your bot name) is now operational!"
![demo8](assets/demos/demo8.png)

</details>

<details>
<summary><strong>For macOS/Linux Users</strong></summary>

You should just cd to the place (the function used to navigate to a folder), open a terminal and cd to the folder, if your bot folder is in the documents folder, usually you can do `cd ~/Documents/(your bot folder name)`.

After opening the terminal or command prompt, you shall be greeted with something like this (don't mind the toml thing, it's git stuff).
![demo6](assets/demos/demo6.png)
Now its time for you to build the project image (the image the contains your database which stores all your bot's progress, the code and more) using `docker compose build`.
![demo7](assets/demos/demo7.png)

And now, its time to start up your bot!
Using `docker compose up` will make the docker starts all the containers and functions to start making connections to Discord's API's, allowing the bot to be online!
And after doing it, the final results should be like this, with the end line saying "(your bot name) is now operational!"
![demo8](assets/demos/demo8.png)
</details>

That's it! You're ready to rock and roll with CarFigures. If you run into any issues, don't hesitate to [ask for help.](https://discord.gg/UX3jEPy6YH) We're here to make sure you have a smooth ride.

<h2>
     <sub>
          <img  src="https://www.iconsdb.com/icons/preview/white/plus-5-xxl.png"
            height="25"
            width="25">
     </sub>
     Contributing
</h2>

If you want to contribute to this project, continue reading!

### How to Contribute

There are several ways you can contribute to the CarFigures Project:

1. **Open Issues:** Found a bug or have a feature request? Open an issue to let us know. This helps us identify and fix issues or consider new features.

2. **Help Us with Documentation:** Improve the documentation to make it easier for others to get started and understand the project. This includes tutorials, guides, and updating the README.md file.

3. **Submit Pull Requests:** Fix bugs, add features, or improve existing code. See below for instructions on submitting a pull request.

4. **Provide Feedback:** Test the project and provide feedback on your experience. This helps us understand what works well and what needs improvement.

5. **Publish the Project:** Share the project with others who might want to use it or contribute.

6. **Join Discussions:** Participate in discussions on GitHub issues or the Discord server to help shape the future direction of the project.

<details>
<summary><strong>How To Open An Issue</strong></summary>

1. Go to the "Issues" section of the repository.

2. Click on the "New Issue" button.

3. Provide a clear and descriptive title for the issue.

4. Include detailed information in the body, such as steps to reproduce the bug or a detailed description of the feature request. We recommend you to use the labels while creating an issue!

</details>

<details>
<summary><strong>How To Help With Documentations</strong></summary>

1. Fork the repository to your GitHub account.

2. Create a new branch for your documentation changes: `git checkout -b improve-docs`

3. Make your changes and commit them with descriptive messages: `git commit -m 'Improve documentation for installation process'`

4. Push your changes to your branch: `git push origin improve-docs`

5. Open a pull request (PR) against the stable branch of the original repository.

</details>

<details>
<summary><strong>How To Submit Features/Bugs</strong></summary>

1. Fork the repository to your GitHub account.

2. Create a new branch for your feature or bug fix: `git checkout -b new-feature`

3. Make your changes and commit them with descriptive messages: `git commit -m 'Add new feature'`

4. Push your changes to your branch: `git checkout -b new-feature`
Open a pull request (PR) against the upstream branch of the original repository.

</details>

### Pull Request (PR) Guidelines

To make sure your PR can be checked and merged smoothly, please follow these guidelines:

- Clearly explain the purpose of the PR and the changes made. This will make it easier to review the PR. I usually don't reject them, but more clarity = faster response.
- Provide tests and documentation for any new features or changes to functionality. It's always a good practice to debug the code before shipping it.
- Include screenshots of the visual before/after changes if possible. This can make it easier for me to review things, but I also like reading changes, so don't worry about this part.
- Make sure all current tests pass without errors.
- Make sure your code complies with the project's coding standards and style, because code that doesn't match the project's style makes my review weird and I end up formatting it to look like the rest of the codebase, so please save me some time.
- Go with as few line changes and commits as possible, this will be easier to track and verify, allowing me to quickly review it and give minor comments if needed.

### Code of Conduct

We are all about creating a welcoming and chill community.
Everyone who contributes is expected to stick to the [Code of Conduct](./assets/CODE_OF_CONDUCT.md) when getting involved with the project and its community members.

### Help and Feedback

- If you need help, have questions, or want to share your thoughts, don't hesitate to open an issue or ask about it in the dev category inside the CarFigures Discord server. I'm here to support you every step of the way.

- I'm stoked about every contribution from the community. Let's join forces and make the project even more rad!

> **Note:** For access to the developer category in the CarFigures Discord server, inform me that you are making a bot using CarFigures, and I will assign you the forker role.

<h2>
     <sub>
          <img  src="https://www.iconsdb.com/icons/preview/white/map-3-xl.png"
            height="25"
            width="25">
     </sub>
     Road Map
</h2>

I'm excited about the future of the project and all the bots that use it! Here are some features and improvements I have planned:

### Upcoming Features

- Economy and Modifying Packages.
- Server/Player Settings Embed
- Leaderboard Embed + Controls
- Crafting Commands | Customizable Through The Admin Panel
- Racing/Battling Package

### Future Plans

- Switch from fastapi_admin to our own tech-stack.
- Implement a premium plan inside CF.
- Combine some existing commands into one (e.g., /user privacy and /user donation policy into /user settings)

<h2>
     <sub>
          <img  src="https://www.iconsdb.com/icons/preview/white/heart-xl.png"
            height="25"
            width="25">
     </sub>
     Final Thoughts
</h2>

I am incredibly grateful to everyone who contributes to The CF Project. Whether you provide code, suggest features, report bugs, or offer emotional support, your efforts are deeply appreciated. Knowing I am not alone in this project and having a supportive community means the world to me.

Thank you all from the bottom of my heart ❤️ (especially you, Peri :3 ❤️).

Let's continue making this project an awesome and valuable project for everyone!
