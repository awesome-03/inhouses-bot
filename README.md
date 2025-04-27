# Inhouse Bot

In our [Discord community](https://discord.gg/inhouses), we refer to custom Valorant 10-mans as "Inhouses". This bot was initially created to assign rank roles for game balancing during these inhouses. However, as new needs arose, the bot evolved with additional features to enhance the overall server experience.

## Features

### Rank Assignment:
- Assign your Valorant account's rank role using the `set_rank ign:[name#tag]` command.
  - To remove the rank icon, simply use the `/remove_rank` command.
- This feature is powered by the [Unofficial Valorant API](https://github.com/Henrik-3/unofficial-valorant-api) created by Henrik-3.

### Auto-Reactions:
- Auto-reactions are reactions that are automatically added to messages from users who have them. They can be used as rewards for server events. To avoid flooding the chat, a small cooldown has been added between reactions.
- Reactions can be added by moderators using the `/add_reaction user:[@mention user] reaction:[:emoji name:]` command.
  - To remove a reaction, use the `/remove_reaction user:[@mention user] reaction:[:emoji name:]` command.
  - A list of all active reactions can be obtained with the `/list_reactions` command.

### Text Commands:
- Text commands are automated messages that users can trigger by typing specific words. They work like any other bot's commands.
- The bot's prefix is set to `!`, so an example of usage would be `!commandName`.
- Moderators can add new text commands using the `/add_command new_command:[command name] command_message:[message]` command.
  - To remove a command, use the `/remove_command command:[command name]` command.

## Setting Up the Bot

Here is a simplified guide to setting up the bot:

1. Clone the repository.
2. Create a virtual environment and activate it.
3. Install the dependencies by running `pip install -r requirements.txt`. *(Python 3.13 or higher is needed to install everything)*.
4. Create a `.env` file and follow the template provided in the `.env.example` file.
5. Create a directory named `logs`.

### Required Discord Roles:
For the bot to work correctly, the following roles must be set up on your server:

1. For the inhouse ping feature (with a 1-hour cooldown to prevent spam): "Inhouse Ping".
2. For the rank assignment feature, you need to create all Valorant rank roles, such as:
   - "Unrated", "Iron 1", "Iron 2", "Iron 3", "Bronze 1", "Bronze 2", "Bronze 3", "Silver 1", "Silver 2", "Silver 3", "Gold 1", "Gold 2", "Gold 3", "Platinum 1", "Platinum 2", "Platinum 3", "Diamond 1", "Diamond 2", "Diamond 3", "Ascendant 1", "Ascendant 2", "Ascendant 3", "Immortal 1", "Immortal 2", "Immortal 3", "Radiant".

Once these steps are completed, you should be able to run `main.py`. *(Note: There's a small chance I missed a step)*
