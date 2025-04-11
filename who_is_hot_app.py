# who_is_hot_compare_app.py (fully upgraded)

import streamlit as st
import plotly.express as px
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players
from nba_api.stats.endpoints import playercareerstats
import pandas as pd
import requests
import time

# Helper to get player ID
def get_player_id(name):
    player_dict = players.get_players()
    for player in player_dict:
        if player['full_name'].lower() == name.lower():
            return player['id']
    return None

# Helper to get game log data
def get_recent_stats(player_id, num_games):
    time.sleep(0.5)
    gamelog = playergamelog.PlayerGameLog(player_id=player_id, season='2023')
    df = gamelog.get_data_frames()[0]
    df = df.head(num_games)[['GAME_DATE', 'PTS', 'REB', 'AST', 'FG_PCT']]
    df = df[::-1]
    return df

# Helper to get player image URL from NBA CDN
def get_player_image_url(name):
    formatted_name = name.lower().replace(" ", "_")
    return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{formatted_name}.png"

def get_season_averages(player_id):
    career = playercareerstats.PlayerCareerStats(player_id=player_id)
    df = career.get_data_frames()[0]
    latest_season = df[df["SEASON_ID"] == "2023-24"]
    if not latest_season.empty:
        return {
            "PTS": latest_season.iloc[0]["PTS"],
            "REB": latest_season.iloc[0]["REB"],
            "AST": latest_season.iloc[0]["AST"],
            "FG_PCT": latest_season.iloc[0]["FG_PCT"]
        }
    else:
        return None

# App UI
st.title("🏀 Who's Hot?")
st.markdown("Compare one or two NBA players over a number of recent games.")

col1, col2 = st.columns(2)

with col1:
    player1_name = st.text_input("Player 1 Name", value="LeBron James")
with col2:
    player2_name = st.text_input("Player 2 Name (Optional)", value="Stephen Curry")

num_games = st.slider("Number of Recent Games", min_value=1, max_value=20, value=5)

# Stat selector
selected_stats = st.multiselect(
    "Select which stats to include in the graph:",
    ["PTS", "REB", "AST", "FG_PCT"],
    default=["PTS", "REB", "AST", "FG_PCT"]
)

if st.button("Show Comparison"):
    if player1_name:
        player1_id = get_player_id(player1_name)
        player2_id = get_player_id(player2_name) if player2_name else None

        if not player1_id:
            st.error(f"❌ Player not found: {player1_name}")
        elif player2_name and not player2_id:
            st.error(f"❌ Player not found: {player2_name}")
        else:
            with st.spinner("Fetching stats..."):
                stats1 = get_recent_stats(player1_id, num_games)
                stats1["Player"] = player1_name

                if player2_id:
                    stats2 = get_recent_stats(player2_id, num_games)
                    stats2["Player"] = player2_name
                    all_stats = pd.concat([stats1, stats2])
                else:
                    all_stats = stats1

                # Player Images
                st.subheader("Player Headshots")
                img_col1, img_col2 = st.columns(2)
                with img_col1:
                    st.image(get_player_image_url(player1_name), caption=player1_name, use_column_width=True)
                if player2_id:
                    with img_col2:
                        st.image(get_player_image_url(player2_name), caption=player2_name, use_column_width=True)

                # Data Table
                st.subheader("Game Stats")
                st.dataframe(all_stats)

                # Averages
                st.subheader("📊 Stat Averages")
                avg_stats = all_stats.groupby("Player")[selected_stats].mean().round(2)
                st.table(avg_stats)
                st.subheader("📊 Heating Up or Cooling Down?")

                threshold = 0.05  # 5% margin
                
                for player in avg_stats.index:
                    pid = get_player_id(player)
                    season_avg = get_season_averages(pid)
                
                    if season_avg:
                        comments = []
                        for stat in selected_stats:
                            recent = avg_stats.loc[player, stat]
                            season = season_avg[stat]
                            if season == 0:
                                continue  # skip stat if season value is 0
                            diff = (recent - season) / season
                            if diff > threshold:
                                comments.append(f"⬆️ {stat} (heating up)")
                            elif diff < -threshold:
                                comments.append(f"⬇️ {stat} (cooling down)")
                            else:
                                comments.append(f"➖ {stat} (stable)")
                
                        summary = ", ".join(comments)
                        st.markdown(f"**{player}** is: {summary}")
                    else:
                        st.warning(f"Could not load season averages for {player}")

                # Plotting
                plot_df = all_stats.melt(
                    id_vars=["GAME_DATE", "Player"],
                    value_vars=selected_stats,
                    var_name="Stat",
                    value_name="Value")

                fig = px.line(
                    plot_df,
                    x="GAME_DATE",
                    y="Value",
                    color="Player",
                    line_dash="Stat",
                    markers=True,
                    title=f"{player1_name} vs {player2_name}" if player2_id else f"{player1_name} - Stats Over Last {num_games} Games")
                fig.update_layout(xaxis_title="Game Date", yaxis_title="Stat Value", hovermode="x unified")
                st.plotly_chart(fig)
