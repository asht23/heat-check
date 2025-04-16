# Tools we need for the app
import streamlit as st
import pandas as pd
import plotly.express as px
import time # for slowdown for safety.
from datetime import datetime # figuring out what season’s games to pull

# NBA API Modules
from nba_api.stats.static import players # Get the list of NBA players to find player IDs
from nba_api.stats.endpoints import playergamelog # Used to pull game-by-game stats for a player

# Converting Player Name to NBA ID (used to pull their stats)
def find_player_id(name):
  all_players = players.get_players()
  for player in all_players:
    if player["full_name"].lower() == name.lower():
      return player['id']
  else:
    return None

# Pulling Recent Game Stats for a Player
def get_recent_stats(player_id, num_games):
  time.sleep(0.5)

  # April 2025 is still the 2024-25 season so use 2024 
  current_season = str(datetime.now().year - 1) if datetime.now().month < 10 else str(datetime.now().year)

  # Using the nba_api to fetch game-by-game stats for a specific player and season.
  gamelog = playergamelog.PlayerGameLog(player_id=player_id, season=current_season)
  stats_table = gamelog.get_data_frames()[0]
  stats_table = stats_table.head(num_games)[['GAME_DATE','PTS', 'REB', 'AST', 'FG_PCT']]
  stats_table = stats_table[::-1] # Flips from newest -> oldest to oldest -> newest

  return stats_table

# Gets NBA player headshot URL from player ID
def get_player_image_url(player_id):
    return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"

# Heating Up or Cooling Down Analysis
def analyze_trend(player_stats, player_name, selected_stats, recent_check):
    if len(player_stats) < recent_check + 1:
        st.warning(f"Not enough games to analyze trend for {player_name}.")
        return

    # Split into recent vs. baseline games
    recent_games = player_stats.tail(recent_check)
    baseline_games = player_stats.head(len(player_stats) - recent_check)

    # Calculate average for each group of games
    recent_avg = recent_games[selected_stats].mean()
    baseline_avg = baseline_games[selected_stats].mean()

    threshold = 0.05  # 5% change to count as hot/cold
    comments = []

    # Loop through each selected stat
    for stat in selected_stats:
        baseline_val = baseline_avg[stat]
        if baseline_val == 0:
            continue  # avoid division by zero

        diff = (recent_avg[stat] - baseline_val) / baseline_val

        if diff > threshold:
            comments.append(f"{stat}: Heating Up")
        elif diff < -threshold:
            comments.append(f"{stat}: Cooling Down")
        else:
            comments.append(f"{stat}: Stable")

    # Output results
    st.subheader(f"{player_name}'s Trend Analysis")
    for comment in comments:
        st.markdown(f"- {comment}")


#Building Streamlit UI Inputs

# Title and Description
st.title("NBA Player Heat Check?🔥")
st.markdown("See what NBA player's are Hot🔥 or Cold❄️ based on recent performances!") # Markdown is used for text customization

# Player name inputs
col1, col2 = st.columns(2)

with col1:
    player1 = st.text_input("Enter Player 1's Name")

with col2:
    player2 = st.text_input("Enter Player 2's Name (Optional)")

# How many recent games to look at
num_games = st.slider("How many recent games do you want to analyze?", min_value=1, max_value=20, value=5)

# What counts as 'recent' for hot/cold check
recent_check = st.slider(
    "Select how many recent games to analyze for 'Hot or Cold?'",
    min_value=1,
    max_value=num_games - 1,
    value=min(3, num_games - 1))

# Stat selector buttons
selected_stats = st.multiselect(
    "Pick which stats to graph",
    options=["PTS", "REB", "AST", "FG_PCT"],
    default=["PTS", "REB", "AST", "FG_PCT"])


if st.button('Analyze'):

  if player1:
    player1_id = find_player_id(player1) # Gets player 1's ID 
    
    if player2:
      player2_id = find_player_id(player2) # Gets player 2's ID
    else:
      player2_id = None # Sets player 2 to None so we know only one player is being analyzed

    if player1_id is None: # Show error if Player 1 name wasn't found
      st.error(f"❌ Player not found: {player1}")
    elif player2 and player2_id is None: # Show error if Player 2 name was entered but not found
      st.error(f"❌ Player not found: {player2}")
    else: # if both players are valid then continue
      with st.spinner("Pulling game stats..."):
        player1_stats = get_recent_stats(player1_id, num_games)  # Step 1: Get recent game stats for Player 1
        player1_stats["Player"] = player1 # Step 2: Add a "Player" column to label the data
        
        if player2_id:
                # Get recent stats for Player 2
          player2_stats = get_recent_stats(player2_id, num_games)
          player2_stats["Player"] = player2 # Add the Player 2 name as a column too

      # Show player headshots side-by-side
      img_col1, img_col2 = st.columns(2)

      with img_col1:
          st.image(get_player_image_url(player1_id), caption=player1, use_container_width=True)

      if player2_id:
          with img_col2:
              st.image(get_player_image_url(player2_id), caption=player2, use_container_width=True)

      # Show player stats in side by side
      stats_col1, stats_col2 = st.columns(2)

      with stats_col1:
          st.subheader(f"{player1}'s Stats")
          st.dataframe(player1_stats)
      if player2_id:
          with stats_col2:
              st.subheader(f"{player2}'s Stats")
              st.dataframe(player2_stats)

      # Trend Analysis
      analyze_trend(player1_stats, player1, selected_stats, recent_check)
      if player2_id:
          analyze_trend(player2_stats, player2, selected_stats, recent_check)

      # Plotting each player's stats
      plot_col1, plot_col2 = st.columns(2)

      with plot_col1:
          st.subheader(f"{player1}'s Stat Trends") 
          plot_df1 = player1_stats.melt(id_vars="GAME_DATE", value_vars=selected_stats, var_name="Stat", value_name="Value")
          fig1 = px.bar(plot_df1, x="GAME_DATE", y="Value", color="Stat", barmode="group")
          fig1.update_layout(title=f"{player1} - Last {num_games} Games", xaxis_title="Game Date", yaxis_title="Stat Value")
          st.plotly_chart(fig1)

      if player2_id:
          with plot_col2:
              st.subheader(f"{player2}'s Stat Trends")
              plot_df2 = player2_stats.melt(id_vars="GAME_DATE", value_vars=selected_stats, var_name="Stat", value_name="Value")
              fig2 = px.bar(plot_df2, x="GAME_DATE", y="Value", color="Stat", barmode="group")
              fig2.update_layout(title=f"{player2} - Last {num_games} Games", xaxis_title="Game Date", yaxis_title="Stat Value")
              st.plotly_chart(fig2)
