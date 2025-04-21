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
    filtered_chars = [] # start with an empty list
    for ch in decomposed:  # check each character
        if not unicodedata.combining(ch):   # if it’s not an accent mark
            filtered_chars.append(ch)    # keep the character
    without_accents = "".join(filtered_chars)   # join back into a string
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
def get_recent_stats(player_id, num_games):  # grab the last `num_games` for a player
    time.sleep(0.5)  # pause so we don’t hit the NBA API too fast

    # decide which season string to use (e.g. “2024” for 2024‑25 if it’s before October)
    current_season = (
        str(datetime.now().year - 1)  # if we’re before Oct, we’re still in last year’s season
        if datetime.now().month < 10 
        else str(datetime.now().year))  # otherwise use this year

    # pull all regular‑season games for that season
    reg_df = playergamelog.PlayerGameLog(
        player_id=player_id,
        season=current_season,
        season_type_all_star="Regular Season").get_data_frames()[0]  # get the regular season DataFrame

    # pull all playoff games for the same season
    po_df = playergamelog.PlayerGameLog(
        player_id=player_id,
        season=current_season,
        season_type_all_star="Playoffs").get_data_frames()[0]  # get the playoffs DataFrame

    # stack regular + playoff logs together
    all_games = pd.concat([reg_df, po_df], ignore_index=True)

    # turn the date column into real datetime objects
    all_games['GAME_DATE'] = pd.to_datetime(all_games['GAME_DATE'])

    # sort so the most recent games are at the top
    all_games = all_games.sort_values('GAME_DATE', ascending=False)

    # pick only the columns we care about and grab the newest `num_games`
    latest = all_games[['GAME_DATE', 'PTS', 'REB', 'AST', 'FG_PCT']].head(num_games)

    # flip them back into chronological order and reset the index
    stats_table = latest.sort_values('GAME_DATE').reset_index(drop=True)

    # format the dates as “Apr 11, 2025” (no time)
    stats_table['GAME_DATE'] = stats_table['GAME_DATE'].dt.strftime('%b %d, %Y')

    # make dates plain strings so the chart shows every label
    stats_table['GAME_DATE'] = stats_table['GAME_DATE'].astype(str)

    return stats_table  # send back the cleaned, sorted, and formatted table




# Gets NBA player headshot URL from player ID
def get_player_image_url(player_id):
    return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"  # Direct URL to NBA headshots

# Heating Up or Cooling Down Analysis
def analyze_trend(player_stats, player_name, selected_stats, recent_check):  # Define function to analyze a player’s performance trend
    if len(player_stats) < recent_check + 1:  # Check if we have at least `recent_check + 1` games worth of data
        st.warning(f"Not enough games to analyze trend for {player_name}.")  # Warn user in Streamlit
        return  # Exit early if insufficient data

    # Split into recent vs. baseline games
    recent_games = player_stats.tail(recent_check)  # Take the last `recent_check` rows as the recent games
    baseline_games = player_stats.head(len(player_stats) - recent_check)  # The rest are baseline games

    # Calculate average for each group of games
    recent_avg = recent_games[selected_stats].mean()  # Compute mean of each selected stat over recent games
    baseline_avg = baseline_games[selected_stats].mean()  # Compute mean of each selected stat over baseline games
    baseline_std = baseline_games[selected_stats].std()  # Compute standard deviation for baseline stats

    threshold = 0.05  # Define a 5% threshold for change (not used in this version)
    comments = []  # Initialize list to collect trend comments

    # Loop through each selected stat
    for stat in selected_stats:
        baseline_val = baseline_avg[stat]  # Baseline average value for this stat
        std_val = baseline_std[stat]       # Baseline standard deviation for this stat

        if pd.isna(std_val) or std_val == 0:  # Skip if std dev is NaN or zero (cannot compare)
            continue  # Move to next stat

        diff = recent_avg[stat] - baseline_val  # Difference between recent and baseline averages

        if diff > std_val:  # If increase is greater than one std dev
            comments.append(f"{stat}: Heating Up 🔥")  # Mark as trending up
        elif diff < -std_val:  # If decrease is greater than one std dev
            comments.append(f"{stat}: Cooling Down ❄️")  # Mark as trending down
        else:
            comments.append(f"{stat}: Stable")  # Otherwise, consider the stat stable

    # Output results
    st.subheader(f"{player_name}'s Trend Analysis")  # Add a subheader in Streamlit
    for comment in comments:  # Iterate over generated comments
        st.markdown(f"- {comment}")  # Display each comment as a markdown bullet



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

