# CarFigures - The Different Experience.

![CarFigures Logo](assets/logos/Banner.png)
[![Array's Profile](https://img.shields.io/badge/Array's%20Profile-ffffff?style=for-the-badge&logo=github&logoColor=black)](https://github.com/arrayunderscore/)
[![Discord.py](https://img.shields.io/badge/Discord.py-ffffff?style=for-the-badge&logo=python&logoColor=blue)](https://python.org)
[![Pull Requests](https://img.shields.io/badge/Pull_Requests-white?style=for-the-badge&logo=git&logoColor=F1502F)](https://github.com/arrayunderscore/CarFigures/pulls)
[![Top.gg](https://img.shields.io/badge/Top.gg-white?style=for-the-badge&logo=top.gg&logoColor=ff3366)](https://top.gg/bot/1127506544578277446)
[![Server Invite](https://img.shields.io/badge/Server_Invite-white?style=for-the-badge&logo=discord&logoColor=7289da&)](https://discord.gg/PVFyN34ykA)

<h2>
     <sub>
          <img  src="https://www.iconsdb.com/icons/preview/white/download-2-xxl.png"
            height="25"
            width="25">
     </sub>
     Installation
</h2>

### Prerequisites
Before starting the installation, ensure you have the following tools installed:

- Git: Used for cloning the project and updating your bot to the latest versions. [Download Git](https://git-scm.com/downloads)
- Docker Desktop: Provides an easy way to run your bot in isolated containers. [Download Docker Desktop](https://www.docker.com/products/docker-desktop).
- Discord Bot Instance: Required to create and manage your bot on Discord. [Create a Discord Bot](https://discord.com/developers/applications).
- TextEditor: Used for editing the code/config file, if you don't know which one to use, I recommend using [Visual Studio Code](https://code.visualstudio.com/).
- Terminal: Used for executing commands inside a shell.
- - if you use Windows, I recommend using [Windows Terminal](https://apps.microsoft.com/detail/9n0dx20hk701?hl=en-US&gl=US) or [Fluent Terminal](https://apps.microsoft.com/detail/9p2krlmfxf9t?hl=en-us&gl=US).
- - if you use Unix-like OS, just use your favorite terminal.

> **Note:** If you are using Linux as your main desktop (like me) or hosting the bot on a Linux server, it is generally better to use [Docker Engine](https://docs.docker.com/engine/install).

### Installing
Now since all this is done, let's start!

Open a new terminal, and clone the project using git!
Git gives you the ability to clone the project inside a new folder it creates with the name you specify, like:
```bash
git clone https://github.com/thecfproject/CarFigures showerdex
```

> **Note:** The config.toml isn't updated by default when updating the bot files, you are required to check if any changes happened to the toml file by yourself, it's your responsibility.
 
<h2>
     <sub>
          <img  src="https://www.iconsdb.com/icons/preview/white/settings-11-xxl.png"
            height="25"
            width="25">
     </sub>
     Configuration
</h2>

CarFigures is designed to be highly customizable, allowing you to tailor the bot's behavior and appearance to your liking,
this is part of CF's philosophy to make customizing your instance as easy as possible.

Now, time to start making that file, Open VisualStudio Code or any other text edtior, then open the bot folder in vscode.\
inside vscode, create a new file called config.toml, and start configuring the bot, 
read the comments I left in there to help you out!

```toml
[settings]
botToken = ""
botDescription = "Catch, collect and exchange cars in your server!"
botName = "CarFigures"
prefix = "!"
maxFavorites = 50
defaultEmbedColor = "5865F2"

[spawn-manager]
requiredMessageRange =  [22, 55] # The required number of messages to be sent after the cooldown to spawn.
spawnMessages = [
    { message = "A wild carfigure has appeared!", rarity = 10 },
    { message = "A blizzard blows in, and with it comes a carfigure!", rarity = 5 },
    { message = "A drop hsa been spotted, and it has a carfigure inside it!", rarity = 2 },
    { message = "Think fast chucklenutts!", rarity = 1 }
]
catchButtonMessages = [
    { message = "Catch Me!", rarity = 10 },
    { message = "Catch This Car!", rarity = 8 },
]
wrongNameMessages = [
    { message = "Wrong Name!", rarity = 10 },
    { message = "Try again!", rarity = 8 },
    { message = "Lol one more time!", rarity = 4 },
    { message = "Damn, should have taken your time!", rarity = 2 }
]
catchBonusRate = [-50, 50]
cooldownTime = 600 # in seconds
minimumMembersRequired = 20

[team]
# This section is meant for administrator commands logging and staff purposes.

# A list of IDs that must be considered owners in addition to the application/team owner.
# Separate IDs with commas (,)
roots = [877557616094638112]

# List of guild IDs where the /sudo command should be registered
# and a list of role IDs that have access to the command.
# Separate IDs with commas (,).
superGuilds = [1289731116525158463]
superUsers = [1290970226627842079]

# Log channel ID for Admin commands logging.
logChannel = 1319049297341452349


[appearance.interface]
collectible = { singular = "carfigure", plural = "carfigures" } # Must be lowercased.
album = "CarType"
country = "Country"
exclusive = "Exclusive"
horsepower = { name = "Horsepower", unit = "atk" }
weight = { name = "Weight", unit = "hp"}

[appearance.commands]
cars = "cars"
sudo = "sudo"
garage = { name = "garage", desc = "Show your garage!" }
exhibit = { name = "exhibit", desc = "Show your showroom in the bot." }
show = { name = "show", desc = "Display info from your carfigures collection." }
info = { name = "info", desc = "Display info for a specific carfigure." }
gift = { name = "gift", desc = "Give a carfigure to a user." }

[information]
## This section is also one of bot's main factures that provides information about the bot which can help others to find more information about the bot.

repositoryLink = "https://github.com/The-CF-Project/CarFigures"
serverInvite = "https://discord.com/invite/PVFyN34ykA"
termsOfService = "https://github.com/thecfproject/CarFigures/blob/upstream/assets/TERMS_OF_SERVICE.md"
privacyPolicy = "https://github.com/thecfproject/CarFigures/blob/upstream/assets/PRIVACY_POLICY.md"

# While this is made to make it easier to include yourself and your team/contributors
# you are NOT allowed to remove El Laggron or Array_YE.
# Separate names with commas (,).
developers = [
    "El Laggron",
    "JRuntime",
]
contributors = [
    "ArielAram",
    "HiboMan",
]

[prometheus] # If you don't know what does this do, don't touch it.
enabled = false
host = "0.0.0.0"
port = 15260
```

<h2>
     <sub>
          <img  src="https://www.iconsdb.com/icons/preview/white/arrow-150-xl.png"
            height="30"
            width="30">
     </sub>
     Booting
</h2>
After configuring and editing the config.toml file, it's time to start the bot instance and play with it!

Start by getting docker desktop/engine up and running, then open your file explorer and head to the bot files.

if you are using Windows, just right click the project folder and select (Open in Terminal).\
if you use a Unix-like Os, you should just cd to the place, open a terminal and cd to the folder location.

Now it's time for you to build the project image (the image of the containers like the database and bot's code/panel) using `docker compose build`.
![demo1](assets/demos/demo1.png)

And now, using `docker compose up` will make the docker start all the containers!
And after doing it, the final results should be like this, with the end line saying "(your bot name) is now operational!"
which means, your bot is now running with no issues!
![demo2](assets/demos/demo2.png)

If you need help, have questions, or want to share your thoughts, don't hesitate to reach out!\
You can open an issue or ask about it in the dev category inside the discord server.

<h2>
     <sub>
          <img  src="https://www.iconsdb.com/icons/preview/white/plus-5-xxl.png"
            height="25"
            width="25">
     </sub>
     Contributing
</h2>

Here's how you can jump in and help make this project even better:

### How to Contribute
There are several ways you can contribute to the CarFigures project:

1. **Open Issues:** Found a bug or have a feature request? Open an issue to let us know. This helps us identify and fix problems or consider new features.
2. **Help with Documentation:** Improve the documentation to make it easier for others to get started and understand the project. This includes tutorials, guides, and updating the README.
3. **Submit Pull Requests:** Fix bugs, add features, or improve existing code. See below for guidelines on how to submit a pull request.
4. **Provide Feedback:** Test the project and give feedback on your experience. This helps us understand what works well and what needs improvement.
5. **Spread the Word:** Share the project with others who might be interested in using or contributing to it.

<details>
<summary><strong>Opening Issues</strong></summary>

1. Go to the Issues section of the repository.
2. Click on the "New Issue" button.
3. Provide a clear and descriptive title for the issue.
4. Include detailed information in the body, such as steps to reproduce the bug or a detailed description of the feature request.
</details>

<details>
<summary><strong>Helping with Documentation</strong></summary>
 
1. Fork the repository to your GitHub account.
2. Create a new branch for your documentation changes: git checkout -b improve-docs
3. Make your changes and commit them with descriptive messages: git commit -m 'Improve documentation for installation process'
4. Push your changes to your branch: git push origin improve-docs
Open a pull request (PR) against the stable branch of the original repository.
</details>

<details>
<summary><strong>Submitting Features/Bug Fixes</strong></summary>

1. Fork the repository to your GitHub account.
2. Create a new branch for your feature or bug fix: git checkout -b new-feature
3. Make your changes and commit them with descriptive messages: git commit -m 'Add new feature'
4. Push your changes to your branch: git push origin new-feature
Open a pull request (PR) against the upstream branch of the original repository.
</details>

<h2>
     <sub>
          <img  src="https://www.iconsdb.com/icons/preview/white/map-3-xl.png"
            height="25"
            width="25">
     </sub>
     Roadmap
</h2>

I'm excited about the future of the project and all the bots that use it!

### Future Plans

- Switching From TortoiseORM | Fastapi to PrismaORM | In-House Panel!
- Migrating the base from Python to TypeScript!
- Have accessiblity Feature! e.g. Internationalization

<h2>
     <sub>
          <img  src="https://www.iconsdb.com/icons/preview/white/heart-xl.png"
            height="25"
            width="25">
     </sub>
     Final Thoughts
</h2>

I am incredibly grateful to everyone who contributes to The CF Project. Whether you provide code, suggest features, report bugs, or offer emotional support, your efforts are deeply appreciated. Knowing I am not alone in this project and having a supportive community means the world to me.

Thank you all from the bottom of my heart. ❤️ 
