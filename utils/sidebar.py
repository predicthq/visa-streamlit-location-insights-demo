import streamlit as st
import datetime
import pytz
import requests
from utils.predicthq import get_api_key, get_predicthq_client
from utils.code_examples import get_code_example


def show_sidebar_options():
    st.sidebar.image("./static/company-logo.png")
    locations = fetch_location_insight_data()

    # Work out which location is currently selected
    index = 0

    if "location" in st.session_state:
        for idx, location in enumerate(locations):
            if st.session_state["location"]["id"] == location["id"]:
                index = idx
                break

    location = st.sidebar.selectbox(
        "Location",
        locations,
        index=index,
        format_func=lambda x: x["name"],
        help="Select the location.",
        disabled=get_api_key() is None,
        key="location",
    )

    # Prepare the date range (today + 30d as the default)
    tz = pytz.timezone(location["tz"])
    today = datetime.datetime.now(tz).date()
    date_options = [
        {
            "id": "next_7_days",
            "name": "Next 7 days",
            "date_from": today,
            "date_to": today + datetime.timedelta(days=7),
        },
        {
            "id": "next_30_days",
            "name": "Next 30 days",
            "date_from": today,
            "date_to": today + datetime.timedelta(days=30),
        },
        {
            "id": "next_90_days",
            "name": "Next 90 days",
            "date_from": today,
            "date_to": today + datetime.timedelta(days=90),
        },
    ]

    # Work out which date is currently selected
    index = 2  # Default to next 90 days

    if "daterange" in st.session_state:
        for idx, date_option in enumerate(date_options):
            if st.session_state["daterange"]["id"] == date_option["id"]:
                index = idx
                break

    st.sidebar.selectbox(
        "Date Range",
        date_options,
        index=index,
        format_func=lambda x: x["name"],
        help="Select the date range for fetching event data.",
        disabled=get_api_key() is None,
        key="daterange",
    )

    # Use an appropriate radius unit depending on location
    radius_unit = location["radius_unit"]
    st.session_state.suggested_radius = location

    # Allow changing the radius if needed (default to suggested radius)
    # The Suggested Radius API is used to determine the best radius to use for the given location and industry
    st.session_state.suggested_radius_slider = st.sidebar.slider(
        f"Suggested Radius around the location ({radius_unit})",
        0.0,
        10.0,
        st.session_state.suggested_radius.get("radius", 2.0),
        0.1,
        help="[Suggested Radius Docs](https://docs.predicthq.com/resources/suggested-radius)",
        key="radius",
    )


def fetch_location_insight_data():

    r = requests.get(
        url="https://api.predicthq.com/saved-locations?limit=10&offset=0&q=&sort=name&subscription_valid_types=events",
        headers={
            "Authorization": f"Bearer {get_api_key()}",
            "Accept": "application/json",
        },
        allow_redirects=False,
    )
    json = r.json()
    results = []
    for location_insight in json["locations"]:
        results.append({"id":location_insight["location_id"],
                        "name": location_insight["name"],
                        "address": location_insight["formatted_address"],
                        "lat": location_insight["geojson"]["geometry"]["coordinates"][1],
                        "lon": location_insight["geojson"]["geometry"]["coordinates"][0],
                        "radius_unit": location_insight["geojson"]["properties"]["radius_unit"],
                        "radius": location_insight["geojson"]["properties"]["radius"],
                        "tz": "America/New_York",})
    
    return results


def show_map_sidebar_code_examples():
    st.sidebar.markdown("## Code examples")

    # The code examples are saved as markdown files in docs/code_examples
    examples = [
        {"name": "Suggested Radius API", "filename": "suggested_radius_api"},
        {
            "name": "Features API (Predicted Attendance aggregation)",
            "filename": "features_api",
        },
        {"name": "Count of Events", "filename": "count_api"},
        {"name": "Demand Surge API", "filename": "demand_surge_api"},
        {"name": "Search Events", "filename": "events_api"},
        {"name": "Python SDK for PredictHQ APIs", "filename": "python_sdk"},
    ]

    for example in examples:
        with st.sidebar.expander(example["name"]):
            st.markdown(get_code_example(example["filename"]))

    st.sidebar.caption(
        "Get the code for this app at [GitHub]("+st.secrets["github_repo"]+")"
    )
