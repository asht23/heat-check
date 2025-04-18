# Tools we need for the app
import streamlit as st  # For creating the web app
import pandas as pd  # For handling and analyzing data tables
import plotly.express as px  # For building visual graphs
import time  # For slowing down API requests to avoid errors
from datetime import datetime  # Used to determine the current NBA season
import unicodedata # # lets us break accented letters apart so we can drop the accents
import re # gives us tools to find and replace text patterns for cleaning names

# NBA API Modules
from nba_api.stats.static import players  # Get the list of NBA players to find player IDs
from nba_api.stats.endpoints import playergamelog  # Used to pull game-by-game stats for a player


# Converting Player Name to NBA ID (used to pull their stats)
def normalize_name(name):
    # 1. Trim spaces
    name = name.strip()
    # 2. Remove accents
    decomposed = unicodedata.normalize('NFKD', name)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    # 3. Lowercase
    lowercase = without_accents.lower()
    # 4. Remove punctuation
    cleaned = re.sub(r"[^a-z0-9\s]", "", lowercase) # matches any character that is not a lowercase letter, digit, or space and deletes them
    # 5. Collapse spaces
    result = re.sub(r"\s+", " ", cleaned).strip() #\s+ will match runs of spaces, "" replaces wtih one space, .strip() removes space

    return result
  
def find_player_id(name):
  all_players = players.get_players()  # Get all NBA players
  for player in all_players:
    if normalize_name(player["full_name"]) == normalize_name(name):
      return player['id'], player["full_name"]  # Return the matching player ID
  else:
    return None, None # If not found, return None

# Pulling Recent Game Stats for a Player
def get_recent_stats(player_id, num_games):
  time.sleep(0.5)  # Wait to avoid hitting API limits

  # April 2025 is still the 2024-25 season so use 2024 
  current_season = str(datetime.now().year - 1) if datetime.now().month < 10 else str(datetime.now().year)

  # Using the nba_api to fetch game-by-game stats for a specific player and season.
  gamelog = playergamelog.PlayerGameLog(player_id=player_id, season=current_season)
  stats_table = gamelog.get_data_frames()[0]  # Get the first (and only) table from the response
  stats_table = stats_table.head(num_games)[['GAME_DATE','PTS', 'REB', 'AST', 'FG_PCT']]  # Trim and reorder columns
  stats_table = stats_table[::-1]  # Flips from newest -> oldest to oldest -> newest

  return stats_table  # Return the cleaned stats table

# Gets NBA player headshot URL from player ID
def get_player_image_url(player_id):
    return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"  # Direct URL to NBA headshots

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
    baseline_std = baseline_games[selected_stats].std()  # Get standard deviation


    threshold = 0.05  # 5% change to count as hot/cold
    comments = []  # Collect trend comments for each stat

    # Loop through each selected stat
    for stat in selected_stats:
      baseline_val = baseline_avg[stat]
      std_val = baseline_std[stat]
    
      if pd.isna(std_val) or std_val == 0:
        continue  # skip if we can't calculate std dev

      diff = recent_avg[stat] - baseline_val

      if diff > std_val:
        comments.append(f"{stat}: Heating Up 🔥")
      elif diff < -std_val:
        comments.append(f"{stat}: Cooling Down ❄️")
      else:
        comments.append(f"{stat}: Stable")


    # Output results
    st.subheader(f"{player_name}'s Trend Analysis")
    for comment in comments:
        st.markdown(f"- {comment}")


#Building Streamlit UI Inputs

# Title and Description
st.title("NBA Player Heat Check?🔥")  # Main heading for the app
st.markdown("See what NBA player's are Hot🔥 or Cold❄️ based on recent performances!")  # Subheading/description

# Player name inputs
col1, col2 = st.columns(2)  # Create two side-by-side columns

with col1:
    player1 = st.text_input("Enter Player 1's Name")  # Input box for Player 1

with col2:
    player2 = st.text_input("Enter Player 2's Name (Optional)")  # Optional input for Player 2

# How many recent games to look at
num_games = st.slider("How many recent games do you want to analyze?", min_value=1, max_value=20, value=5)

# What counts as 'recent' for hot/cold check
recent_check = st.slider(
    "Select how many recent games to analyze for 'Hot 🔥 or Cold ❄️?'",
    min_value=1,
    max_value=num_games - 1,
    value=min(3, num_games - 1))

# Stat selector buttons
selected_stats = st.multiselect(
    "Pick which stats to graph",
    options=["PTS", "REB", "AST", "FG_PCT"],
    default=["PTS", "REB", "AST", "FG_PCT"])

# Main action button
if st.button('Analyze'):
 
  original_name1 = None
  original_name2 = None

  # playerX_id tells you if there’s a valid NBA player,
  # original_nameX holds the official spelling to label tables and charts 
    
  if player1:
    player1_id, original_name1 = find_player_id(player1)  # Gets player 1's ID 

    if player2:
      player2_id, original_name2 = find_player_id(player2)  # Gets player 2's ID
    else:
      player2_id = None  # Sets player 2 to None so we know only one player is being analyzed

    if player1_id is None:  # Show error if Player 1 name wasn't found
      st.error(f"❌ Player not found: {player1}")
    elif player2 and player2_id is None:  # Show error if Player 2 name was entered but not found
      st.error(f"❌ Player not found: {player2}")
    else:  # if both players are valid then continue
      with st.spinner("Pulling game stats..."):  # Show loading spinner while data loads
        player1_stats = get_recent_stats(player1_id, num_games)  # Step 1: Get recent game stats for Player 1
        player1_stats["Player"] = original_name1  # Step 2: Add a "Player" column to label the data

        if player2_id:
          player2_stats = get_recent_stats(player2_id, num_games)  # Get stats for Player 2
          player2_stats["Player"] = original_name2  # Label Player 2's stats

      # Show player headshots side-by-side
      img_col1, img_col2 = st.columns(2)  # Two side-by-side image columns

      with img_col1:
          st.image(get_player_image_url(player1_id), caption=player1, use_container_width=True)  # Display Player 1 photo

      if player2_id:
          with img_col2:
              st.image(get_player_image_url(player2_id), caption=player2, use_container_width=True)  # Display Player 2 photo

      # Show player stats in side by side
      stats_col1, stats_col2 = st.columns(2)

      with stats_col1:
          st.subheader(f"{original_name1}'s Stats")  # Table heading for Player 1
          st.dataframe(player1_stats)  # Table for Player 1 stats
      if player2_id:
          with stats_col2:
              st.subheader(f"{original_name2}'s Stats")  # Table heading for Player 2
              st.dataframe(player2_stats)  # Table for Player 2 stats

      # Trend Analysis
      analyze_trend(player1_stats, original_name1, selected_stats, recent_check)  # Run trend logic for Player 1
      if player2_id:
          analyze_trend(player2_stats, original_name2, selected_stats, recent_check)  # Run trend logic for Player 2

      # Plotting each player's stats
      plot_col1, plot_col2 = st.columns(2)  # Create side-by-side graph columns

      with plot_col1:
          st.subheader(f"{original_name1}'s Stat Trends")  # Heading above Player 1 graph
          plot_df1 = player1_stats.melt(id_vars="GAME_DATE", value_vars=selected_stats, var_name="Stat", value_name="Value")  # Reformat Player 1 stats
          fig1 = px.bar(plot_df1, x="GAME_DATE", y="Value", color="Stat", barmode="group")  # Build bar chart for Player 1
          fig1.update_layout(title=f"{original_name1} - Last {num_games} Games", xaxis_title="Game Date", yaxis_title="Stat Value")  # Customize labels
          st.plotly_chart(fig1)  # Show Player 1 chart 
      
            # Extra FG% Line Chart for Player 1
      if "FG_PCT" in selected_stats and "FG_PCT" in player1_stats.columns:
          st.subheader(f"{original_name1}'s Field Goal Percentage Trend")
          fg_chart1 = px.line(
              player1_stats,
              x="GAME_DATE",
              y="FG_PCT",
              title=f"{original_name1} - FG% Over Last {num_games} Games",
              markers=True)
          fg_chart1.update_layout(xaxis_title="Game Date", yaxis_title="FG%", hovermode="x unified")
          st.plotly_chart(fg_chart1)


      if player2_id:
          with plot_col2:
              st.subheader(f"{original_name2}'s Stat Trends")  # Heading above Player 2 graph
              plot_df2 = player2_stats.melt(id_vars="GAME_DATE", value_vars=selected_stats, var_name="Stat", value_name="Value")  # Reformat Player 2 stats
              fig2 = px.bar(plot_df2, x="GAME_DATE", y="Value", color="Stat", barmode="group")  # Build bar chart for Player 2
              fig2.update_layout(title=f"{original_name2} - Last {num_games} Games", xaxis_title="Game Date", yaxis_title="Stat Value")  # Customize labels
              st.plotly_chart(fig2)  # Show Player 2 chart
                    # Extra FG% Line Chart for Player 2
          if "FG_PCT" in selected_stats and "FG_PCT" in player2_stats.columns:
              st.subheader(f"{original_name2}'s Field Goal Percentage Trend")
              fg_chart2 = px.line(
                  player2_stats,
                  x="GAME_DATE",
                  y="FG_PCT",
                  title=f"{original_name2} - FG% Over Last {num_games} Games",
                  markers=True)
              fg_chart2.update_layout(xaxis_title="Game Date", yaxis_title="FG%", hovermode="x unified")
              st.plotly_chart(fg_chart2)

